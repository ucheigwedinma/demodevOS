"""
BOQ-Driven WBS Auto-Generation Engine
======================================

Route B: BOQ → auto-generate WBS + quantities → schedule

Takes a BillOfMaterials, maps its items to planning templates via
BoqCategoryMapping, calculates durations from quantities ÷ production rates,
and creates a ProjectBlueprint with phases, activities, tasks, and dependencies.
"""
import logging
import math
from decimal import Decimal

from django.utils import timezone

logger = logging.getLogger(__name__)


def generate_blueprint_from_boq(bom, user=None):
    """
    Create a ProjectBlueprint from a BillOfMaterials.

    1. Read BOM items grouped by category/section
    2. Map each category to a template phase via BoqCategoryMapping
    3. For each mapped phase, copy its activities and task templates
    4. Calculate task durations from BOQ quantity ÷ production rate
    5. Split large quantities into zone-based tasks
    6. Wire up dependencies from template definitions
    7. Return the created blueprint

    Returns: (blueprint, summary_dict)
    """
    from apps.projects.blueprint_models import (
        BlueprintActivity,
        BlueprintDependency,
        BlueprintPhase,
        BlueprintTask,
        ProjectBlueprint,
    )
    from apps.settings.models import TemplateActivity, TemplateDependency

    from .models import BoqCategoryMapping, BOMItem

    org = bom.organization
    items = BOMItem.objects.filter(bom=bom).order_by("sort_order")

    if not items.exists():
        raise ValueError("BOM has no items to generate a plan from.")

    # Group items by category
    category_items = {}
    for item in items:
        cat = (item.category or item.section or "Uncategorized").strip()
        category_items.setdefault(cat, []).append(item)

    # Load mappings for this org
    mappings = {
        m.boq_category.lower(): m
        for m in BoqCategoryMapping.objects.filter(
            organization=org,
        ).select_related("template_phase", "template_phase__template")
    }

    # Create blueprint
    blueprint = ProjectBlueprint.objects.create(
        organization=org,
        name=f"Auto-Plan — {bom.name}",
        description=(
            f"Auto-generated from BOM '{bom.bom_number} — {bom.name}'. "
            f"{items.count()} items across {len(category_items)} categories."
        ),
        status="draft",
        source_bom=bom,
        created_by=user,
    )

    summary = {
        "phases_created": 0,
        "activities_created": 0,
        "tasks_created": 0,
        "dependencies_created": 0,
        "unmapped_categories": [],
        "items_processed": 0,
    }

    phase_map = {}  # template_phase_id → BlueprintPhase
    activity_map = {}  # template_activity_id → BlueprintActivity

    for cat_name, cat_items in category_items.items():
        mapping = mappings.get(cat_name.lower())

        if not mapping:
            # No mapping — create a generic phase for unmapped items
            summary["unmapped_categories"].append(cat_name)
            phase = _get_or_create_phase(
                blueprint, phase_map, None, cat_name, len(phase_map),
            )
            # Create a single activity with items as tasks
            activity = BlueprintActivity.objects.create(
                phase=phase,
                name=cat_name,
                wbs_code=f"{phase.sort_order + 1}.1",
                sort_order=0,
            )
            summary["activities_created"] += 1

            for idx, item in enumerate(cat_items):
                BlueprintTask.objects.create(
                    activity=activity,
                    name=item.material_name,
                    description=f"Qty: {item.quantity} {item.unit_of_measure}",
                    assigned_role="TBD",
                    priority="medium",
                    sort_order=idx,
                    estimated_duration_days=1,
                    boq_quantity=item.quantity,
                    boq_unit=item.unit_of_measure,
                )
                summary["tasks_created"] += 1
                summary["items_processed"] += 1
            continue

        # Mapped category — use the template phase structure
        tmpl_phase = mapping.template_phase
        phase = _get_or_create_phase(
            blueprint, phase_map, tmpl_phase.id,
            tmpl_phase.name, tmpl_phase.sort_order,
            duration_days=tmpl_phase.duration_days,
            weight=tmpl_phase.weight,
        )

        # Copy template activities
        tmpl_activities = TemplateActivity.objects.filter(
            phase=tmpl_phase,
        ).prefetch_related("task_templates").order_by("sort_order")

        for tmpl_act in tmpl_activities:
            bp_activity = _get_or_create_activity(
                phase, activity_map, tmpl_act,
            )
            if bp_activity._just_created:
                summary["activities_created"] += 1

            # For each BOQ item in this category, create tasks from task templates
            for item in cat_items:
                for tt in tmpl_act.task_templates.filter(status="active").order_by("sort_order"):
                    duration = _calculate_duration(
                        item.quantity, tt.production_rate, mapping.default_production_rate,
                        tt.standard_duration_hours,
                    )
                    # Check if we need to split
                    split_count = 1
                    if mapping.split_threshold and item.quantity > mapping.split_threshold:
                        split_count = math.ceil(float(item.quantity) / float(mapping.split_threshold))

                    for zone_idx in range(split_count):
                        zone_qty = (
                            item.quantity / split_count
                            if split_count > 1
                            else item.quantity
                        )
                        zone_suffix = f" (Zone {zone_idx + 1})" if split_count > 1 else ""
                        task_name = f"{tt.name} — {item.material_name}{zone_suffix}"

                        BlueprintTask.objects.create(
                            activity=bp_activity,
                            name=task_name,
                            description=tt.description or "",
                            assigned_role=tt.assigned_role or "",
                            priority=tt.priority or "medium",
                            sort_order=summary["tasks_created"],
                            estimated_duration_days=max(1, int(duration / split_count)) if split_count > 1 else duration,
                            boq_quantity=zone_qty,
                            boq_unit=item.unit_of_measure,
                            boq_item_id=item.id,
                            crew_size=tt.crew_size or 1,
                            equipment_type=tt.equipment_type or "",
                        )
                        summary["tasks_created"] += 1

                summary["items_processed"] += 1

        # Copy template dependencies within this phase
        tmpl_deps = TemplateDependency.objects.filter(
            template=tmpl_phase.template,
            predecessor_activity__phase=tmpl_phase,
            successor_activity__phase=tmpl_phase,
        )
        for dep in tmpl_deps:
            pred_bp = activity_map.get(dep.predecessor_activity_id)
            succ_bp = activity_map.get(dep.successor_activity_id)
            if pred_bp and succ_bp:
                BlueprintDependency.objects.get_or_create(
                    blueprint=blueprint,
                    predecessor_activity=pred_bp,
                    successor_activity=succ_bp,
                    defaults={
                        "dependency_type": dep.dependency_type,
                        "lag_hours": dep.lag_hours,
                    },
                )
                summary["dependencies_created"] += 1

    # Wire up cross-phase dependencies based on phase sort order
    sorted_phases = list(
        BlueprintPhase.objects.filter(blueprint=blueprint).order_by("sort_order")
    )
    for i in range(1, len(sorted_phases)):
        # Last activity of prev phase → first activity of current phase
        prev_last = BlueprintActivity.objects.filter(phase=sorted_phases[i - 1]).order_by("-sort_order").first()
        curr_first = BlueprintActivity.objects.filter(phase=sorted_phases[i]).order_by("sort_order").first()
        if prev_last and curr_first:
            BlueprintDependency.objects.get_or_create(
                blueprint=blueprint,
                predecessor_activity=prev_last,
                successor_activity=curr_first,
                defaults={"dependency_type": "FS", "lag_hours": 0},
            )
            summary["dependencies_created"] += 1

    logger.info(
        "Blueprint %s generated from BOM %s: %s",
        blueprint.pk, bom.pk, summary,
    )
    return blueprint, summary


def _get_or_create_phase(blueprint, phase_map, tmpl_phase_id, name, sort_order, duration_days=None, weight=1.0):
    """Get existing or create a new BlueprintPhase."""
    from apps.projects.blueprint_models import BlueprintPhase

    key = tmpl_phase_id or name
    if key in phase_map:
        return phase_map[key]

    phase = BlueprintPhase.objects.create(
        blueprint=blueprint,
        name=name,
        sort_order=sort_order,
        duration_days=duration_days or 30,
        weight=weight,
    )
    phase_map[key] = phase
    return phase


def _get_or_create_activity(phase, activity_map, tmpl_activity):
    """Get existing or create a new BlueprintActivity from a template activity."""
    from apps.projects.blueprint_models import BlueprintActivity

    if tmpl_activity.id in activity_map:
        existing = activity_map[tmpl_activity.id]
        existing._just_created = False
        return existing

    activity = BlueprintActivity.objects.create(
        phase=phase,
        name=tmpl_activity.name,
        wbs_code=tmpl_activity.wbs_code or "",
        sort_order=tmpl_activity.sort_order,
    )
    activity._just_created = True
    activity_map[tmpl_activity.id] = activity
    return activity


def _calculate_duration(quantity, production_rate, fallback_rate, standard_hours):
    """
    Calculate task duration in days.

    Priority:
    1. quantity ÷ production_rate (if both exist)
    2. quantity ÷ fallback_rate (if production_rate missing)
    3. standard_hours ÷ 9 (convert hours to days at 9hr/day)
    4. Default: 1 day
    """
    qty = float(quantity or 0)

    if qty > 0 and production_rate and float(production_rate) > 0:
        return max(1, math.ceil(qty / float(production_rate)))

    if qty > 0 and fallback_rate and float(fallback_rate) > 0:
        return max(1, math.ceil(qty / float(fallback_rate)))

    if standard_hours and float(standard_hours) > 0:
        return max(1, math.ceil(float(standard_hours) / 9))

    return 1

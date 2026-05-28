"""
Template-to-Project Instantiation Service.

Bridges the Project Planner (template engine) with live project execution.

When a project is created from a template, this service:
1. Creates phases from template phases (with WBS activities)
2. Creates tasks from task templates linked to activities
3. Applies dependencies from template dependencies
4. Seeds budget from the committed scenario baseline
5. Populates schedule from template schedule settings
6. Seeds mobilization equipment/crew requirements from resource model

This closes the Plan → Execute loop completely, ensuring the planner's
blueprint drives the entire downstream construction workflow.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

logger = logging.getLogger(__name__)


def instantiate_project_from_template(project, template_id: int) -> dict:
    """
    Populate a newly created project from a project template.

    Returns a summary dict of what was created.
    """
    from apps.projects.models import (
        Project,
        ProjectMilestone,
        ProjectPhase,
        ProjectPhaseDependency,
        ProjectSiteMobilization,
        ProjectTask,
    )
    from apps.settings.models import ProjectTemplate, TemplatePlanScenario, TemplateScheduleSettings

    try:
        template = ProjectTemplate.objects.prefetch_related(
            "phases__activities__task_templates",
            "phases__milestones",
            "dependencies",
        ).get(pk=template_id)
    except ProjectTemplate.DoesNotExist:
        logger.warning("Template %s not found for project %s", template_id, project.pk)
        return {"error": "Template not found"}

    org = project.organization
    start_date = project.start_date or project.construction_start_date or timezone.localdate()
    summary = {
        "phases_created": 0,
        "tasks_created": 0,
        "milestones_created": 0,
        "dependencies_created": 0,
        "budget_seeded": False,
        "schedule_applied": False,
        "mobilization_seeded": False,
    }

    # --- 1. Create phases from template phases ---
    phase_map = {}  # template_phase_id → ProjectPhase
    activity_map = {}  # template_activity_id → activity data
    task_map = {}  # template_task_id → ProjectTask
    day_cursor = 0

    for tmpl_phase in template.phases.order_by("sort_order"):
        phase_start = start_date + timedelta(days=day_cursor)
        phase_duration = tmpl_phase.duration_days or 30
        phase_end = phase_start + timedelta(days=phase_duration)

        phase = ProjectPhase.objects.create(
            organization=org,
            project=project,
            name=tmpl_phase.name,
            description=tmpl_phase.description,
            sort_order=tmpl_phase.sort_order,
            status=ProjectPhase.Status.NOT_STARTED,
            planned_start_date=phase_start,
            planned_end_date=phase_end,
            weight=tmpl_phase.weight,
        )
        phase_map[tmpl_phase.id] = phase
        summary["phases_created"] += 1

        # --- Create milestones from template milestones ---
        for tmpl_ms in tmpl_phase.milestones.order_by("sort_order"):
            ms_date = phase_start + timedelta(days=tmpl_ms.days_from_phase_start or phase_duration)
            ProjectMilestone.objects.create(
                organization=org,
                phase=phase,
                name=tmpl_ms.name,
                description=tmpl_ms.description,
                sort_order=tmpl_ms.sort_order,
                target_date=ms_date,
            )
            summary["milestones_created"] += 1

        # --- Create tasks from activities → task templates ---
        for tmpl_activity in tmpl_phase.activities.order_by("sort_order"):
            activity_map[tmpl_activity.id] = {
                "phase": phase,
                "wbs_code": tmpl_activity.wbs_code,
                "duration": tmpl_activity.estimated_duration_days or 1,
            }

            for tmpl_task in tmpl_activity.task_templates.order_by("sort_order"):
                task_start = phase_start + timedelta(days=tmpl_activity.sort_order * 2)
                task = ProjectTask.objects.create(
                    organization=org,
                    phase=phase,
                    name=tmpl_task.name,
                    description=tmpl_task.description,
                    assigned_role=tmpl_task.assigned_role,
                    priority=tmpl_task.priority,
                    sort_order=tmpl_task.sort_order,
                    status=ProjectTask.Status.NOT_STARTED,
                    start_date=task_start,
                    due_date=task_start + timedelta(
                        days=int(tmpl_task.standard_duration_hours / 9) if tmpl_task.standard_duration_hours else 1
                    ),
                )
                task_map[tmpl_task.id] = task
                summary["tasks_created"] += 1

                # If task is marked as milestone, create a project milestone
                if tmpl_task.is_milestone:
                    ProjectMilestone.objects.create(
                        organization=org,
                        phase=phase,
                        name=f"Milestone: {tmpl_task.name}",
                        target_date=task.due_date,
                        sort_order=1000 + tmpl_task.sort_order,
                    )
                    summary["milestones_created"] += 1

        day_cursor += phase_duration

    # --- 2. Apply dependencies ---
    for tmpl_dep in template.dependencies.all():
        from_phase = None
        to_phase = None

        if tmpl_dep.from_activity_id and tmpl_dep.from_activity_id in activity_map:
            from_phase = activity_map[tmpl_dep.from_activity_id]["phase"]
        if tmpl_dep.to_activity_id and tmpl_dep.to_activity_id in activity_map:
            to_phase = activity_map[tmpl_dep.to_activity_id]["phase"]

        if from_phase and to_phase and from_phase.id != to_phase.id:
            # Create phase-level dependency
            if not ProjectPhaseDependency.objects.filter(
                predecessor=from_phase, successor=to_phase
            ).exists():
                ProjectPhaseDependency.objects.create(
                    organization=org,
                    predecessor=from_phase,
                    successor=to_phase,
                    dependency_type=tmpl_dep.dependency_type.upper(),
                    lag_days=int(tmpl_dep.lag_hours / 24) if tmpl_dep.lag_hours else 0,
                )
                summary["dependencies_created"] += 1

    # --- 3. Seed budget from committed scenario baseline ---
    try:
        baseline_scenario = TemplatePlanScenario.objects.filter(
            template=template, is_baseline=True,
        ).first()

        if baseline_scenario and baseline_scenario.projected_total_cost > 0:
            if not project.budget or project.budget == Decimal("0"):
                Project.objects.filter(pk=project.pk).update(
                    budget=baseline_scenario.projected_total_cost,
                )
                summary["budget_seeded"] = True

            # Distribute budget across phases proportionally by weight
            total_weight = sum(p.weight for p in phase_map.values())
            if total_weight > 0:
                for tmpl_phase_id, phase in phase_map.items():
                    phase_budget = baseline_scenario.projected_total_cost * Decimal(str(phase.weight / total_weight))
                    if not phase.planned_budget or phase.planned_budget == Decimal("0"):
                        phase.planned_budget = phase_budget
                        phase.save(update_fields=["planned_budget", "updated_at"])
    except Exception:
        logger.debug("Budget seeding skipped", exc_info=True)

    # --- 4. Apply schedule settings ---
    try:
        sched = TemplateScheduleSettings.objects.filter(template=template).first()
        if sched:
            # Apply duration scalar to project target end date
            scalar = float(sched.duration_scalar_pct or 100) / 100
            total_days = int(day_cursor * scalar)
            target_end = start_date + timedelta(days=total_days)
            Project.objects.filter(pk=project.pk).update(
                target_end_date=target_end,
            )
            summary["schedule_applied"] = True
    except Exception:
        logger.debug("Schedule application skipped", exc_info=True)

    # --- 5. Seed mobilization from resource model ---
    try:
        mobilization, _ = ProjectSiteMobilization.objects.get_or_create(
            project=project,
            defaults={"organization": org},
        )
        # Set planned start from project start
        if not mobilization.planned_start_date:
            mobilization.planned_start_date = start_date
            mobilization.save(update_fields=["planned_start_date", "updated_at"])
            summary["mobilization_seeded"] = True
    except Exception:
        logger.debug("Mobilization seeding skipped", exc_info=True)

    # --- 6. Planner → HR: Workforce demand ---
    try:
        sched = TemplateScheduleSettings.objects.filter(template=template).first()
        resource_roles = sched.resource_roles if sched else []
        if resource_roles:
            from .models import ProjectWorkforceLog
            for role_spec in resource_roles:
                role_name = role_spec.get("role", "")
                capacity = int(role_spec.get("capacity", 1))
                if not role_name:
                    continue
                # Create one workforce demand entry per phase per role
                for _tmpl_id, phase in phase_map.items():
                    ProjectWorkforceLog.objects.create(
                        organization=org,
                        project=project,
                        trade=role_name,
                        shift="day",
                        report_date=phase.planned_start_date or start_date,
                        daily_attendance="present",
                        laborers_count=capacity if "labour" in role_name.lower() else 0,
                        skilled_count=capacity if "labour" not in role_name.lower() else 0,
                        notes=f"Auto-generated workforce demand: {capacity}x {role_name} @ ₦{role_spec.get('daily_rate', 0):,}/day",
                    )
            summary["workforce_demand_created"] = True
    except Exception:
        logger.debug("Workforce demand creation skipped", exc_info=True)

    # --- 7. Planner → Procurement: Material demand plan ---
    try:
        from apps.procurement.models import PurchaseRequisition, PurchaseRequisitionItem
        from apps.inventory.models import BOMItem

        # Gather all BOM items linked to template activities
        activity_ids = list(
            TemplateActivity.objects.filter(phase__template=template).values_list("id", flat=True)
        )
        # Check for task templates with required_materials
        task_templates = TaskTemplate.objects.filter(
            activity_id__in=activity_ids,
        ).exclude(required_materials=[])

        material_lines = []
        for tt in task_templates:
            for mat in (tt.required_materials or []):
                material_lines.append({
                    "description": mat.get("name", tt.name),
                    "quantity": Decimal(str(mat.get("quantity", 1))),
                    "unit": mat.get("unit", "ea"),
                    "unit_price": Decimal(str(mat.get("unit_cost", 0))),
                })

        if material_lines:
            pr = PurchaseRequisition.objects.create(
                organization=org,
                title=f"Material Demand — {project.name}",
                requester=user.get_full_name() if user else "System",
                project=project,
                priority="medium",
                required_date=start_date + timedelta(days=14),
                justification=f"Auto-generated material demand plan from project template '{template.name}'.",
            )
            for idx, line in enumerate(material_lines):
                PurchaseRequisitionItem.objects.create(
                    requisition=pr,
                    description=line["description"],
                    quantity=line["quantity"],
                    unit_of_measure=line["unit"],
                    estimated_unit_price=line["unit_price"],
                    sort_order=idx,
                )
            pr.recalculate_totals()
            summary["procurement_demand_created"] = True
    except Exception:
        logger.debug("Procurement demand creation skipped", exc_info=True)

    # --- 8. Notify ---
    try:
        from apps.accounts.models import UserProfile
        from apps.notifications.services import Notification, dispatch_workflow_notification

        admins = [
            p.user
            for p in UserProfile.objects.filter(
                organization=org, role="admin", user__is_active=True
            ).select_related("user")
        ]
        if admins:
            dispatch_workflow_notification(
                organization=org,
                event_key="project_instantiated_from_template",
                recipients=admins,
                fallback_title=f"Project Instantiated — {project.name}",
                fallback_message=(
                    f"Project '{project.name}' has been created from template '{template.name}'. "
                    f"{summary['phases_created']} phase(s), {summary['tasks_created']} task(s), "
                    f"{summary['milestones_created']} milestone(s), and {summary['dependencies_created']} "
                    f"dependency(ies) have been automatically configured. "
                    + ("Budget has been seeded from the baseline scenario. " if summary['budget_seeded'] else "")
                    + "The project is ready for execution planning."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
            )
    except Exception:
        logger.debug("Instantiation notification skipped", exc_info=True)

    logger.info(
        "Project %s instantiated from template %s: %s",
        project.pk, template_id, summary,
    )
    return summary


def instantiate_project_from_blueprint(blueprint, user=None) -> dict:
    """
    Commit a blueprint and create a live project from it.

    This is the primary bridge from the Project Planner to execution.
    The blueprint becomes the project's single source of truth.
    """
    from apps.projects.blueprint_models import ProjectBlueprint
    from apps.projects.models import (
        Project,
        ProjectMilestone,
        ProjectPhase,
        ProjectPhaseDependency,
        ProjectSiteMobilization,
        ProjectTask,
    )

    if blueprint.status == ProjectBlueprint.Status.COMMITTED:
        return {"error": "Blueprint is already committed."}

    org = blueprint.organization
    today = timezone.localdate()
    start_date = today

    summary = {
        "project_id": None,
        "phases_created": 0,
        "tasks_created": 0,
        "milestones_created": 0,
        "dependencies_created": 0,
        "budget_seeded": False,
    }

    # --- Create the project ---
    project = Project.objects.create(
        organization=org,
        name=blueprint.name,
        description=blueprint.description,
        status=Project.Status.PLANNING,
        start_date=start_date,
        budget=blueprint.projected_total_cost if blueprint.projected_total_cost else None,
    )
    summary["project_id"] = project.id
    summary["budget_seeded"] = bool(blueprint.projected_total_cost)

    # --- Create the kickoff (ProjectSetupConfig) record ---
    # Blueprint already provided phases, so jump straight to BoQ baseline as the
    # next step the user needs to complete.
    from apps.projects.models import ProjectSetupConfig
    ProjectSetupConfig.objects.create(
        project=project,
        current_step=ProjectSetupConfig.SetupStep.BOQ_BASELINE,
        is_complete=False,
        planned_phases=blueprint.phases.count() or 3,
        template_applied=False,
    )

    # --- Create phases ---
    phase_map = {}  # BlueprintPhase.id → ProjectPhase
    activity_map = {}  # BlueprintActivity.id → ProjectPhase (for dependency mapping)
    day_cursor = 0

    for bp_phase in blueprint.phases.order_by("sort_order"):
        phase_duration = bp_phase.duration_days or 30
        phase_start = start_date + timedelta(days=day_cursor)
        phase_end = phase_start + timedelta(days=phase_duration)

        phase = ProjectPhase.objects.create(
            organization=org,
            project=project,
            name=bp_phase.name,
            description=bp_phase.description,
            sort_order=bp_phase.sort_order,
            status=ProjectPhase.Status.NOT_STARTED,
            planned_start_date=phase_start,
            planned_end_date=phase_end,
            planned_budget=bp_phase.planned_budget,
            weight=bp_phase.weight,
        )
        phase_map[bp_phase.id] = phase
        summary["phases_created"] += 1

        # --- Create tasks from activities ---
        for bp_activity in bp_phase.activities.order_by("sort_order"):
            activity_map[bp_activity.id] = phase

            for bp_task in bp_activity.tasks.order_by("sort_order"):
                task_dur = int(bp_task.standard_duration_hours / 9) if bp_task.standard_duration_hours else 1
                task_start = phase_start + timedelta(days=bp_activity.sort_order * 2)

                task = ProjectTask.objects.create(
                    organization=org,
                    phase=phase,
                    name=bp_task.name,
                    description=bp_task.description,
                    assigned_to=bp_task.assigned_role or "",
                    priority=bp_task.priority or ProjectTask.Priority.MEDIUM,
                    sort_order=bp_task.sort_order,
                    status=ProjectTask.Status.PENDING,
                    due_date=task_start + timedelta(days=task_dur),
                )
                summary["tasks_created"] += 1

                # Milestone tasks
                if bp_task.is_milestone:
                    ProjectMilestone.objects.create(
                        organization=org,
                        phase=phase,
                        name=f"Milestone: {bp_task.name}",
                        target_date=task.due_date,
                        sort_order=1000 + bp_task.sort_order,
                    )
                    summary["milestones_created"] += 1

        day_cursor += phase_duration

    # --- Create dependencies ---
    for bp_dep in blueprint.dependencies.all():
        from_phase = activity_map.get(bp_dep.from_activity_id) if bp_dep.from_activity_id else None
        to_phase = activity_map.get(bp_dep.to_activity_id) if bp_dep.to_activity_id else None

        if from_phase and to_phase and from_phase.id != to_phase.id:
            if not ProjectPhaseDependency.objects.filter(
                project=project,
                predecessor_phase=from_phase,
                successor_phase=to_phase,
            ).exists():
                dep_type = (bp_dep.dependency_type or "fs").lower()
                if dep_type not in {"fs", "ss", "ff", "sf"}:
                    dep_type = "fs"
                ProjectPhaseDependency.objects.create(
                    organization=org,
                    project=project,
                    predecessor_phase=from_phase,
                    successor_phase=to_phase,
                    dependency_type=dep_type,
                    lag_days=int(bp_dep.lag_hours / 24) if bp_dep.lag_hours else 0,
                )
                summary["dependencies_created"] += 1

    # --- Apply schedule ---
    scalar = float(blueprint.duration_scalar_pct or 100) / 100
    total_days = int(day_cursor * scalar)
    Project.objects.filter(pk=project.pk).update(
        target_end_date=start_date + timedelta(days=total_days),
    )

    # --- Seed mobilization ---
    try:
        mobilization, _ = ProjectSiteMobilization.objects.get_or_create(
            project=project,
            defaults={"organization": org, "planned_start_date": start_date},
        )
    except Exception:
        pass

    # --- Link blueprint to project and commit ---
    blueprint.project = project
    blueprint.status = ProjectBlueprint.Status.COMMITTED
    blueprint.save(update_fields=["project", "status", "updated_at"])

    # --- Notify ---
    try:
        from apps.accounts.models import UserProfile
        from apps.notifications.services import Notification, dispatch_workflow_notification

        admins = [
            p.user
            for p in UserProfile.objects.filter(
                organization=org, role="admin", user__is_active=True
            ).select_related("user")
        ]
        if admins:
            dispatch_workflow_notification(
                organization=org,
                event_key="project_created_from_blueprint",
                recipients=admins,
                fallback_title=f"Project Created from Blueprint — {project.name}",
                fallback_message=(
                    f"Project '{project.name}' has been created from blueprint '{blueprint.name}'. "
                    f"{summary['phases_created']} phase(s), {summary['tasks_created']} task(s), "
                    f"{summary['milestones_created']} milestone(s), and {summary['dependencies_created']} "
                    f"dependency(ies) have been configured. "
                    + ("Budget seeded from the plan. " if summary['budget_seeded'] else "")
                    + "The project is ready for execution."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
            )
    except Exception:
        logger.debug("Blueprint commit notification skipped", exc_info=True)

    logger.info("Project %s created from blueprint %s: %s", project.pk, blueprint.pk, summary)
    return summary


def sync_boq_to_work_packages(project) -> int:
    """
    Sync BoQ task mappings to work packages.

    For each BoqTaskMapping linked to this project, ensure the mapped BOM item
    is linked to the corresponding work package (via the M2M linked_bom_items).

    Returns the number of links created.
    """
    from apps.inventory.models import BoqTaskMapping
    from apps.projects.models import ProjectWorkPackage

    mappings = BoqTaskMapping.objects.filter(project=project).select_related("bom_item", "task")
    links_created = 0

    for mapping in mappings:
        if not mapping.task:
            continue
        # Find the work package that owns this task (by matching work_package field)
        wp_name = mapping.task.work_package
        if not wp_name:
            continue
        wp = ProjectWorkPackage.objects.filter(
            project=project,
            name__iexact=wp_name,
        ).first()
        if wp and mapping.bom_item:
            if not wp.linked_bom_items.filter(pk=mapping.bom_item.pk).exists():
                wp.linked_bom_items.add(mapping.bom_item)
                links_created += 1

    logger.info(
        "BoQ → WorkPackage sync for project %s: %d links created",
        project.pk, links_created,
    )
    return links_created

from __future__ import annotations

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def _resolve_employee_project(employee):
    """Best-effort project resolver for HR records tied to an employee."""
    from apps.projects.models import Project, ProjectTask

    if not employee:
        return None

    if employee.user_id:
        task = (
            ProjectTask.objects.filter(
                organization_id=employee.organization_id,
                assigned_user_id=employee.user_id,
            )
            .select_related("phase__project")
            .order_by("-updated_at", "-created_at", "-id")
            .first()
        )
        if task and task.phase_id and task.phase and task.phase.project_id:
            return task.phase.project

    projects = list(
        Project.objects.filter(organization_id=employee.organization_id)
        .order_by("-created_at", "-id")[:2]
    )
    if len(projects) == 1:
        return projects[0]
    return None


def sync_site_mobilization_for_project(project):
    """Sync linked Site Mobilization checklist fields from Procurement + HR."""
    from apps.hr.models import EquipmentAllocation, OrientationChecklistItem
    from apps.procurement.models import GoodsReceipt, PurchaseOrder
    from apps.projects.models import ProjectSiteMobilization

    if not project:
        return None

    mobilization, _ = ProjectSiteMobilization.objects.get_or_create(
        project=project,
        defaults={"organization": project.organization},
    )
    if mobilization.organization_id != project.organization_id:
        mobilization.organization = project.organization
        mobilization.save(update_fields=["organization", "updated_at"])

    contractor_count = (
        PurchaseOrder.objects.filter(
            project=project,
            status__in=[
                PurchaseOrder.Status.APPROVED,
                PurchaseOrder.Status.ISSUED,
                PurchaseOrder.Status.PARTIALLY_RECEIVED,
                PurchaseOrder.Status.RECEIVED,
            ],
        )
        .values("vendor_id")
        .distinct()
        .count()
    )
    material_staging_count = GoodsReceipt.objects.filter(
        purchase_order__project=project,
        status__in=[
            GoodsReceipt.Status.INSPECTED,
            GoodsReceipt.Status.ACCEPTED,
            GoodsReceipt.Status.PARTIALLY_ACCEPTED,
        ],
    ).count()

    employee_project_cache: dict[int, int | None] = {}

    def _belongs_to_project(employee) -> bool:
        if not employee:
            return False
        cached = employee_project_cache.get(employee.id)
        if cached is None:
            resolved = _resolve_employee_project(employee)
            cached = resolved.id if resolved else -1
            employee_project_cache[employee.id] = cached
        return cached == project.id

    equipment_delivered_count = 0
    equipment_allocations = EquipmentAllocation.objects.filter(
        organization=project.organization,
        status=EquipmentAllocation.Status.ALLOCATED,
    ).select_related("employee__user")
    for allocation in equipment_allocations:
        if _belongs_to_project(allocation.employee):
            equipment_delivered_count += 1

    safety_induction_count = 0
    safety_inductions = OrientationChecklistItem.objects.filter(
        organization=project.organization,
        category=OrientationChecklistItem.Category.SAFETY_TRAINING,
        is_completed=True,
    ).select_related("employee__user")
    for item in safety_inductions:
        if _belongs_to_project(item.employee):
            safety_induction_count += 1

    linked_updates = {
        "contractors_mobilized": contractor_count > 0,
        "equipment_delivered": equipment_delivered_count > 0,
        "material_staging": material_staging_count > 0,
        "safety_induction": safety_induction_count > 0,
        "linked_procurement_contractors_count": contractor_count,
        "linked_procurement_material_staging_count": material_staging_count,
        "linked_hr_equipment_delivery_count": equipment_delivered_count,
        "linked_hr_safety_induction_count": safety_induction_count,
    }

    update_fields: list[str] = []
    for field_name, next_value in linked_updates.items():
        if getattr(mobilization, field_name) != next_value:
            setattr(mobilization, field_name, next_value)
            update_fields.append(field_name)

    if update_fields:
        mobilization.last_integrations_synced_at = timezone.now()
        update_fields.extend(["last_integrations_synced_at", "updated_at"])
        mobilization.save(update_fields=update_fields)

        # Notify project stakeholders of mobilization changes
        try:
            from apps.accounts.models import UserProfile
            from apps.notifications.services import Notification, dispatch_workflow_notification

            org = project.organization
            admins = [
                p.user
                for p in UserProfile.objects.filter(
                    organization=org, role="admin", user__is_active=True
                ).select_related("user")
            ]
            changed = [f.replace("_", " ").replace("linked ", "").title() for f in update_fields if f.startswith("linked_") or f in ("contractors_mobilized", "equipment_delivered", "material_staging", "safety_induction")]
            if admins and changed:
                dispatch_workflow_notification(
                    organization=org,
                    event_key="project_site_mobilization_updated",
                    recipients=admins,
                    context={"project_name": project.name, "changes": ", ".join(changed)},
                    fallback_title=f"Site Mobilization Updated — {project.name}",
                    fallback_message=(
                        f"The site mobilization checklist for project '{project.name}' has been "
                        f"automatically updated. Changes: {', '.join(changed).lower()}."
                    ),
                    fallback_category=Notification.Category.SYSTEM,
                )
        except Exception:
            logger.debug("Site mobilization notification skipped", exc_info=True)

    return mobilization


def sync_site_mobilization_for_project_id(project_id: int | None):
    from apps.projects.models import Project

    if not project_id:
        return None
    project = (
        Project.objects.select_related("organization")
        .filter(id=project_id)
        .first()
    )
    if not project:
        return None
    return sync_site_mobilization_for_project(project)


def sync_site_mobilization_from_purchase_order(purchase_order):
    return sync_site_mobilization_for_project(getattr(purchase_order, "project", None))


def sync_site_mobilization_from_goods_receipt(goods_receipt):
    project = None
    if getattr(goods_receipt, "purchase_order_id", None):
        project = getattr(goods_receipt.purchase_order, "project", None)
    return sync_site_mobilization_for_project(project)


def sync_site_mobilization_from_equipment_allocation(allocation):
    if not getattr(allocation, "employee_id", None):
        return None
    project = _resolve_employee_project(allocation.employee)
    return sync_site_mobilization_for_project(project)


def sync_site_mobilization_from_orientation_item(item):
    if not getattr(item, "employee_id", None):
        return None
    project = _resolve_employee_project(item.employee)
    return sync_site_mobilization_for_project(project)

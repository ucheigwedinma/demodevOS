from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal

from django.utils import timezone

logger = logging.getLogger(__name__)


def _hook_reference(source: str, organization_id: int | None, source_key: str) -> str:
    return f"HOOK:{source}:org:{organization_id}:{source_key}"


def _notify_cost_sync(*, organization, project, source_label, amount, description):
    """Dispatch a notification when a cross-module cost sync updates project tracking."""
    try:
        from apps.accounts.models import UserProfile
        from apps.notifications.services import Notification, dispatch_workflow_notification

        admins = [
            p.user
            for p in UserProfile.objects.filter(
                organization=organization, role="admin", user__is_active=True
            ).select_related("user")
        ]
        if not admins:
            return
        amount_text = f" (₦{amount:,.2f})" if amount else ""
        dispatch_workflow_notification(
            organization=organization,
            event_key="project_cost_sync",
            recipients=admins,
            context={
                "project_name": project.name,
                "source": source_label,
                "amount": str(amount or ""),
            },
            fallback_title=f"Project Cost Updated — {project.name}",
            fallback_message=(
                f"A cost entry has been synced to project '{project.name}' "
                f"from {source_label}{amount_text}. "
                f"Description: {description}."
            ),
            fallback_category=Notification.Category.SYSTEM,
        )
    except Exception:
        logger.debug("Cost sync notification skipped", exc_info=True)


def _ensure_tracking_phase(project):
    from apps.projects.models import ProjectPhase

    phase = project.phases.order_by("sort_order", "id").first()
    if phase:
        return phase

    return ProjectPhase.objects.create(
        organization=project.organization,
        project=project,
        name="Auto Cost Tracking",
        description="Auto-created phase used for cross-module finance cost tracking.",
        sort_order=0,
        status=ProjectPhase.Status.NOT_STARTED,
        planned_start_date=project.start_date,
        planned_end_date=project.target_end_date,
    )


def _upsert_project_cost_entry(
    *,
    project,
    category: str,
    reference: str,
    amount,
    entry_date,
    description: str,
    vendor: str = "",
):
    from apps.projects.models import ProjectCostEntry

    amount_value = Decimal(str(amount or "0"))
    if amount_value <= Decimal("0"):
        ProjectCostEntry.objects.filter(
            organization_id=project.organization_id,
            reference_number=reference,
        ).delete()
        return None

    phase = _ensure_tracking_phase(project)
    entry = ProjectCostEntry.objects.filter(
        organization_id=project.organization_id,
        reference_number=reference,
    ).first()

    if entry is None:
        return ProjectCostEntry.objects.create(
            organization=project.organization,
            phase=phase,
            description=description,
            amount=amount_value,
            date=entry_date or timezone.localdate(),
            category=category,
            vendor=vendor,
            reference_number=reference,
        )

    update_fields: list[str] = []
    if entry.phase_id != phase.id:
        entry.phase = phase
        update_fields.append("phase")
    if entry.description != description:
        entry.description = description
        update_fields.append("description")
    if entry.amount != amount_value:
        entry.amount = amount_value
        update_fields.append("amount")
    normalized_date = entry_date or timezone.localdate()
    if entry.date != normalized_date:
        entry.date = normalized_date
        update_fields.append("date")
    if entry.category != category:
        entry.category = category
        update_fields.append("category")
    if entry.vendor != vendor:
        entry.vendor = vendor
        update_fields.append("vendor")

    if update_fields:
        entry.save(update_fields=update_fields)
    return entry


def sync_procurement_purchase_order_cost(purchase_order):
    from apps.projects.models import ProjectCostEntry

    reference = _hook_reference(
        "procurement_po",
        purchase_order.organization_id,
        f"po:{purchase_order.id}",
    )
    if (
        not purchase_order.project_id
        or purchase_order.status == purchase_order.Status.CANCELLED
    ):
        delete_procurement_purchase_order_cost(purchase_order)
        return None

    desc = f"Procurement PO {purchase_order.po_number or purchase_order.id}"
    entry = _upsert_project_cost_entry(
        project=purchase_order.project,
        category=ProjectCostEntry.Category.MATERIALS,
        reference=reference,
        amount=purchase_order.total_amount,
        entry_date=purchase_order.issue_date,
        description=desc,
        vendor=purchase_order.vendor.name if purchase_order.vendor_id else "",
    )
    _notify_cost_sync(
        organization=purchase_order.organization,
        project=purchase_order.project,
        source_label="procurement purchase order",
        amount=purchase_order.total_amount,
        description=desc,
    )
    return entry


def delete_procurement_purchase_order_cost(purchase_order):
    from apps.projects.models import ProjectCostEntry

    reference = _hook_reference(
        "procurement_po",
        purchase_order.organization_id,
        f"po:{purchase_order.id}",
    )
    ProjectCostEntry.objects.filter(
        organization_id=purchase_order.organization_id,
        reference_number=reference,
    ).delete()


def _resolve_employee_project(employee):
    from apps.projects.models import Project, ProjectTask

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
        if task and task.phase_id:
            return task.phase.project

    projects = Project.objects.filter(organization_id=employee.organization_id).order_by(
        "-created_at",
        "-id",
    )
    if projects.count() == 1:
        return projects.first()
    return None


def sync_hr_payroll_run_costs(payroll_run):
    from apps.projects.models import ProjectCostEntry

    prefix = _hook_reference(
        "hr_payroll_run",
        payroll_run.organization_id,
        f"run:{payroll_run.id}",
    )
    existing_entries = ProjectCostEntry.objects.filter(
        organization_id=payroll_run.organization_id,
        reference_number__startswith=f"{prefix}:project:",
    )

    if payroll_run.status != payroll_run.Status.COMPLETED:
        existing_entries.delete()
        return

    project_amounts: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    project_map = {}
    for payslip in payroll_run.payslips.select_related("employee__user"):
        project = _resolve_employee_project(payslip.employee)
        if not project:
            continue
        amount = Decimal(str(payslip.net_salary or "0"))
        if amount <= Decimal("0"):
            continue
        project_amounts[project.id] += amount
        project_map[project.id] = project

    desired_references: set[str] = set()
    for project_id, amount in project_amounts.items():
        reference = f"{prefix}:project:{project_id}"
        desired_references.add(reference)
        _upsert_project_cost_entry(
            project=project_map[project_id],
            category=ProjectCostEntry.Category.LABOR,
            reference=reference,
            amount=amount,
            entry_date=(
                payroll_run.run_date
                or payroll_run.period_end
                or timezone.localdate()
            ),
            description=(
                f"Payroll run {payroll_run.name} "
                f"({payroll_run.period_start} to {payroll_run.period_end})"
            ),
            vendor="",
        )

    existing_entries.exclude(reference_number__in=desired_references).delete()

    if project_amounts:
        total = sum(project_amounts.values())
        _notify_cost_sync(
            organization=payroll_run.organization,
            project=next(iter(project_map.values())),
            source_label="payroll run",
            amount=total,
            description=f"Payroll run {payroll_run.name} ({payroll_run.period_start} to {payroll_run.period_end})",
        )


def delete_hr_payroll_run_costs(payroll_run):
    from apps.projects.models import ProjectCostEntry

    prefix = _hook_reference(
        "hr_payroll_run",
        payroll_run.organization_id,
        f"run:{payroll_run.id}",
    )
    ProjectCostEntry.objects.filter(
        organization_id=payroll_run.organization_id,
        reference_number__startswith=f"{prefix}:project:",
    ).delete()


def _resolve_compliance_project(violation):
    from apps.projects.models import Project

    if not violation.property_id:
        return None
    return (
        Project.objects.filter(
            organization_id=violation.organization_id,
            property_id=violation.property_id,
        )
        .order_by("-created_at", "-id")
        .first()
    )


def sync_compliance_permit_fee_cost(violation):
    from apps.projects.models import ProjectCostEntry

    project = _resolve_compliance_project(violation)
    if not project:
        delete_compliance_permit_fee_cost(violation)
        return None

    reference = _hook_reference(
        "compliance_violation",
        violation.organization_id,
        f"violation:{violation.id}",
    )
    desc = f"Compliance permit fee: {violation.title}"
    entry = _upsert_project_cost_entry(
        project=project,
        category=ProjectCostEntry.Category.PERMITS,
        reference=reference,
        amount=violation.fine_amount,
        entry_date=violation.reported_date,
        description=desc,
        vendor="",
    )
    _notify_cost_sync(
        organization=violation.organization,
        project=project,
        source_label="compliance permit fee",
        amount=violation.fine_amount,
        description=desc,
    )
    return entry


def delete_compliance_permit_fee_cost(violation):
    from apps.projects.models import ProjectCostEntry

    reference = _hook_reference(
        "compliance_violation",
        violation.organization_id,
        f"violation:{violation.id}",
    )
    ProjectCostEntry.objects.filter(
        organization_id=violation.organization_id,
        reference_number=reference,
    ).delete()


def sync_inventory_material_usage_cost(transaction):
    from apps.projects.models import ProjectCostEntry

    reference = _hook_reference(
        "inventory_issue",
        transaction.organization_id,
        f"txn:{transaction.id}",
    )
    if (
        transaction.transaction_type != transaction.TransactionType.ISSUE
        or not transaction.project_id
        or transaction.source_module == "projects_cost"
    ):
        delete_inventory_material_usage_cost(transaction)
        return None

    amount = transaction.total_cost
    if amount in (None, Decimal("0.00")) and transaction.unit_cost is not None:
        amount = (transaction.unit_cost or Decimal("0.00")) * (
            transaction.quantity or Decimal("0")
        )

    item_label = (
        transaction.item.sku
        if transaction.item_id and transaction.item and transaction.item.sku
        else f"item-{transaction.item_id}"
    )
    desc = f"Inventory usage: {item_label}"
    entry = _upsert_project_cost_entry(
        project=transaction.project,
        category=ProjectCostEntry.Category.MATERIALS,
        reference=reference,
        amount=amount,
        entry_date=transaction.transaction_date,
        description=desc,
        vendor="",
    )
    _notify_cost_sync(
        organization=transaction.organization,
        project=transaction.project,
        source_label="inventory material usage",
        amount=amount,
        description=desc,
    )
    return entry


def delete_inventory_material_usage_cost(transaction):
    from apps.projects.models import ProjectCostEntry

    reference = _hook_reference(
        "inventory_issue",
        transaction.organization_id,
        f"txn:{transaction.id}",
    )
    ProjectCostEntry.objects.filter(
        organization_id=transaction.organization_id,
        reference_number=reference,
    ).delete()

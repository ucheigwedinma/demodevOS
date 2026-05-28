import logging

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


def _sync_profile_department_and_business_unit(
    *,
    user_id: int | None,
    organization_id: int | None,
    clear_when_unassigned: bool = True,
):
    if not user_id:
        return

    from apps.accounts.models import UserProfile
    from apps.hr.models import PositionAssignment

    profile = UserProfile.objects.select_related("department__division").filter(user_id=user_id).first()
    if profile is None:
        return

    assignments = PositionAssignment.objects.select_related(
        "position__department__division"
    ).filter(
        user_id=user_id,
        is_active=True,
    )
    if organization_id:
        assignments = assignments.filter(organization_id=organization_id)

    assignment = assignments.filter(is_primary=True).order_by("-start_date", "-id").first()
    if assignment is None:
        assignment = assignments.order_by("-start_date", "-id").first()

    next_department = assignment.position.department if assignment and assignment.position_id else None
    if next_department is None and not clear_when_unassigned:
        next_department = getattr(profile, "department", None)

    next_department_id = next_department.id if next_department else None
    next_business_unit = (
        next_department.division.name if next_department and next_department.division_id else ""
    )
    if not next_business_unit and not clear_when_unassigned:
        next_business_unit = profile.business_unit or ""

    update_fields: list[str] = []
    if organization_id and profile.organization_id != organization_id:
        profile.organization_id = organization_id
        update_fields.append("organization")
    if profile.department_id != next_department_id:
        profile.department_id = next_department_id
        update_fields.append("department")
    if profile.business_unit != next_business_unit:
        profile.business_unit = next_business_unit
        update_fields.append("business_unit")

    if update_fields:
        profile.save(update_fields=update_fields)


@receiver(post_save, sender="hr.PositionAssignment")
def on_position_assignment_change_sync_profile_mapping(sender, instance, **kwargs):
    """Keep user department + business unit in sync with active position assignment."""
    from apps.hr.automation import sync_position_vacancy_state

    _sync_profile_department_and_business_unit(
        user_id=getattr(instance, "user_id", None),
        organization_id=getattr(instance, "organization_id", None),
    )
    if getattr(instance, "position_id", None):
        sync_position_vacancy_state(instance.position_id)


@receiver(post_delete, sender="hr.PositionAssignment")
def on_position_assignment_delete_sync_profile_mapping(sender, instance, **kwargs):
    """Recalculate user department + business unit when an assignment is removed."""
    from apps.hr.automation import sync_position_vacancy_state

    _sync_profile_department_and_business_unit(
        user_id=getattr(instance, "user_id", None),
        organization_id=getattr(instance, "organization_id", None),
    )
    if getattr(instance, "position_id", None):
        sync_position_vacancy_state(instance.position_id)


@receiver(post_save, sender="hr.Position")
def on_position_change_sync_vacancy_state(sender, instance, **kwargs):
    """Keep slot/vacancy automation in sync and trigger recruitment drafts when needed."""
    from apps.hr.automation import sync_position_vacancy_state

    if getattr(instance, "id", None):
        sync_position_vacancy_state(instance.id)


@receiver(post_save, sender="hr.EmployeeRecord")
def on_employee_record_created_sync_profile_mapping(sender, instance, created, **kwargs):
    """On hire record creation, align profile mapping from the employee's active assignment."""
    if not created:
        return
    _sync_profile_department_and_business_unit(
        user_id=getattr(instance, "user_id", None),
        organization_id=getattr(instance, "organization_id", None),
        clear_when_unassigned=False,
    )


@receiver(post_save, sender="hr.LeaveRequest")
def on_leave_request_created(sender, instance, created, **kwargs):
    """Notify the reporting manager when a leave request is submitted."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import (
        dispatch_workflow_notification,
        resolve_raci_recipients,
    )

    org = getattr(instance, "organization", None)
    if not org and instance.employee_id:
        org = getattr(instance.employee, "organization", None)
    if not org:
        return

    # Resolve recipients: team leads + reporting manager + RACI
    recipients = []
    if instance.employee_id:
        employee_user = getattr(instance.employee, "user", None)
        if employee_user:
            profile = getattr(employee_user, "profile", None)
            if profile and profile.reporting_manager_id:
                recipients.append(profile.reporting_manager)
            from apps.hr.models import PositionAssignment
            team_lead_ids = set(
                PositionAssignment.objects.filter(
                    organization=org,
                    user_id=employee_user.id,
                    is_active=True,
                    position__team__lead__isnull=False,
                ).values_list("position__team__lead_id", flat=True).distinct()
            )
            if team_lead_ids:
                from django.contrib.auth import get_user_model

                user_model = get_user_model()
                recipients.extend(
                    list(user_model.objects.filter(id__in=team_lead_ids, is_active=True))
                )

    raci = resolve_raci_recipients(
        organization=org,
        process_key="hr.leave",
        fallback_users=recipients or None,
    )
    all_recipients = list(
        {
            user.id: user
            for user in [*(recipients or []), *(raci.all or [])]
            if user is not None
        }.values()
    )

    if not all_recipients:
        return

    employee_name = ""
    if instance.employee_id:
        employee_user = getattr(instance.employee, "user", None)
        if employee_user:
            employee_name = employee_user.get_full_name() or employee_user.email

    leave_type_label = str(instance.leave_type) if instance.leave_type_id else "Leave"

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_leave_submitted",
        recipients=all_recipients,
        context={
            "employee_name": employee_name,
            "leave_type": leave_type_label,
            "start_date": str(instance.start_date) if instance.start_date else "",
            "end_date": str(instance.end_date) if instance.end_date else "",
            "action_url": "/hr/leave",
        },
        link_url="/hr/leave",
        fallback_channels=["in_app", "email"],
        fallback_title=f"Leave Request Submitted — {employee_name}",
        fallback_message=(
            f"{employee_name} has submitted a {leave_type_label} leave request "
            f"from {instance.start_date} to {instance.end_date}. "
            f"Please review and approve or decline at your earliest convenience."
        ),
        fallback_category=Notification.Category.HR_LEAVE,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="hr.LeaveRequest")
def on_leave_decision(sender, instance, created, **kwargs):
    """Notify the employee when their leave request is approved or rejected."""
    if created:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    if instance.status not in ("approved", "rejected"):
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = getattr(instance, "organization", None)
    if not org and instance.employee_id:
        org = getattr(instance.employee, "organization", None)
    if not org:
        return

    employee_user = None
    if instance.employee_id:
        employee_user = getattr(instance.employee, "user", None)
    if not employee_user:
        return

    leave_type_label = str(instance.leave_type) if instance.leave_type_id else "Leave"
    decision = "approved" if instance.status == "approved" else "rejected"

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_leave_decision",
        recipients=[employee_user],
        context={
            "leave_type": leave_type_label,
            "start_date": str(instance.start_date) if instance.start_date else "",
            "end_date": str(instance.end_date) if instance.end_date else "",
            "decision": decision,
            "action_url": "/hr/leave",
        },
        link_url="/hr/leave",
        fallback_channels=["in_app", "email"],
        fallback_title=f"Leave Request {decision.title()}",
        fallback_message=(
            f"Your {leave_type_label} leave request from {instance.start_date} "
            f"to {instance.end_date} has been {decision}."
            f"{' Your leave balance has been updated accordingly.' if decision == 'approved' else ' Please contact your manager for further details.'}"
        ),
        fallback_category=Notification.Category.HR_LEAVE,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="hr.PayrollRun")
def on_payroll_run_change_sync_project_costs(sender, instance, **kwargs):
    """Sync project payroll costs when payroll run fields change."""
    from apps.finance.cost_tracking_hooks import sync_hr_payroll_run_costs

    sync_hr_payroll_run_costs(instance)


@receiver(post_delete, sender="hr.PayrollRun")
def on_payroll_run_delete_remove_project_costs(sender, instance, **kwargs):
    """Remove hook-generated payroll cost entries when payroll run is deleted."""
    from apps.finance.cost_tracking_hooks import delete_hr_payroll_run_costs

    delete_hr_payroll_run_costs(instance)


@receiver(post_save, sender="hr.Payslip")
def on_payslip_change_sync_project_costs(sender, instance, **kwargs):
    """Resync payroll hook entries when a payslip changes."""
    if not instance.payroll_run_id:
        return

    from apps.finance.cost_tracking_hooks import sync_hr_payroll_run_costs
    from apps.hr.models import PayrollRun

    payroll_run = PayrollRun.objects.filter(id=instance.payroll_run_id).first()
    if payroll_run:
        sync_hr_payroll_run_costs(payroll_run)


@receiver(post_delete, sender="hr.Payslip")
def on_payslip_delete_sync_project_costs(sender, instance, **kwargs):
    """Resync payroll hook entries when a payslip is deleted."""
    if not instance.payroll_run_id:
        return

    from apps.finance.cost_tracking_hooks import sync_hr_payroll_run_costs
    from apps.hr.models import PayrollRun

    payroll_run = PayrollRun.objects.filter(id=instance.payroll_run_id).first()
    if payroll_run:
        sync_hr_payroll_run_costs(payroll_run)


@receiver(post_save, sender="hr.EquipmentAllocation")
def on_equipment_allocation_change_sync_site_mobilization(sender, instance, **kwargs):
    """Sync project site mobilization when HR equipment delivery changes."""
    from apps.projects.site_mobilization import (
        sync_site_mobilization_from_equipment_allocation,
    )

    sync_site_mobilization_from_equipment_allocation(instance)


@receiver(post_delete, sender="hr.EquipmentAllocation")
def on_equipment_allocation_delete_sync_site_mobilization(sender, instance, **kwargs):
    """Resync project site mobilization when HR equipment allocation is deleted."""
    from apps.projects.site_mobilization import (
        sync_site_mobilization_from_equipment_allocation,
    )

    sync_site_mobilization_from_equipment_allocation(instance)


@receiver(post_save, sender="hr.OrientationChecklistItem")
def on_orientation_checklist_change_sync_site_mobilization(sender, instance, **kwargs):
    """Sync project site mobilization when safety induction checklist changes."""
    from apps.projects.site_mobilization import (
        sync_site_mobilization_from_orientation_item,
    )

    sync_site_mobilization_from_orientation_item(instance)


@receiver(post_delete, sender="hr.OrientationChecklistItem")
def on_orientation_checklist_delete_sync_site_mobilization(sender, instance, **kwargs):
    """Resync project site mobilization when safety induction item is deleted."""
    from apps.projects.site_mobilization import (
        sync_site_mobilization_from_orientation_item,
    )

    sync_site_mobilization_from_orientation_item(instance)


# ---------------------------------------------------------------------------
# Notification helpers
# ---------------------------------------------------------------------------

def _org_admin_users(org):
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org, role="admin", user__is_active=True
        ).select_related("user")
    ]


def _employee_user(instance):
    """Try to resolve the User from an EmployeeRecord FK."""
    if hasattr(instance, "employee") and instance.employee_id:
        return getattr(instance.employee, "user", None)
    return None


# ---------------------------------------------------------------------------
# Job Requisition notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.JobRequisition")
def on_job_requisition_status_changed(sender, instance, created, **kwargs):
    """Notify on new requisition or status change."""
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    position = getattr(instance, "position", None)
    position_title = str(position) if position else "Unknown position"

    if created:
        title = f"New Job Requisition — {position_title}"
        message = f"A new job requisition has been raised for the {position_title} position. It is pending approval before recruitment can begin."
    else:
        update_fields = kwargs.get("update_fields")
        if update_fields and "status" not in update_fields:
            return
        status_label = instance.get_status_display()
        title = f"Job Requisition {status_label} — {position_title}"
        message = f"The job requisition for {position_title} has been updated to {status_label}.{' Recruitment may now proceed.' if status_label.lower() == 'approved' else ''}"

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_requisition_status_changed",
        recipients=_org_admin_users(org),
        context={
            "position_title": position_title,
            "new_status": instance.get_status_display(),
            "action_url": "/hr/recruitment",
        },
        link_url="/hr/recruitment",
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.HR_LIFECYCLE,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Job Offer notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.JobOffer")
def on_job_offer_status_changed(sender, instance, created, **kwargs):
    """Notify on new offer or status change."""
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    candidate_name = str(instance.candidate) if instance.candidate_id else "Unknown"

    if created:
        title = f"New Job Offer Created — {candidate_name}"
        message = f"A job offer has been created for {candidate_name} and is awaiting review before it can be extended to the candidate."
    else:
        update_fields = kwargs.get("update_fields")
        if update_fields and "status" not in update_fields:
            return
        status_label = instance.get_status_display()
        title = f"Job Offer {status_label} — {candidate_name}"
        message = f"The job offer for {candidate_name} has been updated to {status_label}.{' Onboarding preparations can begin.' if status_label.lower() == 'accepted' else ''}"

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_offer_status_changed",
        recipients=_org_admin_users(org),
        context={
            "candidate_name": candidate_name,
            "new_status": instance.get_status_display(),
            "action_url": "/hr/recruitment",
        },
        link_url="/hr/recruitment",
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.HR_LIFECYCLE,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Onboarding Task notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.OnboardingTask")
def on_onboarding_task_created(sender, instance, created, **kwargs):
    """Notify when an onboarding task is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    task_name = getattr(instance, "title", "") or str(instance)
    assignee = getattr(instance, "assigned_to", None)
    recipients = [assignee] if assignee else _org_admin_users(org)

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_onboarding_task_assigned",
        recipients=recipients,
        context={
            "task_name": task_name,
            "action_url": "/hr/onboarding",
        },
        link_url="/hr/onboarding",
        fallback_channels=["in_app"],
        fallback_title=f"Onboarding Task Assigned — {task_name}",
        fallback_message=(
            f"You have been assigned the onboarding task '{task_name}'. "
            f"Please complete it before the deadline to ensure a smooth onboarding experience."
        ),
        fallback_category=Notification.Category.HR_LIFECYCLE,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Overtime Request notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.OvertimeRequest")
def on_overtime_request_status_changed(sender, instance, created, **kwargs):
    """Notify on new overtime request or approval/rejection."""
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    emp_user = _employee_user(instance)

    if created:
        title = "New overtime request submitted"
        message = "An overtime request has been submitted for approval."
        recipients = _org_admin_users(org)
    else:
        update_fields = kwargs.get("update_fields")
        if update_fields and "status" not in update_fields:
            return
        status_label = instance.get_status_display()
        title = f"Overtime request {status_label}"
        message = f"Your overtime request has been {status_label}."
        recipients = [emp_user] if emp_user else _org_admin_users(org)

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_overtime_status_changed",
        recipients=recipients,
        context={
            "new_status": instance.get_status_display(),
            "action_url": "/hr/overtime",
        },
        link_url="/hr/overtime",
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.HR_LEAVE,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Performance Review notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.PerformanceReview")
def on_performance_review_status_changed(sender, instance, created, **kwargs):
    """Notify on review status changes."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    emp_user = _employee_user(instance)
    status_label = instance.get_status_display()
    recipients = [emp_user] if emp_user else _org_admin_users(org)

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_performance_review_status_changed",
        recipients=recipients,
        context={
            "new_status": status_label,
            "action_url": "/hr/performance",
        },
        link_url="/hr/performance",
        fallback_channels=["in_app"],
        fallback_title=f"Performance Review {status_label.title()}",
        fallback_message=(
            f"Your performance review has been updated to {status_label}."
            f"{'Please complete your self-assessment before the review meeting.' if status_label.lower() in ('in_progress', 'pending') else ' You can view the full review details in the HR module.'}"
        ),
        fallback_category=Notification.Category.HR_LIFECYCLE,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Probation Record notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.ProbationRecord")
def on_probation_status_changed(sender, instance, created, **kwargs):
    """Notify on probation status changes."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    emp_user = _employee_user(instance)
    status_label = instance.get_status_display()
    recipients = []
    if emp_user:
        recipients.append(emp_user)
    recipients.extend(u for u in _org_admin_users(org) if u not in recipients)

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_probation_status_changed",
        recipients=recipients,
        context={
            "new_status": status_label,
            "action_url": "/hr/probation",
        },
        link_url="/hr/probation",
        fallback_channels=["in_app"],
        fallback_title=f"Probation Status Updated — {status_label}",
        fallback_message=(
            f"The probation record has been updated to {status_label}."
            f"{'Congratulations — the probation period has been successfully completed.' if status_label.lower() in ('confirmed', 'completed') else ' Please review the probation progress and provide feedback.'}"
        ),
        fallback_category=Notification.Category.HR_LIFECYCLE,
        fallback_severity=Notification.Severity.INFO,
    )


# ---------------------------------------------------------------------------
# Employee Record notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="hr.EmployeeRecord")
def on_employee_created_notification(sender, instance, created, **kwargs):
    """Notify admins when a new employee record is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    emp_name = ""
    if hasattr(instance, "user") and instance.user:
        emp_name = instance.user.get_full_name() or instance.user.email
    if not emp_name:
        emp_name = f"{getattr(instance, 'first_name', '')} {getattr(instance, 'last_name', '')}".strip() or str(instance)

    dispatch_workflow_notification(
        organization=org,
        event_key="hr_employee_created",
        recipients=_org_admin_users(org),
        context={
            "employee_name": emp_name,
            "action_url": "/hr/employees",
        },
        link_url="/hr/employees",
        fallback_channels=["in_app"],
        fallback_title=f"New Employee Record Created — {emp_name}",
        fallback_message=(
            f"An employee record has been created for {emp_name}. "
            f"Onboarding tasks and access provisioning can now be initiated."
        ),
        fallback_category=Notification.Category.HR_LIFECYCLE,
        fallback_severity=Notification.Severity.INFO,
    )


# ── Employee Terminated ───────────────────────────────────────────────


@receiver(pre_save, sender="hr.EmployeeRecord")
def capture_employee_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_emp_status = sender.objects.get(pk=instance.pk).employment_status
        except sender.DoesNotExist:
            instance._prev_emp_status = None
    else:
        instance._prev_emp_status = None


@receiver(post_save, sender="hr.EmployeeRecord")
def on_employee_terminated(sender, instance, created, **kwargs):
    """Notify when an employee is terminated."""
    if created:
        return
    prev = getattr(instance, "_prev_emp_status", None)
    if prev == instance.employment_status or instance.employment_status != "terminated":
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        emp_name = instance.user.get_full_name() if instance.user else f"Employee #{instance.pk}"
        reason = instance.termination_reason[:100] if instance.termination_reason else "No reason provided"

        dispatch_workflow_notification(
            organization=org,
            event_key="employee_terminated",
            recipients=_org_admin_users(org),
            link_url="/hr/employees",
            fallback_channels=["in_app"],
            fallback_title=f"Employee Terminated — {emp_name}",
            fallback_message=(
                f"{emp_name} has been marked as terminated. "
                f"Reason: {reason}. "
                f"Please ensure exit procedures, access revocation, and final pay are processed."
            ),
            fallback_category=Notification.Category.HR_LIFECYCLE,
            fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Employee terminated notification skipped", exc_info=True)

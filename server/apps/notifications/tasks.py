"""
Periodic notification tasks — checks for time-based events that need alerts.

Runs via Celery Beat. Register in admin or settings:
  Task: notifications.run_critical_notification_checks
  Schedule: Every hour (or every 6 hours for less urgent checks)
"""

import logging
from datetime import date, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


def _org_admin_users(org):
    """Return active admin users for the given organization."""
    from apps.accounts.models import UserProfile
    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org, role="admin", user__is_active=True,
        ).select_related("user")
    ]


def _notify(org, recipients, title, message, severity, category, link_url, event_key="system_alert"):
    """Create a notification if one with the same title doesn't already exist today."""
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    # Deduplicate — don't send the same alert twice in one day
    already_sent = Notification.objects.filter(
        organization=org,
        title=title,
        created_at__date=date.today(),
    ).exists()
    if already_sent:
        return

    dispatch_workflow_notification(
        organization=org,
        event_key=event_key,
        recipients=recipients,
        link_url=link_url,
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=category,
        fallback_severity=severity,
    )


@shared_task(name="notifications.run_critical_notification_checks")
def run_critical_notification_checks():
    """Run all critical time-based notification checks across all orgs."""
    from apps.accounts.models import Organization

    results = {
        "leases_expiring": 0,
        "overdue_invoices": 0,
        "overdue_bills": 0,
        "budget_breaches": 0,
        "certs_expiring": 0,
        "sla_breaches": 0,
        "approvals_pending": 0,
        "meetings_reminder": 0,
        "actions_overdue": 0,
        "milestones_overdue": 0,
        "compliance_deadlines": 0,
        "docs_expiring": 0,
        "training_overdue": 0,
        "errors": 0,
    }

    for org in Organization.objects.filter(is_active=True):
        try:
            admins = _org_admin_users(org)
            if not admins:
                continue

            results["leases_expiring"] += _check_leases_expiring(org, admins)
            results["overdue_invoices"] += _check_overdue_invoices(org, admins)
            results["overdue_bills"] += _check_overdue_bills(org, admins)
            results["budget_breaches"] += _check_budget_thresholds(org, admins)
            results["certs_expiring"] += _check_certifications_expiring(org, admins)
            results["sla_breaches"] += _check_ticket_sla_breaches(org, admins)
            results["approvals_pending"] += _check_pending_approvals(org)
            results["meetings_reminder"] += _check_meetings_starting_soon(org, admins)
            results["actions_overdue"] += _check_action_items_overdue(org, admins)
            results["milestones_overdue"] += _check_milestones_overdue(org, admins)
            results["compliance_deadlines"] += _check_compliance_deadlines(org, admins)
            results["docs_expiring"] += _check_documents_expiring(org, admins)
            results["training_overdue"] += _check_training_overdue(org, admins)
        except Exception:
            results["errors"] += 1
            logger.debug(f"Notification check failed for org {org.name}", exc_info=True)

    logger.info(f"Critical notification checks complete: {results}")
    return results


# ── 1. Lease Expiring (30/60/90 days) ─────────────────────────────────


def _check_leases_expiring(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.tenants.models import LeaseAgreement
    except ImportError:
        return 0

    today = date.today()
    thresholds = [
        (90, "90 days", Notification.Severity.INFO),
        (60, "60 days", Notification.Severity.WARNING),
        (30, "30 days", Notification.Severity.WARNING),
        (7, "7 days", Notification.Severity.CRITICAL),
    ]

    for days, label, severity in thresholds:
        target_date = today + timedelta(days=days)
        expiring = LeaseAgreement.objects.filter(
            organization=org,
            end_date=target_date,
            status__in=["active", "renewed"],
        ).select_related("tenant", "unit")

        for lease in expiring:
            tenant_name = getattr(lease.tenant, "name", "Unknown")
            unit_name = getattr(lease.unit, "unit_number", "N/A") if hasattr(lease, "unit") else "N/A"
            _notify(
                org=org,
                recipients=admins,
                title=f"Lease Expiring in {label} — {tenant_name}",
                message=(
                    f"Lease for {tenant_name} (Unit: {unit_name}) expires on "
                    f"{lease.end_date.strftime('%d %B %Y')}. "
                    f"Please initiate renewal or termination."
                ),
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/tenants/leases",
                event_key="lease_expiring",
            )
            count += 1

    return count


# ── 2. Invoice Overdue ────────────────────────────────────────────────


def _check_overdue_invoices(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.finance.models import Invoice
    except ImportError:
        return 0

    today = date.today()
    overdue = Invoice.objects.filter(
        organization=org,
        status__in=["sent", "overdue"],
        due_date__lt=today,
    ).exclude(status="paid")

    for inv in overdue[:20]:  # Cap at 20 per org per run
        days_overdue = (today - inv.due_date).days
        if days_overdue in (1, 7, 14, 30) or days_overdue % 30 == 0:
            severity = Notification.Severity.CRITICAL if days_overdue > 30 else Notification.Severity.WARNING
            _notify(
                org=org,
                recipients=admins,
                title=f"Invoice Overdue ({days_overdue}d) — {inv.invoice_number}",
                message=(
                    f"Invoice {inv.invoice_number} for {inv.total_amount} is "
                    f"{days_overdue} days past due (due: {inv.due_date.strftime('%d/%m/%Y')}). "
                    f"Customer: {getattr(inv.customer, 'name', 'N/A') if hasattr(inv, 'customer') else 'N/A'}."
                ),
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/finance/invoices",
                event_key="invoice_overdue",
            )
            count += 1

    return count


# ── 3. Bill Overdue ───────────────────────────────────────────────────


def _check_overdue_bills(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.finance.models import Bill
    except ImportError:
        return 0

    today = date.today()
    overdue = Bill.objects.filter(
        organization=org,
        status__in=["draft", "approved"],
        due_date__lt=today,
    ).exclude(status="paid")

    for bill in overdue[:20]:
        days_overdue = (today - bill.due_date).days
        if days_overdue in (1, 7, 14, 30) or days_overdue % 30 == 0:
            severity = Notification.Severity.CRITICAL if days_overdue > 30 else Notification.Severity.WARNING
            _notify(
                org=org,
                recipients=admins,
                title=f"Bill Overdue ({days_overdue}d) — {bill.bill_number}",
                message=(
                    f"Bill {bill.bill_number} for {bill.total_amount} is "
                    f"{days_overdue} days past due (due: {bill.due_date.strftime('%d/%m/%Y')}). "
                    f"Vendor: {getattr(bill.vendor, 'name', 'N/A') if hasattr(bill, 'vendor') else 'N/A'}."
                ),
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/finance/bills",
                event_key="bill_overdue",
            )
            count += 1

    return count


# ── 4. Budget Threshold Breach (75%, 90%, 100%) ───────────────────────


def _check_budget_thresholds(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.finance.models import Budget, BudgetLineItem
    except ImportError:
        return 0

    budgets = Budget.objects.filter(
        organization=org,
        status="active",
    )

    for budget in budgets:
        total_budgeted = sum(
            li.budgeted_amount for li in budget.line_items.all()
            if li.budgeted_amount
        )
        if total_budgeted <= 0:
            continue

        # Calculate actual spent
        total_spent = 0
        for li in budget.line_items.all():
            if hasattr(li, "get_actual_spent"):
                total_spent += li.get_actual_spent()

        pct = round(total_spent / total_budgeted * 100, 1)
        budget_name = getattr(budget, "name", "") or f"Budget #{budget.pk}"
        project_name = getattr(budget.project, "name", "") if hasattr(budget, "project") and budget.project else ""
        label = f"{budget_name} ({project_name})" if project_name else budget_name

        for threshold in [100, 90, 75]:
            if pct >= threshold:
                if threshold == 100:
                    severity = Notification.Severity.CRITICAL
                    verb = "EXCEEDED"
                elif threshold == 90:
                    severity = Notification.Severity.WARNING
                    verb = "at 90%"
                else:
                    severity = Notification.Severity.INFO
                    verb = "at 75%"

                _notify(
                    org=org,
                    recipients=admins,
                    title=f"Budget {verb} — {label}",
                    message=(
                        f"Budget '{label}' has reached {pct}% utilisation "
                        f"(Spent: {total_spent:,.2f} / Budgeted: {total_budgeted:,.2f}). "
                        f"{'Immediate action required.' if threshold == 100 else 'Review spending commitments.'}"
                    ),
                    severity=severity,
                    category=Notification.Category.SYSTEM,
                    link_url="/finance/budgets",
                    event_key="budget_threshold",
                )
                count += 1
                break  # Only alert for the highest threshold crossed

    return count


# ── 5. Certification Expiring (HR) ────────────────────────────────────


def _check_certifications_expiring(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    today = date.today()

    # Check employee certifications
    try:
        from apps.hr.models import EmployeeCertification
        thresholds = [
            (30, "30 days", Notification.Severity.WARNING),
            (14, "14 days", Notification.Severity.WARNING),
            (7, "7 days", Notification.Severity.CRITICAL),
        ]

        for days, label, severity in thresholds:
            target = today + timedelta(days=days)
            expiring = EmployeeCertification.objects.filter(
                organization=org,
                expiry_date=target,
            ).select_related("employee")

            for cert in expiring:
                emp_name = getattr(cert.employee, "full_name", str(cert.employee)) if cert.employee else "Unknown"
                cert_name = getattr(cert, "certification_name", "") or getattr(cert, "name", f"Cert #{cert.pk}")
                _notify(
                    org=org,
                    recipients=admins,
                    title=f"Certification Expiring in {label} — {emp_name}",
                    message=(
                        f"{cert_name} for {emp_name} expires on "
                        f"{cert.expiry_date.strftime('%d %B %Y')}. "
                        f"Please arrange renewal."
                    ),
                    severity=severity,
                    category=Notification.Category.HR_LIFECYCLE,
                    link_url="/hr/certifications",
                    event_key="certification_expiring",
                )
                count += 1
    except (ImportError, Exception):
        logger.debug("HR certification check skipped", exc_info=True)

    # Check employee licenses
    try:
        from apps.hr.models import EmployeeLicense
        for days, label, severity in [(30, "30 days", Notification.Severity.WARNING), (7, "7 days", Notification.Severity.CRITICAL)]:
            target = today + timedelta(days=days)
            expiring = EmployeeLicense.objects.filter(
                organization=org,
                expiry_date=target,
            ).select_related("employee")

            for lic in expiring:
                emp_name = getattr(lic.employee, "full_name", str(lic.employee)) if lic.employee else "Unknown"
                lic_name = getattr(lic, "license_name", "") or getattr(lic, "name", f"License #{lic.pk}")
                _notify(
                    org=org,
                    recipients=admins,
                    title=f"License Expiring in {label} — {emp_name}",
                    message=(
                        f"{lic_name} for {emp_name} expires on "
                        f"{lic.expiry_date.strftime('%d %B %Y')}. "
                        f"Renewal required for compliance."
                    ),
                    severity=severity,
                    category=Notification.Category.HR_LIFECYCLE,
                    link_url="/hr/licenses",
                    event_key="license_expiring",
                )
                count += 1
    except (ImportError, Exception):
        logger.debug("HR license check skipped", exc_info=True)

    return count


# ── 6. Ticket SLA Breach (Support Desk) ───────────────────────────────


def _check_ticket_sla_breaches(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.support_desk.models import Ticket
    except ImportError:
        return 0

    from django.utils import timezone
    now = timezone.now()

    open_tickets = Ticket.objects.filter(
        organization=org,
        status__in=["open", "in_progress", "pending"],
    )

    for ticket in open_tickets[:50]:
        # Check response SLA
        sla_hours = getattr(ticket, "sla_response_hours", None) or getattr(ticket, "response_sla_hours", None)
        if not sla_hours:
            continue

        created = ticket.created_at
        deadline = created + timedelta(hours=sla_hours)
        if now > deadline:
            hours_overdue = round((now - deadline).total_seconds() / 3600, 1)
            ticket_ref = getattr(ticket, "ticket_number", "") or f"#{ticket.pk}"
            severity = Notification.Severity.CRITICAL if hours_overdue > 24 else Notification.Severity.WARNING
            _notify(
                org=org,
                recipients=admins,
                title=f"SLA Breach ({hours_overdue}h) — {ticket_ref}",
                message=(
                    f"Ticket {ticket_ref} has breached its {sla_hours}h SLA by "
                    f"{hours_overdue} hours. Subject: {ticket.title[:80]}. "
                    f"Immediate attention required."
                ),
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/support-desk/tickets",
                event_key="ticket_sla_breach",
            )
            count += 1

    return count


# ── 7. Approval Pending (assigned to specific user) ───────────────────


def _check_pending_approvals(org) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.workflows.models import WorkflowStep
    except ImportError:
        return 0

    from django.utils import timezone
    now = timezone.now()

    pending_steps = WorkflowStep.objects.filter(
        workflow_instance__organization=org,
        decision="pending",
    ).select_related("workflow_instance", "approver_user")

    for step in pending_steps[:50]:
        if not step.approver_user:
            continue

        # Only notify if pending for more than 4 hours
        assigned_at = step.assigned_at if hasattr(step, "assigned_at") else step.workflow_instance.submitted_at
        if not assigned_at:
            continue
        if (now - assigned_at).total_seconds() < 4 * 3600:
            continue

        hours_pending = round((now - assigned_at).total_seconds() / 3600, 1)
        wi = step.workflow_instance
        obj_name = str(wi.content_object) if wi.content_object else f"Record #{wi.object_id}"

        _notify(
            org=org,
            recipients=[step.approver_user],
            title=f"Approval Pending ({hours_pending}h) — {obj_name}",
            message=(
                f"You have a pending approval for '{obj_name}' that has been "
                f"waiting {hours_pending} hours. "
                f"{'SLA deadline approaching.' if hours_pending > 24 else 'Please review when convenient.'}"
            ),
            severity=Notification.Severity.WARNING if hours_pending > 24 else Notification.Severity.INFO,
            category=Notification.Category.SYSTEM,
            link_url="/settings/workflows",
            event_key="approval_pending",
        )
        count += 1

    return count


# ── 8. Meeting Starting Soon (1 hour reminder) ────────────────────────


def _check_meetings_starting_soon(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.meetings.models import Meeting
    except ImportError:
        return 0

    from django.utils import timezone
    now = timezone.now()
    one_hour = now + timedelta(hours=1)

    upcoming = Meeting.objects.filter(
        organization=org,
        status="scheduled",
        scheduled_start__gte=now,
        scheduled_start__lte=one_hour,
    ).select_related("project")

    for meeting in upcoming:
        start_time = meeting.scheduled_start.strftime("%H:%M")
        project_name = meeting.project.name if meeting.project else ""

        # Notify attendees who are users
        attendee_user_ids = list(
            meeting.attendees.filter(user__isnull=False).values_list("user_id", flat=True)
        )
        if meeting.organized_by_id:
            attendee_user_ids.append(meeting.organized_by_id)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_recipients = list(User.objects.filter(pk__in=set(attendee_user_ids), is_active=True))
        if not user_recipients:
            user_recipients = admins

        _notify(
            org=org,
            recipients=user_recipients,
            title=f"Meeting in 1 Hour — {meeting.title}",
            message=(
                f"'{meeting.title}' starts at {start_time}"
                + (f" ({meeting.location})" if meeting.location else "")
                + (f" for {project_name}" if project_name else "")
                + f". {meeting.attendees.count()} attendees."
                + (f" Join: {meeting.meeting_link}" if meeting.meeting_link else "")
            ),
            severity=Notification.Severity.INFO,
            category=Notification.Category.SYSTEM,
            link_url="/calendar",
            event_key="meeting_reminder",
        )
        count += 1

    return count


# ── 9. Meeting Action Items Overdue ───────────────────────────────────


def _check_action_items_overdue(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.meetings.models import MeetingActionItem
    except ImportError:
        return 0

    today = date.today()
    overdue = MeetingActionItem.objects.filter(
        meeting__organization=org,
        status__in=["open", "in_progress"],
        due_date__lt=today,
    ).select_related("meeting")

    for ai in overdue[:30]:
        days_overdue = (today - ai.due_date).days
        if days_overdue not in (1, 3, 7, 14) and days_overdue % 7 != 0:
            continue

        meeting_ref = ai.meeting.meeting_number if ai.meeting else ""
        severity = Notification.Severity.CRITICAL if days_overdue > 7 else Notification.Severity.WARNING

        _notify(
            org=org,
            recipients=admins,
            title=f"Action Item Overdue ({days_overdue}d) — {meeting_ref}",
            message=(
                f"Action item from {meeting_ref}: \"{ai.description[:80]}\" "
                f"assigned to {ai.assigned_to} was due {ai.due_date.strftime('%d/%m/%Y')} "
                f"({days_overdue} days ago)."
            ),
            severity=severity,
            category=Notification.Category.SYSTEM,
            link_url="/calendar",
            event_key="action_item_overdue",
        )
        count += 1

        # Also update the status
        if ai.status != "overdue":
            MeetingActionItem.objects.filter(pk=ai.pk).update(status="overdue")

    return count


# ── 10. Project Milestone Overdue ─────────────────────────────────────


def _check_milestones_overdue(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    try:
        from apps.projects.models import ProjectMilestone
    except ImportError:
        return 0

    today = date.today()
    overdue = ProjectMilestone.objects.filter(
        organization=org,
        is_completed=False,
        target_date__lt=today,
    ).select_related("phase", "phase__project")

    for ms in overdue[:30]:
        days_overdue = (today - ms.target_date).days
        if days_overdue not in (1, 3, 7, 14, 30) and days_overdue % 30 != 0:
            continue

        project_name = ms.phase.project.name if ms.phase and ms.phase.project else "Unknown Project"
        phase_name = ms.phase.name if ms.phase else ""
        severity = Notification.Severity.CRITICAL if days_overdue > 14 else Notification.Severity.WARNING

        _notify(
            org=org,
            recipients=admins,
            title=f"Milestone Overdue ({days_overdue}d) — {ms.name}",
            message=(
                f"Milestone '{ms.name}' for {project_name}"
                + (f" (Phase: {phase_name})" if phase_name else "")
                + f" was due {ms.target_date.strftime('%d/%m/%Y')} ({days_overdue} days ago). "
                + f"This may be blocking downstream tasks and stage gates."
            ),
            severity=severity,
            category=Notification.Category.PROJECT_UPDATE,
            link_url="/projects/milestones-stage-gates",
            event_key="milestone_overdue",
        )
        count += 1

    return count


# ── 11. Compliance Deadline Approaching (14 days) ─────────────────────


def _check_compliance_deadlines(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    today = date.today()
    target_14d = today + timedelta(days=14)

    # Check facility compliance checklists
    try:
        from apps.facility_management.models import FacilityComplianceChecklist
        upcoming = FacilityComplianceChecklist.objects.filter(
            organization=org,
            due_date__lte=target_14d,
            due_date__gte=today,
        ).exclude(status__in=["completed", "passed"])

        for checklist in upcoming[:20]:
            days_left = (checklist.due_date - today).days
            name = getattr(checklist, "name", "") or getattr(checklist, "title", "") or f"Checklist #{checklist.pk}"
            severity = Notification.Severity.CRITICAL if days_left <= 3 else Notification.Severity.WARNING
            _notify(
                org=org, recipients=admins,
                title=f"Compliance Deadline in {days_left}d — {name}",
                message=f"Compliance checklist '{name}' is due on {checklist.due_date.strftime('%d/%m/%Y')} ({days_left} days). Please complete all required items.",
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/facility-management/health-safety",
                event_key="compliance_deadline",
            )
            count += 1
    except (ImportError, Exception):
        logger.debug("Compliance deadline check skipped", exc_info=True)

    # Check project permits expiring
    try:
        from apps.projects.models import ProjectPermit
        permits = ProjectPermit.objects.filter(
            organization=org,
            expiry_date__lte=target_14d,
            expiry_date__gte=today,
        ).exclude(status__in=["expired", "renewed"])

        for permit in permits[:20]:
            days_left = (permit.expiry_date - today).days
            severity = Notification.Severity.CRITICAL if days_left <= 3 else Notification.Severity.WARNING
            _notify(
                org=org, recipients=admins,
                title=f"Permit Expiring in {days_left}d — {permit.name}",
                message=f"Permit '{permit.name}' ({permit.reference}) expires on {permit.expiry_date.strftime('%d/%m/%Y')}. Initiate renewal.",
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/projects/approvals-permits",
                event_key="permit_expiring",
            )
            count += 1
    except (ImportError, Exception):
        logger.debug("Permit expiry check skipped", exc_info=True)

    return count


# ── 12. Document Expiring (30 days) ───────────────────────────────────


def _check_documents_expiring(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    today = date.today()
    target_30d = today + timedelta(days=30)

    try:
        from apps.projects.models import ProjectDocument
        expiring = ProjectDocument.objects.filter(
            organization=org,
            expiry_date__lte=target_30d,
            expiry_date__gte=today,
        ).exclude(execution_status="superseded")

        for doc in expiring[:20]:
            days_left = (doc.expiry_date - today).days
            if days_left not in (30, 14, 7, 3, 1):
                continue
            severity = Notification.Severity.CRITICAL if days_left <= 7 else Notification.Severity.WARNING
            _notify(
                org=org, recipients=admins,
                title=f"Document Expiring in {days_left}d — {doc.reference}",
                message=f"Document '{doc.title}' ({doc.reference}) expires on {doc.expiry_date.strftime('%d/%m/%Y')}. Classification: {doc.get_classification_display()}.",
                severity=severity,
                category=Notification.Category.SYSTEM,
                link_url="/projects/document-control",
                event_key="document_expiring",
            )
            count += 1
    except (ImportError, Exception):
        logger.debug("Document expiry check skipped", exc_info=True)

    return count


# ── 13. Training Plan/Certification Overdue ───────────────────────────


def _check_training_overdue(org, admins) -> int:
    from apps.notifications.models import Notification

    count = 0
    today = date.today()

    # Check overdue training plans
    try:
        from apps.hr.models import TrainingPlan
        overdue = TrainingPlan.objects.filter(
            organization=org,
            due_date__lt=today,
        ).exclude(status__in=["completed", "cancelled"])

        for plan in overdue[:20]:
            days_overdue = (today - plan.due_date).days
            if days_overdue not in (1, 7, 14, 30) and days_overdue % 30 != 0:
                continue
            plan_name = getattr(plan, "name", "") or getattr(plan, "title", "") or f"Plan #{plan.pk}"
            _notify(
                org=org, recipients=admins,
                title=f"Training Plan Overdue ({days_overdue}d) — {plan_name}",
                message=f"Training plan '{plan_name}' was due {plan.due_date.strftime('%d/%m/%Y')} ({days_overdue} days ago). Please follow up with assigned employees.",
                severity=Notification.Severity.WARNING,
                category=Notification.Category.HR_LIFECYCLE,
                link_url="/hr/training-plans",
                event_key="training_plan_overdue",
            )
            count += 1
    except (ImportError, Exception):
        logger.debug("Training plan overdue check skipped", exc_info=True)

    # Check overdue training completions
    try:
        from apps.hr.models import TrainingCompletion
        overdue = TrainingCompletion.objects.filter(
            organization=org,
            due_date__lt=today,
            completed_date__isnull=True,
        )

        for tc in overdue[:20]:
            days_overdue = (today - tc.due_date).days
            if days_overdue not in (1, 7, 14) and days_overdue % 14 != 0:
                continue
            emp_name = str(tc.employee) if hasattr(tc, "employee") and tc.employee else "Unknown"
            course_name = str(tc.course) if hasattr(tc, "course") and tc.course else getattr(tc, "training_name", f"Training #{tc.pk}")
            _notify(
                org=org, recipients=admins,
                title=f"Training Overdue ({days_overdue}d) — {emp_name}",
                message=f"{emp_name} has not completed '{course_name}' which was due {tc.due_date.strftime('%d/%m/%Y')} ({days_overdue} days ago).",
                severity=Notification.Severity.WARNING,
                category=Notification.Category.HR_LIFECYCLE,
                link_url="/hr/training-completions",
                event_key="training_completion_overdue",
            )
            count += 1
    except (ImportError, Exception):
        logger.debug("Training completion overdue check skipped", exc_info=True)

    return count

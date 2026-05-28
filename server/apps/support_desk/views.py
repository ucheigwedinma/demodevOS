from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q, Sum
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.services import dispatch_workflow_notification, get_workflow_notification_catalog
from apps.settings.models import (
    Department,
    NotificationChannel,
    NotificationChannelSettings,
    NotificationTemplate,
    Role,
)
from apps.settings.permissions import HasRolePermission

from .models import (
    SupportAutomationRule,
    SupportAutomationRun,
    SupportCommunicationLog,
    SupportKnowledgeArticle,
    SupportSlaPolicy,
    SupportTicket,
    SupportTicketComment,
    default_first_response_hours_for_priority,
    default_sla_hours_for_priority,
)
from .serializers import (
    SupportAutomationOverviewSerializer,
    SupportAutomationRuleSerializer,
    SupportAutomationRunSerializer,
    SupportCommunicationLogDetailSerializer,
    SupportCommunicationLogListSerializer,
    SupportCommunicationLogWriteSerializer,
    SupportCommunicationOverviewSerializer,
    SupportCommunicationWhatsAppSendSerializer,
    SupportDeskConfigurationOverviewSerializer,
    SupportDeskOverviewSerializer,
    SupportDeskReportsOverviewSerializer,
    SupportDeskTicketLookupsSerializer,
    SupportKnowledgeArticleDetailSerializer,
    SupportKnowledgeArticleFeedbackSerializer,
    SupportKnowledgeArticleListSerializer,
    SupportKnowledgeArticleWriteSerializer,
    SupportKnowledgeBaseOverviewSerializer,
    SupportRequestWriteSerializer,
    SupportSlaEscalationsOverviewSerializer,
    SupportSlaEscalationTicketSerializer,
    SupportSlaPolicySerializer,
    SupportTicketAssignSerializer,
    SupportTicketAttachmentSerializer,
    SupportTicketAttachmentWriteSerializer,
    SupportTicketCloseSerializer,
    SupportTicketDetailSerializer,
    SupportTicketEscalateSerializer,
    SupportTicketInternalNoteSerializer,
    SupportTicketLinkSerializer,
    SupportTicketListSerializer,
    SupportTicketPrioritySerializer,
    SupportTicketReplySerializer,
    SupportTicketWriteSerializer,
)
from .sla import format_sla_target_hours, get_ticket_sla_targets, get_ticket_sla_timeline
from .whatsapp_providers import get_whatsapp_provider_adapter


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    # All users are org-scoped — no bypass
    return False


def _requested_org_id(request):
    raw = request.query_params.get("organization_id") or request.query_params.get("org_id")
    if raw in (None, ""):
        return None
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _scope_queryset_for_request(request, queryset, *, org_field: str = "organization"):
    if _is_superuser(request):
        requested_org_id = _requested_org_id(request)
        if requested_org_id:
            org_id_field = org_field if org_field.endswith("_id") else f"{org_field}_id"
            return queryset.filter(**{org_id_field: requested_org_id})
        return queryset

    organization = _user_org(request)
    if organization is None:
        return queryset.none()
    return queryset.filter(**{org_field: organization})


def _ticket_queryset(request):
    queryset = (
        SupportTicket.objects
        .select_related("requester", "customer", "contact_account", "department", "assigned_agent", "invoice", "invoice__property", "team")
        .prefetch_related("linked_tickets", "comments", "attachments")
    )
    queryset = _scope_queryset_for_request(request, queryset, org_field="organization")
    # Workspace team visibility: hide tickets attached to secret teams the
    # caller doesn't belong to. Tickets without a team scope (`team__isnull`)
    # behave exactly as before — no regression on existing data.
    # See docs/workspace-teams-design.md §12.
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from django.db.models import Q
        queryset = queryset.exclude(
            Q(team__isnull=False)
            & Q(team__visibility="secret")
            & ~Q(team__memberships__user=user)
        )
    return queryset


def _user_display(user) -> str:
    if user is None:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _format_duration_hours(hours: float | None) -> str:
    if hours is None:
        return "--"
    total_minutes = round(hours * 60)
    duration_hours, duration_minutes = divmod(total_minutes, 60)
    if duration_hours == 0:
        return f"{duration_minutes}m"
    if duration_minutes == 0:
        return f"{duration_hours}h"
    return f"{duration_hours}h {duration_minutes}m"


def _average_duration_hours(values) -> float | None:
    durations = [
        duration.total_seconds() / 3600
        for duration in values
        if duration is not None and duration.total_seconds() >= 0
    ]
    if not durations:
        return None
    return round(sum(durations) / len(durations), 2)


SUPPORT_STANDARD_REPORTS = [
    {
        "key": "tickets_by_department",
        "title": "Tickets by Department",
        "description": "Track support workload distribution across business departments.",
    },
    {
        "key": "tickets_by_category",
        "title": "Tickets by Category",
        "description": "Break down support demand by issue/request category.",
    },
    {
        "key": "resolution_time",
        "title": "Resolution Time",
        "description": "Measure average ticket resolution turnaround.",
    },
    {
        "key": "agent_performance",
        "title": "Agent Performance",
        "description": "Review handled volume, SLA outcomes, and response quality by agent.",
    },
    {
        "key": "sla_compliance",
        "title": "SLA Compliance",
        "description": "Track resolved tickets meeting SLA targets versus breached tickets.",
    },
    {
        "key": "escalation_rate",
        "title": "Escalation Rate",
        "description": "Monitor escalation frequency across the selected reporting window.",
    },
    {
        "key": "customer_satisfaction",
        "title": "Customer Satisfaction",
        "description": "Measure ticket feedback scores submitted by requesters.",
    },
]


SUPPORT_REQUEST_TYPE_CATALOG = [
    {
        "key": "it_access",
        "label": "IT Access Request",
        "description": "Provision system access, role permissions, or shared tools for a user.",
        "approval_required": True,
        "sla_target_hours": 8,
        "is_active": True,
    },
    {
        "key": "software_installation",
        "label": "Software Installation",
        "description": "Install or update approved software on a workstation or endpoint.",
        "approval_required": True,
        "sla_target_hours": 24,
        "is_active": True,
    },
    {
        "key": "password_reset",
        "label": "Password Reset",
        "description": "Reset a locked or expired account password for an internal user.",
        "approval_required": False,
        "sla_target_hours": 2,
        "is_active": True,
    },
    {
        "key": "hr_policy",
        "label": "HR Policy Clarification",
        "description": "Clarify leave, benefits, or employee policy interpretation.",
        "approval_required": False,
        "sla_target_hours": 16,
        "is_active": True,
    },
    {
        "key": "finance_payment",
        "label": "Finance Payment Inquiry",
        "description": "Track payment status, remittance timing, or invoice settlement queries.",
        "approval_required": True,
        "sla_target_hours": 24,
        "is_active": True,
    },
    {
        "key": "facility_maintenance",
        "label": "Facility Maintenance",
        "description": "Log facilities faults and maintenance work requests.",
        "approval_required": False,
        "sla_target_hours": 12,
        "is_active": True,
    },
]


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except (TypeError, ValueError, AttributeError):
        return None


def _report_window_from_request(request) -> tuple[date, date]:
    today = timezone.localdate()
    end_date = _parse_iso_date(request.query_params.get("end_date")) or today
    start_date = _parse_iso_date(request.query_params.get("start_date"))

    if start_date is None:
        try:
            days = int(str(request.query_params.get("days", "30")).strip())
        except (TypeError, ValueError):
            days = 30
        days = max(1, min(days, 365))
        start_date = end_date - timedelta(days=days - 1)

    if start_date > end_date:
        start_date = end_date

    return start_date, end_date


def _sync_ticket_comment_from_communication(log: SupportCommunicationLog):
    if not log.ticket_id:
        return

    content = (log.message or "").strip() or (log.transcript or "").strip() or (log.subject or "").strip()
    if not content:
        return

    if log.interaction_type == SupportCommunicationLog.InteractionType.INTERNAL_NOTE:
        SupportTicketComment.objects.create(
            ticket=log.ticket,
            author=log.author,
            comment_type=SupportTicketComment.CommentType.INTERNAL_NOTE,
            body=content,
        )
        return

    if log.interaction_type in {
        SupportCommunicationLog.InteractionType.TICKET_CONVERSATION,
        SupportCommunicationLog.InteractionType.EMAIL_REPLY,
        SupportCommunicationLog.InteractionType.WHATSAPP,
    }:
        SupportTicketComment.objects.create(
            ticket=log.ticket,
            author=log.author,
            comment_type=SupportTicketComment.CommentType.REQUESTER_REPLY,
            body=content,
        )
        update_fields = ["updated_at"]
        if log.ticket.first_response_at is None:
            log.ticket.first_response_at = timezone.now()
            update_fields.append("first_response_at")
        if log.ticket.status not in {
            SupportTicket.Status.RESOLVED,
            SupportTicket.Status.CLOSED,
            SupportTicket.Status.ESCALATED,
        }:
            log.ticket.status = SupportTicket.Status.PENDING_REQUESTER
            update_fields.append("status")
        log.ticket.save(update_fields=update_fields)


def _notify_user(
    *,
    recipient,
    event_key: str,
    title: str,
    message: str,
    template_context: dict[str, object] | None = None,
    category: str = Notification.Category.SYSTEM,
    severity: str = Notification.Severity.INFO,
    link_url: str = "",
):
    if recipient is None:
        return
    organization = getattr(getattr(recipient, "profile", None), "organization", None)
    dispatch_workflow_notification(
        organization=organization,
        event_key=event_key,
        recipients=[recipient],
        context=template_context or {},
        link_url=link_url,
        fallback_channels=["in_app"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=category,
        fallback_severity=severity,
    )


def _notify_user_once(
    *,
    recipient,
    event_key: str,
    title: str,
    message: str,
    template_context: dict[str, object] | None = None,
    category: str = Notification.Category.SYSTEM,
    severity: str = Notification.Severity.INFO,
    link_url: str = "",
):
    if recipient is None:
        return

    if Notification.objects.filter(
        recipient=recipient,
        title=title,
        category=category,
    ).exists():
        return

    _notify_user(
        recipient=recipient,
        event_key=event_key,
        title=title,
        message=message,
        template_context=template_context,
        category=category,
        severity=severity,
        link_url=link_url,
    )


def _ticket_manager(ticket: SupportTicket):
    if ticket.department_id and ticket.department and ticket.department.head_id:
        return ticket.department.head

    User = get_user_model()
    return (
        User.objects
        .filter(
            profile__organization=ticket.organization,
            profile__user_status="active",
        )
        .filter(
            Q(profile__assigned_role__slug__icontains="manager")
            | Q(profile__assigned_role__name__icontains="manager")
        )
        .first()
    )


def _breach_recipients(ticket: SupportTicket, role_hint: str):
    User = get_user_model()
    role_hint = (role_hint or "director").strip()

    recipients_qs = (
        User.objects
        .filter(
            profile__organization=ticket.organization,
            profile__user_status="active",
        )
        .filter(
            Q(profile__assigned_role__slug__icontains=role_hint)
            | Q(profile__assigned_role__name__icontains=role_hint)
            | Q(profile__job_title__icontains=role_hint)
        )
        .distinct()
    )
    recipients = list(recipients_qs[:6])
    if recipients:
        return recipients

    return list(
        User.objects.filter(
            profile__organization=ticket.organization,
            profile__role="admin",
            profile__user_status="active",
        )[:6]
    )


def _to_float(value, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _automation_rule_matches(
    rule: SupportAutomationRule,
    ticket: SupportTicket,
    *,
    trigger_context: dict[str, object] | None = None,
) -> bool:
    conditions = rule.conditions or {}
    trigger_context = trigger_context or {}

    subject_contains = str(conditions.get("subject_contains", "")).strip().lower()
    if subject_contains and subject_contains not in (ticket.subject or "").lower():
        return False

    condition_category = str(conditions.get("category", "")).strip()
    if condition_category and ticket.category != condition_category:
        return False

    condition_priority = str(conditions.get("priority", "")).strip()
    if condition_priority and ticket.priority != condition_priority:
        return False

    condition_status = str(conditions.get("status", "")).strip()
    if condition_status and ticket.status != condition_status:
        return False

    status_changed_to = str(conditions.get("status_changed_to", "")).strip()
    if status_changed_to:
        previous_status = str(trigger_context.get("previous_status", "")).strip()
        if previous_status == ticket.status:
            return False
        if ticket.status != status_changed_to:
            return False

    sla_progress_gte = conditions.get("sla_progress_gte")
    if sla_progress_gte is not None:
        resolution_progress = _to_float(trigger_context.get("resolution_progress_percent"))
        if resolution_progress < _to_float(sla_progress_gte):
            return False

    sla_breach_imminent_hours = conditions.get("sla_breach_imminent_hours")
    if sla_breach_imminent_hours is not None:
        now = trigger_context.get("now") or timezone.now()
        if ticket.sla_deadline is None:
            return False
        remaining_hours = (ticket.sla_deadline - now).total_seconds() / 3600
        threshold_hours = _to_float(sla_breach_imminent_hours, fallback=0.0)
        if remaining_hours < 0 or remaining_hours > threshold_hours:
            return False

    return True


def _automation_apply_actions(
    rule: SupportAutomationRule,
    ticket: SupportTicket,
    *,
    actor=None,
) -> dict[str, object]:
    actions = rule.actions or {}
    notes: list[str] = []
    update_fields: list[str] = []
    now = timezone.now()

    assign_department_id = actions.get("assign_department_id")
    if assign_department_id:
        department = Department.objects.filter(
            id=assign_department_id,
            division__organization=ticket.organization,
            is_active=True,
        ).first()
        if department and ticket.department_id != department.id:
            ticket.department = department
            update_fields.append("department")
            notes.append(f"Assigned to department {department.name}")

    assign_agent_id = actions.get("assign_agent_id")
    if assign_agent_id:
        User = get_user_model()
        assignee = User.objects.filter(
            id=assign_agent_id,
            profile__organization=ticket.organization,
            profile__user_status="active",
        ).first()
        if assignee and ticket.assigned_agent_id != assignee.id:
            ticket.assigned_agent = assignee
            update_fields.append("assigned_agent")
            notes.append(f"Assigned to {assignee.get_full_name().strip() or assignee.email}")

            _notify_user(
                recipient=assignee,
                event_key="support_ticket_assigned",
                title=f"Assigned ticket {ticket.ticket_id}",
                message=f"You have been assigned support ticket {ticket.ticket_id}: {ticket.subject}",
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "requester_name": _user_display(ticket.requester),
                    "action_url": "/support-desk/tickets",
                },
                link_url="/support-desk/tickets",
            )

    set_priority = str(actions.get("set_priority", "")).strip()
    if set_priority and set_priority in dict(SupportTicket.Priority.choices):
        if ticket.priority != set_priority:
            ticket.priority = set_priority
            ticket.sla_deadline = ticket.computed_sla_deadline()
            update_fields.extend(["priority", "sla_deadline"])
            notes.append(f"Priority set to {ticket.get_priority_display()}")

    set_status = str(actions.get("set_status", "")).strip()
    if set_status and set_status in dict(SupportTicket.Status.choices):
        if ticket.status != set_status:
            ticket.status = set_status
            update_fields.append("status")
            notes.append(f"Status set to {ticket.get_status_display()}")
            if set_status == SupportTicket.Status.ESCALATED and ticket.escalated_at is None:
                ticket.escalated_at = now
                update_fields.append("escalated_at")

    if actions.get("escalate_to_supervisor"):
        supervisor = _ticket_manager(ticket)
        if ticket.status != SupportTicket.Status.ESCALATED:
            ticket.status = SupportTicket.Status.ESCALATED
            update_fields.append("status")
        if ticket.escalated_at is None:
            ticket.escalated_at = now
            update_fields.append("escalated_at")
        notes.append("Escalated to supervisor")

        if supervisor and ticket.assigned_agent_id != supervisor.id:
            ticket.assigned_agent = supervisor
            update_fields.append("assigned_agent")
            notes.append(f"Supervisor assigned: {_user_display(supervisor)}")
            _notify_user(
                recipient=supervisor,
                event_key="support_ticket_escalated",
                title=f"Escalated ticket {ticket.ticket_id}",
                message=f"Ticket {ticket.ticket_id} has been escalated to you by automation.",
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "action_url": "/support-desk/tickets",
                },
                category=Notification.Category.WORKFLOW_ESCALATED,
                severity=Notification.Severity.WARNING,
                link_url="/support-desk/tickets",
            )

    if update_fields:
        ticket.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])

    note_text = str(actions.get("add_internal_note", "")).strip()
    if note_text:
        SupportTicketComment.objects.create(
            ticket=ticket,
            author=actor,
            comment_type=SupportTicketComment.CommentType.INTERNAL_NOTE,
            body=f"[Automation: {rule.name}] {note_text}",
        )
        notes.append("Internal note posted")

    return {
        "notes": notes,
        "ticket_id": ticket.id,
        "ticket_ref": ticket.ticket_id,
    }


def _run_ticket_automation(
    ticket: SupportTicket,
    *,
    trigger_type: str,
    actor=None,
    trigger_context: dict[str, object] | None = None,
):
    rules = (
        SupportAutomationRule.objects
        .filter(
            organization=ticket.organization,
            is_active=True,
            trigger_type=trigger_type,
        )
        .order_by("priority", "id")
    )

    for rule in rules:
        if rule.run_once_per_ticket and SupportAutomationRun.objects.filter(
            rule=rule,
            ticket=ticket,
            status=SupportAutomationRun.Status.MATCHED,
        ).exists():
            continue

        if not _automation_rule_matches(rule, ticket, trigger_context=trigger_context):
            continue

        try:
            details = _automation_apply_actions(rule, ticket, actor=actor)
            summary = "; ".join(details.get("notes") or []) or "Rule matched with no field updates."
            SupportAutomationRun.objects.create(
                organization=ticket.organization,
                rule=rule,
                ticket=ticket,
                trigger_type=trigger_type,
                status=SupportAutomationRun.Status.MATCHED,
                summary=summary,
                details=details,
            )
        except Exception as exc:
            SupportAutomationRun.objects.create(
                organization=ticket.organization,
                rule=rule,
                ticket=ticket,
                trigger_type=trigger_type,
                status=SupportAutomationRun.Status.FAILED,
                summary=f"Automation failed: {exc}",
                details={"error": str(exc)},
            )


def _evaluate_ticket_sla(ticket: SupportTicket, *, now=None):
    now = now or timezone.now()

    if ticket.status in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED}:
        return None

    targets = get_ticket_sla_targets(ticket)
    policy = targets["policy"]
    timeline = get_ticket_sla_timeline(ticket, now=now, targets=targets)

    resolution_deadline = timeline["resolution_deadline_at"]
    if ticket.sla_deadline != resolution_deadline:
        type(ticket).objects.filter(pk=ticket.pk).update(
            sla_deadline=resolution_deadline,
            updated_at=now,
        )
        ticket.sla_deadline = resolution_deadline

    resolution_progress = timeline["resolution_progress_percent"]
    agent_threshold = policy.agent_notify_threshold_percent if policy else 50
    manager_threshold = policy.manager_notify_threshold_percent if policy else 80
    notify_agent = policy.notify_assigned_agent if policy else True
    notify_manager = policy.notify_manager if policy else True

    _run_ticket_automation(
        ticket,
        trigger_type=SupportAutomationRule.TriggerType.SLA_THRESHOLD,
        trigger_context={
            "now": now,
            "resolution_progress_percent": resolution_progress,
            "resolution_deadline_at": timeline["resolution_deadline_at"],
        },
    )

    if notify_agent and ticket.assigned_agent_id and resolution_progress >= agent_threshold:
        _notify_user_once(
            recipient=ticket.assigned_agent,
            event_key="support_sla_threshold_agent",
            title=f"SLA {agent_threshold}% reached - {ticket.ticket_id}",
            message=(
                f"Ticket {ticket.ticket_id} has reached {agent_threshold}% "
                "of its SLA resolution window."
            ),
            template_context={
                "ticket_id": ticket.ticket_id,
                "ticket_subject": ticket.subject,
                "action_url": "/support-desk/sla-escalations",
            },
            category=Notification.Category.WORKFLOW_SLA_WARNING,
            severity=Notification.Severity.WARNING,
            link_url="/support-desk/sla-escalations",
        )

    if notify_manager and resolution_progress >= manager_threshold:
        manager = _ticket_manager(ticket)
        _notify_user_once(
            recipient=manager,
            event_key="support_sla_threshold_manager",
            title=f"SLA {manager_threshold}% reached - {ticket.ticket_id}",
            message=(
                f"Ticket {ticket.ticket_id} has reached {manager_threshold}% "
                "of its SLA resolution window."
            ),
            template_context={
                "ticket_id": ticket.ticket_id,
                "ticket_subject": ticket.subject,
                "action_url": "/support-desk/sla-escalations",
            },
            category=Notification.Category.WORKFLOW_SLA_WARNING,
            severity=Notification.Severity.WARNING,
            link_url="/support-desk/sla-escalations",
        )

    if timeline["resolution_breached"]:
        if ticket.status not in {
            SupportTicket.Status.ESCALATED,
            SupportTicket.Status.RESOLVED,
            SupportTicket.Status.CLOSED,
        }:
            type(ticket).objects.filter(pk=ticket.pk).update(
                status=SupportTicket.Status.ESCALATED,
                escalated_at=now,
                updated_at=now,
            )
            ticket.status = SupportTicket.Status.ESCALATED
            ticket.escalated_at = now

        if ticket.assigned_agent_id:
            _notify_user_once(
                recipient=ticket.assigned_agent,
                event_key="support_sla_breached_agent",
                title=f"SLA breached - {ticket.ticket_id}",
                message=(
                    f"Ticket {ticket.ticket_id} has breached its SLA resolution "
                    "target and was escalated."
                ),
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "action_url": "/support-desk/sla-escalations",
                },
                category=Notification.Category.WORKFLOW_ESCALATED,
                severity=Notification.Severity.CRITICAL,
                link_url="/support-desk/sla-escalations",
            )

        breach_role = policy.breach_escalation_role if policy else "director"
        for recipient in _breach_recipients(ticket, breach_role):
            _notify_user_once(
                recipient=recipient,
                event_key="support_sla_breached_director",
                title=f"SLA breached - {ticket.ticket_id}",
                message=(
                    f"Ticket {ticket.ticket_id} has breached SLA and requires "
                    f"{breach_role} escalation."
                ),
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "action_url": "/support-desk/sla-escalations",
                },
                category=Notification.Category.WORKFLOW_ESCALATED,
                severity=Notification.Severity.CRITICAL,
                link_url="/support-desk/sla-escalations",
            )

    return {
        "targets": targets,
        "timeline": timeline,
    }


def _build_sla_policy_matrix(request):
    active_policies = _scope_queryset_for_request(
        request,
        SupportSlaPolicy.objects.filter(is_active=True),
        org_field="organization",
    )

    matrix = []
    for priority, label in SupportTicket.Priority.choices:
        policy = (
            active_policies.filter(priority=priority).order_by("category", "id").first()
            or active_policies.filter(priority="").order_by("category", "id").first()
        )
        if policy:
            response_hours = policy.response_target_hours
            resolution_hours = policy.resolution_target_hours
            policy_name = policy.name
            agent_threshold = policy.agent_notify_threshold_percent
            manager_threshold = policy.manager_notify_threshold_percent
            breach_role = policy.breach_escalation_role
        else:
            response_hours = default_first_response_hours_for_priority(priority)
            resolution_hours = default_sla_hours_for_priority(priority)
            policy_name = "Default SLA"
            agent_threshold = 50
            manager_threshold = 80
            breach_role = "director"

        matrix.append(
            {
                "priority": priority,
                "priority_label": label,
                "policy_name": policy_name,
                "first_response_target_display": format_sla_target_hours(response_hours),
                "resolution_target_display": format_sla_target_hours(resolution_hours),
                "agent_notify_threshold_percent": agent_threshold,
                "manager_notify_threshold_percent": manager_threshold,
                "breach_escalation_role": breach_role,
            }
        )

    return matrix


class SupportTicketFilter(filters.FilterSet):
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    updated_after = filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="lte")
    sla_breached = filters.BooleanFilter(method="filter_sla_breached")

    class Meta:
        model = SupportTicket
        fields = [
            "requester",
            "customer",
            "contact_account",
            "department",
            "category",
            "priority",
            "status",
            "assigned_agent",
        ]

    def filter_sla_breached(self, queryset, _name, value):
        if value:
            return queryset.exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]).filter(
                sla_deadline__lt=timezone.now()
            )
        return queryset


class SupportDeskOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.overview"
    rbac_action = "view"

    def get(self, request):
        tickets = _ticket_queryset(request).order_by("-created_at")
        active_tickets = tickets.exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])

        priority_breakdown = [
            {
                "key": key,
                "label": label,
                "count": tickets.filter(priority=key).count(),
            }
            for key, label in SupportTicket.Priority.choices
        ]
        status_breakdown = [
            {
                "key": key,
                "label": label,
                "count": tickets.filter(status=key).count(),
            }
            for key, label in SupportTicket.Status.choices
        ]

        resolution_hours = _average_duration_hours(
            ticket.resolved_at - ticket.created_at
            for ticket in tickets
            if ticket.resolved_at is not None
        )
        first_response_hours = _average_duration_hours(
            ticket.first_response_at - ticket.created_at
            for ticket in tickets
            if ticket.first_response_at is not None
        )

        active_by_agent: dict[int, dict[str, int | str]] = {}
        now = timezone.now()
        for ticket in active_tickets:
            if ticket.assigned_agent is None:
                continue
            agent_id = ticket.assigned_agent_id
            if agent_id not in active_by_agent:
                active_by_agent[agent_id] = {
                    "agent_id": agent_id,
                    "agent_name": ticket.assigned_agent.get_full_name().strip() or ticket.assigned_agent.email,
                    "active_tickets": 0,
                    "sla_breaches": 0,
                }
            active_by_agent[agent_id]["active_tickets"] += 1
            if ticket.sla_deadline and ticket.sla_deadline < now:
                active_by_agent[agent_id]["sla_breaches"] += 1

        customer_scores = [
            ticket.customer_satisfaction_score
            for ticket in tickets
            if ticket.customer_satisfaction_score is not None
        ]
        customer_satisfaction_score = None
        if customer_scores:
            customer_satisfaction_score = round(sum(customer_scores) / len(customer_scores), 2)

        payload = {
            "open_tickets": active_tickets.count(),
            "tickets_by_priority": priority_breakdown,
            "tickets_by_status": status_breakdown,
            "sla_breaches": active_tickets.filter(sla_deadline__lt=now).count(),
            "average_resolution_time_hours": resolution_hours,
            "average_resolution_time_display": _format_duration_hours(resolution_hours),
            "agent_workload": sorted(
                active_by_agent.values(),
                key=lambda item: (-item["active_tickets"], -item["sla_breaches"], str(item["agent_name"])),
            )[:5],
            "recent_requests": tickets[:6],
            "first_response_time_hours": first_response_hours,
            "first_response_time_display": _format_duration_hours(first_response_hours),
            "ticket_backlog": active_tickets.count(),
            "escalated_tickets": tickets.filter(status=SupportTicket.Status.ESCALATED).count(),
            "customer_satisfaction_score": customer_satisfaction_score,
            "customer_satisfaction_display": "--" if customer_satisfaction_score is None else f"{customer_satisfaction_score:.2f}/5",
        }

        serializer = SupportDeskOverviewSerializer(payload, context={"request": request})
        return Response(serializer.data)


class SupportDeskReportsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.overview"
    rbac_action = "view"

    def get(self, request):
        window_start, window_end = _report_window_from_request(request)
        now = timezone.now()

        tickets = list(
            _ticket_queryset(request)
            .filter(
                created_at__date__gte=window_start,
                created_at__date__lte=window_end,
            )
            .order_by("created_at", "id")
        )
        total_tickets = len(tickets)

        department_counts: dict[tuple[int | None, str], int] = {}
        for ticket in tickets:
            department_key = ticket.department_id
            department_name = (
                ticket.department.name
                if ticket.department_id and ticket.department
                else "Unassigned"
            )
            lookup_key = (department_key, department_name)
            department_counts[lookup_key] = department_counts.get(lookup_key, 0) + 1
        tickets_by_department = [
            {
                "key": str(department_id or "unassigned"),
                "label": department_name,
                "count": count,
            }
            for (department_id, department_name), count in department_counts.items()
        ]
        tickets_by_department.sort(key=lambda row: (-row["count"], row["label"]))

        tickets_by_category = [
            {
                "key": key,
                "label": label,
                "count": sum(1 for ticket in tickets if ticket.category == key),
            }
            for key, label in SupportTicket.Category.choices
        ]

        resolution_durations = [
            ticket.resolved_at - ticket.created_at
            for ticket in tickets
            if ticket.resolved_at is not None
        ]
        resolution_time_average_hours = _average_duration_hours(resolution_durations)

        agent_buckets: dict[int, dict[str, object]] = {}
        for ticket in tickets:
            if ticket.assigned_agent_id is None or ticket.assigned_agent is None:
                continue

            agent_id = ticket.assigned_agent_id
            bucket = agent_buckets.setdefault(
                agent_id,
                {
                    "agent_id": agent_id,
                    "agent_name": _user_display(ticket.assigned_agent),
                    "total_tickets": 0,
                    "resolved_tickets": 0,
                    "sla_breaches": 0,
                    "resolution_durations": [],
                    "customer_scores": [],
                },
            )
            bucket["total_tickets"] += 1

            if ticket.resolved_at is not None:
                bucket["resolved_tickets"] += 1
                duration = ticket.resolved_at - ticket.created_at
                if duration.total_seconds() >= 0:
                    bucket["resolution_durations"].append(duration)

            if (
                ticket.sla_deadline
                and (
                    (ticket.resolved_at is not None and ticket.resolved_at > ticket.sla_deadline)
                    or (
                        ticket.resolved_at is None
                        and ticket.status not in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED}
                        and ticket.sla_deadline < now
                    )
                )
            ):
                bucket["sla_breaches"] += 1

            if ticket.customer_satisfaction_score is not None:
                bucket["customer_scores"].append(ticket.customer_satisfaction_score)

        agent_performance = []
        for bucket in agent_buckets.values():
            average_resolution = _average_duration_hours(bucket["resolution_durations"])
            customer_scores = bucket["customer_scores"]
            average_csat = (
                round(sum(customer_scores) / len(customer_scores), 2)
                if customer_scores
                else None
            )
            agent_performance.append(
                {
                    "agent_id": bucket["agent_id"],
                    "agent_name": bucket["agent_name"],
                    "total_tickets": bucket["total_tickets"],
                    "resolved_tickets": bucket["resolved_tickets"],
                    "sla_breaches": bucket["sla_breaches"],
                    "average_resolution_hours": average_resolution,
                    "average_resolution_display": _format_duration_hours(average_resolution),
                    "customer_satisfaction_score": average_csat,
                    "customer_satisfaction_display": (
                        "--" if average_csat is None else f"{average_csat:.2f}/5"
                    ),
                }
            )
        agent_performance.sort(
            key=lambda row: (
                -row["resolved_tickets"],
                row["sla_breaches"],
                row["agent_name"],
            )
        )

        resolved_with_sla = [
            ticket
            for ticket in tickets
            if ticket.resolved_at is not None and ticket.sla_deadline is not None
        ]
        compliant_count = sum(
            1 for ticket in resolved_with_sla if ticket.resolved_at <= ticket.sla_deadline
        )
        breached_count = len(resolved_with_sla) - compliant_count
        compliance_rate = (
            round((compliant_count / len(resolved_with_sla)) * 100, 2)
            if resolved_with_sla
            else 0.0
        )

        escalated_count = sum(
            1
            for ticket in tickets
            if ticket.escalated_at is not None or ticket.status == SupportTicket.Status.ESCALATED
        )
        escalation_rate = (
            round((escalated_count / total_tickets) * 100, 2)
            if total_tickets
            else 0.0
        )

        customer_scores = [
            ticket.customer_satisfaction_score
            for ticket in tickets
            if ticket.customer_satisfaction_score is not None
        ]
        customer_average_score = (
            round(sum(customer_scores) / len(customer_scores), 2)
            if customer_scores
            else None
        )

        trend_seed: dict[date, dict[str, object]] = {}
        cursor = window_start
        while cursor <= window_end:
            trend_seed[cursor] = {
                "created_count": 0,
                "resolved_count": 0,
                "resolution_hours": [],
                "sla_compliant": 0,
                "sla_breached": 0,
            }
            cursor += timedelta(days=1)

        for ticket in tickets:
            created_day = timezone.localtime(ticket.created_at).date()
            if window_start <= created_day <= window_end:
                trend_seed[created_day]["created_count"] += 1

            if ticket.resolved_at is None:
                continue

            resolved_day = timezone.localtime(ticket.resolved_at).date()
            if not (window_start <= resolved_day <= window_end):
                continue

            trend_bucket = trend_seed[resolved_day]
            trend_bucket["resolved_count"] += 1

            duration = ticket.resolved_at - ticket.created_at
            if duration.total_seconds() >= 0:
                trend_bucket["resolution_hours"].append(duration.total_seconds() / 3600)

            if ticket.sla_deadline:
                if ticket.resolved_at <= ticket.sla_deadline:
                    trend_bucket["sla_compliant"] += 1
                else:
                    trend_bucket["sla_breached"] += 1

        ticket_trend = []
        resolution_trend = []
        sla_performance_trend = []
        for trend_date in sorted(trend_seed.keys()):
            trend_bucket = trend_seed[trend_date]
            resolution_hours: list[float] = trend_bucket["resolution_hours"]
            average_resolution = (
                round(sum(resolution_hours) / len(resolution_hours), 2)
                if resolution_hours
                else None
            )
            sla_total = trend_bucket["sla_compliant"] + trend_bucket["sla_breached"]
            day_compliance_rate = (
                round((trend_bucket["sla_compliant"] / sla_total) * 100, 2)
                if sla_total
                else 0.0
            )

            ticket_trend.append(
                {
                    "date": trend_date,
                    "created_count": trend_bucket["created_count"],
                    "resolved_count": trend_bucket["resolved_count"],
                }
            )
            resolution_trend.append(
                {
                    "date": trend_date,
                    "resolved_count": trend_bucket["resolved_count"],
                    "average_resolution_hours": average_resolution,
                    "average_resolution_display": _format_duration_hours(average_resolution),
                }
            )
            sla_performance_trend.append(
                {
                    "date": trend_date,
                    "compliant_count": trend_bucket["sla_compliant"],
                    "breached_count": trend_bucket["sla_breached"],
                    "compliance_rate": day_compliance_rate,
                }
            )

        payload = {
            "window_start": window_start,
            "window_end": window_end,
            "total_tickets": total_tickets,
            "standard_reports": SUPPORT_STANDARD_REPORTS,
            "tickets_by_department": tickets_by_department,
            "tickets_by_category": tickets_by_category,
            "resolution_time_average_hours": resolution_time_average_hours,
            "resolution_time_average_display": _format_duration_hours(
                resolution_time_average_hours
            ),
            "agent_performance": agent_performance,
            "sla_compliance": {
                "compliant_count": compliant_count,
                "breached_count": breached_count,
                "compliance_rate": compliance_rate,
            },
            "escalation_rate": {
                "escalated_count": escalated_count,
                "total_tickets": total_tickets,
                "escalation_rate": escalation_rate,
            },
            "customer_satisfaction": {
                "average_score": customer_average_score,
                "response_count": len(customer_scores),
                "display": (
                    "--" if customer_average_score is None else f"{customer_average_score:.2f}/5"
                ),
            },
            "ticket_trend": ticket_trend,
            "resolution_trend": resolution_trend,
            "sla_performance_trend": sla_performance_trend,
        }

        serializer = SupportDeskReportsOverviewSerializer(payload)
        return Response(serializer.data)


class SupportDeskConfigurationOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.automation"
    rbac_action = "view"

    def get(self, request):
        tickets = _scope_queryset_for_request(
            request,
            SupportTicket.objects.all(),
            org_field="organization",
        )

        ticket_categories = [
            {
                "key": key,
                "label": label,
                "count": tickets.filter(category=key).count(),
            }
            for key, label in SupportTicket.Category.choices
        ]
        priority_levels = [
            {
                "key": key,
                "label": label,
                "count": tickets.filter(priority=key).count(),
            }
            for key, label in SupportTicket.Priority.choices
        ]
        ticket_statuses = [
            {
                "key": key,
                "label": label,
                "count": tickets.filter(status=key).count(),
            }
            for key, label in SupportTicket.Status.choices
        ]

        support_teams = [
            {
                "id": department.id,
                "name": department.name,
                "head_name": _user_display(department.head),
                "is_active": department.is_active,
            }
            for department in (
                _scope_queryset_for_request(
                    request,
                    Department.objects.all(),
                    org_field="division__organization",
                )
                .filter(is_active=True)
                .select_related("head")
                .order_by("name")
            )
        ]

        agent_roles = [
            {
                "id": role.id,
                "name": role.name,
                "slug": role.slug,
                "user_count": role.user_count,
            }
            for role in (
                _scope_queryset_for_request(
                    request,
                    Role.objects.all(),
                    org_field="organization",
                )
                .annotate(user_count=Count("assigned_users"))
                .order_by("name")
            )
        ]

        sla_policies = _scope_queryset_for_request(
            request,
            SupportSlaPolicy.objects.all(),
            org_field="organization",
        ).order_by(
            "name", "id"
        )
        automation_rules = _scope_queryset_for_request(
            request,
            SupportAutomationRule.objects.all(),
            org_field="organization",
        ).order_by("trigger_type", "priority", "name", "id")

        support_templates_qs = _scope_queryset_for_request(
            request,
            NotificationTemplate.objects.filter(event_key__startswith="support_"),
            org_field="organization",
        ).order_by("event_key", "channel", "name")
        email_templates = [
            {
                "id": template.id,
                "code": template.code,
                "name": template.name,
                "event_key": template.event_key,
                "severity_tier": template.severity_tier,
                "is_active": template.is_active,
                "updated_at": template.updated_at,
            }
            for template in support_templates_qs.filter(channel=NotificationChannel.EMAIL)
        ]

        channel_settings = None
        requested_org_id = _requested_org_id(request)
        if requested_org_id:
            channel_settings = NotificationChannelSettings.objects.filter(
                organization_id=requested_org_id
            ).first()
        elif not _is_superuser(request):
            organization = _user_org(request)
            if organization is not None:
                channel_settings, _ = NotificationChannelSettings.objects.get_or_create(
                    organization=organization,
                    defaults={
                        "email_enabled": True,
                        "in_app_enabled": True,
                        "sms_enabled": False,
                        "push_enabled": False,
                    },
                )

        channel_settings_payload = {
            "email_enabled": True,
            "in_app_enabled": True,
            "sms_enabled": False,
            "push_enabled": False,
        }
        if channel_settings is not None:
            channel_settings_payload = {
                "email_enabled": channel_settings.email_enabled,
                "in_app_enabled": channel_settings.in_app_enabled,
                "sms_enabled": channel_settings.sms_enabled,
                "push_enabled": channel_settings.push_enabled,
            }

        enabled_channels: set[str] = set()
        if channel_settings_payload["email_enabled"]:
            enabled_channels.add(NotificationChannel.EMAIL)
        if channel_settings_payload["in_app_enabled"]:
            enabled_channels.add(NotificationChannel.IN_APP)
        if channel_settings_payload["sms_enabled"]:
            enabled_channels.add(NotificationChannel.SMS)
        if channel_settings_payload["push_enabled"]:
            enabled_channels.add(NotificationChannel.PUSH)

        channel_order = ["email", "in_app", "sms", "push"]
        channel_rank = {key: index for index, key in enumerate(channel_order)}

        coverage: dict[str, dict[str, object]] = {}
        for template in support_templates_qs:
            bucket = coverage.setdefault(
                template.event_key,
                {
                    "configured_channels": set(),
                    "active_channels": set(),
                    "total_templates": 0,
                    "active_templates": 0,
                },
            )
            bucket["configured_channels"].add(template.channel)
            bucket["total_templates"] += 1
            if template.is_active:
                bucket["active_templates"] += 1
                if template.channel in enabled_channels:
                    bucket["active_channels"].add(template.channel)

        catalog_events = [
            event
            for event in get_workflow_notification_catalog()
            if event.get("module") == "support_desk"
            or str(event.get("key", "")).startswith("support_")
        ]
        catalog_by_key = {event["key"]: event for event in catalog_events}

        notification_rules = []
        all_event_keys = sorted(
            set(catalog_by_key.keys()) | set(coverage.keys()),
            key=lambda value: value.lower(),
        )
        for event_key in all_event_keys:
            catalog_row = catalog_by_key.get(event_key)
            bucket = coverage.get(event_key) or {
                "configured_channels": set(),
                "active_channels": set(),
                "total_templates": 0,
                "active_templates": 0,
            }

            configured_channels = sorted(
                list(bucket["configured_channels"]),
                key=lambda channel: channel_rank.get(channel, 999),
            )
            active_channels = sorted(
                list(bucket["active_channels"]),
                key=lambda channel: channel_rank.get(channel, 999),
            )

            notification_rules.append(
                {
                    "key": event_key,
                    "label": (
                        catalog_row["label"]
                        if catalog_row
                        else event_key.replace("_", " ").title()
                    ),
                    "description": (
                        catalog_row["description"]
                        if catalog_row
                        else "Custom support notification event configured by administrators."
                    ),
                    "default_channels": catalog_row["default_channels"] if catalog_row else [],
                    "configured_channels": configured_channels,
                    "active_channels": active_channels,
                    "total_templates": bucket["total_templates"],
                    "active_templates": bucket["active_templates"],
                    "is_enabled": bool(active_channels),
                }
            )

        payload = {
            "ticket_categories": ticket_categories,
            "priority_levels": priority_levels,
            "ticket_statuses": ticket_statuses,
            "support_teams": support_teams,
            "agent_roles": agent_roles,
            "sla_policies": sla_policies,
            "automation_rules": automation_rules,
            "request_types": SUPPORT_REQUEST_TYPE_CATALOG,
            "email_templates": email_templates,
            "notification_rules": notification_rules,
            "channel_settings": channel_settings_payload,
        }
        serializer = SupportDeskConfigurationOverviewSerializer(
            payload,
            context={"request": request},
        )
        return Response(serializer.data)


class SupportTicketViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.tickets"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "lookups": "view",
        "assign_agent": "assign",
        "change_priority": "edit",
        "add_internal_note": "comment",
        "reply_to_requester": "comment",
        "attach_file": "edit",
        "link_related_ticket": "edit",
        "escalate": "edit",
        "close_ticket": "edit",
    }
    filterset_class = SupportTicketFilter
    search_fields = [
        "ticket_id",
        "subject",
        "description",
        "requester__first_name",
        "requester__last_name",
        "requester__email",
        "customer__name",
        "customer__email",
        "customer__phone",
        "contact_account__first_name",
        "contact_account__last_name",
        "contact_account__legal_name",
        "contact_account__trade_name",
        "contact_account__email",
        "contact_account__phone",
        "assigned_agent__first_name",
        "assigned_agent__last_name",
        "assigned_agent__email",
    ]
    ordering_fields = ["ticket_id", "created_at", "updated_at", "sla_deadline", "priority", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = _ticket_queryset(self.request)
        view_name = self.request.query_params.get("view", "").strip()

        if view_name == "open":
            queryset = queryset.exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])
        elif view_name == "mine":
            queryset = queryset.filter(assigned_agent=self.request.user)
        elif view_name == "unassigned":
            queryset = queryset.filter(assigned_agent__isnull=True).exclude(
                status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
            )
        elif view_name == "escalated":
            queryset = queryset.filter(status=SupportTicket.Status.ESCALATED)
        elif view_name == "resolved":
            queryset = queryset.filter(status=SupportTicket.Status.RESOLVED)
        elif view_name == "closed":
            queryset = queryset.filter(status=SupportTicket.Status.CLOSED)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return SupportTicketListSerializer
        if self.action == "retrieve":
            return SupportTicketDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return SupportTicketWriteSerializer
        return SupportTicketDetailSerializer

    def _run_automation_for_ticket(self, ticket: SupportTicket, *, previous_status: str | None = None):
        _run_ticket_automation(
            ticket,
            trigger_type=SupportAutomationRule.TriggerType.TICKET_UPDATED,
            actor=self.request.user,
            trigger_context={"previous_status": previous_status or ticket.status},
        )
        if previous_status is not None and previous_status != ticket.status:
            _run_ticket_automation(
                ticket,
                trigger_type=SupportAutomationRule.TriggerType.STATUS_CHANGED,
                actor=self.request.user,
                trigger_context={"previous_status": previous_status},
            )

    def perform_create(self, serializer):
        ticket = serializer.save()
        if ticket.assigned_agent_id:
            _notify_user(
                recipient=ticket.assigned_agent,
                event_key="support_ticket_assigned",
                title=f"Assigned ticket {ticket.ticket_id}",
                message=f"You have been assigned support ticket {ticket.ticket_id}: {ticket.subject}",
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "requester_name": _user_display(ticket.requester),
                    "action_url": "/support-desk/tickets",
                },
                link_url="/support-desk/tickets",
            )
        _run_ticket_automation(
            ticket,
            trigger_type=SupportAutomationRule.TriggerType.TICKET_CREATED,
            actor=self.request.user,
            trigger_context={"previous_status": ticket.status},
        )

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        ticket = serializer.save()
        self._run_automation_for_ticket(ticket, previous_status=previous_status)

    def _get_user_in_org(self, user_id: int):
        User = self.request.user.__class__
        queryset = User.objects.filter(id=user_id)
        requested_org_id = _requested_org_id(self.request)
        if _is_superuser(self.request):
            if requested_org_id:
                queryset = queryset.filter(profile__organization_id=requested_org_id)
        else:
            organization = _user_org(self.request)
            if organization is None:
                return None
            queryset = queryset.filter(profile__organization=organization)
        return queryset.first()

    @action(detail=False, methods=["get"], url_path="lookups")
    def lookups(self, request):
        from apps.crm.models import ContactAccount
        from apps.finance.models import Customer

        User = request.user.__class__
        agents = User.objects.filter(profile__user_status="active").select_related("profile")
        departments = Department.objects.filter(is_active=True)
        customers = Customer.objects.all()
        contact_accounts = ContactAccount.objects.select_related("finance_customer").filter(is_active=True)
        requested_org_id = _requested_org_id(request)
        if _is_superuser(request):
            if requested_org_id:
                agents = agents.filter(profile__organization_id=requested_org_id)
                departments = departments.filter(division__organization_id=requested_org_id)
                customers = customers.filter(organization_id=requested_org_id)
                contact_accounts = contact_accounts.filter(organization_id=requested_org_id)
        else:
            organization = _user_org(request)
            if organization is None:
                agents = agents.none()
                departments = departments.none()
                customers = customers.none()
                contact_accounts = contact_accounts.none()
            else:
                agents = agents.filter(profile__organization=organization)
                departments = departments.filter(division__organization=organization)
                customers = customers.filter(organization=organization)
                contact_accounts = contact_accounts.filter(organization=organization)
        departments = departments.order_by("name")
        customers = customers.order_by("name")
        contact_accounts = contact_accounts.order_by("-updated_at", "-id")

        payload = {
            "requesters": [
                {
                    "id": user.id,
                    "label": _user_display(user),
                    "email": user.email or "",
                }
                for user in agents.order_by("first_name", "last_name", "email")[:200]
            ],
            "agents": [
                {
                    "id": user.id,
                    "label": _user_display(user),
                    "email": user.email or "",
                }
                for user in agents.order_by("first_name", "last_name", "email")[:200]
            ],
            "departments": [
                {
                    "id": department.id,
                    "name": department.name,
                }
                for department in departments[:200]
            ],
            "customers": [
                {
                    "id": customer.id,
                    "label": customer.name,
                    "email": customer.email or "",
                    "phone": customer.phone or "",
                    "support_ticketing_enabled": bool(customer.support_ticketing_enabled),
                }
                for customer in customers[:200]
            ],
            "contact_accounts": [
                {
                    "id": contact.id,
                    "label": contact.display_name,
                    "email": contact.email or "",
                    "phone": contact.phone or "",
                    "finance_customer": contact.finance_customer_id,
                    "support_ticketing_enabled": bool(
                        contact.finance_customer and contact.finance_customer.support_ticketing_enabled
                    ),
                }
                for contact in contact_accounts[:200]
            ],
            "categories": [
                {"key": key, "label": label, "count": 0}
                for key, label in SupportTicket.Category.choices
            ],
            "priorities": [
                {"key": key, "label": label, "count": 0}
                for key, label in SupportTicket.Priority.choices
            ],
            "statuses": [
                {"key": key, "label": label, "count": 0}
                for key, label in SupportTicket.Status.choices
            ],
        }
        serializer = SupportDeskTicketLookupsSerializer(payload)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign_agent(self, request, pk=None):
        ticket = self.get_object()
        previous_status = ticket.status
        serializer = SupportTicketAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assigned_agent = self._get_user_in_org(serializer.validated_data["assigned_agent_id"])
        if assigned_agent is None:
            return Response({"detail": "Assigned agent not found in your organization."}, status=status.HTTP_400_BAD_REQUEST)

        ticket.assigned_agent = assigned_agent
        ticket.save(update_fields=["assigned_agent", "updated_at"])

        _notify_user(
            recipient=assigned_agent,
            event_key="support_ticket_assigned",
            title=f"Assigned ticket {ticket.ticket_id}",
            message=f"You have been assigned support ticket {ticket.ticket_id}: {ticket.subject}",
            template_context={
                "ticket_id": ticket.ticket_id,
                "ticket_subject": ticket.subject,
                "requester_name": _user_display(ticket.requester),
                "action_url": "/support-desk/tickets",
            },
            link_url="/support-desk/tickets",
        )
        self._run_automation_for_ticket(ticket, previous_status=previous_status)

        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="priority")
    def change_priority(self, request, pk=None):
        ticket = self.get_object()
        previous_status = ticket.status
        serializer = SupportTicketPrioritySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.priority = serializer.validated_data["priority"]
        ticket.sla_deadline = ticket.computed_sla_deadline()
        ticket.save(update_fields=["priority", "sla_deadline", "updated_at"])
        self._run_automation_for_ticket(ticket, previous_status=previous_status)

        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="internal-notes")
    def add_internal_note(self, request, pk=None):
        ticket = self.get_object()
        serializer = SupportTicketInternalNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        SupportTicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            comment_type=SupportTicketComment.CommentType.INTERNAL_NOTE,
            body=serializer.validated_data["body"],
        )

        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="reply")
    def reply_to_requester(self, request, pk=None):
        ticket = self.get_object()
        previous_status = ticket.status
        serializer = SupportTicketReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        SupportTicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            comment_type=SupportTicketComment.CommentType.REQUESTER_REPLY,
            body=serializer.validated_data["body"],
        )

        update_fields = ["updated_at"]
        if ticket.first_response_at is None:
            ticket.first_response_at = timezone.now()
            update_fields.append("first_response_at")
        if ticket.status not in {SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED, SupportTicket.Status.ESCALATED}:
            ticket.status = SupportTicket.Status.PENDING_REQUESTER
            update_fields.append("status")
        ticket.save(update_fields=update_fields)

        _notify_user(
            recipient=ticket.requester,
            event_key="support_ticket_reply_posted",
            title=f"Update on ticket {ticket.ticket_id}",
            message=f"Support replied to your ticket {ticket.ticket_id}: {ticket.subject}",
            template_context={
                "ticket_id": ticket.ticket_id,
                "ticket_subject": ticket.subject,
                "action_url": "/support-desk/tickets",
            },
            link_url="/support-desk/tickets",
        )
        self._run_automation_for_ticket(ticket, previous_status=previous_status)

        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="link-related")
    def link_related_ticket(self, request, pk=None):
        ticket = self.get_object()
        serializer = SupportTicketLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        related_ticket_id = serializer.validated_data.get("related_ticket_id")
        related_ticket_ref = serializer.validated_data.get("related_ticket_ref")
        related_ticket_qs = _ticket_queryset(request).exclude(pk=ticket.pk)
        if related_ticket_id is not None:
            related_ticket_qs = related_ticket_qs.filter(pk=related_ticket_id)
        else:
            related_ticket_qs = related_ticket_qs.filter(ticket_id=related_ticket_ref)
        related_ticket = related_ticket_qs.first()
        if related_ticket is None:
            return Response({"detail": "Related ticket not found."}, status=status.HTTP_400_BAD_REQUEST)

        ticket.linked_tickets.add(related_ticket)
        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="escalate")
    def escalate(self, request, pk=None):
        ticket = self.get_object()
        previous_status = ticket.status
        serializer = SupportTicketEscalateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["reason"]:
            SupportTicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                comment_type=SupportTicketComment.CommentType.INTERNAL_NOTE,
                body=f"Escalation reason: {serializer.validated_data['reason']}",
            )

        ticket.status = SupportTicket.Status.ESCALATED
        ticket.escalated_at = timezone.now()
        ticket.save(update_fields=["status", "escalated_at", "updated_at"])

        if ticket.assigned_agent_id:
            _notify_user(
                recipient=ticket.assigned_agent,
                event_key="support_ticket_escalated",
                title=f"Escalated ticket {ticket.ticket_id}",
                message=f"Ticket {ticket.ticket_id} has been escalated.",
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "action_url": "/support-desk/tickets",
                },
                category=Notification.Category.WORKFLOW_ESCALATED,
                severity=Notification.Severity.WARNING,
                link_url="/support-desk/tickets",
            )
        self._run_automation_for_ticket(ticket, previous_status=previous_status)

        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="close")
    def close_ticket(self, request, pk=None):
        ticket = self.get_object()
        previous_status = ticket.status
        serializer = SupportTicketCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket.status = SupportTicket.Status.CLOSED
        ticket.closed_at = timezone.now()
        if ticket.resolved_at is None:
            ticket.resolved_at = ticket.closed_at
        if "resolution_notes" in serializer.validated_data:
            ticket.resolution_notes = serializer.validated_data["resolution_notes"]
        if "customer_satisfaction_score" in serializer.validated_data:
            ticket.customer_satisfaction_score = serializer.validated_data["customer_satisfaction_score"]
        ticket.save(
            update_fields=[
                "status",
                "closed_at",
                "resolved_at",
                "resolution_notes",
                "customer_satisfaction_score",
                "updated_at",
            ]
        )
        self._run_automation_for_ticket(ticket, previous_status=previous_status)

        return Response(SupportTicketDetailSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="attachments")
    @parser_classes([MultiPartParser, FormParser])
    def attach_file(self, request, pk=None):
        ticket = self.get_object()
        serializer = SupportTicketAttachmentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = serializer.save(ticket=ticket, uploaded_by=request.user)
        return Response(
            SupportTicketAttachmentSerializer(attachment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class SupportRequestViewSet(SupportTicketViewSet):
    """
    Request workspace endpoints.

    This viewset reuses the ticket lifecycle/actions while scoping records to
    SupportTicket.category == "request".
    """

    rbac_sub_module = "support_desk.requests"

    def get_queryset(self):
        return super().get_queryset().filter(category=SupportTicket.Category.REQUEST)

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return SupportRequestWriteSerializer
        return super().get_serializer_class()


class SupportCommunicationLogFilter(filters.FilterSet):
    happened_after = filters.IsoDateTimeFilter(field_name="happened_at", lookup_expr="gte")
    happened_before = filters.IsoDateTimeFilter(field_name="happened_at", lookup_expr="lte")

    class Meta:
        model = SupportCommunicationLog
        fields = [
            "ticket",
            "author",
            "interaction_type",
            "direction",
            "channel",
        ]


class SupportCommunicationLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.communication"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "send_whatsapp": "comment",
    }
    filterset_class = SupportCommunicationLogFilter
    search_fields = [
        "ticket__ticket_id",
        "ticket__subject",
        "subject",
        "message",
        "transcript",
        "external_message_id",
    ]
    ordering_fields = [
        "happened_at",
        "created_at",
        "interaction_type",
        "channel",
        "direction",
    ]
    ordering = ["-happened_at", "-id"]

    def get_queryset(self):
        queryset = SupportCommunicationLog.objects.select_related("ticket", "author")
        return _scope_queryset_for_request(
            self.request,
            queryset,
            org_field="organization",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return SupportCommunicationLogListSerializer
        if self.action == "retrieve":
            return SupportCommunicationLogDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return SupportCommunicationLogWriteSerializer
        return SupportCommunicationLogDetailSerializer

    def perform_create(self, serializer):
        log = serializer.save()
        _sync_ticket_comment_from_communication(log)

    @action(detail=False, methods=["post"], url_path="whatsapp")
    def send_whatsapp(self, request):
        serializer = SupportCommunicationWhatsAppSendSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        ticket = serializer.validated_data.get("ticket")
        recipient_phone = serializer.validated_data["recipient_phone"]
        try:
            adapter = get_whatsapp_provider_adapter(serializer.validated_data.get("provider"))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        dispatch_error = ""
        dispatch_result = None
        try:
            dispatch_result = adapter.send_message(
                recipient_phone=recipient_phone,
                message=serializer.validated_data["message"],
                metadata=serializer.validated_data.get("metadata") or {},
            )
        except Exception as exc:
            dispatch_error = str(exc)

        metadata = serializer.validated_data.get("metadata") or {}
        metadata = {
            **metadata,
            "integration": "whatsapp",
            "provider": adapter.provider_key,
            "provider_label": adapter.provider_label,
            "recipient_phone": recipient_phone,
            "status": dispatch_result.status if dispatch_result else "failed",
            "mode": dispatch_result.mode if dispatch_result else "live",
            "dispatch_payload": dispatch_result.payload if dispatch_result else {},
            "error": dispatch_error,
        }

        log = SupportCommunicationLog.objects.create(
            organization=_user_org(request),
            ticket=ticket,
            author=request.user,
            interaction_type=SupportCommunicationLog.InteractionType.WHATSAPP,
            direction=SupportCommunicationLog.Direction.OUTBOUND,
            channel=SupportCommunicationLog.Channel.WHATSAPP,
            subject=f"WhatsApp message to {recipient_phone}",
            message=serializer.validated_data["message"],
            external_message_id=(
                serializer.validated_data.get("external_message_id", "")
                or (dispatch_result.provider_message_id if dispatch_result else "")
            ),
            metadata=metadata,
            happened_at=timezone.now(),
        )
        _sync_ticket_comment_from_communication(log)

        if ticket and ticket.requester_id:
            _notify_user(
                recipient=ticket.requester,
                event_key="support_whatsapp_message_sent",
                title=f"WhatsApp update on ticket {ticket.ticket_id}",
                message=f"A support WhatsApp message was sent regarding ticket {ticket.ticket_id}.",
                template_context={
                    "ticket_id": ticket.ticket_id,
                    "ticket_subject": ticket.subject,
                    "action_url": "/support-desk/communication",
                },
                link_url="/support-desk/communication",
            )

        serialized = SupportCommunicationLogDetailSerializer(log, context={"request": request}).data
        if dispatch_error:
            return Response(
                {
                    "detail": "WhatsApp provider dispatch failed. The communication log was recorded.",
                    "provider_error": dispatch_error,
                    "log": serialized,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(serialized, status=status.HTTP_201_CREATED)


class SupportCommunicationOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.communication"
    rbac_action = "view"

    def get(self, request):
        logs = _scope_queryset_for_request(
            request,
            SupportCommunicationLog.objects.all(),
            org_field="organization",
        )

        payload = {
            "total_interactions": logs.count(),
            "ticket_conversations_count": logs.filter(
                interaction_type=SupportCommunicationLog.InteractionType.TICKET_CONVERSATION
            ).count(),
            "internal_notes_count": logs.filter(
                interaction_type=SupportCommunicationLog.InteractionType.INTERNAL_NOTE
            ).count(),
            "email_replies_count": logs.filter(
                interaction_type=SupportCommunicationLog.InteractionType.EMAIL_REPLY
            ).count(),
            "chat_transcripts_count": logs.filter(
                interaction_type=SupportCommunicationLog.InteractionType.CHAT_TRANSCRIPT
            ).count(),
            "call_logs_count": logs.filter(
                interaction_type=SupportCommunicationLog.InteractionType.CALL_LOG
            ).count(),
            "whatsapp_messages_count": logs.filter(
                interaction_type=SupportCommunicationLog.InteractionType.WHATSAPP
            ).count(),
            "inbound_count": logs.filter(
                direction=SupportCommunicationLog.Direction.INBOUND
            ).count(),
            "outbound_count": logs.filter(
                direction=SupportCommunicationLog.Direction.OUTBOUND
            ).count(),
            "internal_count": logs.filter(
                direction=SupportCommunicationLog.Direction.INTERNAL
            ).count(),
            "interactions_by_channel": [
                {
                    "key": key,
                    "label": label,
                    "count": logs.filter(channel=key).count(),
                }
                for key, label in SupportCommunicationLog.Channel.choices
            ],
            "recent_logs": logs.select_related("ticket", "author").order_by("-happened_at", "-id")[:10],
        }

        serializer = SupportCommunicationOverviewSerializer(payload, context={"request": request})
        return Response(serializer.data)


class SupportAutomationRuleFilter(filters.FilterSet):
    class Meta:
        model = SupportAutomationRule
        fields = ["trigger_type", "is_active"]


class SupportAutomationRunFilter(filters.FilterSet):
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = SupportAutomationRun
        fields = ["trigger_type", "status", "rule", "ticket"]


class SupportAutomationRuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.automation"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "toggle_active": "configure",
    }
    filterset_class = SupportAutomationRuleFilter
    search_fields = ["name", "description"]
    ordering_fields = ["name", "priority", "trigger_type", "updated_at"]
    ordering = ["trigger_type", "priority", "name"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            SupportAutomationRule.objects.all(),
            org_field="organization",
        )

    def get_serializer_class(self):
        return SupportAutomationRuleSerializer

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save(update_fields=["is_active", "updated_at"])
        return Response(SupportAutomationRuleSerializer(rule, context={"request": request}).data)


class SupportAutomationRunViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.automation"
    serializer_class = SupportAutomationRunSerializer
    filterset_class = SupportAutomationRunFilter
    search_fields = ["rule__name", "ticket__ticket_id", "summary"]
    ordering_fields = ["created_at", "trigger_type", "status"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        queryset = SupportAutomationRun.objects.select_related("rule", "ticket")
        return _scope_queryset_for_request(
            self.request,
            queryset,
            org_field="organization",
        )


class SupportAutomationOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.automation"
    rbac_action = "view"

    def get(self, request):
        rules = _scope_queryset_for_request(
            request,
            SupportAutomationRule.objects.all(),
            org_field="organization",
        )
        runs = _scope_queryset_for_request(
            request,
            SupportAutomationRun.objects.all(),
            org_field="organization",
        )

        payload = {
            "active_rule_count": rules.filter(is_active=True).count(),
            "total_rule_count": rules.count(),
            "recent_run_count": runs.filter(created_at__gte=timezone.now() - timedelta(hours=24)).count(),
            "last_run_at": runs.order_by("-created_at").values_list("created_at", flat=True).first(),
            "runs_by_status": [
                {
                    "key": key,
                    "label": label,
                    "count": runs.filter(status=key).count(),
                }
                for key, label in SupportAutomationRun.Status.choices
            ],
            "runs_by_trigger": [
                {
                    "key": key,
                    "label": label,
                    "count": runs.filter(trigger_type=key).count(),
                }
                for key, label in SupportAutomationRule.TriggerType.choices
            ],
            "recent_runs": runs.select_related("rule", "ticket").order_by("-created_at", "-id")[:12],
        }
        serializer = SupportAutomationOverviewSerializer(payload, context={"request": request})
        return Response(serializer.data)


class SupportKnowledgeArticleFilter(filters.FilterSet):
    updated_after = filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="gte")
    updated_before = filters.IsoDateTimeFilter(field_name="updated_at", lookup_expr="lte")

    class Meta:
        model = SupportKnowledgeArticle
        fields = [
            "status",
            "visibility",
            "category",
            "owner",
            "reviewer",
        ]


class SupportKnowledgeArticleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.knowledge_base"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
        "submit_for_review": "edit",
        "publish": "approve",
        "archive_article": "archive",
        "record_feedback": "view",
        "record_view": "view",
    }
    filterset_class = SupportKnowledgeArticleFilter
    search_fields = [
        "title",
        "slug",
        "summary",
        "body",
        "category",
    ]
    ordering_fields = [
        "title",
        "status",
        "updated_at",
        "published_at",
        "view_count",
        "helpful_votes",
    ]
    ordering = ["-updated_at"]

    def get_queryset(self):
        queryset = SupportKnowledgeArticle.objects.select_related("owner", "reviewer")
        return _scope_queryset_for_request(
            self.request,
            queryset,
            org_field="organization",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return SupportKnowledgeArticleListSerializer
        if self.action == "retrieve":
            return SupportKnowledgeArticleDetailSerializer
        if self.action in ("create", "update", "partial_update"):
            return SupportKnowledgeArticleWriteSerializer
        return SupportKnowledgeArticleDetailSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=["post"], url_path="submit-review")
    def submit_for_review(self, request, pk=None):
        article = self.get_object()
        article.status = SupportKnowledgeArticle.Status.IN_REVIEW
        if article.reviewer_id is None:
            article.reviewer = request.user
        article.last_reviewed_at = timezone.now()
        article.save(update_fields=["status", "reviewer", "last_reviewed_at", "updated_at"])
        return Response(SupportKnowledgeArticleDetailSerializer(article, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        article = self.get_object()
        article.status = SupportKnowledgeArticle.Status.PUBLISHED
        article.published_at = timezone.now()
        article.last_reviewed_at = timezone.now()
        article.save(update_fields=["status", "published_at", "last_reviewed_at", "updated_at"])
        return Response(SupportKnowledgeArticleDetailSerializer(article, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive_article(self, request, pk=None):
        article = self.get_object()
        article.status = SupportKnowledgeArticle.Status.ARCHIVED
        article.save(update_fields=["status", "updated_at"])
        return Response(SupportKnowledgeArticleDetailSerializer(article, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="feedback")
    def record_feedback(self, request, pk=None):
        article = self.get_object()
        serializer = SupportKnowledgeArticleFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data["helpful"]:
            SupportKnowledgeArticle.objects.filter(pk=article.pk).update(helpful_votes=F("helpful_votes") + 1)
        else:
            SupportKnowledgeArticle.objects.filter(pk=article.pk).update(not_helpful_votes=F("not_helpful_votes") + 1)
        article.refresh_from_db(fields=["helpful_votes", "not_helpful_votes", "updated_at"])
        return Response(SupportKnowledgeArticleDetailSerializer(article, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="record-view")
    def record_view(self, request, pk=None):
        article = self.get_object()
        SupportKnowledgeArticle.objects.filter(pk=article.pk).update(view_count=F("view_count") + 1)
        article.refresh_from_db(fields=["view_count", "updated_at"])
        return Response(SupportKnowledgeArticleDetailSerializer(article, context={"request": request}).data)


class SupportKnowledgeBaseOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.knowledge_base"
    rbac_action = "view"

    def get(self, request):
        today = timezone.localdate()
        articles = _scope_queryset_for_request(
            request,
            SupportKnowledgeArticle.objects.all(),
            org_field="organization",
        )
        total_articles = articles.count()

        published_articles = articles.filter(status=SupportKnowledgeArticle.Status.PUBLISHED).count()
        in_review_articles = articles.filter(status=SupportKnowledgeArticle.Status.IN_REVIEW).count()
        draft_articles = articles.filter(status=SupportKnowledgeArticle.Status.DRAFT).count()
        archived_articles = articles.filter(status=SupportKnowledgeArticle.Status.ARCHIVED).count()

        due_for_review_count = articles.filter(
            status=SupportKnowledgeArticle.Status.PUBLISHED,
            next_review_due_at__isnull=False,
            next_review_due_at__lte=today,
        ).count()

        aggregate = articles.aggregate(
            total_views=Sum("view_count"),
            helpful_votes=Sum("helpful_votes"),
            not_helpful_votes=Sum("not_helpful_votes"),
        )
        total_views = aggregate["total_views"] or 0
        helpful_votes = aggregate["helpful_votes"] or 0
        not_helpful_votes = aggregate["not_helpful_votes"] or 0
        feedback_total = helpful_votes + not_helpful_votes
        helpful_feedback_ratio = None if feedback_total == 0 else round((helpful_votes / feedback_total) * 100, 2)

        top_articles = (
            articles
            .filter(status=SupportKnowledgeArticle.Status.PUBLISHED)
            .order_by("-view_count", "-helpful_votes", "title")[:8]
        )

        payload = {
            "total_articles": total_articles,
            "published_articles": published_articles,
            "in_review_articles": in_review_articles,
            "draft_articles": draft_articles,
            "archived_articles": archived_articles,
            "due_for_review_count": due_for_review_count,
            "total_views": total_views,
            "helpful_feedback_ratio": helpful_feedback_ratio,
            "top_articles": top_articles,
        }
        serializer = SupportKnowledgeBaseOverviewSerializer(payload, context={"request": request})
        return Response(serializer.data)


class SupportSlaPolicyFilter(filters.FilterSet):
    class Meta:
        model = SupportSlaPolicy
        fields = [
            "category",
            "priority",
            "is_active",
        ]


class SupportSlaPolicyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.sla_escalations"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "configure",
        "update": "configure",
        "partial_update": "configure",
        "destroy": "configure",
        "toggle_active": "configure",
    }
    filterset_class = SupportSlaPolicyFilter
    search_fields = ["name", "description"]
    ordering_fields = [
        "name",
        "response_target_hours",
        "resolution_target_hours",
        "escalate_after_hours",
        "updated_at",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            SupportSlaPolicy.objects.all(),
            org_field="organization",
        )

    def get_serializer_class(self):
        return SupportSlaPolicySerializer

    @action(detail=True, methods=["post"], url_path="toggle-active")
    def toggle_active(self, request, pk=None):
        policy = self.get_object()
        policy.is_active = not policy.is_active
        policy.save(update_fields=["is_active", "updated_at"])
        return Response(SupportSlaPolicySerializer(policy, context={"request": request}).data)


class SupportSlaEscalationTicketViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.sla_escalations"
    serializer_class = SupportSlaEscalationTicketSerializer
    filterset_class = SupportTicketFilter
    search_fields = [
        "ticket_id",
        "subject",
        "description",
        "requester__first_name",
        "requester__last_name",
        "requester__email",
        "customer__name",
        "customer__email",
        "customer__phone",
        "contact_account__first_name",
        "contact_account__last_name",
        "contact_account__legal_name",
        "contact_account__trade_name",
        "contact_account__email",
        "contact_account__phone",
        "assigned_agent__first_name",
        "assigned_agent__last_name",
        "assigned_agent__email",
    ]
    ordering_fields = ["ticket_id", "created_at", "updated_at", "sla_deadline", "priority", "status"]
    ordering = ["sla_deadline", "-priority", "created_at"]

    def get_queryset(self):
        now = timezone.now()
        queue = self.request.query_params.get("queue", "").strip()
        queryset = _ticket_queryset(self.request).exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])

        for ticket in queryset:
            _evaluate_ticket_sla(ticket, now=now)

        queryset = _ticket_queryset(self.request).exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED])

        if queue == "breached":
            queryset = queryset.filter(sla_deadline__lt=now)
        elif queue == "escalated":
            queryset = queryset.filter(status=SupportTicket.Status.ESCALATED)
        elif queue == "upcoming":
            queryset = queryset.filter(sla_deadline__gte=now, sla_deadline__lte=now + timedelta(hours=24))
        elif queue == "at_risk":
            queryset = queryset.filter(sla_deadline__gte=now, sla_deadline__lte=now + timedelta(hours=4))

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["now"] = timezone.now()
        return context


class SupportSlaEscalationsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "support_desk.sla_escalations"
    rbac_action = "view"

    def get(self, request):
        now = timezone.now()
        active_tickets = _ticket_queryset(request).exclude(
            status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
        )
        for ticket in active_tickets:
            _evaluate_ticket_sla(ticket, now=now)

        tickets = _ticket_queryset(request)
        active_tickets = tickets.exclude(
            status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]
        )
        active_ticket_list = list(active_tickets)

        breached_ticket_ids: list[int] = []
        upcoming_deadline_count = 0
        warning_50_count = 0
        warning_80_count = 0
        overdue_hours: list[float] = []

        for ticket in active_ticket_list:
            targets = get_ticket_sla_targets(ticket)
            timeline = get_ticket_sla_timeline(ticket, now=now, targets=targets)
            policy = targets["policy"]

            agent_threshold = policy.agent_notify_threshold_percent if policy else 50
            manager_threshold = policy.manager_notify_threshold_percent if policy else 80
            progress = timeline["resolution_progress_percent"]
            resolution_deadline = timeline["resolution_deadline_at"]

            if progress >= agent_threshold and not timeline["resolution_breached"]:
                warning_50_count += 1
            if progress >= manager_threshold and not timeline["resolution_breached"]:
                warning_80_count += 1

            if resolution_deadline and now <= resolution_deadline <= now + timedelta(hours=24):
                upcoming_deadline_count += 1

            if timeline["resolution_breached"]:
                breached_ticket_ids.append(ticket.id)
                overdue_hours.append(
                    (now - resolution_deadline).total_seconds() / 3600
                    if resolution_deadline else 0
                )

        breached_tickets = active_tickets.filter(id__in=breached_ticket_ids)
        escalated_tickets = active_tickets.filter(status=SupportTicket.Status.ESCALATED)

        average_overdue_hours = (
            round(sum(overdue_hours) / len(overdue_hours), 2) if overdue_hours else None
        )
        max_overdue_hours = round(max(overdue_hours), 2) if overdue_hours else None

        breaches_by_priority = [
            {
                "key": key,
                "label": label,
                "count": breached_tickets.filter(priority=key).count(),
            }
            for key, label in SupportTicket.Priority.choices
        ]

        top_breached_tickets = breached_tickets.order_by(
            "sla_deadline", "-priority", "created_at"
        )[:8]
        recent_escalations = escalated_tickets.order_by("-escalated_at", "-updated_at")[:8]

        payload = {
            "active_policy_count": _scope_queryset_for_request(
                request,
                SupportSlaPolicy.objects.filter(is_active=True),
                org_field="organization",
            ).count(),
            "active_ticket_count": len(active_ticket_list),
            "breached_ticket_count": len(breached_ticket_ids),
            "escalated_ticket_count": escalated_tickets.count(),
            "upcoming_deadline_count": upcoming_deadline_count,
            "warning_50_count": warning_50_count,
            "warning_80_count": warning_80_count,
            "average_overdue_hours": average_overdue_hours,
            "max_overdue_hours": max_overdue_hours,
            "breaches_by_priority": breaches_by_priority,
            "policy_matrix": _build_sla_policy_matrix(request),
            "top_breached_tickets": top_breached_tickets,
            "recent_escalations": recent_escalations,
        }
        serializer = SupportSlaEscalationsOverviewSerializer(payload, context={"request": request, "now": now})
        return Response(serializer.data)

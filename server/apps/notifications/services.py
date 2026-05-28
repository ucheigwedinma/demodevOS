from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.settings.models import (
    NotificationChannel,
    NotificationChannelSettings,
    NotificationTemplate,
    SlaSeverityLevel,
)

from .models import Notification, UserNotificationPreference

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkflowNotificationEventDefinition:
    key: str
    label: str
    module: str
    description: str
    default_channels: tuple[str, ...]
    variables: tuple[str, ...]
    default_severity_tier: str = SlaSeverityLevel.REVIEW


@dataclass
class RaciRecipients:
    """Recipients resolved from RACI process authority configuration."""

    responsible: list = field(default_factory=list)
    accountable: list = field(default_factory=list)
    consulted: list = field(default_factory=list)
    informed: list = field(default_factory=list)

    @property
    def all(self) -> list:
        """All unique recipients across all RACI roles."""
        seen: dict[int, Any] = {}
        for user in (*self.responsible, *self.accountable, *self.consulted, *self.informed):
            uid = getattr(user, "id", None)
            if uid and uid not in seen:
                seen[uid] = user
        return list(seen.values())

    @property
    def decision_makers(self) -> list:
        """Responsible + Accountable (unique)."""
        seen: dict[int, Any] = {}
        for user in (*self.responsible, *self.accountable):
            uid = getattr(user, "id", None)
            if uid and uid not in seen:
                seen[uid] = user
        return list(seen.values())

    @property
    def stakeholders(self) -> list:
        """Consulted + Informed (unique)."""
        seen: dict[int, Any] = {}
        for user in (*self.consulted, *self.informed):
            uid = getattr(user, "id", None)
            if uid and uid not in seen:
                seen[uid] = user
        return list(seen.values())


def resolve_raci_recipients(
    *,
    organization: Any,
    process_key: str,
    fallback_users: list | None = None,
) -> RaciRecipients:
    """
    Resolve notification recipients from RACI process authority configuration.

    1. Query ProcessAuthority for the given process_key
    2. Resolve each Approver → User (direct) or Role → Users with that assigned_role
    3. Check UserDelegation for active delegations → substitute delegates
    4. If no ProcessAuthority configured, fall back to fallback_users as INFORMED
    """
    from apps.accounts.models import UserProfile
    from apps.workflows.models import (
        ProcessAuthority,
        ProcessWorkflowStep,
        UserDelegation,
    )

    result = RaciRecipients()

    if organization is None:
        if fallback_users:
            result.informed = list(fallback_users)
        return result

    # Find all process steps for this process_key in the org
    step_ids = list(
        ProcessWorkflowStep.objects.filter(
            organization=organization,
            process_key=process_key,
            is_active=True,
        ).values_list("id", flat=True)
    )

    if not step_ids:
        if fallback_users:
            result.informed = list(fallback_users)
        return result

    # Get all active authorities for these steps
    authorities = (
        ProcessAuthority.objects.filter(
            workflow_step_id__in=step_ids,
            is_active=True,
        )
        .select_related("approver", "approver__user", "approver__role")
        .order_by("sort_order")
    )

    if not authorities.exists():
        if fallback_users:
            result.informed = list(fallback_users)
        return result

    now = timezone.now()

    # Check for active delegations in this org
    active_delegations = {
        d.delegator_id: d.delegate_id
        for d in UserDelegation.objects.filter(
            organization=organization,
            status=UserDelegation.Status.ACTIVE,
            starts_at__lte=now,
            ends_at__gte=now,
        ).select_related("delegate")
    }

    # Cache for role → users resolution
    _role_users_cache: dict[int, list] = {}

    def _resolve_approver_users(approver) -> list:
        """Resolve an Approver to a list of User objects."""
        users = []
        if approver.user_id:
            users.append(approver.user)
        elif approver.role_id:
            role_id = approver.role_id
            if role_id not in _role_users_cache:
                _role_users_cache[role_id] = list(
                    UserProfile.objects.filter(
                        organization=organization,
                        assigned_role_id=role_id,
                        user__is_active=True,
                    )
                    .select_related("user")
                    .values_list("user", flat=False)
                )
                # Re-fetch as User objects
                from django.contrib.auth.models import User

                user_ids = UserProfile.objects.filter(
                    organization=organization,
                    assigned_role_id=role_id,
                    user__is_active=True,
                ).values_list("user_id", flat=True)
                _role_users_cache[role_id] = list(
                    User.objects.filter(id__in=user_ids, is_active=True)
                )
            users.extend(_role_users_cache[role_id])
        return users

    def _apply_delegation(user):
        """Substitute delegate if the user has an active delegation."""
        if user.id in active_delegations:
            from django.contrib.auth.models import User

            try:
                return User.objects.get(
                    id=active_delegations[user.id], is_active=True
                )
            except User.DoesNotExist:
                pass
        return user

    raci_map = {
        ProcessAuthority.AuthorityType.RESPONSIBLE: result.responsible,
        ProcessAuthority.AuthorityType.ACCOUNTABLE: result.accountable,
        ProcessAuthority.AuthorityType.CONSULTED: result.consulted,
        ProcessAuthority.AuthorityType.INFORMED: result.informed,
    }

    for authority in authorities:
        target_list = raci_map.get(authority.authority_type, result.informed)
        users = _resolve_approver_users(authority.approver)
        for user in users:
            resolved = _apply_delegation(user)
            if resolved and getattr(resolved, "is_active", False):
                target_list.append(resolved)

    return result


WORKFLOW_NOTIFICATION_EVENTS: tuple[WorkflowNotificationEventDefinition, ...] = (
    WorkflowNotificationEventDefinition(
        key="support_ticket_assigned",
        label="Support Ticket Assigned",
        module="support_desk",
        description="Notifies an agent when a ticket is assigned.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("ticket_id", "ticket_subject", "requester_name", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="support_ticket_reply_posted",
        label="Support Ticket Reply Posted",
        module="support_desk",
        description="Notifies requester when support posts a reply.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("ticket_id", "ticket_subject", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="support_ticket_escalated",
        label="Support Ticket Escalated",
        module="support_desk",
        description="Notifies assignee when a support ticket is escalated.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("ticket_id", "ticket_subject", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="finance_budget_threshold_warning",
        label="Budget Threshold Warning",
        module="finance",
        description="Warns recipients when spending crosses warning threshold.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "account_code",
            "account_name",
            "percent_used",
            "budgeted_amount",
            "actual_amount",
            "budget_name",
            "action_url",
        ),
    ),
    WorkflowNotificationEventDefinition(
        key="finance_budget_threshold_exceeded",
        label="Budget Threshold Exceeded",
        module="finance",
        description="Alerts recipients when spending exceeds tolerance.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "account_code",
            "account_name",
            "percent_used",
            "budgeted_amount",
            "actual_amount",
            "budget_name",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ESCALATION,
    ),
    WorkflowNotificationEventDefinition(
        key="finance_weekly_budget_digest",
        label="Weekly Budget Digest",
        module="finance",
        description="Sends weekly budget digest summary to active org members.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("digest_date", "action_url", "digest_text", "digest_html"),
    ),
    WorkflowNotificationEventDefinition(
        key="reports_ready",
        label="Report Ready",
        module="analytics",
        description="Notifies recipients when a report run is generated and ready.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "report_name",
            "report_code",
            "run_id",
            "generated_at",
            "output_format",
            "view_url",
            "download_url",
            "action_url",
        ),
    ),
    WorkflowNotificationEventDefinition(
        key="documents_expiry_90_day",
        label="Document Expiry (90 Days)",
        module="documents",
        description="Alerts recipients 31-90 days before document expiry.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "document_number",
            "document_title",
            "category_label",
            "expiry_date",
            "days_to_expiry",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.REVIEW,
    ),
    WorkflowNotificationEventDefinition(
        key="documents_expiry_30_day",
        label="Document Expiry (30 Days)",
        module="documents",
        description="Alerts recipients 0-30 days before document expiry.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "document_number",
            "document_title",
            "category_label",
            "expiry_date",
            "days_to_expiry",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="documents_expired",
        label="Document Expired",
        module="documents",
        description="Alerts recipients when a compliance document expires.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "document_number",
            "document_title",
            "category_label",
            "expiry_date",
            "days_overdue",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ESCALATION,
    ),
    WorkflowNotificationEventDefinition(
        key="documents_expiry_escalated",
        label="Document Expiry Escalation",
        module="documents",
        description="Escalation notice for overdue document expiry.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "document_number",
            "document_title",
            "category_label",
            "expiry_date",
            "days_overdue",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ESCALATION,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_reservation_payment_instruction",
        label="Reservation Payment Instruction",
        module="crm",
        description="Notifies assigned sales owner when payment instruction is issued.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("reservation_number", "deposit_amount", "deposit_due_date", "action_url"),
    ),
    # ----- Projects -----
    WorkflowNotificationEventDefinition(
        key="projects_phase_status_changed",
        label="Project Phase Status Changed",
        module="projects",
        description="Notifies stakeholders when a project phase transitions status.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("project_name", "phase_name", "old_status", "new_status", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="projects_milestone_approval_needed",
        label="Milestone Approval Needed",
        module="projects",
        description="Notifies approvers when a project milestone requires approval.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("project_name", "milestone_name", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="projects_milestone_decision",
        label="Milestone Approval Decision",
        module="projects",
        description="Notifies stakeholders when a milestone is approved or rejected.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("project_name", "milestone_name", "decision", "decided_by", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="projects_task_assigned",
        label="Project Task Assigned",
        module="projects",
        description="Notifies a user when a project task is assigned to them.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("project_name", "task_name", "assignee_name", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="projects_risk_escalated",
        label="Project Risk Escalated",
        module="projects",
        description="Alerts stakeholders when a high/critical risk is registered.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("project_name", "risk_title", "severity", "action_url"),
        default_severity_tier=SlaSeverityLevel.ESCALATION,
    ),
    WorkflowNotificationEventDefinition(
        key="projects_field_escalation",
        label="Field Escalation Raised",
        module="projects",
        description="Alerts project managers when a field escalation is created.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("project_name", "escalation_title", "severity", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    # ----- Properties -----
    WorkflowNotificationEventDefinition(
        key="properties_unit_held",
        label="Unit Hold Placed",
        module="properties",
        description="Notifies stakeholders when a unit inventory is placed on hold.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("unit_number", "property_name", "held_by", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="properties_unit_released",
        label="Unit Hold Released",
        module="properties",
        description="Notifies stakeholders when a unit hold is released.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("unit_number", "property_name", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="properties_unit_sold_leased",
        label="Unit Sold or Leased",
        module="properties",
        description="Notifies stakeholders when a unit is sold or leased.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("unit_number", "property_name", "new_status", "allocated_to", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="properties_work_order_created",
        label="High-Priority Work Order Created",
        module="properties",
        description="Alerts maintenance team when a high-priority work order is created.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("work_order_number", "property_name", "priority", "description", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    # ----- Procurement -----
    WorkflowNotificationEventDefinition(
        key="procurement_pr_submitted",
        label="Purchase Requisition Submitted",
        module="procurement",
        description="Notifies approvers when a purchase requisition is submitted.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("pr_number", "requester", "total_amount", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="procurement_po_approved",
        label="Purchase Order Approved",
        module="procurement",
        description="Notifies the requester when a purchase order is approved.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("po_number", "vendor_name", "total_amount", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="procurement_po_rejected",
        label="Purchase Order Rejected",
        module="procurement",
        description="Notifies the requester when a purchase order is rejected.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("po_number", "vendor_name", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="procurement_grn_received",
        label="Goods Receipt Logged",
        module="procurement",
        description="Notifies procurement and finance when goods are received.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("grn_number", "po_number", "vendor_name", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="procurement_rfq_quote_received",
        label="RFQ Vendor Quote Received",
        module="procurement",
        description="Notifies procurement team when a vendor submits an RFQ quote.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("rfq_number", "vendor_name", "quoted_amount", "action_url"),
    ),
    # ----- HR -----
    WorkflowNotificationEventDefinition(
        key="hr_leave_submitted",
        label="Leave Request Submitted",
        module="hr",
        description="Notifies the reporting manager when a leave request is submitted.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("employee_name", "leave_type", "start_date", "end_date", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="hr_leave_decision",
        label="Leave Request Decision",
        module="hr",
        description="Notifies the employee when their leave request is approved or rejected.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("leave_type", "start_date", "end_date", "decision", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="hr_job_offer_sent",
        label="Job Offer Created",
        module="hr",
        description="Notifies HR managers when a job offer is created.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("candidate_name", "position", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="hr_onboarding_task_due",
        label="Onboarding Task Due",
        module="hr",
        description="Reminds assignees of upcoming onboarding task deadlines.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("task_name", "employee_name", "due_date", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="hr_certification_expiring",
        label="Certification Expiring",
        module="hr",
        description="Alerts employees and managers of certifications expiring within 30 days.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("employee_name", "certification_name", "expiry_date", "days_remaining", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    # ----- Partners -----
    WorkflowNotificationEventDefinition(
        key="partners_case_created",
        label="Partner Onboarding Case Created",
        module="partners",
        description="Notifies onboarding managers when a new partner case is created.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("case_number", "partner_type", "company_name", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="partners_stage_completed",
        label="Onboarding Stage Completed",
        module="partners",
        description="Notifies stakeholders when an onboarding stage is completed.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("case_number", "stage_name", "next_stage", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="partners_approval_needed",
        label="Partner Approval Required",
        module="partners",
        description="Notifies designated approvers when a partner stage requires approval.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("case_number", "stage_name", "partner_type", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="partners_case_approved",
        label="Partner Case Approved",
        module="partners",
        description="Notifies case creator when a partner onboarding case is approved.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("case_number", "company_name", "action_url"),
    ),
    # ----- CRM Extensions -----
    WorkflowNotificationEventDefinition(
        key="crm_activity_task_assigned",
        label="CRM Activity Task Assigned",
        module="crm",
        description="Notifies assignees when a CRM activity task is assigned.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("lead_name", "rule_name", "due_at", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_activity_due_reminder",
        label="CRM Activity Due Reminder",
        module="crm",
        description="Reminds assignees when CRM follow-up tasks are due soon.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("lead_name", "rule_name", "due_at", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_site_visit_scheduled",
        label="CRM Site Visit Scheduled",
        module="crm",
        description="Notifies logistics and sales when a client site visit is scheduled.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("lead_name", "scheduled_at", "activity_subject", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_activity_missed_escalated",
        label="CRM Missed Activity Escalated",
        module="crm",
        description="Escalates missed scheduled CRM activities to reporting managers/admins.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("lead_name", "activity_subject", "scheduled_at", "action_url"),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_deal_stage_changed",
        label="CRM Deal Stage Changed",
        module="crm",
        description="Notifies stakeholders when an opportunity/deal stage or status changes.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "deal_name",
            "lead_name",
            "contact_name",
            "old_stage",
            "new_stage",
            "old_status",
            "new_status",
            "action_url",
        ),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_payment_reminder_due",
        label="CRM Reservation Payment Reminder",
        module="crm",
        description="Sends reminders for due or overdue reservation payment installments.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "reservation_number",
            "lead_name",
            "due_date",
            "amount_due",
            "overdue_days",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_broker_commission_ready_for_finance",
        label="CRM Broker Commission Ready for Finance",
        module="crm",
        description="Notifies finance when a closed-won deal commission is calculated.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "broker_name",
            "lead_name",
            "deal_name",
            "deal_value",
            "commission_amount",
            "commission_rate",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_broker_target_hit_incentive",
        label="CRM Broker Target Hit Incentive",
        module="crm",
        description="Notifies management when a broker hits incentive threshold targets.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "broker_name",
            "tier_name",
            "deals_count",
            "revenue_total",
            "target_deals",
            "target_revenue",
            "bonus_pct",
            "triggered_by",
            "action_url",
        ),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_weekly_analytics_report",
        label="CRM Weekly Analytics Report",
        module="crm",
        description="Sends weekly CRM strategic analytics snapshot to management.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "report_date",
            "conversion_rate",
            "sales_velocity_days",
            "weighted_forecast",
            "pipeline_drop_percent",
            "action_url",
        ),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_pipeline_drop_alert",
        label="CRM Pipeline Drop Alert",
        module="crm",
        description="Alerts management when CRM pipeline additions drop materially.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "drop_percent",
            "lookback_days",
            "current_additions_count",
            "previous_additions_count",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_projects_high_demand_insight",
        label="CRM Projects High-Demand Insight",
        module="crm",
        description="Notifies planning stakeholders when CRM demand concentration crosses trigger thresholds.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "area_count",
            "areas_summary",
            "window_days",
            "threshold_percent",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_procurement_bulk_buyer_demand",
        label="CRM Procurement Bulk-Buyer Demand Trigger",
        module="crm",
        description="Notifies procurement stakeholders when bulk-buyer demand triggers furnishing/add-on packages.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=(
            "area_count",
            "areas_summary",
            "window_days",
            "threshold_percent",
            "min_bulk_leads",
            "action_url",
        ),
        default_severity_tier=SlaSeverityLevel.ACTION_REQUIRED,
    ),
    WorkflowNotificationEventDefinition(
        key="crm_lead_assigned",
        label="Lead Assigned",
        module="crm",
        description="Notifies a sales user when a lead is assigned to them.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("lead_name", "company_name", "assigned_by", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_property_launch_match",
        label="Property Launch Match Suggestions",
        module="crm",
        description="Notifies sales owners/admins when a new property launch matches active leads.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("lead_name", "property_name", "match_count", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_reservation_confirmed",
        label="Reservation Confirmed",
        module="crm",
        description="Notifies sales and finance when a unit reservation is confirmed.",
        default_channels=(NotificationChannel.IN_APP, NotificationChannel.EMAIL),
        variables=("reservation_number", "unit_number", "property_name", "action_url"),
    ),
    WorkflowNotificationEventDefinition(
        key="crm_reservation_cancelled",
        label="Reservation Cancelled",
        module="crm",
        description="Notifies the sales owner when a reservation is cancelled.",
        default_channels=(NotificationChannel.IN_APP,),
        variables=("reservation_number", "unit_number", "reason", "action_url"),
    ),
)

_VALID_CHANNELS = {choice[0] for choice in NotificationChannel.choices}
_PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_.-]+)\s*}}")
_SEVERITY_BY_TIER = {
    SlaSeverityLevel.INFO: Notification.Severity.INFO,
    SlaSeverityLevel.REVIEW: Notification.Severity.INFO,
    SlaSeverityLevel.ACTION_REQUIRED: Notification.Severity.WARNING,
    SlaSeverityLevel.ESCALATION: Notification.Severity.CRITICAL,
}


def get_workflow_notification_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": item.key,
            "label": item.label,
            "module": item.module,
            "description": item.description,
            "default_channels": list(item.default_channels),
            "variables": list(item.variables),
            "default_severity_tier": item.default_severity_tier,
        }
        for item in WORKFLOW_NOTIFICATION_EVENTS
    ]


def _normalize_recipients(recipients: Iterable[Any]) -> list[Any]:
    unique: dict[int, Any] = {}
    for recipient in recipients:
        user_id = getattr(recipient, "id", None)
        if not user_id:
            continue
        if not getattr(recipient, "is_active", False):
            continue
        if user_id not in unique:
            unique[user_id] = recipient
    return list(unique.values())


def _as_template_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value}"
    return str(value)


def _render_fragment(raw: str, context: Mapping[str, Any]) -> str:
    if not raw:
        return ""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return _as_template_value(context.get(key))

    return _PLACEHOLDER_RE.sub(replace, raw)


def _enabled_channels_for_org(organization: Any) -> set[str]:
    if organization is None:
        return {NotificationChannel.EMAIL, NotificationChannel.IN_APP}

    channel_settings, _ = NotificationChannelSettings.objects.get_or_create(
        organization=organization,
        defaults={
            "email_enabled": True,
            "in_app_enabled": True,
            "sms_enabled": False,
            "push_enabled": False,
        },
    )

    channels: set[str] = set()
    if channel_settings.email_enabled:
        channels.add(NotificationChannel.EMAIL)
    if channel_settings.in_app_enabled:
        channels.add(NotificationChannel.IN_APP)
    if channel_settings.sms_enabled:
        channels.add(NotificationChannel.SMS)
    if channel_settings.push_enabled:
        channels.add(NotificationChannel.PUSH)
    return channels


def _normalize_channels(channels: Iterable[str] | None, *, enabled_channels: set[str]) -> set[str]:
    if channels is None:
        return set(enabled_channels)
    requested = {channel for channel in channels if channel in _VALID_CHANNELS}
    return requested & enabled_channels


def _preference_map(user_ids: Sequence[int]) -> dict[int, UserNotificationPreference]:
    if not user_ids:
        return {}
    preferences = UserNotificationPreference.objects.filter(user_id__in=user_ids)
    return {pref.user_id: pref for pref in preferences}


def _is_channel_enabled_for_user(channel: str, preference: UserNotificationPreference | None) -> bool:
    if preference is None:
        return channel in {NotificationChannel.IN_APP, NotificationChannel.EMAIL}
    if channel == NotificationChannel.IN_APP:
        return preference.channel_in_app_enabled
    if channel == NotificationChannel.EMAIL:
        return preference.channel_email_enabled
    if channel == NotificationChannel.SMS:
        return preference.channel_sms_enabled
    if channel == NotificationChannel.PUSH:
        return preference.channel_push_enabled
    return False


def _deliver_fallback(
    *,
    recipients: list[Any],
    preference_by_user: Mapping[int, UserNotificationPreference],
    fallback_channels: set[str],
    fallback_title: str,
    fallback_message: str,
    fallback_category: str,
    fallback_severity: str,
    link_url: str,
) -> dict[str, int]:
    notifications_sent = 0
    emails_sent = 0
    message = fallback_message.strip() or fallback_title.strip()
    title = fallback_title.strip() or message

    if NotificationChannel.IN_APP in fallback_channels and message:
        for recipient in recipients:
            if not _is_channel_enabled_for_user(
                NotificationChannel.IN_APP,
                preference_by_user.get(recipient.id),
            ):
                continue
            Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                severity=fallback_severity,
                category=fallback_category,
                link_url=link_url,
            )
            notifications_sent += 1

    if NotificationChannel.EMAIL in fallback_channels and message and title:
        for recipient in recipients:
            if not recipient.email:
                continue
            if not _is_channel_enabled_for_user(
                NotificationChannel.EMAIL,
                preference_by_user.get(recipient.id),
            ):
                continue
            send_mail(
                subject=title,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[recipient.email],
                fail_silently=True,
            )
            emails_sent += 1

    return {
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
    }


def dispatch_workflow_notification(
    *,
    organization: Any,
    event_key: str,
    recipients: Iterable[Any],
    context: Mapping[str, Any] | None = None,
    link_url: str = "",
    channels: Iterable[str] | None = None,
    fallback_channels: Iterable[str] | None = None,
    fallback_title: str = "",
    fallback_message: str = "",
    fallback_category: str = Notification.Category.SYSTEM,
    fallback_severity: str = Notification.Severity.INFO,
) -> dict[str, int]:
    normalized_recipients = _normalize_recipients(recipients)
    if not normalized_recipients:
        return {
            "notifications_sent": 0,
            "emails_sent": 0,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }

    # Check org-level muting and category overrides
    if organization is not None:
        try:
            channel_settings = NotificationChannelSettings.objects.filter(
                organization=organization
            ).first()
            if channel_settings:
                # Event-level muting
                muted = getattr(channel_settings, "muted_event_keys", None) or []
                if event_key in muted:
                    return {
                        "notifications_sent": 0,
                        "emails_sent": 0,
                        "templates_used": 0,
                        "unsupported_channel_templates": 0,
                    }
                # Category-level disable
                overrides = getattr(channel_settings, "category_overrides", None) or {}
                cat_override = overrides.get(fallback_category, {})
                if isinstance(cat_override, dict) and not cat_override.get("enabled", True):
                    return {
                        "notifications_sent": 0,
                        "emails_sent": 0,
                        "templates_used": 0,
                        "unsupported_channel_templates": 0,
                    }
        except Exception:
            pass

    template_context = context or {}
    enabled_channels = _enabled_channels_for_org(organization)
    active_channels = _normalize_channels(channels, enabled_channels=enabled_channels)
    fallback_scope = _normalize_channels(
        fallback_channels if fallback_channels is not None else channels,
        enabled_channels=enabled_channels,
    )

    if not active_channels and not fallback_scope:
        return {
            "notifications_sent": 0,
            "emails_sent": 0,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }

    template_queryset = NotificationTemplate.objects.filter(
        organization=organization,
        event_key=event_key,
        is_active=True,
    )
    if channels is not None:
        template_queryset = template_queryset.filter(channel__in=list(active_channels))

    templates = list(template_queryset.order_by("channel", "name", "id"))
    preference_by_user = _preference_map([recipient.id for recipient in normalized_recipients])

    notifications_sent = 0
    emails_sent = 0
    templates_used = 0
    unsupported_channel_templates = 0

    for template in templates:
        channel = template.channel
        if channel not in active_channels:
            continue

        rendered_subject = _render_fragment(template.subject, template_context).strip()
        rendered_body_text = _render_fragment(template.body_text, template_context).strip()
        rendered_body_html = _render_fragment(template.body_html, template_context).strip()
        severity = _SEVERITY_BY_TIER.get(template.severity_tier, fallback_severity)

        if channel == NotificationChannel.IN_APP:
            title = rendered_subject or fallback_title.strip() or template.name
            message = rendered_body_text or fallback_message.strip() or title
            if not message:
                continue
            for recipient in normalized_recipients:
                if not _is_channel_enabled_for_user(channel, preference_by_user.get(recipient.id)):
                    continue
                Notification.objects.create(
                    recipient=recipient,
                    title=title,
                    message=message,
                    severity=severity,
                    category=fallback_category,
                    link_url=link_url,
                )
                notifications_sent += 1
            templates_used += 1
            continue

        if channel == NotificationChannel.EMAIL:
            subject = rendered_subject or fallback_title.strip() or template.name
            message = rendered_body_text or fallback_message.strip()
            if not subject or not message:
                continue
            for recipient in normalized_recipients:
                if not recipient.email:
                    continue
                if not _is_channel_enabled_for_user(channel, preference_by_user.get(recipient.id)):
                    continue
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[recipient.email],
                    html_message=rendered_body_html or None,
                    fail_silently=True,
                )
                emails_sent += 1
            templates_used += 1
            continue

        unsupported_channel_templates += 1

    if notifications_sent == 0 and emails_sent == 0 and fallback_scope:
        fallback_result = _deliver_fallback(
            recipients=normalized_recipients,
            preference_by_user=preference_by_user,
            fallback_channels=fallback_scope,
            fallback_title=fallback_title,
            fallback_message=fallback_message,
            fallback_category=fallback_category,
            fallback_severity=fallback_severity,
            link_url=link_url,
        )
        notifications_sent += fallback_result["notifications_sent"]
        emails_sent += fallback_result["emails_sent"]

    return {
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "templates_used": templates_used,
        "unsupported_channel_templates": unsupported_channel_templates,
    }

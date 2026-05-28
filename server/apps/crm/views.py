import hashlib
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache
from django.core.mail import send_mail
from django.db import models
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settings.permissions import HasRolePermission

from .analytics import compute_crm_analytics_snapshot
from .matching import (
    generate_matches_for_qualified_lead,
    recompute_matches_for_lead,
    seed_project_interests_from_matches,
)
from .models import (
    Broker,
    BrokerCommissionEarning,
    BrokerCommissionStructure,
    BrokerTier,
    Campaign,
    CampaignRecipient,
    CommunicationLog,
    ContactAccount,
    ContactComplianceReview,
    ContactDealLink,
    ContactDocument,
    ContactInteraction,
    ContactPropertyLink,
    FollowUpRule,
    FollowUpTask,
    Lead,
    LeadActivity,
    LeadDocumentEvent,
    LeadFinancialAssessment,
    LeadPaymentScenario,
    LeadProjectInterest,
    LeadPropertyMatch,
    LeadSource,
    LeadStageTransition,
    LeadUnitPreference,
    MeetingRecord,
    ReservationEvent,
    UnitReservation,
)
from .serializers import (
    BrokerDetailEnhancedSerializer,
    BrokerListEnhancedSerializer,
    BrokerTierSerializer,
    BrokerTierWriteSerializer,
    BrokerWriteSerializer,
    CallRecordingWriteSerializer,
    CampaignAddRecipientsSerializer,
    CampaignDetailSerializer,
    CampaignListSerializer,
    CampaignWriteSerializer,
    CommissionEarningDetailSerializer,
    CommissionEarningListSerializer,
    CommissionEarningWriteSerializer,
    CommissionStructureDetailSerializer,
    CommissionStructureListSerializer,
    CommissionStructureWriteSerializer,
    CommunicationLogDetailSerializer,
    CommunicationLogListSerializer,
    CommunicationLogWriteSerializer,
    ContactAccountDetailSerializer,
    ContactAccountListSerializer,
    ContactAccountWriteSerializer,
    ContactComplianceReviewSerializer,
    ContactDealLinkSerializer,
    ContactDocumentSerializer,
    ContactInteractionSerializer,
    ContactPropertyLinkSerializer,
    FinancialAssessmentDetailSerializer,
    FinancialAssessmentListSerializer,
    FinancialAssessmentWriteSerializer,
    FollowUpRuleSerializer,
    FollowUpRuleWriteSerializer,
    FollowUpTaskCompleteSerializer,
    FollowUpTaskDetailSerializer,
    FollowUpTaskListSerializer,
    FollowUpTaskManualCreateSerializer,
    LeadActivityGlobalWriteSerializer,
    LeadActivitySerializer,
    LeadActivityWriteSerializer,
    LeadConvertSerializer,
    LeadDetailSerializer,
    LeadDocumentEventSerializer,
    LeadDocumentEventWriteSerializer,
    LeadListSerializer,
    LeadPaymentScenarioSerializer,
    LeadPaymentScenarioWriteSerializer,
    LeadProjectInterestSerializer,
    LeadPropertyMatchListSerializer,
    LeadPropertyMatchWriteSerializer,
    LeadSourceSerializer,
    LeadStageChangeSerializer,
    LeadUnitPreferenceSerializer,
    LeadWriteSerializer,
    MeetingRecordDetailSerializer,
    MeetingRecordListSerializer,
    MeetingRecordWriteSerializer,
    OpportunityDealListSerializer,
    OpportunityDealWriteSerializer,
    ReservationCancelSerializer,
    ReservationConfirmSerializer,
    ReservationExtendHoldSerializer,
    ReservationPaymentSerializer,
    UnitReservationDetailSerializer,
    UnitReservationListSerializer,
    UnitReservationWriteSerializer,
)
from .tasks import (
    check_pipeline_drop_for_org,
    send_weekly_crm_analytics_report_for_org,
    sync_crm_procurement_demand_insights_for_org,
    sync_crm_project_demand_insights_for_org,
)


def _user_org(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _is_superuser(request):
    return request.user.is_superuser


def _requested_org_id(request):
    raw = request.query_params.get("organization_id") or request.query_params.get("org_id")
    if raw in (None, ""):
        return None
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _scope_queryset_for_request(request, queryset, *, org_field: str):
    if _is_superuser(request):
        requested_org_id = _requested_org_id(request)
        if requested_org_id:
            return queryset.filter(**{org_field: requested_org_id})
        return queryset

    org = _user_org(request)
    org_id = getattr(org, "id", None)
    if not org_id:
        return queryset.none()
    return queryset.filter(**{org_field: org_id})


def _scoped_lead_queryset(request):
    qs = _scope_queryset_for_request(
        request,
        Lead.objects.all(),
        org_field="organization_id",
    )
    return qs.select_related("source", "broker", "assigned_to", "converted_customer")


def _scoped_contact_queryset(request):
    return _scope_queryset_for_request(
        request,
        ContactAccount.objects.all(),
        org_field="organization_id",
    ).select_related("finance_customer", "created_by", "updated_by")


def _scoped_property_match_queryset(request):
    return _scope_queryset_for_request(
        request,
        LeadPropertyMatch.objects.all(),
        org_field="organization_id",
    ).select_related("lead", "property", "unit", "project")


def _ensure_contact_related_org(contact, **related):
    for field_name, model_obj in related.items():
        if model_obj is None:
            continue
        related_org_id = getattr(model_obj, "organization_id", None)
        if related_org_id != contact.organization_id:
            raise ValidationError(
                {
                    field_name: (
                        "Selected record does not belong to the same organization "
                        "as this contact."
                    )
                }
            )


def _select_auto_assignee_for_lead(organization):
    """Pick the least-loaded sales rep in the organization."""
    if organization is None:
        return None

    from apps.accounts.models import UserProfile

    profiles = UserProfile.objects.select_related("user", "assigned_role").filter(
        organization=organization,
        user_status=UserProfile.UserStatus.ACTIVE,
        user__is_active=True,
    )
    if not profiles.exists():
        return None

    sales_profiles = profiles.filter(
        Q(job_title__icontains="sales")
        | Q(job_title__icontains="leasing")
        | Q(assigned_role__slug__icontains="sales")
        | Q(assigned_role__name__icontains="sales")
        | Q(assigned_role__slug__icontains="crm")
        | Q(assigned_role__name__icontains="crm")
    )
    candidates = sales_profiles if sales_profiles.exists() else profiles
    candidate_profiles = list(candidates.order_by("user_id"))
    if not candidate_profiles:
        return None

    candidate_user_ids = [profile.user_id for profile in candidate_profiles]
    workload = (
        Lead.objects.filter(
            organization=organization,
            status=Lead.Status.ACTIVE,
            is_archived=False,
            assigned_to_id__in=candidate_user_ids,
        )
        .values("assigned_to_id")
        .annotate(total=Count("id"))
    )
    workload_map = {row["assigned_to_id"]: row["total"] for row in workload}

    selected = min(
        candidate_profiles,
        key=lambda profile: (workload_map.get(profile.user_id, 0), profile.user_id),
    )
    return selected.user


def _generate_follow_up_tasks_for_stage_entry(lead, stage):
    rules = FollowUpRule.objects.filter(
        organization_id=lead.organization_id,
        trigger_stage=stage,
        is_active=True,
    ).order_by("follow_up_within_hours", "id")
    if not rules.exists():
        return 0

    created_count = 0
    now = timezone.now()
    for rule in rules:
        has_open_task = FollowUpTask.objects.filter(
            rule=rule,
            lead=lead,
            status__in=[
                FollowUpTask.Status.PENDING,
                FollowUpTask.Status.IN_PROGRESS,
                FollowUpTask.Status.BREACHED,
                FollowUpTask.Status.ESCALATED,
            ],
        ).exists()
        if has_open_task:
            continue

        assigned_to_id = lead.assigned_to_id if rule.auto_assign_to_owner else None
        FollowUpTask.objects.create(
            rule=rule,
            lead=lead,
            assigned_to_id=assigned_to_id,
            due_at=now + timezone.timedelta(hours=rule.follow_up_within_hours),
        )
        created_count += 1

    return created_count


def _trigger_property_recommendations_for_qualified_lead(lead, *, actor=None):
    from apps.projects.models import Project

    match_result = generate_matches_for_qualified_lead(lead=lead)
    created_count = seed_project_interests_from_matches(lead=lead, limit=3)

    # Backward-compatible fallback: if matching didn't produce enough project
    # interests, continue to seed from pipeline-priority project ordering.
    if created_count < 3:
        existing_project_ids = set(
            lead.project_interests.values_list("project_id", flat=True)
        )
        stage_priority = models.Case(
            models.When(status=Project.Status.IN_PROGRESS, then=models.Value(0)),
            models.When(status=Project.Status.PLANNING, then=models.Value(1)),
            models.When(status=Project.Status.COMPLETED, then=models.Value(2)),
            default=models.Value(3),
            output_field=models.IntegerField(),
        )
        project_candidates = (
            Project.objects.filter(organization_id=lead.organization_id)
            .exclude(status=Project.Status.ON_HOLD)
            .annotate(_priority=stage_priority)
            .order_by("_priority", "-created_at")
        )
        if lead.lead_type in (Lead.LeadType.BUYER, Lead.LeadType.INVESTOR):
            project_candidates = project_candidates.filter(
                project_type__in=[
                    Project.ProjectType.RESIDENTIAL,
                    Project.ProjectType.MIXED_USE,
                ]
            )

        for project in project_candidates:
            if project.id in existing_project_ids:
                continue
            LeadProjectInterest.objects.create(
                lead=lead,
                project=project,
                interest_level=LeadProjectInterest.InterestLevel.MEDIUM,
                notes="Auto-recommended when lead reached Qualified stage.",
            )
            existing_project_ids.add(project.id)
            created_count += 1
            if created_count >= 3:
                break

    LeadActivity.objects.create(
        lead=lead,
        activity_type=LeadActivity.ActivityType.NOTE,
        subject="Property recommendations generated",
        description=(
            f"Property matching refreshed ({match_result['active_count']} active match(es)); "
            f"{created_count} project recommendation(s) available."
        ),
        performed_by=actor if getattr(actor, "is_authenticated", False) else None,
        completed_at=timezone.now(),
        is_completed=True,
    )
    return created_count


def _sync_contact_to_finance_customer(contact):
    from apps.finance.models import Customer

    customer_qs = Customer.objects.filter(organization_id=contact.organization_id)
    customer = None
    if contact.email:
        customer = customer_qs.filter(email__iexact=contact.email).first()
    if customer is None and contact.phone:
        customer = customer_qs.filter(phone=contact.phone).first()

    contact_name = contact.display_name
    contact_person = (
        contact.full_name
        if contact.entity_type == ContactAccount.EntityType.INDIVIDUAL
        else (contact.primary_contact_name or contact.full_name)
    )
    if customer is None:
        customer = Customer.objects.create(
            organization_id=contact.organization_id,
            name=contact_name,
            contact_person=contact_person or "",
            email=contact.email,
            phone=contact.phone,
            address=contact.address,
            notes=f"Auto-synced from CRM Contact Account #{contact.id}",
        )
    else:
        customer.name = contact_name or customer.name
        customer.contact_person = contact_person or customer.contact_person
        if contact.email:
            customer.email = contact.email
        if contact.phone:
            customer.phone = contact.phone
        if contact.address:
            customer.address = contact.address
        customer.save(
            update_fields=[
                "name", "contact_person", "email", "phone", "address", "updated_at",
            ]
        )

    contact.finance_customer = customer
    contact.finance_synced_at = timezone.now()
    contact.save(update_fields=["finance_customer", "finance_synced_at", "updated_at"])
    return customer


def _compliance_recipients_for_org(organization):
    from apps.accounts.models import UserProfile

    base_qs = UserProfile.objects.select_related("user", "assigned_role").filter(
        organization=organization,
        user_status=UserProfile.UserStatus.ACTIVE,
        user__is_active=True,
    )
    compliance_qs = base_qs.filter(
        Q(job_title__icontains="compliance")
        | Q(job_title__icontains="risk")
        | Q(job_title__icontains="legal")
        | Q(assigned_role__slug__icontains="compliance")
        | Q(assigned_role__name__icontains="compliance")
        | Q(assigned_role__slug__icontains="risk")
        | Q(assigned_role__name__icontains="risk")
    )
    target_qs = compliance_qs if compliance_qs.exists() else base_qs.filter(role="admin")
    seen = set()
    recipients = []
    for profile in target_qs.order_by("user_id"):
        if profile.user_id in seen:
            continue
        seen.add(profile.user_id)
        recipients.append(profile.user)
    return recipients


def _trigger_compliance_review_for_kyc_document(document, *, actor=None):
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    contact = document.contact
    review = ContactComplianceReview.objects.create(
        contact=contact,
        document=document,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        status=ContactComplianceReview.Status.PENDING_REVIEW,
        notes="Auto-triggered from KYC document upload.",
    )

    update_fields = ["kyc_status", "kyc_last_uploaded_at", "updated_at"]
    contact.kyc_status = ContactAccount.KYCStatus.PENDING_REVIEW
    contact.kyc_last_uploaded_at = timezone.now()
    if getattr(actor, "is_authenticated", False):
        contact.updated_by = actor
        update_fields.append("updated_by")
    contact.save(update_fields=update_fields)

    recipients = _compliance_recipients_for_org(contact.organization)
    if recipients:
        dispatch_workflow_notification(
            organization=contact.organization,
            event_key="crm_contact_kyc_review_requested",
            recipients=recipients,
            context={
                "contact_name": contact.display_name,
                "document_name": document.file_name,
                "action_url": f"/crm/contacts/{contact.id}",
            },
            link_url=f"/crm/contacts/{contact.id}",
            fallback_channels=["in_app"],
            fallback_title="KYC Document Requires Review",
            fallback_message=(
                f"A KYC document '{document.file_name}' has been uploaded for "
                f"{contact.display_name} and is awaiting verification. "
                f"Please review and approve or request resubmission."
            ),
            fallback_category=Notification.Category.CRM_LEAD,
            fallback_severity=Notification.Severity.WARNING,
        )
    return review


MANUAL_ACTIVITY_TASK_RULE_NAME = "Manual Activity Task"


def _manual_follow_up_rule_for_org(organization):
    if organization is None:
        return None

    rule, _created = FollowUpRule.objects.get_or_create(
        organization=organization,
        name=MANUAL_ACTIVITY_TASK_RULE_NAME,
        defaults={
            "description": "Manual CRM activity task assignment and reminders.",
            "trigger_stage": Lead.PipelineStage.INQUIRY,
            "follow_up_within_hours": 24,
            "required_activity_type": LeadActivity.ActivityType.FOLLOW_UP,
            "auto_assign_to_owner": False,
            "is_active": True,
        },
    )

    update_fields = []
    if not rule.is_active:
        rule.is_active = True
        update_fields.append("is_active")
    if rule.required_activity_type != LeadActivity.ActivityType.FOLLOW_UP:
        rule.required_activity_type = LeadActivity.ActivityType.FOLLOW_UP
        update_fields.append("required_activity_type")
    if rule.auto_assign_to_owner:
        rule.auto_assign_to_owner = False
        update_fields.append("auto_assign_to_owner")
    if update_fields:
        rule.save(update_fields=[*update_fields, "updated_at"])
    return rule

def _active_org_user_profiles(organization):
    from apps.accounts.models import UserProfile

    if organization is None:
        return UserProfile.objects.none()
    return UserProfile.objects.select_related("user", "assigned_role").filter(
        organization=organization,
        user_status=UserProfile.UserStatus.ACTIVE,
        user__is_active=True,
    )


def _logistics_recipients_for_org(organization):
    profiles = _active_org_user_profiles(organization)
    logistics_qs = profiles.filter(
        Q(job_title__icontains="logistics")
        | Q(job_title__icontains="transport")
        | Q(job_title__icontains="operations")
        | Q(job_title__icontains="facility")
        | Q(assigned_role__slug__icontains="logistics")
        | Q(assigned_role__name__icontains="logistics")
        | Q(assigned_role__slug__icontains="operations")
        | Q(assigned_role__name__icontains="operations")
    )
    target_qs = logistics_qs if logistics_qs.exists() else profiles.filter(role="admin")

    recipients = []
    seen = set()
    for profile in target_qs.order_by("user_id"):
        if profile.user_id in seen:
            continue
        seen.add(profile.user_id)
        recipients.append(profile.user)
    return recipients


def _notify_task_assignment(task, *, actor=None):
    if not task or not task.assigned_to_id:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    actor_name = ""
    if actor and getattr(actor, "is_authenticated", False):
        actor_name = actor.get_full_name() or actor.username or actor.email

    due_label = task.due_at.strftime("%b %d, %Y %I:%M %p")
    lead_name = task.lead.full_name
    title = f"CRM task assigned: {lead_name}"
    message = (
        f"You have a CRM follow-up task for {lead_name} due on {due_label}."
        + (f" Assigned by {actor_name}." if actor_name else "")
    )

    dispatch_workflow_notification(
        organization=task.lead.organization,
        event_key="crm_activity_task_assigned",
        recipients=[task.assigned_to],
        context={
            "lead_name": lead_name,
            "due_at": due_label,
            "rule_name": task.rule.name,
            "action_url": f"/crm/activities-tasks?task_id={task.id}",
        },
        link_url=f"/crm/activities-tasks?task_id={task.id}",
        fallback_channels=["in_app", "email"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )


def _ensure_scheduled_activity_task(activity, *, assigned_to=None, actor=None):
    if activity is None:
        return None
    if activity.is_completed or not activity.scheduled_at:
        return None

    rule = _manual_follow_up_rule_for_org(activity.lead.organization)
    if rule is None:
        return None

    marker = f"[activity:{activity.id}]"
    existing_task = (
        FollowUpTask.objects.filter(
        rule=rule,
        lead=activity.lead,
        notes__icontains=marker,
        status__in=[
            FollowUpTask.Status.PENDING,
            FollowUpTask.Status.IN_PROGRESS,
            FollowUpTask.Status.BREACHED,
            FollowUpTask.Status.ESCALATED,
        ],
    )
        .order_by("-id")
        .first()
    )

    assignee = assigned_to or activity.lead.assigned_to
    if existing_task:
        update_fields = []
        if existing_task.due_at != activity.scheduled_at:
            existing_task.due_at = activity.scheduled_at
            update_fields.append("due_at")
        assignee_id = getattr(assignee, "id", None)
        if assignee_id and existing_task.assigned_to_id != assignee_id:
            existing_task.assigned_to = assignee
            update_fields.append("assigned_to")
        if update_fields:
            existing_task.save(update_fields=[*update_fields, "updated_at"])
            _notify_task_assignment(existing_task, actor=actor)
        return existing_task

    task = FollowUpTask.objects.create(
        rule=rule,
        lead=activity.lead,
        assigned_to=assignee,
        due_at=activity.scheduled_at,
        notes=f"{marker} Scheduled activity follow-up: {activity.subject}",
    )
    _notify_task_assignment(task, actor=actor)
    return task


def _notify_site_visit_scheduled(activity, *, actor=None):
    if activity.activity_type != LeadActivity.ActivityType.SITE_VISIT:
        return
    if activity.scheduled_at is None:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    lead = activity.lead
    scheduled_label = activity.scheduled_at.strftime("%b %d, %Y %I:%M %p")

    if lead.email:
        subject = f"Site visit scheduled: {lead.full_name}"
        message = (
            f"Hello {lead.full_name},\n\n"
            f"Your site visit is scheduled for {scheduled_label}.\n"
            f"Activity: {activity.subject}\n\n"
            "If you need to reschedule, please contact your sales representative."
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=None,
            recipient_list=[lead.email],
            fail_silently=True,
        )

    recipients = []
    seen = set()

    def add_recipient(user_obj):
        if not user_obj:
            return
        uid = getattr(user_obj, "id", None)
        if not uid or not getattr(user_obj, "is_active", False):
            return
        if uid in seen:
            return
        seen.add(uid)
        recipients.append(user_obj)

    add_recipient(lead.assigned_to)
    for user_obj in _logistics_recipients_for_org(lead.organization):
        add_recipient(user_obj)

    if recipients:
        dispatch_workflow_notification(
            organization=lead.organization,
            event_key="crm_site_visit_scheduled",
            recipients=recipients,
            context={
                "lead_name": lead.full_name,
                "scheduled_at": scheduled_label,
                "activity_subject": activity.subject,
                "action_url": f"/crm/activities-tasks?activity_id={activity.id}",
            },
            link_url=f"/crm/activities-tasks?activity_id={activity.id}",
            fallback_channels=["in_app", "email"],
            fallback_title=f"Site Visit Scheduled — {lead.full_name}",
            fallback_message=(
                f"A site visit '{activity.subject}' has been scheduled for "
                f"{lead.full_name} on {scheduled_label}. "
                f"Please coordinate logistics and confirm attendance with the client."
            ),
            fallback_category=Notification.Category.CRM_LEAD,
            fallback_severity=Notification.Severity.INFO,
        )


CRM_OVERVIEW_CACHE_TTL_SECONDS = 120


def _sorted_query_hash(query_params) -> str:
    normalized = []
    for key in sorted(query_params.keys()):
        values = sorted(str(value) for value in query_params.getlist(key))
        normalized.extend(f"{key}={value}" for value in values)
    if not normalized:
        return "noquery"
    return hashlib.sha1("&".join(normalized).encode("utf-8")).hexdigest()[:16]


def _crm_overview_cache_key(request, scope: str) -> str:
    org_id = 0
    if _is_superuser(request):
        requested_org_id = _requested_org_id(request)
        org_id = requested_org_id or 0
    else:
        org = _user_org(request)
        org_id = getattr(org, "id", 0) or 0
    return (
        f"crm:overview:{scope}:u:{request.user.id}:"
        f"org:{org_id}:super:{int(_is_superuser(request))}:"
        f"q:{_sorted_query_hash(request.query_params)}"
    )


_CLOSED_WON_STAGE_ALIASES = {"closed won", "won"}
_CLOSED_LOST_STAGE_ALIASES = {"closed lost", "lost"}
_KYC_REQUIRED_PIPELINE_STAGES = {
    Lead.PipelineStage.SPA_ISSUED,
    Lead.PipelineStage.CLOSED,
}
_KYC_REQUIRED_DEAL_STAGE_TERMS = ("contract", "spa")


def _to_decimal(value, default: str = "0.00") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _payment_plan_default_currency_code() -> str:
    from apps.finance.models import PaymentPlan

    default_value = PaymentPlan._meta.get_field("currency").default
    return default_value() if callable(default_value) else default_value


def _normalize_stage_value(stage_value: str | None) -> str:
    if not stage_value:
        return ""
    normalized = stage_value.replace("_", " ").strip().lower()
    return " ".join(normalized.split())


def _is_closed_won_state(*, status_value: str | None, stage_value: str | None) -> bool:
    if status_value == ContactDealLink.Status.WON:
        return True
    return _normalize_stage_value(stage_value) in _CLOSED_WON_STAGE_ALIASES


def _is_closed_lost_state(*, status_value: str | None, stage_value: str | None) -> bool:
    if status_value == ContactDealLink.Status.LOST:
        return True
    return _normalize_stage_value(stage_value) in _CLOSED_LOST_STAGE_ALIASES


def _lead_contract_stage_kyc_block_reason(*, lead: Lead) -> str | None:
    linked_contacts = ContactAccount.objects.filter(
        organization_id=lead.organization_id,
        deal_links__lead=lead,
    ).distinct()
    linked_count = linked_contacts.count()
    verified_count = linked_contacts.filter(
        kyc_status=ContactAccount.KYCStatus.VERIFIED
    ).count()

    if verified_count > 0:
        return None

    if linked_count == 0:
        return (
            "KYC verification is required before moving this deal to contract stages. "
            "Link a contact account with verified KYC first."
        )

    return (
        "KYC verification is required before moving this deal to contract stages. "
        f"Linked contacts with verified KYC: {verified_count}/{linked_count}."
    )


def _ensure_lead_contract_stage_kyc_gate(*, lead: Lead, target_stage: str):
    if target_stage not in _KYC_REQUIRED_PIPELINE_STAGES:
        return
    block_reason = _lead_contract_stage_kyc_block_reason(lead=lead)
    if block_reason:
        raise ValidationError({"stage": block_reason})


def _deal_transition_requires_verified_kyc(*, stage_value: str | None, status_value: str | None) -> bool:
    normalized_stage = _normalize_stage_value(stage_value)
    if any(term in normalized_stage for term in _KYC_REQUIRED_DEAL_STAGE_TERMS):
        return True
    return _is_closed_won_state(status_value=status_value, stage_value=stage_value)


def _ensure_deal_contract_stage_kyc_gate(
    *,
    contact: ContactAccount | None,
    lead: Lead | None,
    stage_value: str | None,
    status_value: str | None,
):
    if not _deal_transition_requires_verified_kyc(
        stage_value=stage_value,
        status_value=status_value,
    ):
        return

    if contact is not None and contact.kyc_status == ContactAccount.KYCStatus.VERIFIED:
        return

    if lead is not None:
        block_reason = _lead_contract_stage_kyc_block_reason(lead=lead)
        if block_reason is None:
            return
    elif contact is not None:
        block_reason = (
            "KYC verification is required before moving this deal to contract stages. "
            f"Contact '{contact.display_name}' is {contact.get_kyc_status_display()}."
        )
    else:
        block_reason = (
            "KYC verification is required before moving this deal to contract stages."
        )

    raise ValidationError({"stage": block_reason, "status": block_reason})


def _deal_value_for_automation(*, deal: ContactDealLink, reservation: UnitReservation | None) -> Decimal:
    if deal.deal_value is not None:
        return _to_decimal(deal.deal_value)
    if reservation is not None and reservation.total_price is not None:
        return _to_decimal(reservation.total_price)
    return Decimal("0.00")


def _reserve_unit_for_deal(*, deal: ContactDealLink, actor=None):
    reservation = deal.reservation
    if reservation is None or not reservation.unit_id:
        return

    from apps.properties.models import PropertyInventory, Unit

    unit = reservation.unit
    if unit.status == Unit.UnitStatus.AVAILABLE:
        unit.status = Unit.UnitStatus.RESERVED
        unit.save(update_fields=["status", "updated_at"])

    inventory, _ = PropertyInventory.objects.get_or_create(
        organization_id=reservation.organization_id,
        unit=unit,
        defaults={
            "status": PropertyInventory.InventoryStatus.RESERVED,
            "reservation": reservation,
            "held_by": (deal.contact.display_name if deal.contact_id else ""),
            "held_until": reservation.hold_expires_at,
            "list_price": unit.asking_price,
        },
    )
    update_fields = []
    if inventory.reservation_id != reservation.id:
        inventory.reservation = reservation
        update_fields.append("reservation")
    if inventory.status == PropertyInventory.InventoryStatus.AVAILABLE:
        inventory.status = PropertyInventory.InventoryStatus.RESERVED
        update_fields.append("status")
    holder_name = deal.contact.display_name if deal.contact_id else ""
    if holder_name and inventory.held_by != holder_name:
        inventory.held_by = holder_name[:255]
        update_fields.append("held_by")
    if reservation.hold_expires_at and inventory.held_until != reservation.hold_expires_at:
        inventory.held_until = reservation.hold_expires_at
        update_fields.append("held_until")
    if update_fields:
        inventory.save(update_fields=[*update_fields, "updated_at"])

    ReservationEvent.objects.create(
        reservation=reservation,
        event_type=ReservationEvent.EventType.NOTE_ADDED,
        performed_by=actor if getattr(actor, "is_authenticated", False) else None,
        notes="Unit reserved from Opportunity / Deal creation.",
        metadata={
            "automation": "deal_created_reserve_unit",
            "deal_link_id": deal.id,
            "unit_id": unit.id,
            "unit_status": unit.status,
            "inventory_status": inventory.status,
        },
    )


def _release_unit_for_lost_deal(*, deal: ContactDealLink, actor=None):
    reservation = deal.reservation
    if reservation is None or not reservation.unit_id:
        return

    from apps.properties.models import PropertyInventory, Unit

    unit = reservation.unit
    if unit.status == Unit.UnitStatus.RESERVED:
        unit.status = Unit.UnitStatus.AVAILABLE
        unit.save(update_fields=["status", "updated_at"])

    inventory = (
        PropertyInventory.objects
        .filter(organization_id=reservation.organization_id, unit=unit)
        .first()
    )
    if inventory is not None:
        update_fields = []
        if inventory.status in (
            PropertyInventory.InventoryStatus.HELD,
            PropertyInventory.InventoryStatus.RESERVED,
        ):
            inventory.status = PropertyInventory.InventoryStatus.AVAILABLE
            update_fields.append("status")
        if inventory.reservation_id == reservation.id:
            inventory.reservation = None
            update_fields.append("reservation")
        if inventory.held_by:
            inventory.held_by = ""
            update_fields.append("held_by")
        if inventory.held_until is not None:
            inventory.held_until = None
            update_fields.append("held_until")
        if inventory.allocated_to:
            inventory.allocated_to = ""
            update_fields.append("allocated_to")
        if inventory.allocated_on is not None:
            inventory.allocated_on = None
            update_fields.append("allocated_on")
        if update_fields:
            inventory.save(update_fields=[*update_fields, "updated_at"])

    ReservationEvent.objects.create(
        reservation=reservation,
        event_type=ReservationEvent.EventType.NOTE_ADDED,
        performed_by=actor if getattr(actor, "is_authenticated", False) else None,
        notes="Unit released from Opportunity / Deal marked as lost.",
        metadata={
            "automation": "deal_lost_release_unit",
            "deal_link_id": deal.id,
            "unit_id": unit.id,
            "unit_status": unit.status,
            "inventory_status": (
                inventory.status
                if inventory is not None
                else ""
            ),
        },
    )


def _ensure_finance_customer_for_lead(*, lead: Lead, reservation_number: str = ""):
    from apps.finance.models import Customer

    if lead.converted_customer_id:
        return lead.converted_customer

    customer = Customer.objects.create(
        organization_id=lead.organization_id,
        name=lead.full_name or "CRM Lead",
        contact_person=lead.full_name or "",
        email=lead.email,
        phone=lead.phone,
        address="",
        notes=(
            "Auto-created from CRM closed-won deal"
            + (f" ({reservation_number})" if reservation_number else "")
            + "."
        ),
    )
    lead.converted_customer = customer
    lead.save(update_fields=["converted_customer", "updated_at"])
    return customer


def _generate_reservation_document_for_closed_won(
    *,
    deal: ContactDealLink,
    reservation: UnitReservation,
    request,
    actor,
    reservation_field: str,
    title: str,
    document_type_code: str,
    success_notes: str,
    automation_key: str,
):
    existing_doc_id = getattr(reservation, f"{reservation_field}_id", None)
    if existing_doc_id:
        return getattr(reservation, reservation_field), None

    if not getattr(actor, "is_authenticated", False):
        return None, f"Authenticated user required for {title.lower()} generation."

    from apps.documents.generation_service import generate_branded_document
    from apps.settings.models import ensure_default_document_automation_settings

    automation_settings = ensure_default_document_automation_settings(reservation.organization)
    if (
        automation_settings is None
        or automation_settings.default_generation_owner_role_id is None
        or automation_settings.default_generation_phase_id is None
        or automation_settings.default_generation_retention_policy_id is None
    ):
        return None, "Document automation defaults are incomplete."

    lead = reservation.lead
    customer = _ensure_finance_customer_for_lead(
        lead=lead,
        reservation_number=reservation.reservation_number,
    )
    deal_value = _deal_value_for_automation(deal=deal, reservation=reservation)
    unit = reservation.unit
    property_obj = unit.property if unit and unit.property_id else None

    payload = {
        "generation_kind": "contract",
        "document_type_code": document_type_code,
        "title": f"{title} — {reservation.reservation_number}",
        "summary": (
            f"Auto-generated {title.lower()} from closed-won deal for {lead.full_name} "
            f"({reservation.reservation_number})."
        ),
        "body": (
            f"Document: {title}\n"
            f"Buyer: {lead.full_name}\n"
            f"Reservation: {reservation.reservation_number}\n"
            f"Unit: {unit.unit_number if unit else ''}\n"
            f"Property: {property_obj.name if property_obj else ''}\n"
            f"Agreed Value: {deal_value}\n"
        ),
        "template_code": automation_settings.default_generation_template_code or "",
        "variables": {
            "deal_link_id": deal.id,
            "reservation_number": reservation.reservation_number,
            "lead_name": lead.full_name,
            "unit_number": unit.unit_number if unit else "",
            "property_name": property_obj.name if property_obj else "",
            "deal_value": str(deal_value),
            "document_type_code": document_type_code,
        },
        "project_code": "",
        "contract_value": deal_value,
        "project": reservation.project,
        "land": property_obj,
        "unit": unit,
        "client": customer,
        "vendor": None,
        "business_unit_division": None,
        "business_unit_department": None,
        "owner_role": automation_settings.default_generation_owner_role,
        "phase": automation_settings.default_generation_phase,
        "retention_policy": automation_settings.default_generation_retention_policy,
        "confidentiality_level": automation_settings.default_generation_confidentiality_level,
    }

    try:
        result = generate_branded_document(
            request=request,
            user=actor,
            validated_data=payload,
        )
    except Exception as exc:
        return None, str(exc)

    setattr(reservation, reservation_field, result.document)
    reservation.save(update_fields=[reservation_field, "updated_at"])

    ReservationEvent.objects.create(
        reservation=reservation,
        event_type=ReservationEvent.EventType.FORM_GENERATED,
        performed_by=actor if getattr(actor, "is_authenticated", False) else None,
        notes=success_notes,
        metadata={
            "automation": automation_key,
            "deal_link_id": deal.id,
            "document_type_code": document_type_code,
            "document_id": result.document.id,
            "document_number": result.document.document_number,
            "document_version_id": result.version.id,
            "generation_record_id": result.generation_record.id,
        },
    )
    return result.document, None


def _generate_sales_agreement_for_reservation(
    *,
    deal: ContactDealLink,
    reservation: UnitReservation,
    request,
    actor,
):
    return _generate_reservation_document_for_closed_won(
        deal=deal,
        reservation=reservation,
        request=request,
        actor=actor,
        reservation_field="reservation_agreement",
        title="Sales Agreement",
        document_type_code="sales_agreement",
        success_notes="Sales agreement generated from closed-won deal.",
        automation_key="deal_closed_won_sales_agreement_generation",
    )


def _generate_allocation_letter_for_reservation(
    *,
    deal: ContactDealLink,
    reservation: UnitReservation,
    request,
    actor,
):
    return _generate_reservation_document_for_closed_won(
        deal=deal,
        reservation=reservation,
        request=request,
        actor=actor,
        reservation_field="allocation_letter",
        title="Allocation Letter",
        document_type_code="allocation_letter",
        success_notes="Allocation letter generated from closed-won deal.",
        automation_key="deal_closed_won_allocation_letter_generation",
    )


def _create_invoice_for_deal(*, deal: ContactDealLink, reservation: UnitReservation | None):
    from apps.finance.models import Invoice, InvoiceLineItem

    lead = deal.lead or (reservation.lead if reservation else None)
    if lead is None:
        return None

    marker = f"[CRM_DEAL_LINK:{deal.id}]"
    existing_invoice = (
        Invoice.objects.filter(
            organization_id=lead.organization_id,
            notes__icontains=marker,
        )
        .order_by("-id")
        .first()
    )
    if existing_invoice:
        return existing_invoice

    customer = _ensure_finance_customer_for_lead(
        lead=lead,
        reservation_number=reservation.reservation_number if reservation else "",
    )
    property_obj = None
    if reservation and reservation.unit_id and reservation.unit.property_id:
        property_obj = reservation.unit.property

    today = timezone.now().date()
    due_date = today + timezone.timedelta(days=14)
    deal_value = _deal_value_for_automation(deal=deal, reservation=reservation)

    invoice = Invoice.objects.create(
        organization_id=lead.organization_id,
        customer=customer,
        property=property_obj,
        status=Invoice.Status.DRAFT,
        issue_date=today,
        due_date=due_date,
        notes=(
            f"Auto-created from CRM closed-won deal #{deal.id}. "
            f"{marker}"
        ),
    )
    line_description = (
        f"Unit Sale — {reservation.unit.unit_number}"
        if reservation and reservation.unit_id
        else f"CRM Deal — {deal.deal_name or lead.full_name}"
    )
    InvoiceLineItem.objects.create(
        invoice=invoice,
        description=line_description,
        quantity=Decimal("1.00"),
        unit_price=deal_value,
        sort_order=1,
    )
    invoice.recalculate_totals()
    return invoice


def _create_payment_schedule_for_deal(
    *,
    deal: ContactDealLink,
    reservation: UnitReservation | None,
    invoice=None,
    actor=None,
):
    from apps.finance.models import PaymentInstallment, PaymentPlan
    from apps.settings.models import SystemPreferences

    lead = deal.lead or (reservation.lead if reservation else None)
    if lead is None:
        return None

    if reservation is not None and reservation.payment_plan_id:
        plan = reservation.payment_plan
        update_fields = []
        customer = _ensure_finance_customer_for_lead(
            lead=lead,
            reservation_number=reservation.reservation_number if reservation else "",
        )
        if plan.customer_id is None:
            plan.customer = customer
            update_fields.append("customer")
        if plan.direction != PaymentPlan.Direction.RECEIVABLE:
            plan.direction = PaymentPlan.Direction.RECEIVABLE
            update_fields.append("direction")
        if update_fields:
            plan.save(update_fields=[*update_fields, "updated_at"])
        return plan

    marker = f"[CRM_DEAL_PAYMENT_PLAN:{deal.id}]"
    existing_plan = (
        PaymentPlan.objects.filter(
            organization_id=lead.organization_id,
            notes__icontains=marker,
        )
        .order_by("-id")
        .first()
    )
    if existing_plan is not None:
        if reservation is not None and reservation.payment_plan_id is None:
            reservation.payment_plan = existing_plan
            reservation.save(update_fields=["payment_plan", "updated_at"])
        return existing_plan

    customer = _ensure_finance_customer_for_lead(
        lead=lead,
        reservation_number=reservation.reservation_number if reservation else "",
    )
    deal_value = _deal_value_for_automation(deal=deal, reservation=reservation)
    today = timezone.now().date()
    due_date = getattr(invoice, "due_date", None) or (today + timezone.timedelta(days=14))
    unit = reservation.unit if reservation and reservation.unit_id else None

    default_currency = (
        SystemPreferences.objects.filter(organization_id=lead.organization_id)
        .values_list("default_currency", flat=True)
        .first()
        or _payment_plan_default_currency_code()
    )
    plan = PaymentPlan.objects.create(
        organization_id=lead.organization_id,
        title=f"Deal {deal.id} Payment Schedule — {lead.full_name}",
        description="Auto-generated receivable schedule from CRM closed-won deal.",
        status=PaymentPlan.Status.ACTIVE,
        plan_type=PaymentPlan.PlanType.CUSTOM,
        direction=PaymentPlan.Direction.RECEIVABLE,
        frequency=PaymentPlan.Frequency.ONE_TIME,
        customer=customer,
        project=reservation.project if reservation and reservation.project_id else None,
        unit=unit,
        total_amount=deal_value,
        currency=default_currency,
        start_date=today,
        end_date=due_date,
        number_of_installments=1,
        notes=f"Auto-created from CRM closed-won deal #{deal.id}. {marker}",
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    PaymentInstallment.objects.create(
        payment_plan=plan,
        installment_number=1,
        label="Deal Settlement",
        amount=deal_value,
        scheduled_date=today,
        due_date=due_date,
        status=PaymentInstallment.Status.DUE,
    )
    if reservation is not None and reservation.payment_plan_id is None:
        reservation.payment_plan = plan
        reservation.save(update_fields=["payment_plan", "updated_at"])
    return plan


def _post_customer_ledger_for_deal(
    *,
    deal: ContactDealLink,
    reservation: UnitReservation | None,
    invoice=None,
    actor=None,
):
    from apps.finance.gl_utils import post_journal_entry
    from apps.finance.models import Account, AccountSubType, AccountType, JournalEntry, JournalLine, JournalSourceType

    lead = deal.lead or (reservation.lead if reservation else None)
    if lead is None:
        return None

    marker = f"[CRM_DEAL_LEDGER:{deal.id}]"
    existing = (
        JournalEntry.objects.filter(
            organization_id=lead.organization_id,
            description__icontains=marker,
        )
        .order_by("-id")
        .first()
    )
    if existing is not None:
        if existing.status != JournalEntry.Status.POSTED and getattr(actor, "is_authenticated", False):
            try:
                existing = post_journal_entry(existing.id, actor)
            except Exception:
                pass
        return existing

    ar_account = (
        Account.objects.filter(
            organization_id=lead.organization_id,
            code="1100",
            is_active=True,
        ).first()
        or Account.objects.filter(
            organization_id=lead.organization_id,
            account_type=AccountType.ASSET,
            sub_type=AccountSubType.CURRENT_ASSET,
            name__icontains="receivable",
            is_active=True,
        )
        .order_by("code")
        .first()
    )
    revenue_account = (
        Account.objects.filter(
            organization_id=lead.organization_id,
            code="4100",
            is_active=True,
        ).first()
        or Account.objects.filter(
            organization_id=lead.organization_id,
            account_type=AccountType.REVENUE,
            sub_type=AccountSubType.OPERATING_REVENUE,
            is_active=True,
        )
        .order_by("code")
        .first()
    )
    if ar_account is None or revenue_account is None:
        raise ValueError("Required AR / revenue GL accounts are missing for closed-won ledger posting.")

    amount = _to_decimal(getattr(invoice, "total_amount", None))
    if amount <= Decimal("0.00"):
        amount = _deal_value_for_automation(deal=deal, reservation=reservation)
    if amount <= Decimal("0.00"):
        return None

    source_id = getattr(invoice, "id", None) or deal.id
    journal = JournalEntry.objects.create(
        organization_id=lead.organization_id,
        entry_date=timezone.now().date(),
        description=(
            f"Auto-posted customer receivable from CRM closed-won deal #{deal.id}. "
            f"{marker}"
        ),
        reference=f"CRM-DEAL-{deal.id}",
        source_type=JournalSourceType.INVOICE,
        source_id=source_id,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    JournalLine.objects.create(
        journal=journal,
        line_number=1,
        account=ar_account,
        debit_amount=amount,
        credit_amount=Decimal("0.00"),
        memo=f"Accounts receivable for CRM deal #{deal.id}",
    )
    JournalLine.objects.create(
        journal=journal,
        line_number=2,
        account=revenue_account,
        debit_amount=Decimal("0.00"),
        credit_amount=amount,
        memo=f"Property sales revenue for CRM deal #{deal.id}",
    )
    if getattr(actor, "is_authenticated", False):
        journal = post_journal_entry(journal.id, actor)
    return journal


def _mark_unit_sold_for_deal(*, deal: ContactDealLink, reservation: UnitReservation | None, actor=None):
    if reservation is None or not reservation.unit_id:
        return

    from apps.properties.models import PropertyInventory, Unit

    unit = reservation.unit
    if unit.status != Unit.UnitStatus.SOLD:
        unit.status = Unit.UnitStatus.SOLD
        unit.save(update_fields=["status", "updated_at"])

    inventory, _ = PropertyInventory.objects.get_or_create(
        organization_id=reservation.organization_id,
        unit=unit,
        defaults={"status": PropertyInventory.InventoryStatus.SOLD},
    )
    update_fields = []
    if inventory.reservation_id != reservation.id:
        inventory.reservation = reservation
        update_fields.append("reservation")
    buyer_name = reservation.lead.full_name if reservation.lead_id else ""
    if buyer_name and inventory.allocated_to != buyer_name:
        inventory.allocated_to = buyer_name[:255]
        update_fields.append("allocated_to")
    allocated_on = timezone.now().date()
    if inventory.allocated_on != allocated_on:
        inventory.allocated_on = allocated_on
        update_fields.append("allocated_on")
    if inventory.held_by:
        inventory.held_by = ""
        update_fields.append("held_by")
    if inventory.held_until is not None:
        inventory.held_until = None
        update_fields.append("held_until")
    if update_fields:
        inventory.save(update_fields=[*update_fields, "updated_at"])

    ReservationEvent.objects.create(
        reservation=reservation,
        event_type=ReservationEvent.EventType.UNIT_TRANSFERRED,
        performed_by=actor if getattr(actor, "is_authenticated", False) else None,
        notes="Property inventory status updated to Sold from closed-won deal.",
        metadata={
            "automation": "deal_closed_won_property_status",
            "deal_link_id": deal.id,
            "unit_id": unit.id,
            "unit_status": unit.status,
            "inventory_status": inventory.status,
            "property_id": unit.property_id,
        },
    )


def _commission_marker_for_deal(*, deal: ContactDealLink, trigger_stage: str) -> str:
    deal_identifier = getattr(deal, "id", None)
    if deal_identifier is None:
        if getattr(deal, "reservation_id", None):
            deal_identifier = f"reservation-{deal.reservation_id}"
        elif getattr(deal, "lead_id", None):
            deal_identifier = f"lead-{deal.lead_id}"
        else:
            deal_identifier = "unspecified"
    return f"[CRM_DEAL_COMMISSION:{deal_identifier}:{trigger_stage}]"


def _resolve_commission_structure_for_deal(
    *,
    broker: Broker | None,
    lead: Lead | None,
    reservation: UnitReservation | None,
    trigger_stage: str,
):
    if broker is None or lead is None:
        return None

    today = timezone.now().date()
    structure_qs = BrokerCommissionStructure.objects.filter(
        organization_id=lead.organization_id,
        is_active=True,
        trigger_stage=trigger_stage,
    ).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=today),
        Q(effective_to__isnull=True) | Q(effective_to__gte=today),
    )
    project_id = reservation.project_id if reservation is not None else None

    def first_match(queryset):
        return queryset.order_by("-is_default", "-id").first()

    if project_id:
        match = first_match(
            structure_qs.filter(
                broker=broker,
                project_id=project_id,
            )
        )
        if match:
            return match

    match = first_match(
        structure_qs.filter(
            broker=broker,
            project__isnull=True,
        )
    )
    if match:
        return match

    if project_id:
        match = first_match(
            structure_qs.filter(
                broker__isnull=True,
                project_id=project_id,
            )
        )
        if match:
            return match

    match = first_match(
        structure_qs.filter(
            is_default=True,
            broker__isnull=True,
            project__isnull=True,
        )
    )
    if match:
        return match

    return first_match(
        structure_qs.filter(
            broker__isnull=True,
            project__isnull=True,
        )
    )


def _finance_recipients_for_org(organization):
    profiles = _active_org_user_profiles(organization)
    finance_qs = profiles.filter(
        Q(job_title__icontains="finance")
        | Q(job_title__icontains="account")
        | Q(job_title__icontains="treasury")
        | Q(job_title__icontains="cfo")
        | Q(assigned_role__slug__icontains="finance")
        | Q(assigned_role__name__icontains="finance")
        | Q(assigned_role__slug__icontains="account")
        | Q(assigned_role__name__icontains="account")
    )
    target_qs = finance_qs if finance_qs.exists() else profiles.filter(role="admin")

    recipients = []
    seen = set()
    for profile in target_qs.order_by("user_id"):
        if profile.user_id in seen:
            continue
        seen.add(profile.user_id)
        recipients.append(profile.user)
    return recipients


def _broker_incentive_recipients_for_org(organization):
    profiles = _active_org_user_profiles(organization)
    broker_ops_qs = profiles.filter(
        Q(job_title__icontains="broker")
        | Q(job_title__icontains="channel")
        | Q(job_title__icontains="partner")
        | Q(job_title__icontains="sales")
        | Q(job_title__icontains="business development")
        | Q(assigned_role__slug__icontains="broker")
        | Q(assigned_role__name__icontains="broker")
        | Q(assigned_role__slug__icontains="partner")
        | Q(assigned_role__name__icontains="partner")
        | Q(assigned_role__slug__icontains="sales")
        | Q(assigned_role__name__icontains="sales")
        | Q(assigned_role__slug__icontains="crm")
        | Q(assigned_role__name__icontains="crm")
    )
    target_qs = broker_ops_qs if broker_ops_qs.exists() else profiles.filter(role="admin")

    recipients = []
    seen = set()
    for profile in target_qs.order_by("user_id"):
        if profile.user_id in seen:
            continue
        seen.add(profile.user_id)
        recipients.append(profile.user)
    return recipients


def _notify_finance_of_commission(*, earning: BrokerCommissionEarning, deal: ContactDealLink):
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    organization = getattr(earning.broker, "organization", None)
    recipients = _finance_recipients_for_org(organization)
    if not recipients:
        return

    deal_label = (
        deal.deal_name
        or (earning.lead.full_name if earning.lead_id else "")
        or f"Deal #{getattr(deal, 'id', '')}"
    )
    link_url = f"/crm/brokers?commission_earning_id={earning.id}"
    dispatch_workflow_notification(
        organization=organization,
        event_key="crm_broker_commission_ready_for_finance",
        recipients=recipients,
        context={
            "broker_name": earning.broker.name,
            "lead_name": earning.lead.full_name if earning.lead_id else "",
            "deal_name": deal_label,
            "deal_value": str(_to_decimal(earning.deal_value).quantize(Decimal("0.01"))),
            "commission_amount": str(_to_decimal(earning.total_commission).quantize(Decimal("0.01"))),
            "commission_rate": str(_to_decimal(earning.commission_rate).quantize(Decimal("0.01"))),
            "action_url": link_url,
        },
        link_url=link_url,
        fallback_channels=["in_app", "email"],
        fallback_title=f"Broker Commission Ready for Processing — {earning.broker.name}",
        fallback_message=(
            f"A commission of ₦{earning.total_commission:,.2f} has been calculated for "
            f"{earning.broker.name} on deal '{deal_label}'. "
            f"This is now ready for finance review and disbursement."
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.WARNING,
    )


def _maybe_trigger_broker_target_incentive(*, earning: BrokerCommissionEarning, actor=None) -> bool:
    broker = earning.broker
    tier = getattr(broker, "tier", None)
    if tier is None or not tier.is_active:
        return False

    evaluation_months = max(int(tier.evaluation_period_months or 0), 1)
    cutoff = timezone.now() - timezone.timedelta(days=evaluation_months * 30)
    performance_qs = broker.commission_earnings.filter(
        created_at__gte=cutoff,
        trigger_stage=BrokerCommissionStructure.TriggerStage.CLOSED,
    ).exclude(status=BrokerCommissionEarning.Status.CANCELLED)
    metrics = performance_qs.aggregate(
        deals_count=Count("id"),
        total_deal_value=Sum("deal_value"),
    )
    deals_count = int(metrics["deals_count"] or 0)
    total_deal_value = _to_decimal(metrics["total_deal_value"])
    required_deals = int(tier.min_deals or 0)
    required_revenue = _to_decimal(tier.min_revenue)
    if deals_count < required_deals or total_deal_value < required_revenue:
        return False

    marker = f"[CRM_INCENTIVE_TRIGGERED:tier:{tier.id}]"
    if broker.commission_earnings.filter(notes__icontains=marker).exists():
        return False

    incentive_note = (
        f"{marker} Auto-triggered when broker hit tier target with "
        f"{deals_count} closed deal(s) and "
        f"{total_deal_value.quantize(Decimal('0.01'))} in deal value."
    )
    if (earning.notes or "").strip():
        earning.notes = f"{earning.notes.strip()}\n{incentive_note}"
    else:
        earning.notes = incentive_note
    earning.save(update_fields=["notes", "updated_at"])

    recipients = _broker_incentive_recipients_for_org(broker.organization)
    if not recipients:
        return True

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    actor_name = ""
    if actor is not None and getattr(actor, "is_authenticated", False):
        actor_name = actor.get_full_name() or actor.username or actor.email
    link_url = f"/crm/brokers?broker_id={broker.id}"
    dispatch_workflow_notification(
        organization=broker.organization,
        event_key="crm_broker_target_hit_incentive",
        recipients=recipients,
        context={
            "broker_name": broker.name,
            "tier_name": tier.name,
            "deals_count": deals_count,
            "revenue_total": str(total_deal_value.quantize(Decimal("0.01"))),
            "target_deals": required_deals,
            "target_revenue": str(required_revenue.quantize(Decimal("0.01"))),
            "bonus_pct": str(_to_decimal(tier.bonus_pct).quantize(Decimal("0.01"))),
            "triggered_by": actor_name,
            "action_url": link_url,
        },
        link_url=link_url,
        fallback_channels=["in_app", "email"],
        fallback_title=f"Broker Incentive Target Reached — {broker.name}",
        fallback_message=(
            f"{broker.name} has reached the '{tier.name}' incentive tier with {deals_count} "
            f"closed deal(s). The corresponding bonus should be reviewed and applied by management."
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )
    return True


def _resolve_hr_employee_for_broker(*, broker: Broker):
    from apps.hr.models import EmployeeRecord

    organization = getattr(broker, "organization", None)
    if organization is None:
        return None

    qs = (
        EmployeeRecord.objects.select_related("user")
        .filter(organization=organization)
        .exclude(
            employment_status__in=[
                EmployeeRecord.EmploymentStatus.TERMINATED,
                EmployeeRecord.EmploymentStatus.RESIGNED,
            ]
        )
    )
    broker_email = (broker.email or "").strip()
    if broker_email:
        employee = qs.filter(user__email__iexact=broker_email).order_by("-id").first()
        if employee is not None:
            return employee
    return None


def _sync_hr_sales_performance_rewards(
    *,
    deal: ContactDealLink,
    earning: BrokerCommissionEarning,
):
    """Post CRM sales performance payouts into HR bonuses for payroll visibility."""
    from apps.hr.models import Bonus

    if earning is None or getattr(earning, "broker_id", None) is None:
        return None

    broker = earning.broker
    employee = _resolve_hr_employee_for_broker(broker=broker)
    if employee is None:
        return None

    organization = employee.organization
    deal_id = getattr(deal, "id", "n/a")
    reward_date = timezone.localdate(getattr(earning, "triggered_at", None) or timezone.now())

    commission_component = _to_decimal(earning.total_commission) - _to_decimal(earning.bonus_amount)
    if commission_component < Decimal("0.00"):
        commission_component = Decimal("0.00")
    commission_component = commission_component.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    incentive_component = _to_decimal(earning.bonus_amount)
    if incentive_component < Decimal("0.00"):
        incentive_component = Decimal("0.00")
    incentive_component = incentive_component.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    created_bonus_ids = []
    commission_marker = f"[CRM_DEAL_HR_COMMISSION:{deal_id}]"
    if commission_component > Decimal("0.00"):
        existing_commission = (
            Bonus.objects.filter(
                organization=organization,
                employee=employee,
                reason__icontains=commission_marker,
            )
            .order_by("-id")
            .first()
        )
        if existing_commission is None:
            created = Bonus.objects.create(
                organization=organization,
                employee=employee,
                bonus_type=Bonus.BonusType.PERFORMANCE,
                amount=commission_component,
                date=reward_date,
                reason=(
                    f"CRM sales performance commission for deal #{deal_id} via broker "
                    f"{broker.name}. {commission_marker}"
                ),
                status=Bonus.Status.PENDING,
            )
            created_bonus_ids.append(created.id)

    incentive_marker = f"[CRM_DEAL_HR_BONUS:{deal_id}]"
    if incentive_component > Decimal("0.00"):
        existing_incentive = (
            Bonus.objects.filter(
                organization=organization,
                employee=employee,
                reason__icontains=incentive_marker,
            )
            .order_by("-id")
            .first()
        )
        if existing_incentive is None:
            created = Bonus.objects.create(
                organization=organization,
                employee=employee,
                bonus_type=Bonus.BonusType.PERFORMANCE,
                amount=incentive_component,
                date=reward_date,
                reason=(
                    f"CRM sales performance incentive bonus for deal #{deal_id} via broker "
                    f"{broker.name}. {incentive_marker}"
                ),
                status=Bonus.Status.PENDING,
            )
            created_bonus_ids.append(created.id)

    return {
        "employee_id": employee.id,
        "employee_name": employee.user.get_full_name() or employee.user.email,
        "created_bonus_ids": created_bonus_ids,
        "commission_amount": str(commission_component),
        "incentive_amount": str(incentive_component),
    }


def _create_closed_won_commission_earning(*, deal: ContactDealLink, actor=None):
    reservation = deal.reservation
    lead = deal.lead or (reservation.lead if reservation is not None else None)
    if lead is None or not lead.broker_id:
        return None

    broker = lead.broker
    trigger_stage = BrokerCommissionStructure.TriggerStage.CLOSED
    marker = _commission_marker_for_deal(
        deal=deal,
        trigger_stage=trigger_stage,
    )
    existing = (
        BrokerCommissionEarning.objects.filter(
            broker=broker,
            lead=lead,
            trigger_stage=trigger_stage,
            notes__icontains=marker,
        )
        .order_by("-id")
        .first()
    )
    if existing is not None:
        return existing

    structure = _resolve_commission_structure_for_deal(
        broker=broker,
        lead=lead,
        reservation=reservation,
        trigger_stage=trigger_stage,
    )
    rate = _to_decimal(getattr(structure, "base_rate", None))
    if structure is None:
        rate = _to_decimal(getattr(broker, "commission_rate", None))

    earning = BrokerCommissionEarning.objects.create(
        broker=broker,
        lead=lead,
        commission_structure=structure,
        project=reservation.project if reservation is not None and reservation.project_id else None,
        deal_value=_deal_value_for_automation(deal=deal, reservation=reservation),
        commission_rate=rate,
        base_commission=Decimal("0.00"),
        tier_multiplier=Decimal("1.00"),
        bonus_amount=Decimal("0.00"),
        total_commission=Decimal("0.00"),
        trigger_stage=trigger_stage,
        status=BrokerCommissionEarning.Status.PENDING,
        notes=f"Auto-created from closed-won deal #{getattr(deal, 'id', 'n/a')}. {marker}",
    )
    earning.compute()
    earning.save(
        update_fields=[
            "commission_rate",
            "base_commission",
            "tier_multiplier",
            "bonus_amount",
            "total_commission",
            "updated_at",
        ]
    )

    _notify_finance_of_commission(earning=earning, deal=deal)
    _maybe_trigger_broker_target_incentive(earning=earning, actor=actor)
    return earning


def _trigger_closed_won_automations(*, deal: ContactDealLink, request, actor=None):
    reservation = deal.reservation

    sales_agreement_error = None
    allocation_letter_error = None
    if reservation is not None:
        _, sales_agreement_error = _generate_sales_agreement_for_reservation(
            deal=deal,
            reservation=reservation,
            request=request,
            actor=actor,
        )
        _, allocation_letter_error = _generate_allocation_letter_for_reservation(
            deal=deal,
            reservation=reservation,
            request=request,
            actor=actor,
        )

    commission_earning = None
    commission_error = None
    try:
        commission_earning = _create_closed_won_commission_earning(
            deal=deal,
            actor=actor,
        )
    except Exception as exc:
        commission_error = str(exc)

    hr_rewards_sync = None
    hr_rewards_error = None
    if commission_earning is not None:
        try:
            hr_rewards_sync = _sync_hr_sales_performance_rewards(
                deal=deal,
                earning=commission_earning,
            )
        except Exception as exc:
            hr_rewards_error = str(exc)

    invoice = _create_invoice_for_deal(deal=deal, reservation=reservation)
    payment_plan = None
    payment_plan_error = None
    try:
        payment_plan = _create_payment_schedule_for_deal(
            deal=deal,
            reservation=reservation,
            invoice=invoice,
            actor=actor,
        )
    except Exception as exc:
        payment_plan_error = str(exc)

    ledger_entry = None
    ledger_error = None
    try:
        ledger_entry = _post_customer_ledger_for_deal(
            deal=deal,
            reservation=reservation,
            invoice=invoice,
            actor=actor,
        )
    except Exception as exc:
        ledger_error = str(exc)

    _mark_unit_sold_for_deal(deal=deal, reservation=reservation, actor=actor)

    if reservation is not None and invoice is not None:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes="Invoice created from closed-won deal.",
            metadata={
                "automation": "deal_closed_won_invoice_creation",
                "deal_link_id": deal.id,
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "invoice_total": str(invoice.total_amount),
            },
        )

    if reservation is not None and payment_plan is not None:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes="Payment schedule created from closed-won deal.",
            metadata={
                "automation": "deal_closed_won_payment_schedule_creation",
                "deal_link_id": deal.id,
                "payment_plan_id": payment_plan.id,
                "payment_plan_number": payment_plan.plan_number,
                "installment_count": payment_plan.installments.count(),
                "payment_plan_total": str(payment_plan.total_amount),
            },
        )

    if reservation is not None and ledger_entry is not None:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes="Customer ledger posted from closed-won deal.",
            metadata={
                "automation": "deal_closed_won_customer_ledger_posted",
                "deal_link_id": deal.id,
                "journal_entry_id": ledger_entry.id,
                "journal_number": ledger_entry.journal_number,
                "journal_status": ledger_entry.status,
                "ledger_row_count": ledger_entry.ledger_entries.count(),
            },
        )

    if reservation is not None and commission_earning is not None:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes="Broker commission calculated and sent to Finance.",
            metadata={
                "automation": "deal_closed_won_broker_commission",
                "deal_link_id": deal.id,
                "commission_earning_id": commission_earning.id,
                "broker_id": commission_earning.broker_id,
                "broker_name": commission_earning.broker.name,
                "commission_total": str(commission_earning.total_commission),
            },
        )

    if (
        reservation is not None
        and hr_rewards_sync is not None
        and hr_rewards_sync.get("created_bonus_ids")
    ):
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes="CRM sales performance synced to HR commissions/bonuses.",
            metadata={
                "automation": "deal_closed_won_hr_rewards_sync",
                "deal_link_id": deal.id,
                "employee_id": hr_rewards_sync.get("employee_id"),
                "employee_name": hr_rewards_sync.get("employee_name"),
                "bonus_ids": hr_rewards_sync.get("created_bonus_ids", []),
                "commission_amount": hr_rewards_sync.get("commission_amount"),
                "incentive_amount": hr_rewards_sync.get("incentive_amount"),
            },
        )

    if reservation is not None and sales_agreement_error:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes=f"Sales agreement generation automation failed: {sales_agreement_error}",
            metadata={
                "automation": "deal_closed_won_sales_agreement_error",
                "deal_link_id": deal.id,
                "error": sales_agreement_error,
            },
        )

    if reservation is not None and allocation_letter_error:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes=f"Allocation letter generation automation failed: {allocation_letter_error}",
            metadata={
                "automation": "deal_closed_won_allocation_letter_error",
                "deal_link_id": deal.id,
                "error": allocation_letter_error,
            },
        )

    if reservation is not None and payment_plan_error:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes=f"Payment schedule automation failed: {payment_plan_error}",
            metadata={
                "automation": "deal_closed_won_payment_schedule_error",
                "deal_link_id": deal.id,
                "error": payment_plan_error,
            },
        )

    if reservation is not None and ledger_error:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes=f"Customer ledger automation failed: {ledger_error}",
            metadata={
                "automation": "deal_closed_won_customer_ledger_error",
                "deal_link_id": deal.id,
                "error": ledger_error,
            },
        )

    if reservation is not None and commission_error:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes=f"Broker commission automation failed: {commission_error}",
            metadata={
                "automation": "deal_closed_won_broker_commission_error",
                "deal_link_id": deal.id,
                "error": commission_error,
            },
        )

    if reservation is not None and hr_rewards_error:
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.NOTE_ADDED,
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            notes=f"CRM to HR rewards sync automation failed: {hr_rewards_error}",
            metadata={
                "automation": "deal_closed_won_hr_rewards_sync_error",
                "deal_link_id": deal.id,
                "error": hr_rewards_error,
            },
        )


def _deal_stage_change_recipients(deal: ContactDealLink) -> list:
    recipients = []
    seen = set()

    def add_user(user_obj):
        if not user_obj:
            return
        user_id = getattr(user_obj, "id", None)
        if not user_id or not getattr(user_obj, "is_active", False):
            return
        if user_id in seen:
            return
        seen.add(user_id)
        recipients.append(user_obj)

    lead = getattr(deal, "lead", None)
    contact = getattr(deal, "contact", None)
    add_user(getattr(lead, "assigned_to", None))
    add_user(getattr(contact, "created_by", None))
    add_user(getattr(contact, "updated_by", None))

    org = None
    if contact is not None:
        org = getattr(contact, "organization", None)
    if org is None and lead is not None:
        org = getattr(lead, "organization", None)

    for profile in _active_org_user_profiles(org).filter(role="admin").order_by("user_id"):
        add_user(profile.user)

    return recipients


def _notify_deal_stage_change(
    *,
    deal: ContactDealLink,
    previous_stage: str | None,
    previous_status: str | None,
):
    stage_changed = (previous_stage or "") != (deal.stage or "")
    status_changed = (previous_status or "") != (deal.status or "")
    if not stage_changed and not status_changed:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    recipients = _deal_stage_change_recipients(deal)
    if not recipients:
        return

    lead_name = getattr(deal.lead, "full_name", "") if getattr(deal, "lead_id", None) else ""
    contact_name = (
        getattr(deal.contact, "display_name", "")
        if getattr(deal, "contact_id", None)
        else ""
    )
    new_stage = (deal.stage or "Unstaged").strip() or "Unstaged"
    old_stage = (previous_stage or "Unstaged").strip() or "Unstaged"
    new_status = (deal.status or "active").replace("_", " ").title()
    old_status = (previous_status or "active").replace("_", " ").title()
    deal_label = deal.deal_name or lead_name or contact_name or f"Deal #{deal.id}"
    link_url = f"/crm/opportunities?deal_id={deal.id}"

    dispatch_workflow_notification(
        organization=deal.contact.organization if getattr(deal, "contact_id", None) else getattr(deal.lead, "organization", None),
        event_key="crm_deal_stage_changed",
        recipients=recipients,
        context={
            "deal_name": deal_label,
            "lead_name": lead_name,
            "contact_name": contact_name,
            "old_stage": old_stage,
            "new_stage": new_stage,
            "old_status": old_status,
            "new_status": new_status,
            "action_url": link_url,
        },
        link_url=link_url,
        fallback_channels=["in_app", "email"],
        fallback_title=f"Deal Stage Updated — {deal_label}",
        fallback_message=(
            f"Deal '{deal_label}' has moved from {old_stage} ({old_status}) "
            f"to {new_stage} ({new_status}). Please review and update next steps accordingly."
        ),
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.INFO,
    )


def _apply_deal_automations(
    *,
    deal: ContactDealLink,
    request,
    actor=None,
    created: bool = False,
    previous_status: str | None = None,
    previous_stage: str | None = None,
):
    if created:
        _reserve_unit_for_deal(deal=deal, actor=actor)

    if previous_stage is not None or previous_status is not None:
        _notify_deal_stage_change(
            deal=deal,
            previous_stage=previous_stage,
            previous_status=previous_status,
        )

    was_closed_lost = _is_closed_lost_state(
        status_value=previous_status,
        stage_value=previous_stage,
    )
    is_closed_lost = _is_closed_lost_state(
        status_value=deal.status,
        stage_value=deal.stage,
    )
    if is_closed_lost and not was_closed_lost:
        _release_unit_for_lost_deal(deal=deal, actor=actor)

    was_closed_won = _is_closed_won_state(
        status_value=previous_status,
        stage_value=previous_stage,
    )
    is_closed_won = _is_closed_won_state(
        status_value=deal.status,
        stage_value=deal.stage,
    )
    if not is_closed_won or was_closed_won:
        return

    if deal.status != ContactDealLink.Status.WON:
        deal.status = ContactDealLink.Status.WON
        deal.save(update_fields=["status"])

    _trigger_closed_won_automations(deal=deal, request=request, actor=actor)


# --- Action Map ---

_CRM_ACTION_MAP = {
    "list": "view", "retrieve": "view", "create": "create",
    "update": "edit", "partial_update": "edit", "destroy": "delete",
    "performance": "view", "forecast": "view",
    "change_stage": "edit", "convert": "edit", "mark_lost": "edit",
    "compute_scores": "edit", "complete": "edit", "complete_task": "edit",
    "sync_finance": "edit", "request_kyc_review": "edit",
    "mark_in_review": "edit", "reject": "approve",
    "approve": "approve", "confirm": "approve",
    "mark_paid": "edit", "add_recording": "create", "add_recipients": "edit",
    "launch": "edit", "pause": "edit", "escalate": "edit",
    "manual_create": "create",
    "record_payment": "edit", "cancel": "edit", "extend_hold": "edit",
}


# ---------------------------------------------------------------------------
# Lead Source
# ---------------------------------------------------------------------------


class LeadSourceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    serializer_class = LeadSourceSerializer
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        return _scope_queryset_for_request(
            self.request,
            LeadSource.objects.all(),
            org_field="organization",
        )

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------


class BrokerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["name", "company", "license_number", "email"]
    filterset_fields = ["status", "tier"]
    ordering = ["name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            Broker.objects.all(),
            org_field="organization",
        )
        return qs.select_related("tier").prefetch_related("leads", "commission_earnings")

    def get_serializer_class(self):
        if self.action == "list":
            return BrokerListEnhancedSerializer
        if self.action in ("create", "update", "partial_update"):
            return BrokerWriteSerializer
        return BrokerDetailEnhancedSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))

    @action(detail=True, methods=["get"])
    def performance(self, request, pk=None):
        """Performance analytics for a single broker."""
        broker = self.get_object()
        leads = broker.leads.all()

        # Period filter
        months = int(request.query_params.get("months", 12))
        cutoff = timezone.now() - timezone.timedelta(days=months * 30)

        period_leads = leads.filter(created_at__gte=cutoff)
        total_leads = period_leads.count()
        won_leads = period_leads.filter(status="won").count()
        lost_leads = period_leads.filter(status="lost").count()
        active_leads = period_leads.filter(status="active").count()

        # Revenue (sum of deal values from commission earnings)
        earnings = broker.commission_earnings.filter(created_at__gte=cutoff)
        revenue = earnings.aggregate(
            total_deal_value=Sum("deal_value"),
            total_commission_amount=Sum("total_commission"),
            paid_commission=Sum(
                models.Case(
                    models.When(status="paid", then=models.F("total_commission")),
                    default=0,
                    output_field=models.DecimalField(),
                )
            ),
            pending_commission=Sum(
                models.Case(
                    models.When(status="pending", then=models.F("total_commission")),
                    default=0,
                    output_field=models.DecimalField(),
                )
            ),
        )

        # Pipeline velocity
        closed_leads = period_leads.filter(closed_date__isnull=False)
        avg_days = None
        if closed_leads.exists():
            from django.db.models import ExpressionWrapper, F, fields
            avg_result = closed_leads.annotate(
                days=ExpressionWrapper(
                    F("closed_date") - F("inquiry_date"),
                    output_field=fields.DurationField(),
                )
            ).aggregate(avg=Avg("days"))
            if avg_result["avg"]:
                avg_days = avg_result["avg"].days

        # Monthly breakdown
        from django.db.models.functions import TruncMonth

        monthly = list(
            period_leads.filter(status="won")
            .annotate(month=TruncMonth("closed_date"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        conversion_rate = round(won_leads / total_leads * 100, 1) if total_leads > 0 else 0

        return Response({
            "period_months": months,
            "total_leads": total_leads,
            "won_leads": won_leads,
            "lost_leads": lost_leads,
            "active_leads": active_leads,
            "conversion_rate": conversion_rate,
            "avg_days_to_close": avg_days,
            "total_deal_value": revenue["total_deal_value"] or 0,
            "total_commission": revenue["total_commission_amount"] or 0,
            "paid_commission": revenue["paid_commission"] or 0,
            "pending_commission": revenue["pending_commission"] or 0,
            "monthly_deals": [
                {"month": str(m["month"])[:7], "count": m["count"]}
                for m in monthly
            ],
        })

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        """Commission forecast based on active pipeline deals."""
        broker = self.get_object()
        active_leads = broker.leads.filter(status="active")

        # Stage probabilities for forecasting
        stage_probabilities = {
            Lead.PipelineStage.INQUIRY: 0.05,
            Lead.PipelineStage.QUALIFIED: 0.15,
            Lead.PipelineStage.SITE_VISIT: 0.30,
            Lead.PipelineStage.OFFER_MADE: 0.50,
            Lead.PipelineStage.RESERVATION: 0.75,
            Lead.PipelineStage.SPA_ISSUED: 0.90,
            Lead.PipelineStage.CLOSED: 1.00,
        }

        # Get applicable commission rate
        rate = float(broker.commission_rate or 2)
        tier_mult = float(broker.tier.commission_multiplier) if broker.tier else 1.0

        forecasts = []
        total_weighted = 0
        total_best_case = 0

        for lead in active_leads.select_related("source"):
            deal_value = float(lead.budget_min or 0)
            if deal_value == 0:
                continue

            probability = stage_probabilities.get(lead.pipeline_stage, 0.05)
            base_commission = deal_value * rate / 100
            adjusted_commission = base_commission * tier_mult
            weighted = adjusted_commission * probability

            total_weighted += weighted
            total_best_case += adjusted_commission

            forecasts.append({
                "lead_id": lead.id,
                "lead_name": lead.full_name,
                "pipeline_stage": lead.pipeline_stage,
                "deal_value": deal_value,
                "probability": probability,
                "estimated_commission": round(adjusted_commission, 2),
                "weighted_commission": round(weighted, 2),
            })

        return Response({
            "broker_id": broker.id,
            "broker_name": broker.name,
            "commission_rate": rate,
            "tier_multiplier": tier_mult,
            "active_pipeline_count": len(forecasts),
            "total_pipeline_value": sum(f["deal_value"] for f in forecasts),
            "best_case_commission": round(total_best_case, 2),
            "weighted_forecast": round(total_weighted, 2),
            "pipeline_deals": forecasts,
        })


# ---------------------------------------------------------------------------
# Property Matching Engine
# ---------------------------------------------------------------------------


class LeadPropertyMatchViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    http_method_names = ["get", "patch", "head", "options"]
    ordering = ["-match_score", "-updated_at"]

    def get_queryset(self):
        queryset = _scoped_property_match_queryset(self.request)
        params = self.request.query_params

        lead_id = params.get("lead_id")
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)

        candidate_type = params.get("candidate_type")
        if candidate_type:
            queryset = queryset.filter(candidate_type=candidate_type)

        match_status = params.get("status")
        if match_status:
            queryset = queryset.filter(status=match_status)

        is_active = params.get("is_active")
        if is_active is not None and is_active != "":
            normalized = str(is_active).strip().lower()
            queryset = queryset.filter(is_active=normalized in ("1", "true", "yes"))

        min_score = params.get("min_score")
        if min_score:
            try:
                queryset = queryset.filter(match_score__gte=Decimal(str(min_score)))
            except Exception:
                pass

        return queryset

    def get_serializer_class(self):
        if self.action in ("partial_update",):
            return LeadPropertyMatchWriteSerializer
        return LeadPropertyMatchListSerializer


class PropertyMatchOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        matches = _scoped_property_match_queryset(request).filter(is_active=True)
        lead_id = request.query_params.get("lead_id")
        if lead_id:
            matches = matches.filter(lead_id=lead_id)

        total_matches = matches.count()
        suggested = matches.filter(status=LeadPropertyMatch.MatchStatus.SUGGESTED).count()
        shortlisted = matches.filter(status=LeadPropertyMatch.MatchStatus.SHORTLISTED).count()
        unit_matches = matches.filter(candidate_type=LeadPropertyMatch.CandidateType.UNIT).count()
        project_matches = matches.filter(candidate_type=LeadPropertyMatch.CandidateType.PROJECT).count()
        average_score = matches.aggregate(avg=Avg("match_score"))["avg"] or Decimal("0.00")

        by_status_rows = (
            matches.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        by_type_rows = (
            matches.values("candidate_type")
            .annotate(count=Count("id"))
            .order_by("candidate_type")
        )

        return Response(
            {
                "total_matches": total_matches,
                "suggested_matches": suggested,
                "shortlisted_matches": shortlisted,
                "unit_matches": unit_matches,
                "project_matches": project_matches,
                "average_score": str(
                    Decimal(str(average_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                ),
                "by_status": list(by_status_rows),
                "by_candidate_type": list(by_type_rows),
            }
        )


class PropertyMatchRefreshView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "edit"

    def post(self, request):
        lead_id = request.data.get("lead_id")
        property_id = request.data.get("property_id")
        if not lead_id:
            return Response(
                {"lead_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lead = get_object_or_404(_scoped_lead_queryset(request), pk=lead_id)
        if property_id:
            try:
                property_id = int(property_id)
            except (TypeError, ValueError):
                return Response(
                    {"property_id": ["Must be a valid integer."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        result = recompute_matches_for_lead(
            lead=lead,
            source=LeadPropertyMatch.MatchSource.MANUAL_REFRESH,
            property_id=property_id,
        )
        return Response(
            {
                "lead_id": lead.id,
                "lead_name": lead.full_name,
                **result,
            }
        )


# ---------------------------------------------------------------------------
# Lead
# ---------------------------------------------------------------------------


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["first_name", "last_name", "email", "phone", "company"]
    filterset_fields = ["pipeline_stage", "status", "priority", "lead_type", "payment_capability", "is_archived"]
    ordering_fields = ["created_at", "inquiry_date", "score", "first_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return _scoped_lead_queryset(self.request)

    def get_serializer_class(self):
        if self.action == "list":
            return LeadListSerializer
        if self.action in ("create", "update", "partial_update"):
            return LeadWriteSerializer
        return LeadDetailSerializer

    def perform_create(self, serializer):
        organization = _user_org(self.request)
        assigned_to = serializer.validated_data.get("assigned_to")
        manual_assignment = self.request.data.get("assigned_to")
        manual_assignment_provided = str(manual_assignment).strip().lower() not in ("", "none", "null")

        if assigned_to is None and not manual_assignment_provided:
            assigned_to = _select_auto_assignee_for_lead(organization)

        lead = serializer.save(
            organization=organization,
            assigned_to=assigned_to,
        )
        _generate_follow_up_tasks_for_stage_entry(lead, lead.pipeline_stage)
        if lead.pipeline_stage == Lead.PipelineStage.QUALIFIED:
            _trigger_property_recommendations_for_qualified_lead(
                lead,
                actor=self.request.user,
            )

    def update(self, request, *args, **kwargs):
        lead = self.get_object()
        if lead.is_archived:
            return Response({"detail": "Archived leads cannot be modified."}, status=status.HTTP_403_FORBIDDEN)
        previous_stage = lead.pipeline_stage
        response = super().update(request, *args, **kwargs)
        lead.refresh_from_db(fields=["pipeline_stage"])
        if lead.pipeline_stage != previous_stage:
            _generate_follow_up_tasks_for_stage_entry(lead, lead.pipeline_stage)
            if lead.pipeline_stage == Lead.PipelineStage.QUALIFIED:
                _trigger_property_recommendations_for_qualified_lead(lead, actor=request.user)
        return response

    def partial_update(self, request, *args, **kwargs):
        lead = self.get_object()
        if lead.is_archived:
            return Response({"detail": "Archived leads cannot be modified."}, status=status.HTTP_403_FORBIDDEN)
        previous_stage = lead.pipeline_stage
        response = super().partial_update(request, *args, **kwargs)
        lead.refresh_from_db(fields=["pipeline_stage"])
        if lead.pipeline_stage != previous_stage:
            _generate_follow_up_tasks_for_stage_entry(lead, lead.pipeline_stage)
            if lead.pipeline_stage == Lead.PipelineStage.QUALIFIED:
                _trigger_property_recommendations_for_qualified_lead(lead, actor=request.user)
        return response

    def destroy(self, request, *args, **kwargs):
        lead = self.get_object()
        if lead.is_archived:
            return Response({"detail": "Archived leads cannot be deleted."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    # --- Custom actions ---

    @action(detail=True, methods=["post"])
    def change_stage(self, request, pk=None):
        """Move lead to a different pipeline stage and record transition."""
        lead = self.get_object()
        serializer = LeadStageChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_stage = serializer.validated_data["stage"]
        notes = serializer.validated_data.get("notes", "")

        if new_stage == lead.pipeline_stage:
            return Response(
                {"error": "Lead is already in this stage."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        _ensure_lead_contract_stage_kyc_gate(lead=lead, target_stage=new_stage)

        old_stage = lead.pipeline_stage

        # Record transition
        LeadStageTransition.objects.create(
            lead=lead,
            from_stage=old_stage,
            to_stage=new_stage,
            transitioned_by=request.user,
            notes=notes,
        )

        # Update lead stage and corresponding date field
        lead.pipeline_stage = new_stage
        stage_date_map = {
            Lead.PipelineStage.QUALIFIED: "qualified_date",
            Lead.PipelineStage.SITE_VISIT: "site_visit_date",
            Lead.PipelineStage.OFFER_MADE: "offer_date",
            Lead.PipelineStage.RESERVATION: "reservation_date",
            Lead.PipelineStage.SPA_ISSUED: "spa_issued_date",
            Lead.PipelineStage.CLOSED: "closed_date",
        }
        date_field = stage_date_map.get(new_stage)
        if date_field and getattr(lead, date_field) is None:
            setattr(lead, date_field, timezone.now().date())

        if new_stage == Lead.PipelineStage.CLOSED:
            lead.status = Lead.Status.WON

        lead.save()
        _generate_follow_up_tasks_for_stage_entry(lead, new_stage)
        if new_stage == Lead.PipelineStage.QUALIFIED:
            _trigger_property_recommendations_for_qualified_lead(lead, actor=request.user)
        return Response(LeadDetailSerializer(lead).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert a closed lead into a Finance Customer."""
        from apps.finance.models import Customer

        lead = self.get_object()
        serializer = LeadConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if lead.converted_customer is not None:
            return Response(
                {"error": "Lead has already been converted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = Customer.objects.create(
            name=lead.full_name,
            contact_person=lead.full_name,
            email=lead.email,
            phone=lead.phone,
            address="",
            notes=f"Converted from CRM Lead. {serializer.validated_data.get('notes', '')}".strip(),
        )
        lead.converted_customer = customer
        lead.status = Lead.Status.WON
        lead.is_archived = True
        lead.archived_at = timezone.now()
        lead.archived_reason = "SPA Signed"
        if lead.pipeline_stage != Lead.PipelineStage.CLOSED:
            old_stage = lead.pipeline_stage
            lead.pipeline_stage = Lead.PipelineStage.CLOSED
            lead.closed_date = timezone.now().date()
            LeadStageTransition.objects.create(
                lead=lead,
                from_stage=old_stage,
                to_stage=Lead.PipelineStage.CLOSED,
                transitioned_by=request.user,
                notes="Auto-transitioned on conversion to customer.",
            )
        lead.save()

        return Response({
            "lead_id": lead.id,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "message": "Lead successfully converted to customer.",
        })

    @action(detail=True, methods=["post"])
    def mark_lost(self, request, pk=None):
        """Mark a lead as lost with a reason."""
        lead = self.get_object()
        reason = request.data.get("reason", "")
        lead.status = Lead.Status.LOST
        lead.lost_reason = reason
        lead.closed_date = lead.closed_date or timezone.now().date()
        lead.save(update_fields=["status", "lost_reason", "closed_date", "updated_at"])
        return Response(LeadDetailSerializer(lead).data)


# ---------------------------------------------------------------------------
# Nested: Lead Project Interest
# ---------------------------------------------------------------------------


class LeadProjectInterestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    serializer_class = LeadProjectInterestSerializer

    def _get_lead(self):
        return get_object_or_404(_scoped_lead_queryset(self.request), pk=self.kwargs["lead_pk"])

    def get_queryset(self):
        return LeadProjectInterest.objects.filter(
            lead=self._get_lead(),
        ).select_related("project")

    def perform_create(self, serializer):
        serializer.save(lead=self._get_lead())


# ---------------------------------------------------------------------------
# Nested: Lead Unit Preference
# ---------------------------------------------------------------------------


class LeadUnitPreferenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    serializer_class = LeadUnitPreferenceSerializer

    def _get_lead(self):
        return get_object_or_404(_scoped_lead_queryset(self.request), pk=self.kwargs["lead_pk"])

    def get_queryset(self):
        return LeadUnitPreference.objects.filter(lead=self._get_lead())

    def perform_create(self, serializer):
        serializer.save(lead=self._get_lead())


# ---------------------------------------------------------------------------
# Nested: Lead Activity
# ---------------------------------------------------------------------------


class LeadActivityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    filterset_fields = ["activity_type", "is_completed"]
    ordering = ["-created_at"]

    def _get_lead(self):
        return get_object_or_404(_scoped_lead_queryset(self.request), pk=self.kwargs["lead_pk"])

    def get_queryset(self):
        return LeadActivity.objects.filter(
            lead=self._get_lead(),
        ).select_related("performed_by")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LeadActivityWriteSerializer
        return LeadActivitySerializer

    def perform_create(self, serializer):
        activity = serializer.save(
            lead=self._get_lead(),
            performed_by=self.request.user,
        )
        _ensure_scheduled_activity_task(activity, actor=self.request.user)
        _notify_site_visit_scheduled(activity, actor=self.request.user)


# ---------------------------------------------------------------------------
# Global CRM Activities (cross-lead)
# ---------------------------------------------------------------------------


class CRMActivityViewSet(viewsets.ModelViewSet):
    """Global activity feed and logger for calls/emails/meetings/site visits."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["subject", "description", "lead__first_name", "lead__last_name", "lead__email"]
    filterset_fields = ["activity_type", "is_completed", "lead"]
    ordering_fields = ["scheduled_at", "completed_at", "created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            LeadActivity.objects.all(),
            org_field="lead__organization_id",
        )
        return qs.select_related("lead", "performed_by")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LeadActivityGlobalWriteSerializer
        return LeadActivitySerializer

    def perform_create(self, serializer):
        activity = serializer.save(performed_by=self.request.user)
        if activity.is_completed and not activity.completed_at:
            activity.completed_at = timezone.now()
            activity.save(update_fields=["completed_at", "updated_at"])
        _ensure_scheduled_activity_task(activity, actor=self.request.user)
        _notify_site_visit_scheduled(activity, actor=self.request.user)

    def perform_update(self, serializer):
        previous_type = serializer.instance.activity_type
        previous_scheduled_at = serializer.instance.scheduled_at
        activity = serializer.save()
        if activity.is_completed and not activity.completed_at:
            activity.completed_at = timezone.now()
            activity.save(update_fields=["completed_at", "updated_at"])
        if not activity.is_completed:
            _ensure_scheduled_activity_task(activity, actor=self.request.user)
            should_notify_site_visit = (
                activity.activity_type == LeadActivity.ActivityType.SITE_VISIT
                and activity.scheduled_at is not None
                and (
                    previous_type != LeadActivity.ActivityType.SITE_VISIT
                    or previous_scheduled_at != activity.scheduled_at
                )
            )
            if should_notify_site_visit:
                _notify_site_visit_scheduled(activity, actor=self.request.user)


class ActivityTaskManagementOverviewView(APIView):
    """Overview payload for CRM Activities & Task Management workspace."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        now = timezone.now()
        try:
            days = int(request.query_params.get("days", 30))
        except (TypeError, ValueError):
            days = 30
        days = min(max(days, 7), 180)
        cutoff = now - timezone.timedelta(days=days)

        activities = _scope_queryset_for_request(
            request,
            LeadActivity.objects.filter(
                Q(created_at__gte=cutoff)
                | Q(updated_at__gte=cutoff)
                | Q(scheduled_at__gte=cutoff)
            ),
            org_field="lead__organization_id",
        ).select_related("lead", "performed_by")

        tasks = _scope_queryset_for_request(
            request,
            FollowUpTask.objects.filter(
                Q(created_at__gte=cutoff)
                | Q(updated_at__gte=cutoff)
                | Q(due_at__gte=cutoff)
                | Q(completed_at__gte=cutoff)
                | Q(escalated_at__gte=cutoff)
            ),
            org_field="rule__organization_id",
        ).select_related("lead", "assigned_to", "rule")

        activity_counts = list(
            activities.values("activity_type").annotate(count=Count("id")).order_by("-count", "activity_type")
        )
        task_status_counts = list(
            tasks.values("status").annotate(count=Count("id")).order_by("-count", "status")
        )

        upcoming_activities_qs = activities.filter(
            is_completed=False,
            scheduled_at__gte=now,
        ).order_by("scheduled_at")[:8]
        upcoming_activities = [
            {
                "id": row.id,
                "lead": row.lead_id,
                "lead_name": row.lead.full_name,
                "subject": row.subject,
                "activity_type": row.activity_type,
                "activity_type_display": row.get_activity_type_display(),
                "scheduled_at": row.scheduled_at,
                "is_completed": row.is_completed,
                "performed_by_name": row.performed_by.get_full_name() if row.performed_by_id else None,
            }
            for row in upcoming_activities_qs
        ]

        timeline_entries = []
        for row in activities.order_by("-updated_at")[:40]:
            timestamp = row.completed_at or row.scheduled_at or row.updated_at or row.created_at
            timeline_entries.append(
                {
                    "kind": "activity",
                    "id": row.id,
                    "timestamp": timestamp,
                    "lead_id": row.lead_id,
                    "lead_name": row.lead.full_name,
                    "title": row.subject,
                    "subtitle": row.get_activity_type_display(),
                    "status": "completed" if row.is_completed else "pending",
                    "status_display": "Completed" if row.is_completed else "Pending",
                }
            )
        for row in tasks.order_by("-updated_at")[:40]:
            timestamp = row.escalated_at or row.completed_at or row.due_at or row.updated_at or row.created_at
            timeline_entries.append(
                {
                    "kind": "task",
                    "id": row.id,
                    "timestamp": timestamp,
                    "lead_id": row.lead_id,
                    "lead_name": row.lead.full_name,
                    "title": row.rule.name,
                    "subtitle": f"Due {row.due_at.strftime('%b %d, %Y %I:%M %p')}",
                    "status": row.status,
                    "status_display": row.get_status_display(),
                }
            )
        timeline_entries.sort(
            key=lambda item: item["timestamp"] or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )

        profile = getattr(request.user, "profile", None)
        calendar_sync = {
            "timezone_override": getattr(profile, "calendar_timezone_override", "") if profile else "",
            "default_meeting_duration_minutes": getattr(profile, "calendar_default_meeting_duration_minutes", 30),
            "meeting_buffer_minutes": getattr(profile, "calendar_meeting_buffer_minutes", 10),
            "google_sync_enabled": bool(getattr(profile, "calendar_sync_google_enabled", False)),
            "outlook_sync_enabled": bool(getattr(profile, "calendar_sync_outlook_enabled", False)),
            "ical_sync_enabled": bool(getattr(profile, "calendar_sync_ical_enabled", False)),
        }

        payload = {
            "window_days": days,
            "total_activities": activities.count(),
            "completed_activities": activities.filter(is_completed=True).count(),
            "scheduled_upcoming_count": activities.filter(
                is_completed=False, scheduled_at__gte=now
            ).count(),
            "missed_activities_count": activities.filter(
                is_completed=False, scheduled_at__lt=now
            ).count(),
            "activities_by_type": [
                {
                    "activity_type": row["activity_type"],
                    "label": dict(LeadActivity.ActivityType.choices).get(row["activity_type"], row["activity_type"]),
                    "count": row["count"],
                }
                for row in activity_counts
            ],
            "total_tasks": tasks.count(),
            "open_task_count": tasks.filter(
                status__in=[FollowUpTask.Status.PENDING, FollowUpTask.Status.IN_PROGRESS]
            ).count(),
            "overdue_task_count": tasks.filter(
                status__in=[FollowUpTask.Status.PENDING, FollowUpTask.Status.IN_PROGRESS],
                due_at__lt=now,
            ).count(),
            "escalated_task_count": tasks.filter(status=FollowUpTask.Status.ESCALATED).count(),
            "task_status_breakdown": [
                {
                    "status": row["status"],
                    "label": dict(FollowUpTask.Status.choices).get(row["status"], row["status"]),
                    "count": row["count"],
                }
                for row in task_status_counts
            ],
            "calendar_integration": calendar_sync,
            "upcoming_activities": upcoming_activities,
            "timeline": timeline_entries[:60],
        }
        return Response(payload)


# ---------------------------------------------------------------------------
# Pipeline Overview / Velocity Metrics
# ---------------------------------------------------------------------------


class PipelineOverviewView(APIView):
    """Dashboard-level pipeline metrics and stage counts."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "pipeline")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        leads = _scope_queryset_for_request(
            request,
            Lead.objects.all(),
            org_field="organization_id",
        )

        # Stage counts
        stage_counts = (
            leads.filter(status=Lead.Status.ACTIVE)
            .values("pipeline_stage")
            .annotate(count=Count("id"))
            .order_by("pipeline_stage")
        )
        stage_map = {sc["pipeline_stage"]: sc["count"] for sc in stage_counts}

        # Overall stats
        total = leads.count()
        active = leads.filter(status=Lead.Status.ACTIVE).count()
        won = leads.filter(status=Lead.Status.WON).count()
        lost = leads.filter(status=Lead.Status.LOST).count()

        # Velocity: average days in pipeline for closed leads
        closed_leads = leads.filter(closed_date__isnull=False)
        avg_days = None
        if closed_leads.exists():
            from django.db.models import ExpressionWrapper, F, fields
            avg_days_result = closed_leads.annotate(
                days=ExpressionWrapper(
                    F("closed_date") - F("inquiry_date"),
                    output_field=fields.DurationField(),
                )
            ).aggregate(avg=Avg("days"))
            if avg_days_result["avg"] is not None:
                avg_days = avg_days_result["avg"].days

        # Conversion rate
        conversion_rate = round(won / total * 100, 1) if total > 0 else 0

        # By source
        source_breakdown = list(
            leads.filter(source__isnull=False)
            .values("source__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        payload = {
            "total_leads": total,
            "active_leads": active,
            "won_leads": won,
            "lost_leads": lost,
            "conversion_rate": conversion_rate,
            "avg_days_to_close": avg_days,
            "pipeline_stages": [
                {
                    "stage": stage,
                    "label": label,
                    "count": stage_map.get(stage, 0),
                }
                for stage, label in Lead.PipelineStage.choices
            ],
            "by_source": [
                {"source": s["source__name"], "count": s["count"]}
                for s in source_breakdown
            ],
        }
        cache.set(cache_key, payload, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(payload)


# ---------------------------------------------------------------------------
# Contact & Account Management
# ---------------------------------------------------------------------------


class ContactAccountViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = [
        "first_name",
        "last_name",
        "legal_name",
        "trade_name",
        "primary_contact_name",
        "email",
        "phone",
        "registration_number",
    ]
    filterset_fields = ["entity_type", "kyc_status", "risk_profile", "is_active"]
    ordering_fields = ["created_at", "updated_at", "finance_synced_at", "first_name", "legal_name"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = _scoped_contact_queryset(self.request).annotate(
            interaction_count=Count("interactions", distinct=True),
            active_deal_count=Count(
                "deal_links",
                filter=Q(deal_links__status=ContactDealLink.Status.ACTIVE),
                distinct=True,
            ),
            document_count=Count("documents", distinct=True),
        )
        if self.action == "retrieve":
            return qs.prefetch_related(
                "interactions",
                "deal_links__lead",
                "deal_links__reservation",
                "property_links__project",
                "property_links__property",
                "property_links__unit",
                "documents__compliance_reviews",
                "compliance_reviews__document",
                "compliance_reviews__requested_by",
                "compliance_reviews__reviewed_by",
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ContactAccountListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ContactAccountWriteSerializer
        return ContactAccountDetailSerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        contact = serializer.save(
            organization=_user_org(self.request),
            created_by=user,
            updated_by=user,
        )
        _sync_contact_to_finance_customer(contact)

    def perform_update(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        contact = serializer.save(updated_by=user)
        _sync_contact_to_finance_customer(contact)

    @action(detail=True, methods=["post"])
    def sync_finance(self, request, pk=None):
        contact = self.get_object()
        customer = _sync_contact_to_finance_customer(contact)
        return Response(
            {
                "contact_id": contact.id,
                "finance_customer_id": customer.id,
                "finance_customer_name": customer.name,
                "finance_synced_at": contact.finance_synced_at,
            }
        )

    @action(detail=True, methods=["post"])
    def request_kyc_review(self, request, pk=None):
        contact = self.get_object()
        document_id = request.data.get("document")
        if document_id:
            document = get_object_or_404(contact.documents.all(), pk=document_id)
        else:
            document = contact.documents.filter(is_kyc_document=True).order_by("-uploaded_at").first()
            if document is None:
                document = contact.documents.order_by("-uploaded_at").first()

        if document is None:
            return Response(
                {"detail": "No document found for this contact."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        review = _trigger_compliance_review_for_kyc_document(document, actor=request.user)
        return Response(
            ContactComplianceReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )


class ContactAccountOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "contacts")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        contacts = _scoped_contact_queryset(request)
        now = timezone.now()
        kyc_pending_statuses = [
            ContactAccount.KYCStatus.PENDING_REVIEW,
            ContactAccount.KYCStatus.UNDER_REVIEW,
        ]
        response = {
            "total_contacts": contacts.count(),
            "individual_contacts": contacts.filter(
                entity_type=ContactAccount.EntityType.INDIVIDUAL
            ).count(),
            "organization_accounts": contacts.filter(
                entity_type=ContactAccount.EntityType.ORGANIZATION
            ).count(),
            "kyc_verified": contacts.filter(kyc_status=ContactAccount.KYCStatus.VERIFIED).count(),
            "kyc_pending": contacts.filter(kyc_status__in=kyc_pending_statuses).count(),
            "finance_synced": contacts.exclude(finance_customer_id=None).count(),
            "high_value_contacts": contacts.filter(
                Q(budget_max__gte=50_000_000) | Q(net_worth__gte=100_000_000)
            ).count(),
            "follow_up_due": ContactInteraction.objects.filter(
                contact__in=contacts,
                follow_up_required=True,
                follow_up_due_at__isnull=False,
                follow_up_due_at__lte=now,
            ).count(),
            "entity_breakdown": [
                {
                    "entity_type": key,
                    "label": label,
                    "count": contacts.filter(entity_type=key).count(),
                }
                for key, label in ContactAccount.EntityType.choices
            ],
            "kyc_breakdown": [
                {
                    "status": key,
                    "label": label,
                    "count": contacts.filter(kyc_status=key).count(),
                }
                for key, label in ContactAccount.KYCStatus.choices
            ],
        }
        cache.set(cache_key, response, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(response)


class ContactInteractionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    serializer_class = ContactInteractionSerializer
    filterset_fields = ["interaction_type", "follow_up_required"]
    ordering_fields = ["happened_at", "created_at"]
    ordering = ["-happened_at", "-created_at"]

    def _get_contact(self):
        return get_object_or_404(_scoped_contact_queryset(self.request), pk=self.kwargs["contact_pk"])

    def get_queryset(self):
        return ContactInteraction.objects.filter(contact=self._get_contact()).select_related("performed_by")

    def perform_create(self, serializer):
        serializer.save(
            contact=self._get_contact(),
            performed_by=self.request.user if self.request.user.is_authenticated else None,
        )


class ContactDealLinkViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    serializer_class = ContactDealLinkSerializer
    filterset_fields = ["status", "stage"]
    ordering_fields = ["linked_at"]
    ordering = ["-linked_at"]

    def _get_contact(self):
        return get_object_or_404(_scoped_contact_queryset(self.request), pk=self.kwargs["contact_pk"])

    def get_queryset(self):
        return ContactDealLink.objects.filter(contact=self._get_contact()).select_related("lead", "reservation")

    def perform_create(self, serializer):
        contact = self._get_contact()
        lead = serializer.validated_data.get("lead")
        reservation = serializer.validated_data.get("reservation")
        _ensure_contact_related_org(contact, lead=lead, reservation=reservation)
        _ensure_deal_contract_stage_kyc_gate(
            contact=contact,
            lead=lead,
            stage_value=serializer.validated_data.get("stage"),
            status_value=serializer.validated_data.get("status"),
        )
        deal = serializer.save(contact=contact)
        _apply_deal_automations(
            deal=deal,
            request=self.request,
            actor=self.request.user,
            created=True,
        )

    def perform_update(self, serializer):
        contact = self._get_contact()
        previous_status = serializer.instance.status
        previous_stage = serializer.instance.stage
        lead = serializer.validated_data.get("lead", serializer.instance.lead)
        reservation = serializer.validated_data.get("reservation", serializer.instance.reservation)
        _ensure_contact_related_org(contact, lead=lead, reservation=reservation)
        _ensure_deal_contract_stage_kyc_gate(
            contact=contact,
            lead=lead,
            stage_value=serializer.validated_data.get("stage", serializer.instance.stage),
            status_value=serializer.validated_data.get("status", serializer.instance.status),
        )
        deal = serializer.save()
        _apply_deal_automations(
            deal=deal,
            request=self.request,
            actor=self.request.user,
            created=False,
            previous_status=previous_status,
            previous_stage=previous_stage,
        )


class OpportunityDealViewSet(viewsets.ModelViewSet):
    """
    Global Opportunity / Deal management endpoint.

    Backed by ContactDealLink so CRM can manage a cross-contact revenue pipeline.
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = [
        "deal_name",
        "stage",
        "contact__first_name",
        "contact__last_name",
        "contact__legal_name",
        "lead__first_name",
        "lead__last_name",
        "reservation__reservation_number",
    ]
    filterset_fields = ["status", "stage", "contact", "lead", "reservation"]
    ordering_fields = ["linked_at", "deal_value", "close_probability", "stage"]
    ordering = ["-linked_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            ContactDealLink.objects.all(),
            org_field="contact__organization_id",
        )
        return qs.select_related(
            "contact",
            "lead",
            "lead__broker",
            "reservation",
            "reservation__lead",
            "reservation__unit",
            "reservation__unit__property",
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OpportunityDealWriteSerializer
        return OpportunityDealListSerializer

    def perform_create(self, serializer):
        contact = serializer.validated_data["contact"]
        lead = serializer.validated_data.get("lead")
        reservation = serializer.validated_data.get("reservation")
        _ensure_contact_related_org(contact, lead=lead, reservation=reservation)
        _ensure_deal_contract_stage_kyc_gate(
            contact=contact,
            lead=lead,
            stage_value=serializer.validated_data.get("stage"),
            status_value=serializer.validated_data.get("status"),
        )
        deal = serializer.save()
        _apply_deal_automations(
            deal=deal,
            request=self.request,
            actor=self.request.user,
            created=True,
        )

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        previous_stage = serializer.instance.stage
        contact = serializer.validated_data.get("contact", serializer.instance.contact)
        lead = serializer.validated_data.get("lead", serializer.instance.lead)
        reservation = serializer.validated_data.get("reservation", serializer.instance.reservation)
        _ensure_contact_related_org(contact, lead=lead, reservation=reservation)
        _ensure_deal_contract_stage_kyc_gate(
            contact=contact,
            lead=lead,
            stage_value=serializer.validated_data.get("stage", serializer.instance.stage),
            status_value=serializer.validated_data.get("status", serializer.instance.status),
        )
        deal = serializer.save()
        _apply_deal_automations(
            deal=deal,
            request=self.request,
            actor=self.request.user,
            created=False,
            previous_status=previous_status,
            previous_stage=previous_stage,
        )


class OpportunityOverviewView(APIView):
    """Pipeline KPI and stage analytics for Opportunity / Deal management."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "opportunities")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        deals = list(
            _scope_queryset_for_request(
                request,
                ContactDealLink.objects.all(),
                org_field="contact__organization_id",
            ).select_related(
                "lead",
                "lead__broker",
                "reservation",
                "reservation__unit",
                "reservation__unit__property",
            )
        )

        pipeline_value = Decimal("0.00")
        weighted_forecast = Decimal("0.00")
        closed_won_value = Decimal("0.00")
        expected_commission = Decimal("0.00")
        stage_buckets: dict[str, dict[str, Decimal | int | str]] = {}

        active_statuses = {
            ContactDealLink.Status.ACTIVE,
            ContactDealLink.Status.ON_HOLD,
        }

        for deal in deals:
            stage_label = (deal.stage or "").strip() or "Unstaged"
            deal_value = _to_decimal(deal.deal_value)
            probability = max(0, min(int(deal.close_probability or 0), 100))
            weighted = (deal_value * Decimal(probability) / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            stage_bucket = stage_buckets.setdefault(
                stage_label,
                {
                    "stage": stage_label,
                    "count": 0,
                    "deal_value": Decimal("0.00"),
                    "weighted_value": Decimal("0.00"),
                },
            )
            stage_bucket["count"] = int(stage_bucket["count"]) + 1
            stage_bucket["deal_value"] = _to_decimal(stage_bucket["deal_value"]) + deal_value
            stage_bucket["weighted_value"] = _to_decimal(stage_bucket["weighted_value"]) + weighted

            if deal.status in active_statuses:
                pipeline_value += deal_value
                weighted_forecast += weighted

            if _is_closed_won_state(status_value=deal.status, stage_value=deal.stage):
                closed_won_value += deal_value

            if deal.lead_id and getattr(deal.lead, "broker_id", None):
                rate = _to_decimal(getattr(deal.lead.broker, "commission_rate", 0))
                if rate > 0:
                    expected_commission += (
                        deal_value * rate / Decimal("100")
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        commission_qs = _scope_queryset_for_request(
            request,
            BrokerCommissionEarning.objects.all(),
            org_field="lead__organization_id",
        )
        commission_agg = commission_qs.aggregate(
            paid=Sum(
                "total_commission",
                filter=Q(status=BrokerCommissionEarning.Status.PAID),
            ),
            pending=Sum(
                "total_commission",
                filter=Q(
                    status__in=[
                        BrokerCommissionEarning.Status.PENDING,
                        BrokerCommissionEarning.Status.APPROVED,
                        BrokerCommissionEarning.Status.PROCESSING,
                    ]
                ),
            ),
        )

        sorted_stage_buckets = sorted(
            stage_buckets.values(),
            key=lambda item: (-_to_decimal(item["deal_value"]), str(item["stage"]).lower()),
        )
        for bucket in sorted_stage_buckets:
            bucket["deal_value"] = str(_to_decimal(bucket["deal_value"]).quantize(Decimal("0.01")))
            bucket["weighted_value"] = str(_to_decimal(bucket["weighted_value"]).quantize(Decimal("0.01")))

        payload = {
            "total_deals": len(deals),
            "active_deals": sum(1 for deal in deals if deal.status in active_statuses),
            "pipeline_value": str(pipeline_value.quantize(Decimal("0.01"))),
            "weighted_forecast": str(weighted_forecast.quantize(Decimal("0.01"))),
            "closed_won_value": str(closed_won_value.quantize(Decimal("0.01"))),
            "expected_commission": str(expected_commission.quantize(Decimal("0.01"))),
            "commission_paid": str(_to_decimal(commission_agg["paid"]).quantize(Decimal("0.01"))),
            "commission_pending": str(_to_decimal(commission_agg["pending"]).quantize(Decimal("0.01"))),
            "stage_breakdown": sorted_stage_buckets,
        }
        cache.set(cache_key, payload, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(payload)


class CRMAnalyticsReportingOverviewView(APIView):
    """Strategic CRM analytics metrics for conversion, velocity, and forecasting."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "analytics-reporting")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        try:
            window_days = int(request.query_params.get("window_days", 90))
        except (TypeError, ValueError):
            window_days = 90
        try:
            lookback_days = int(request.query_params.get("lookback_days", 7))
        except (TypeError, ValueError):
            lookback_days = 7

        window_days = min(max(window_days, 30), 365)
        lookback_days = min(max(lookback_days, 3), 30)

        if _is_superuser(request):
            organization_id = _requested_org_id(request) or getattr(_user_org(request), "id", None)
        else:
            organization_id = getattr(_user_org(request), "id", None)
        payload = compute_crm_analytics_snapshot(
            organization_id=organization_id,
            window_days=window_days,
            pipeline_drop_lookback_days=lookback_days,
        )
        cache.set(cache_key, payload, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(payload)


class CRMAnalyticsWeeklyReportRunView(APIView):
    """Manual trigger for weekly CRM analytics report dispatch."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "edit"

    def post(self, request):
        try:
            window_days = int(request.data.get("window_days", 90))
        except (TypeError, ValueError):
            window_days = 90
        window_days = min(max(window_days, 30), 365)

        if _is_superuser(request):
            organization_id = _requested_org_id(request) or getattr(_user_org(request), "id", None)
        else:
            organization_id = getattr(_user_org(request), "id", None)

        if not organization_id:
            return Response(
                {"organization_id": ["A valid organization context is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = send_weekly_crm_analytics_report_for_org(
            organization_id=organization_id,
            window_days=window_days,
        )
        status_code = status.HTTP_200_OK if not result.get("skipped") else status.HTTP_202_ACCEPTED
        return Response(result, status=status_code)


class CRMAnalyticsPipelineDropCheckView(APIView):
    """Manual trigger for CRM pipeline-drop alert evaluation."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "edit"

    def post(self, request):
        try:
            lookback_days = int(request.data.get("lookback_days", 7))
        except (TypeError, ValueError):
            lookback_days = 7
        lookback_days = min(max(lookback_days, 3), 30)
        force = bool(request.data.get("force", False))

        if _is_superuser(request):
            organization_id = _requested_org_id(request) or getattr(_user_org(request), "id", None)
        else:
            organization_id = getattr(_user_org(request), "id", None)

        if not organization_id:
            return Response(
                {"organization_id": ["A valid organization context is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = check_pipeline_drop_for_org(
            organization_id=organization_id,
            lookback_days=lookback_days,
            force=force,
        )
        return Response(result, status=status.HTTP_200_OK)


class CRMAnalyticsProjectDemandSyncView(APIView):
    """Manual trigger for CRM -> Projects demand insight sync."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "edit"

    def post(self, request):
        try:
            window_days = int(request.data.get("window_days", 90))
        except (TypeError, ValueError):
            window_days = 90
        try:
            threshold_percent = float(request.data.get("threshold_percent", 25.0))
        except (TypeError, ValueError):
            threshold_percent = 25.0
        try:
            min_leads = int(request.data.get("min_leads", 5))
        except (TypeError, ValueError):
            min_leads = 5
        try:
            top_areas = int(request.data.get("top_areas", 12))
        except (TypeError, ValueError):
            top_areas = 12
        force = bool(request.data.get("force", False))

        if _is_superuser(request):
            organization_id = _requested_org_id(request) or getattr(_user_org(request), "id", None)
        else:
            organization_id = getattr(_user_org(request), "id", None)

        if not organization_id:
            return Response(
                {"organization_id": ["A valid organization context is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = sync_crm_project_demand_insights_for_org(
            organization_id=organization_id,
            window_days=window_days,
            threshold_percent=threshold_percent,
            min_leads=min_leads,
            top_areas=top_areas,
            force=force,
        )
        status_code = status.HTTP_200_OK if not result.get("skipped") else status.HTTP_202_ACCEPTED
        return Response(result, status=status_code)


class CRMAnalyticsProcurementDemandSyncView(APIView):
    """Manual trigger for CRM -> Procurement bulk-buyer demand sync."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "edit"

    def post(self, request):
        try:
            window_days = int(request.data.get("window_days", 90))
        except (TypeError, ValueError):
            window_days = 90
        try:
            threshold_percent = float(request.data.get("threshold_percent", 20.0))
        except (TypeError, ValueError):
            threshold_percent = 20.0
        try:
            min_leads = int(request.data.get("min_leads", 5))
        except (TypeError, ValueError):
            min_leads = 5
        try:
            min_bulk_leads = int(request.data.get("min_bulk_leads", 3))
        except (TypeError, ValueError):
            min_bulk_leads = 3
        try:
            top_areas = int(request.data.get("top_areas", 12))
        except (TypeError, ValueError):
            top_areas = 12
        force = bool(request.data.get("force", False))

        if _is_superuser(request):
            organization_id = _requested_org_id(request) or getattr(_user_org(request), "id", None)
        else:
            organization_id = getattr(_user_org(request), "id", None)

        if not organization_id:
            return Response(
                {"organization_id": ["A valid organization context is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = sync_crm_procurement_demand_insights_for_org(
            organization_id=organization_id,
            window_days=window_days,
            threshold_percent=threshold_percent,
            min_leads=min_leads,
            min_bulk_leads=min_bulk_leads,
            top_areas=top_areas,
            force=force,
        )
        status_code = status.HTTP_200_OK if not result.get("skipped") else status.HTTP_202_ACCEPTED
        return Response(result, status=status_code)


class ContactPropertyLinkViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    serializer_class = ContactPropertyLinkSerializer
    filterset_fields = ["relationship_type"]
    ordering_fields = ["linked_at"]
    ordering = ["-linked_at"]

    def _get_contact(self):
        return get_object_or_404(_scoped_contact_queryset(self.request), pk=self.kwargs["contact_pk"])

    def get_queryset(self):
        return ContactPropertyLink.objects.filter(contact=self._get_contact()).select_related(
            "project",
            "property",
            "unit",
        )

    def perform_create(self, serializer):
        contact = self._get_contact()
        project = serializer.validated_data.get("project")
        property_obj = serializer.validated_data.get("property")
        unit = serializer.validated_data.get("unit")
        _ensure_contact_related_org(
            contact,
            project=project,
            property=property_obj,
            unit=unit,
        )
        serializer.save(contact=contact)

    def perform_update(self, serializer):
        contact = self._get_contact()
        project = serializer.validated_data.get("project", serializer.instance.project)
        property_obj = serializer.validated_data.get("property", serializer.instance.property)
        unit = serializer.validated_data.get("unit", serializer.instance.unit)
        _ensure_contact_related_org(
            contact,
            project=project,
            property=property_obj,
            unit=unit,
        )
        serializer.save()


class ContactDocumentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    serializer_class = ContactDocumentSerializer
    filterset_fields = ["document_type", "is_kyc_document"]
    ordering_fields = ["uploaded_at", "expires_at"]
    ordering = ["-uploaded_at"]

    def _get_contact(self):
        return get_object_or_404(_scoped_contact_queryset(self.request), pk=self.kwargs["contact_pk"])

    def get_queryset(self):
        return ContactDocument.objects.filter(contact=self._get_contact()).select_related("uploaded_by")

    def perform_create(self, serializer):
        contact = self._get_contact()
        document = serializer.save(
            contact=contact,
            uploaded_by=self.request.user if self.request.user.is_authenticated else None,
        )
        if document.is_kyc_document:
            _trigger_compliance_review_for_kyc_document(document, actor=self.request.user)

    def perform_update(self, serializer):
        was_kyc_document = serializer.instance.is_kyc_document
        document = serializer.save()
        if document.is_kyc_document and not was_kyc_document:
            _trigger_compliance_review_for_kyc_document(document, actor=self.request.user)


class ContactComplianceReviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    serializer_class = ContactComplianceReviewSerializer
    filterset_fields = ["status"]
    ordering_fields = ["requested_at", "updated_at"]
    ordering = ["-requested_at"]

    def _get_contact(self):
        return get_object_or_404(_scoped_contact_queryset(self.request), pk=self.kwargs["contact_pk"])

    def get_queryset(self):
        return ContactComplianceReview.objects.filter(contact=self._get_contact()).select_related(
            "document",
            "requested_by",
            "reviewed_by",
        )

    @staticmethod
    def _contact_kyc_status_for_review_status(review_status):
        status_map = {
            ContactComplianceReview.Status.PENDING_REVIEW: ContactAccount.KYCStatus.PENDING_REVIEW,
            ContactComplianceReview.Status.IN_REVIEW: ContactAccount.KYCStatus.UNDER_REVIEW,
            ContactComplianceReview.Status.APPROVED: ContactAccount.KYCStatus.VERIFIED,
            ContactComplianceReview.Status.REJECTED: ContactAccount.KYCStatus.REJECTED,
        }
        return status_map.get(review_status)

    def _sync_contact_from_review(self, review):
        contact = review.contact
        next_kyc_status = self._contact_kyc_status_for_review_status(review.status)
        if next_kyc_status is None:
            return

        update_fields = ["kyc_status", "updated_at"]
        contact.kyc_status = next_kyc_status
        if self.request.user.is_authenticated:
            contact.updated_by = self.request.user
            update_fields.append("updated_by")
        contact.save(update_fields=update_fields)

    def perform_create(self, serializer):
        contact = self._get_contact()
        document = serializer.validated_data.get("document")
        if document is not None and document.contact_id != contact.id:
            raise ValidationError({"document": "Document does not belong to this contact."})

        review = serializer.save(
            contact=contact,
            requested_by=self.request.user if self.request.user.is_authenticated else None,
        )
        self._sync_contact_from_review(review)

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        next_status = serializer.validated_data.get("status", previous_status)
        save_kwargs = {}
        if next_status != previous_status and next_status in {
            ContactComplianceReview.Status.IN_REVIEW,
            ContactComplianceReview.Status.APPROVED,
            ContactComplianceReview.Status.REJECTED,
        }:
            save_kwargs["reviewed_by"] = self.request.user if self.request.user.is_authenticated else None
            save_kwargs["reviewed_at"] = timezone.now()

        review = serializer.save(**save_kwargs)
        self._sync_contact_from_review(review)

    @action(detail=True, methods=["post"])
    def mark_in_review(self, request, contact_pk=None, pk=None):
        review = self.get_object()
        review.status = ContactComplianceReview.Status.IN_REVIEW
        review.reviewed_by = request.user if request.user.is_authenticated else None
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        self._sync_contact_from_review(review)
        return Response(ContactComplianceReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, contact_pk=None, pk=None):
        review = self.get_object()
        review.status = ContactComplianceReview.Status.APPROVED
        review.reviewed_by = request.user if request.user.is_authenticated else None
        review.reviewed_at = timezone.now()
        review.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        self._sync_contact_from_review(review)
        return Response(ContactComplianceReviewSerializer(review).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, contact_pk=None, pk=None):
        review = self.get_object()
        notes = request.data.get("notes")
        review.status = ContactComplianceReview.Status.REJECTED
        review.reviewed_by = request.user if request.user.is_authenticated else None
        review.reviewed_at = timezone.now()
        update_fields = ["status", "reviewed_by", "reviewed_at", "updated_at"]
        if notes is not None:
            review.notes = str(notes).strip()
            update_fields.append("notes")
        review.save(update_fields=update_fields)
        self._sync_contact_from_review(review)
        return Response(ContactComplianceReviewSerializer(review).data)


# ---------------------------------------------------------------------------
# Financial Pre-Assessment
# ---------------------------------------------------------------------------


class FinancialAssessmentViewSet(viewsets.ModelViewSet):
    """CRUD + scoring actions for lead financial assessments."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["lead__first_name", "lead__last_name", "lead__email"]
    filterset_fields = ["status", "risk_level", "mortgage_prequalified"]
    ordering_fields = ["created_at", "affordability_score", "risk_score", "assessment_date"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            LeadFinancialAssessment.objects.all(),
            org_field="lead__organization",
        )
        return qs.select_related("lead", "assessed_by").prefetch_related("scenarios")

    def get_serializer_class(self):
        if self.action == "list":
            return FinancialAssessmentListSerializer
        if self.action in ("create", "update", "partial_update"):
            return FinancialAssessmentWriteSerializer
        return FinancialAssessmentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(assessed_by=self.request.user)

    @action(detail=True, methods=["post"])
    def compute_scores(self, request, pk=None):
        """Run affordability and risk scoring algorithms."""
        assessment = self.get_object()
        assessment.compute_affordability()
        assessment.compute_risk()

        # Auto-recommend payment plan
        if assessment.affordability_score is not None:
            if assessment.affordability_score >= 80 and assessment.liquid_assets and assessment.lead.budget_min:
                if float(assessment.liquid_assets) >= float(assessment.lead.budget_min):
                    assessment.recommended_plan = LeadFinancialAssessment.RecommendedPlan.CASH
                else:
                    assessment.recommended_plan = LeadFinancialAssessment.RecommendedPlan.MIXED
            elif assessment.mortgage_prequalified:
                assessment.recommended_plan = LeadFinancialAssessment.RecommendedPlan.MORTGAGE
            else:
                assessment.recommended_plan = LeadFinancialAssessment.RecommendedPlan.INSTALLMENT

            # Recommended down payment and monthly
            if assessment.max_affordable_price and assessment.lead.budget_min:
                price = float(assessment.lead.budget_min)
                if assessment.recommended_plan == LeadFinancialAssessment.RecommendedPlan.CASH:
                    assessment.recommended_down_payment_pct = 100
                    assessment.recommended_monthly_payment = 0
                else:
                    assessment.recommended_down_payment_pct = 20
                    financed = price * 0.8
                    assessment.recommended_monthly_payment = round(financed / 240, 2)

        assessment.save()
        return Response(FinancialAssessmentDetailSerializer(assessment).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark assessment as completed."""
        assessment = self.get_object()
        assessment.status = LeadFinancialAssessment.Status.COMPLETED
        assessment.assessment_date = timezone.now().date()
        assessment.save(update_fields=["status", "assessment_date", "updated_at"])
        return Response(FinancialAssessmentDetailSerializer(assessment).data)


# ---------------------------------------------------------------------------
# Payment Scenarios (nested under assessment)
# ---------------------------------------------------------------------------


class LeadPaymentScenarioViewSet(viewsets.ModelViewSet):
    """Manage payment plan scenarios within an assessment."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"

    def get_queryset(self):
        return LeadPaymentScenario.objects.filter(
            assessment_id=self.kwargs["assessment_pk"],
        )

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LeadPaymentScenarioWriteSerializer
        return LeadPaymentScenarioSerializer

    def perform_create(self, serializer):
        scenario = serializer.save(assessment_id=self.kwargs["assessment_pk"])
        scenario.compute()
        scenario.save()

    def perform_update(self, serializer):
        scenario = serializer.save()
        scenario.compute()
        scenario.save()


# ---------------------------------------------------------------------------
# Broker Tier
# ---------------------------------------------------------------------------


class BrokerTierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    search_fields = ["name", "code"]
    filterset_fields = ["is_active"]
    ordering = ["sort_order", "name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            BrokerTier.objects.all(),
            org_field="organization",
        )
        return qs.prefetch_related("brokers")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BrokerTierWriteSerializer
        return BrokerTierSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Commission Structure
# ---------------------------------------------------------------------------


class CommissionStructureViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    search_fields = ["name", "description"]
    filterset_fields = ["commission_type", "trigger_stage", "is_default", "is_active", "broker", "project"]
    ordering = ["-is_default", "name"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            BrokerCommissionStructure.objects.all(),
            org_field="organization",
        )
        return qs.select_related("broker", "project").prefetch_related("earnings")

    def get_serializer_class(self):
        if self.action == "list":
            return CommissionStructureListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CommissionStructureWriteSerializer
        return CommissionStructureDetailSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Commission Earning
# ---------------------------------------------------------------------------


class CommissionEarningViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["broker__name", "lead__first_name", "lead__last_name"]
    filterset_fields = ["status", "trigger_stage", "broker", "project"]
    ordering_fields = ["created_at", "total_commission", "deal_value", "triggered_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            BrokerCommissionEarning.objects.all(),
            org_field="broker__organization",
        )
        return qs.select_related("broker", "lead", "commission_structure", "project", "approved_by")

    def get_serializer_class(self):
        if self.action == "list":
            return CommissionEarningListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CommissionEarningWriteSerializer
        return CommissionEarningDetailSerializer

    def perform_create(self, serializer):
        earning = serializer.save()
        earning.compute()
        earning.save()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending commission earning."""
        earning = self.get_object()
        if earning.status != BrokerCommissionEarning.Status.PENDING:
            return Response(
                {"error": "Only pending earnings can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        earning.status = BrokerCommissionEarning.Status.APPROVED
        earning.approved_by = request.user
        earning.approved_at = timezone.now()
        earning.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        return Response(CommissionEarningDetailSerializer(earning).data)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        """Mark an approved commission as paid (sends to finance)."""
        earning = self.get_object()
        if earning.status not in (
            BrokerCommissionEarning.Status.APPROVED,
            BrokerCommissionEarning.Status.PROCESSING,
        ):
            return Response(
                {"error": "Only approved/processing earnings can be marked as paid."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        earning.status = BrokerCommissionEarning.Status.PAID
        earning.paid_at = timezone.now()
        earning.payment_reference = request.data.get("payment_reference", "")
        earning.save(update_fields=["status", "paid_at", "payment_reference", "updated_at"])
        return Response(CommissionEarningDetailSerializer(earning).data)


# ---------------------------------------------------------------------------
# Broker Performance Overview (all brokers)
# ---------------------------------------------------------------------------


class BrokerPerformanceOverviewView(APIView):
    """Dashboard-level broker performance metrics across all brokers."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "broker-performance")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        brokers = _scope_queryset_for_request(
            request,
            Broker.objects.all(),
            org_field="organization_id",
        )
        leads = _scope_queryset_for_request(
            request,
            Lead.objects.filter(broker__isnull=False),
            org_field="organization_id",
        )

        months = int(request.query_params.get("months", 12))
        cutoff = timezone.now() - timezone.timedelta(days=months * 30)
        period_leads = leads.filter(created_at__gte=cutoff)

        # Aggregate
        total_brokers = brokers.filter(status="active").count()
        total_leads = period_leads.count()
        won_leads = period_leads.filter(status="won").count()

        # Earnings
        earnings = _scope_queryset_for_request(
            request,
            BrokerCommissionEarning.objects.filter(created_at__gte=cutoff),
            org_field="broker__organization_id",
        )
        agg = earnings.aggregate(
            total_commission_amount=Sum("total_commission"),
            total_deal_value=Sum("deal_value"),
            paid=Sum(
                models.Case(
                    models.When(status="paid", then=models.F("total_commission")),
                    default=0, output_field=models.DecimalField(),
                )
            ),
            pending=Sum(
                models.Case(
                    models.When(status="pending", then=models.F("total_commission")),
                    default=0, output_field=models.DecimalField(),
                )
            ),
        )

        # Top brokers by deals closed
        top_by_deals = list(
            period_leads.filter(status="won")
            .values("broker__id", "broker__name")
            .annotate(deals=Count("id"))
            .order_by("-deals")[:10]
        )

        # Top brokers by commission earned
        top_by_commission = list(
            earnings.values("broker__id", "broker__name")
            .annotate(total=Sum("total_commission"))
            .order_by("-total")[:10]
        )

        # Tier distribution
        tier_distribution = list(
            brokers.filter(status="active")
            .values("tier__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        payload = {
            "period_months": months,
            "total_active_brokers": total_brokers,
            "total_broker_leads": total_leads,
            "won_broker_leads": won_leads,
            "conversion_rate": round(won_leads / total_leads * 100, 1) if total_leads > 0 else 0,
            "total_commission": agg["total_commission_amount"] or 0,
            "total_deal_value": agg["total_deal_value"] or 0,
            "paid_commission": agg["paid"] or 0,
            "pending_commission": agg["pending"] or 0,
            "top_by_deals": [
                {"broker_id": t["broker__id"], "broker_name": t["broker__name"], "deals": t["deals"]}
                for t in top_by_deals
            ],
            "top_by_commission": [
                {"broker_id": t["broker__id"], "broker_name": t["broker__name"], "total": t["total"]}
                for t in top_by_commission
            ],
            "tier_distribution": [
                {"tier": t["tier__name"] or "Unassigned", "count": t["count"]}
                for t in tier_distribution
            ],
        }
        cache.set(cache_key, payload, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(payload)


# ---------------------------------------------------------------------------
# Communication Log
# ---------------------------------------------------------------------------


class CommunicationLogViewSet(viewsets.ModelViewSet):
    """CRUD for communication logs — WhatsApp, email, call, SMS tracking."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["subject", "summary", "body", "to_address", "from_address"]
    filterset_fields = ["channel", "direction", "status", "lead", "campaign"]
    ordering_fields = ["communicated_at", "created_at"]
    ordering = ["-communicated_at"]

    @staticmethod
    def _normalize_contact_point(value: str | None) -> str:
        if not value:
            return ""
        return " ".join(str(value).strip().lower().split())

    @classmethod
    def _thread_key_for_comm(cls, comm: CommunicationLog) -> str:
        parties = sorted(
            {
                point
                for point in (
                    cls._normalize_contact_point(getattr(comm, "from_address", "")),
                    cls._normalize_contact_point(getattr(comm, "to_address", "")),
                )
                if point
            }
        )
        parties_key = "|".join(parties) if parties else "no-party"
        token = f"{comm.organization_id}|{comm.lead_id}|{comm.channel}|{parties_key}"
        return hashlib.sha1(token.encode("utf-8")).hexdigest()

    @classmethod
    def _thread_summary_payload(cls, comm: CommunicationLog, thread_key: str) -> dict:
        return {
            "thread_key": thread_key,
            "lead_id": comm.lead_id,
            "lead_name": getattr(comm.lead, "full_name", ""),
            "channel": comm.channel,
            "participants": sorted(
                {
                    point
                    for point in (
                        cls._normalize_contact_point(getattr(comm, "from_address", "")),
                        cls._normalize_contact_point(getattr(comm, "to_address", "")),
                    )
                    if point
                }
            ),
            "message_count": 0,
            "inbound_count": 0,
            "outbound_count": 0,
            "first_message_at": comm.communicated_at,
            "last_message_at": comm.communicated_at,
            "latest_subject": comm.subject or "",
            "latest_summary": comm.summary or "",
            "latest_status": comm.status,
            "latest_direction": comm.direction,
            "campaign_id": comm.campaign_id,
            "campaign_name": getattr(comm.campaign, "name", "") if getattr(comm, "campaign_id", None) else "",
        }

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            CommunicationLog.objects.all(),
            org_field="organization",
        )
        return qs.select_related(
            "lead", "performed_by", "campaign",
        ).prefetch_related("call_recording")

    def get_serializer_class(self):
        if self.action == "list":
            return CommunicationLogListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CommunicationLogWriteSerializer
        return CommunicationLogDetailSerializer

    def perform_create(self, serializer):
        comm = serializer.save(
            organization=_user_org(self.request),
            performed_by=self.request.user,
        )
        # Auto-create a linked LeadActivity
        activity = LeadActivity.objects.create(
            lead=comm.lead,
            activity_type=self._channel_to_activity_type(comm.channel),
            subject=comm.subject or f"{comm.get_channel_display()} — {comm.get_direction_display()}",
            description=comm.summary or comm.body[:500] if comm.body else "",
            is_completed=True,
            completed_at=comm.communicated_at,
            performed_by=self.request.user,
        )
        comm.activity = activity
        comm.save(update_fields=["activity"])

    @staticmethod
    def _channel_to_activity_type(channel):
        mapping = {
            CommunicationLog.Channel.EMAIL: LeadActivity.ActivityType.EMAIL,
            CommunicationLog.Channel.PHONE: LeadActivity.ActivityType.CALL,
            CommunicationLog.Channel.VIDEO_CALL: LeadActivity.ActivityType.MEETING,
            CommunicationLog.Channel.IN_PERSON: LeadActivity.ActivityType.MEETING,
        }
        return mapping.get(channel, LeadActivity.ActivityType.OTHER)

    @action(detail=False, methods=["get"], url_path="threads")
    def threads(self, request):
        """Conversation-style grouped communication threads."""
        qs = self.filter_queryset(self.get_queryset()).order_by("-communicated_at")
        thread_map: dict[str, dict] = {}

        for comm in qs:
            key = self._thread_key_for_comm(comm)
            payload = thread_map.get(key)
            if payload is None:
                payload = self._thread_summary_payload(comm, key)
                thread_map[key] = payload

            payload["message_count"] += 1
            if comm.direction == CommunicationLog.Direction.INBOUND:
                payload["inbound_count"] += 1
            elif comm.direction == CommunicationLog.Direction.OUTBOUND:
                payload["outbound_count"] += 1

            if comm.communicated_at < payload["first_message_at"]:
                payload["first_message_at"] = comm.communicated_at

            if comm.communicated_at >= payload["last_message_at"]:
                payload["last_message_at"] = comm.communicated_at
                payload["latest_subject"] = comm.subject or ""
                payload["latest_summary"] = comm.summary or ""
                payload["latest_status"] = comm.status
                payload["latest_direction"] = comm.direction
                payload["campaign_id"] = comm.campaign_id
                payload["campaign_name"] = (
                    getattr(comm.campaign, "name", "")
                    if getattr(comm, "campaign_id", None)
                    else ""
                )

        threads = sorted(
            thread_map.values(),
            key=lambda item: item["last_message_at"],
            reverse=True,
        )
        page = self.paginate_queryset(threads)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(threads)

    @action(detail=False, methods=["get"], url_path=r"threads/(?P<thread_key>[0-9a-f]{40})/messages")
    def thread_messages(self, request, thread_key=None):
        """Messages belonging to one computed communication thread."""
        qs = self.filter_queryset(self.get_queryset())
        messages = [
            comm for comm in qs
            if self._thread_key_for_comm(comm) == thread_key
        ]
        messages.sort(key=lambda item: item.communicated_at, reverse=True)

        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = CommunicationLogListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CommunicationLogListSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def add_recording(self, request, pk=None):
        """Attach call recording metadata to a phone/video communication log."""
        comm = self.get_object()
        if comm.channel not in (CommunicationLog.Channel.PHONE, CommunicationLog.Channel.VIDEO_CALL):
            return Response(
                {"error": "Recordings can only be attached to phone or video call logs."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if hasattr(comm, "call_recording") and comm.call_recording:
            return Response(
                {"error": "This communication already has a recording attached."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = CallRecordingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(communication=comm)
        return Response(
            CommunicationLogDetailSerializer(comm).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class CampaignViewSet(viewsets.ModelViewSet):
    """Campaign management — create, schedule, and track outreach campaigns."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["name", "description"]
    filterset_fields = ["campaign_type", "status", "channel"]
    ordering_fields = ["created_at", "scheduled_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            Campaign.objects.all(),
            org_field="organization",
        )
        return qs.select_related("created_by", "notification_template").prefetch_related("recipients")

    def get_serializer_class(self):
        if self.action == "list":
            return CampaignListSerializer
        if self.action in ("create", "update", "partial_update"):
            return CampaignWriteSerializer
        return CampaignDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=_user_org(self.request),
            created_by=self.request.user,
        )

    @staticmethod
    def _matching_target_leads(campaign):
        qs = Lead.objects.filter(
            organization=campaign.organization,
            status=Lead.Status.ACTIVE,
            is_archived=False,
        )
        if campaign.target_pipeline_stages:
            qs = qs.filter(pipeline_stage__in=campaign.target_pipeline_stages)
        if campaign.target_lead_sources:
            qs = qs.filter(source_id__in=campaign.target_lead_sources)
        if campaign.target_projects:
            qs = qs.filter(project_interests__project_id__in=campaign.target_projects)
        if campaign.target_lead_types:
            qs = qs.filter(lead_type__in=campaign.target_lead_types)
        return qs.distinct()

    def _add_target_recipients(self, campaign):
        leads = self._matching_target_leads(campaign).only("id")
        lead_ids = [lead.id for lead in leads]
        if not lead_ids:
            return 0
        existing = set(
            CampaignRecipient.objects.filter(
                campaign=campaign,
                lead_id__in=lead_ids,
            ).values_list("lead_id", flat=True)
        )
        to_create = [
            CampaignRecipient(campaign=campaign, lead_id=lead_id)
            for lead_id in lead_ids
            if lead_id not in existing
        ]
        if not to_create:
            return 0
        CampaignRecipient.objects.bulk_create(to_create, ignore_conflicts=True)
        return len(to_create)

    @staticmethod
    def _campaign_source_for_auto_leads(campaign):
        source_ids = [int(v) for v in (campaign.target_lead_sources or []) if str(v).isdigit()]
        if not source_ids:
            return None
        return LeadSource.objects.filter(
            organization=campaign.organization,
            id=source_ids[0],
            is_active=True,
        ).first()

    def _auto_create_launch_leads(self, campaign):
        if not campaign.auto_create_leads_on_launch:
            return 0
        target_count = int(campaign.auto_create_leads_count or 0)
        if target_count <= 0:
            return 0

        already_created = int(campaign.auto_created_leads_count or 0)
        remaining = max(target_count - already_created, 0)
        if remaining <= 0:
            return 0

        source = self._campaign_source_for_auto_leads(campaign)
        assigned_to = _select_auto_assignee_for_lead(campaign.organization)
        lead_type = campaign.auto_create_lead_type or (
            campaign.target_lead_types[0] if campaign.target_lead_types else Lead.LeadType.BUYER
        )

        created_leads = []
        for offset in range(remaining):
            sequence = already_created + offset + 1
            lead = Lead.objects.create(
                organization=campaign.organization,
                first_name="Campaign",
                last_name=f"Lead {campaign.id}-{sequence}",
                lead_type=lead_type,
                source=source,
                assigned_to=assigned_to,
                priority=Lead.Priority.MEDIUM,
                pipeline_stage=Lead.PipelineStage.INQUIRY,
                status=Lead.Status.ACTIVE,
                inquiry_date=timezone.now().date(),
                tags=[f"campaign:{campaign.id}", "auto-generated"],
                notes=f"Auto-created from campaign launch: {campaign.name}",
            )
            _generate_follow_up_tasks_for_stage_entry(lead, lead.pipeline_stage)
            created_leads.append(lead)

        if created_leads:
            CampaignRecipient.objects.bulk_create(
                [CampaignRecipient(campaign=campaign, lead=lead) for lead in created_leads],
                ignore_conflicts=True,
            )
            campaign.auto_created_leads_count = already_created + len(created_leads)
        return len(created_leads)

    @action(detail=True, methods=["post"])
    def add_recipients(self, request, pk=None):
        """Add leads to campaign recipient list."""
        campaign = self.get_object()
        serializer = CampaignAddRecipientsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lead_ids = serializer.validated_data["lead_ids"]
        org = _user_org(request)
        leads = Lead.objects.filter(id__in=lead_ids, organization=org)

        created = 0
        for lead in leads:
            _, was_created = CampaignRecipient.objects.get_or_create(
                campaign=campaign, lead=lead,
            )
            if was_created:
                created += 1

        campaign.total_recipients = campaign.recipients.count()
        campaign.save(update_fields=["total_recipients"])

        return Response({
            "added": created,
            "total_recipients": campaign.total_recipients,
        })

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        """Mark campaign as running (actual sending is handled by Celery)."""
        campaign = self.get_object()
        if campaign.status not in (Campaign.Status.DRAFT, Campaign.Status.SCHEDULED):
            return Response(
                {"error": "Only draft or scheduled campaigns can be launched."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1) Pull recipients by campaign targeting filters.
        self._add_target_recipients(campaign)
        # 2) Auto-create demand-gen leads (once) when configured.
        self._auto_create_launch_leads(campaign)

        campaign.total_recipients = campaign.recipients.count()
        if campaign.total_recipients == 0:
            return Response(
                {"error": "Campaign has no recipients. Add leads first or configure auto-create."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign.status = Campaign.Status.RUNNING
        campaign.started_at = timezone.now()
        campaign.save(
            update_fields=[
                "status",
                "started_at",
                "total_recipients",
                "auto_created_leads_count",
                "updated_at",
            ]
        )
        return Response(CampaignDetailSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause a running campaign."""
        campaign = self.get_object()
        if campaign.status != Campaign.Status.RUNNING:
            return Response(
                {"error": "Only running campaigns can be paused."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        campaign.status = Campaign.Status.PAUSED
        campaign.save(update_fields=["status", "updated_at"])
        return Response(CampaignDetailSerializer(campaign).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a campaign as completed."""
        campaign = self.get_object()
        campaign.status = Campaign.Status.COMPLETED
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(CampaignDetailSerializer(campaign).data)


# ---------------------------------------------------------------------------
# Follow-Up Rule
# ---------------------------------------------------------------------------


class FollowUpRuleViewSet(viewsets.ModelViewSet):
    """Configure SLA-driven follow-up rules per pipeline stage."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    search_fields = ["name", "description"]
    filterset_fields = ["trigger_stage", "is_active", "required_activity_type"]
    ordering = ["trigger_stage", "follow_up_within_hours"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            FollowUpRule.objects.all(),
            org_field="organization",
        )
        return qs.select_related("sla_severity").prefetch_related("tasks")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return FollowUpRuleWriteSerializer
        return FollowUpRuleSerializer

    def perform_create(self, serializer):
        serializer.save(organization=_user_org(self.request))


# ---------------------------------------------------------------------------
# Follow-Up Task
# ---------------------------------------------------------------------------


class FollowUpTaskViewSet(viewsets.ModelViewSet):
    """Track and manage generated follow-up tasks with SLA compliance."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["lead__first_name", "lead__last_name", "rule__name"]
    filterset_fields = ["status", "assigned_to", "lead", "rule"]
    ordering_fields = ["due_at", "created_at"]
    ordering = ["due_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            FollowUpTask.objects.all(),
            org_field="rule__organization",
        )
        return qs.select_related("rule", "lead", "assigned_to", "completed_activity")

    def get_serializer_class(self):
        if self.action == "list":
            return FollowUpTaskListSerializer
        if self.action == "manual_create":
            return FollowUpTaskManualCreateSerializer
        return FollowUpTaskDetailSerializer

    @action(detail=True, methods=["post"])
    def complete_task(self, request, pk=None):
        """Mark a follow-up task as completed."""
        task = self.get_object()
        if task.status in (FollowUpTask.Status.COMPLETED, FollowUpTask.Status.CANCELLED):
            return Response(
                {"error": "Task is already completed or cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = FollowUpTaskCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity_id = serializer.validated_data.get("activity_id")
        if activity_id:
            try:
                activity = LeadActivity.objects.get(id=activity_id, lead=task.lead)
                task.completed_activity = activity
            except LeadActivity.DoesNotExist:
                return Response(
                    {"error": "Activity not found for this lead."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        task.status = FollowUpTask.Status.COMPLETED
        task.completed_at = timezone.now()
        task.notes = serializer.validated_data.get("notes", "")
        task.save()
        return Response(FollowUpTaskDetailSerializer(task).data)

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        """Escalate a breached or overdue follow-up task."""
        task = self.get_object()
        if task.status in (FollowUpTask.Status.COMPLETED, FollowUpTask.Status.CANCELLED):
            return Response(
                {"error": "Cannot escalate a completed or cancelled task."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = FollowUpTask.Status.ESCALATED
        task.escalated_at = timezone.now()
        task.save(update_fields=["status", "escalated_at", "updated_at"])
        return Response(FollowUpTaskDetailSerializer(task).data)

    @action(detail=False, methods=["post"], url_path="manual-create")
    def manual_create(self, request):
        """Create and assign a follow-up task directly from activity management."""
        from apps.accounts.models import UserProfile

        serializer = FollowUpTaskManualCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = _user_org(request)
        if org is None:
            return Response(
                {"detail": "Organization context is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lead = get_object_or_404(
            _scoped_lead_queryset(request),
            pk=serializer.validated_data["lead"],
        )

        assigned_to = lead.assigned_to
        assigned_to_id = serializer.validated_data.get("assigned_to")
        if assigned_to_id is not None:
            if assigned_to_id <= 0:
                assigned_to = None
            else:
                profile = UserProfile.objects.select_related("user").filter(
                    user_id=assigned_to_id,
                    organization=org,
                    user_status=UserProfile.UserStatus.ACTIVE,
                    user__is_active=True,
                ).first()
                if profile is None:
                    return Response(
                        {"assigned_to": ["Selected assignee is not active in this organization."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                assigned_to = profile.user

        rule = None
        rule_id = serializer.validated_data.get("rule")
        if rule_id:
            rule = get_object_or_404(
                _scope_queryset_for_request(
                    request,
                    FollowUpRule.objects.all(),
                    org_field="organization_id",
                ),
                pk=rule_id,
            )
        else:
            rule = _manual_follow_up_rule_for_org(org)

        notes = serializer.validated_data.get("notes", "")
        task = FollowUpTask.objects.create(
            rule=rule,
            lead=lead,
            assigned_to=assigned_to,
            due_at=serializer.validated_data["due_at"],
            notes=notes,
        )
        _notify_task_assignment(task, actor=request.user)

        return Response(
            FollowUpTaskDetailSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Lead Document Event
# ---------------------------------------------------------------------------


class LeadDocumentEventViewSet(viewsets.ModelViewSet):
    """Track document interactions with leads — proposals viewed, SPAs downloaded, etc."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    search_fields = ["document_name", "lead__first_name", "lead__last_name"]
    filterset_fields = ["event_type", "lead", "delivered_via"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            LeadDocumentEvent.objects.all(),
            org_field="lead__organization",
        )
        return qs.select_related("lead", "document", "audit_event", "performed_by")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return LeadDocumentEventWriteSerializer
        return LeadDocumentEventSerializer

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)


# ---------------------------------------------------------------------------
# Meeting Record
# ---------------------------------------------------------------------------


class MeetingRecordViewSet(viewsets.ModelViewSet):
    """Detailed meeting history — extends LeadActivity with structured data."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = ["title", "lead__first_name", "lead__last_name", "location"]
    filterset_fields = ["meeting_type", "outcome", "lead", "project"]
    ordering_fields = ["scheduled_start", "created_at"]
    ordering = ["-scheduled_start"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            MeetingRecord.objects.all(),
            org_field="lead__organization",
        )
        return qs.select_related("lead", "organized_by", "project", "property_unit", "activity")

    def get_serializer_class(self):
        if self.action == "list":
            return MeetingRecordListSerializer
        if self.action in ("create", "update", "partial_update"):
            return MeetingRecordWriteSerializer
        return MeetingRecordDetailSerializer

    def perform_create(self, serializer):
        meeting = serializer.save(organized_by=self.request.user)
        # Auto-create a linked LeadActivity
        activity_type = (
            LeadActivity.ActivityType.SITE_VISIT
            if meeting.meeting_type == MeetingRecord.MeetingType.SITE_VISIT
            else LeadActivity.ActivityType.MEETING
        )
        activity = LeadActivity.objects.create(
            lead=meeting.lead,
            activity_type=activity_type,
            subject=meeting.title,
            description=meeting.agenda or "",
            scheduled_at=meeting.scheduled_start,
            performed_by=self.request.user,
        )
        meeting.activity = activity
        meeting.save(update_fields=["activity"])
        _ensure_scheduled_activity_task(
            activity,
            assigned_to=meeting.lead.assigned_to or self.request.user,
            actor=self.request.user,
        )
        _notify_site_visit_scheduled(activity, actor=self.request.user)


# ---------------------------------------------------------------------------
# Communication Engine Overview (dashboard)
# ---------------------------------------------------------------------------


class CommunicationOverviewView(APIView):
    """Dashboard-level communication metrics across all channels."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "communication")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        months = int(request.query_params.get("months", 3))
        cutoff = timezone.now() - timezone.timedelta(days=months * 30)

        comms = _scope_queryset_for_request(
            request,
            CommunicationLog.objects.filter(communicated_at__gte=cutoff),
            org_field="organization_id",
        )

        # Channel breakdown
        channel_stats = list(
            comms.values("channel")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Direction breakdown
        direction_stats = list(
            comms.values("direction")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Active campaigns
        active_campaigns = _scope_queryset_for_request(
            request,
            Campaign.objects.filter(status__in=["draft", "scheduled", "running"]),
            org_field="organization_id",
        ).count()

        # Follow-up SLA stats
        tasks = _scope_queryset_for_request(
            request,
            FollowUpTask.objects.all(),
            org_field="rule__organization_id",
        )
        pending_tasks = tasks.filter(status__in=["pending", "in_progress"]).count()
        overdue_tasks = tasks.filter(
            status__in=["pending", "in_progress"],
            due_at__lt=timezone.now(),
        ).count()
        breached_tasks = tasks.filter(status="breached").count()

        # Recent document events
        doc_events = _scope_queryset_for_request(
            request,
            LeadDocumentEvent.objects.filter(created_at__gte=cutoff),
            org_field="lead__organization_id",
        ).count()

        # Meetings this month
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        meetings_this_month = _scope_queryset_for_request(
            request,
            MeetingRecord.objects.filter(scheduled_start__gte=month_start),
            org_field="lead__organization_id",
        ).count()

        # Payment reminder visibility (due/overdue receivables linked to reservations)
        from apps.finance.models import PaymentInstallment

        today = timezone.localdate()
        due_soon_cutoff = today + timezone.timedelta(days=2)
        open_installments = _scope_queryset_for_request(
            request,
            PaymentInstallment.objects.exclude(
                status__in=[
                    PaymentInstallment.Status.PAID,
                    PaymentInstallment.Status.WAIVED,
                    PaymentInstallment.Status.CANCELLED,
                ]
            ),
            org_field="payment_plan__reservation__organization_id",
        )
        payment_reminders_due_soon = open_installments.filter(
            due_date__gte=today,
            due_date__lte=due_soon_cutoff,
        ).count()
        payment_reminders_overdue = open_installments.filter(
            due_date__lt=today,
        ).count()

        payload = {
            "period_months": months,
            "total_communications": comms.count(),
            "channel_breakdown": [
                {"channel": c["channel"], "count": c["count"]}
                for c in channel_stats
            ],
            "direction_breakdown": [
                {"direction": d["direction"], "count": d["count"]}
                for d in direction_stats
            ],
            "active_campaigns": active_campaigns,
            "follow_up_pending": pending_tasks,
            "follow_up_overdue": overdue_tasks,
            "follow_up_breached": breached_tasks,
            "document_events": doc_events,
            "meetings_this_month": meetings_this_month,
            "payment_reminders_due_soon": payment_reminders_due_soon,
            "payment_reminders_overdue": payment_reminders_overdue,
        }
        cache.set(cache_key, payload, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(payload)


# ---------------------------------------------------------------------------
# Unit Reservation
# ---------------------------------------------------------------------------


class UnitReservationViewSet(viewsets.ModelViewSet):
    """
    Full CRUD + lifecycle actions for unit reservations.

    Property inventory (units) is distinct from procurement inventory
    (materials/supplies in the inventory app).
    """
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action_map = _CRM_ACTION_MAP
    search_fields = [
        "reservation_number",
        "lead__first_name", "lead__last_name",
        "unit__unit_number",
    ]
    filterset_fields = ["status", "lead", "unit", "project"]
    ordering_fields = ["created_at", "hold_expires_at", "total_price"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = _scope_queryset_for_request(
            self.request,
            UnitReservation.objects.all(),
            org_field="organization",
        )
        return qs.select_related(
            "lead", "unit", "unit__property", "project",
            "converted_customer", "payment_plan",
            "reservation_agreement", "allocation_letter", "performed_by",
        ).prefetch_related("events")

    def get_serializer_class(self):
        if self.action == "list":
            return UnitReservationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return UnitReservationWriteSerializer
        return UnitReservationDetailSerializer

    def perform_create(self, serializer):
        from apps.properties.models import Unit

        unit = serializer.validated_data["unit"]
        lead = serializer.validated_data["lead"]

        # Lock unit
        unit.status = Unit.UnitStatus.RESERVED
        unit.save(update_fields=["status", "updated_at"])

        reservation = serializer.save(
            organization=_user_org(self.request),
            performed_by=self.request.user,
            status=UnitReservation.Status.HOLD,
        )

        # Audit event
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.HOLD_PLACED,
            performed_by=self.request.user,
            notes=f"Hold placed on {unit}",
            metadata={
                "unit_id": unit.id,
                "unit_number": unit.unit_number,
                "total_price": str(reservation.total_price),
                "hold_expires_at": str(reservation.hold_expires_at),
            },
        )

        # Advance lead pipeline to RESERVATION if earlier
        if lead.pipeline_stage in (
            Lead.PipelineStage.INQUIRY,
            Lead.PipelineStage.QUALIFIED,
            Lead.PipelineStage.SITE_VISIT,
            Lead.PipelineStage.OFFER_MADE,
        ):
            old_stage = lead.pipeline_stage
            lead.pipeline_stage = Lead.PipelineStage.RESERVATION
            lead.reservation_date = timezone.now().date()
            lead.save(update_fields=[
                "pipeline_stage", "reservation_date", "updated_at",
            ])
            LeadStageTransition.objects.create(
                lead=lead,
                from_stage=old_stage,
                to_stage=Lead.PipelineStage.RESERVATION,
                transitioned_by=self.request.user,
                notes="Auto-transitioned on reservation creation.",
            )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Confirm reservation: HOLD → PAYMENT_PENDING.
        Creates PaymentPlan + deposit installment, sends notification."""
        reservation = self.get_object()
        if reservation.status != UnitReservation.Status.HOLD:
            return Response(
                {"error": "Only reservations in HOLD status can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        now = timezone.now()
        org = _user_org(request)

        reservation.status = UnitReservation.Status.PAYMENT_PENDING
        reservation.reservation_date = now.date()
        reservation.confirmation_date = now

        # Create PaymentPlan with deposit installment
        from apps.finance.models import PaymentInstallment, PaymentPlan
        from apps.settings.models import SystemPreferences

        default_currency = (
            SystemPreferences.objects.filter(organization=org)
            .values_list("default_currency", flat=True)
            .first()
            or _payment_plan_default_currency_code()
        )
        plan = PaymentPlan.objects.create(
            organization=org,
            title=f"Reservation {reservation.reservation_number} — {reservation.lead.full_name}",
            status=PaymentPlan.Status.ACTIVE,
            plan_type=PaymentPlan.PlanType.CUSTOM,
            direction=PaymentPlan.Direction.RECEIVABLE,
            frequency=PaymentPlan.Frequency.ONE_TIME,
            total_amount=reservation.total_price,
            currency=default_currency,
            start_date=now.date(),
            number_of_installments=1,
            notes=f"Auto-created for reservation {reservation.reservation_number}",
            created_by=request.user,
        )
        deposit_due = reservation.payment_deadline or (
            now + timezone.timedelta(days=14)
        )
        PaymentInstallment.objects.create(
            payment_plan=plan,
            installment_number=1,
            label="Reservation Deposit",
            amount=reservation.deposit_amount,
            scheduled_date=now.date(),
            due_date=deposit_due.date() if hasattr(deposit_due, "date") else deposit_due,
            status=PaymentInstallment.Status.DUE,
        )
        reservation.payment_plan = plan

        # Reservation confirmed + payment instruction notifications
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

        raci = resolve_raci_recipients(
            organization=org,
            process_key="crm.sales",
        )
        confirmed_recipients = raci.all
        if reservation.lead.assigned_to_id and reservation.lead.assigned_to not in confirmed_recipients:
            confirmed_recipients.append(reservation.lead.assigned_to)
        if confirmed_recipients:
            dispatch_workflow_notification(
                organization=org,
                event_key="crm_reservation_confirmed",
                recipients=confirmed_recipients,
                context={
                    "reservation_number": reservation.reservation_number,
                    "unit_number": str(reservation.unit) if reservation.unit_id else "",
                    "property_name": str(reservation.unit.property) if reservation.unit_id and reservation.unit.property_id else "",
                    "action_url": f"/crm/reservations/{reservation.id}",
                },
                link_url=f"/crm/reservations/{reservation.id}",
                fallback_channels=["in_app", "email"],
                fallback_title=f"Reservation Confirmed — {reservation.reservation_number}",
                fallback_message=(
                    f"Reservation {reservation.reservation_number} has been confirmed"
                    f"{f' for unit {reservation.unit}' if reservation.unit_id else ''}. "
                    f"Payment instructions will be issued to the client."
                ),
                fallback_category=Notification.Category.CRM_RESERVATION,
                fallback_severity=Notification.Severity.INFO,
            )

        if reservation.lead.assigned_to:
            due_date_display = (
                deposit_due.strftime("%b %d, %Y")
                if hasattr(deposit_due, "strftime")
                else str(deposit_due)
            )
            dispatch_workflow_notification(
                organization=org,
                event_key="crm_reservation_payment_instruction",
                recipients=[reservation.lead.assigned_to],
                context={
                    "reservation_number": reservation.reservation_number,
                    "deposit_amount": str(reservation.deposit_amount),
                    "deposit_due_date": due_date_display,
                    "action_url": f"/crm/reservations/{reservation.id}",
                },
                link_url=f"/crm/reservations/{reservation.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Payment Instructions Issued — {reservation.reservation_number}",
                fallback_message=(
                    f"Payment instructions have been issued for reservation "
                    f"{reservation.reservation_number}. A deposit of ₦{reservation.deposit_amount:,.2f} "
                    f"is due by {due_date_display}. Please follow up with the client."
                ),
            )

        reservation.save()

        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.RESERVATION_CONFIRMED,
            performed_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
            metadata={"payment_plan_id": plan.id, "plan_number": plan.plan_number},
        )
        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.PAYMENT_INSTRUCTION_SENT,
            performed_by=request.user,
            metadata={"deposit_amount": str(reservation.deposit_amount)},
        )

        return Response(UnitReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=["post"])
    def record_payment(self, request, pk=None):
        """Record a deposit payment against the reservation's payment plan."""
        reservation = self.get_object()
        if reservation.status != UnitReservation.Status.PAYMENT_PENDING:
            return Response(
                {"error": "Reservation is not in PAYMENT_PENDING status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.finance.models import PaymentInstallment
        installment = reservation.payment_plan.installments.filter(
            status__in=["due", "scheduled", "partially_paid"],
        ).first()
        if not installment:
            return Response(
                {"error": "No pending installment found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        installment.paid_amount += data["amount"]
        installment.payment_method = data["payment_method"]
        installment.reference_number = data.get("reference_number", "")
        installment.paid_date = timezone.now().date()
        if installment.paid_amount >= installment.amount:
            installment.status = PaymentInstallment.Status.PAID
        else:
            installment.status = PaymentInstallment.Status.PARTIALLY_PAID
        installment.save()

        event_type = ReservationEvent.EventType.DEPOSIT_RECEIVED
        if installment.paid_amount >= reservation.deposit_amount:
            reservation.status = UnitReservation.Status.PAID
            event_type = ReservationEvent.EventType.FULL_PAYMENT_RECEIVED

        reservation.save(update_fields=["status", "updated_at"])

        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=event_type,
            performed_by=request.user,
            notes=data.get("notes", ""),
            metadata={
                "amount": str(data["amount"]),
                "method": data["payment_method"],
                "reference": data.get("reference_number", ""),
                "installment_paid_total": str(installment.paid_amount),
            },
        )

        return Response(UnitReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """Convert reservation: create Customer, close lead, mark unit SOLD."""
        from apps.finance.models import Customer

        reservation = self.get_object()
        if reservation.status != UnitReservation.Status.PAID:
            return Response(
                {"error": "Only PAID reservations can be converted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lead = reservation.lead
        _ensure_lead_contract_stage_kyc_gate(
            lead=lead,
            target_stage=Lead.PipelineStage.CLOSED,
        )
        reservation.status = UnitReservation.Status.CONVERTING
        reservation.save(update_fields=["status", "updated_at"])

        # Create customer (reuses pattern from LeadViewSet.convert)
        if lead.converted_customer:
            customer = lead.converted_customer
        else:
            customer = Customer.objects.create(
                name=lead.full_name,
                contact_person=lead.full_name,
                email=lead.email,
                phone=lead.phone,
                address="",
                notes=(
                    f"Converted from CRM Lead via reservation "
                    f"{reservation.reservation_number}."
                ),
            )
            lead.converted_customer = customer
            lead.status = Lead.Status.WON
            lead.is_archived = True
            lead.archived_at = timezone.now()
            lead.archived_reason = "SPA Signed"
            if lead.pipeline_stage != Lead.PipelineStage.CLOSED:
                old_stage = lead.pipeline_stage
                lead.pipeline_stage = Lead.PipelineStage.CLOSED
                lead.closed_date = timezone.now().date()
                LeadStageTransition.objects.create(
                    lead=lead,
                    from_stage=old_stage,
                    to_stage=Lead.PipelineStage.CLOSED,
                    transitioned_by=request.user,
                    notes="Auto-transitioned on reservation conversion.",
                )
            lead.save()

        # Link customer to payment plan
        if reservation.payment_plan and not reservation.payment_plan.customer:
            reservation.payment_plan.customer = customer
            reservation.payment_plan.save(update_fields=["customer", "updated_at"])

        # Closed-won automations for reservations:
        # - Contract generation
        # - Invoice creation
        # - Property/unit inventory status → Sold
        deal_link = (
            reservation.contact_deal_links
            .select_related("contact", "lead", "reservation")
            .order_by("-linked_at")
            .first()
        )
        if deal_link is None:
            # Fallback proxy for automation context when no explicit deal link exists.
            deal_link = ContactDealLink(
                lead=lead,
                reservation=reservation,
                deal_name=f"Reservation {reservation.reservation_number}",
                stage="Closed Won",
                status=ContactDealLink.Status.WON,
                deal_value=reservation.total_price,
                close_probability=100,
            )
            deal_link.id = reservation.id
        else:
            update_fields = []
            if deal_link.status != ContactDealLink.Status.WON:
                deal_link.status = ContactDealLink.Status.WON
                update_fields.append("status")
            if not _is_closed_won_state(status_value=deal_link.status, stage_value=deal_link.stage):
                deal_link.stage = "Closed Won"
                update_fields.append("stage")
            if deal_link.close_probability != 100:
                deal_link.close_probability = 100
                update_fields.append("close_probability")
            if update_fields:
                deal_link.save(update_fields=update_fields)

        _trigger_closed_won_automations(
            deal=deal_link,
            request=request,
            actor=request.user,
        )

        # Finalize reservation
        reservation.converted_customer = customer
        reservation.status = UnitReservation.Status.CONVERTED
        reservation.save()

        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.CUSTOMER_CREATED,
            performed_by=request.user,
            metadata={"customer_id": customer.id, "customer_name": customer.name},
        )
        unit = reservation.unit

        return Response({
            "reservation_id": reservation.id,
            "reservation_number": reservation.reservation_number,
            "customer_id": customer.id,
            "customer_name": customer.name,
            "message": "Reservation successfully converted.",
        })

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel reservation and release unit back to AVAILABLE."""
        reservation = self.get_object()
        if reservation.is_terminal:
            return Response(
                {"error": "Reservation is already in a terminal state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Release unit
        reservation.unit.status = "available"
        reservation.unit.save(update_fields=["status", "updated_at"])

        # Void pending payment plan
        if reservation.payment_plan:
            reservation.payment_plan.status = "cancelled"
            reservation.payment_plan.save(update_fields=["status", "updated_at"])

        reservation.status = UnitReservation.Status.CANCELLED
        reservation.cancelled_reason = serializer.validated_data["reason"]
        reservation.save(update_fields=[
            "status", "cancelled_reason", "updated_at",
        ])

        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.CANCELLED,
            performed_by=request.user,
            notes=serializer.validated_data["reason"],
        )

        # Notify sales owner of cancellation
        if reservation.lead_id and reservation.lead.assigned_to_id:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            org = reservation.organization if hasattr(reservation, "organization") else None
            if not org and reservation.lead_id:
                org = getattr(reservation.lead, "organization", None)
            if org:
                dispatch_workflow_notification(
                    organization=org,
                    event_key="crm_reservation_cancelled",
                    recipients=[reservation.lead.assigned_to],
                    context={
                        "reservation_number": reservation.reservation_number,
                        "unit_number": str(reservation.unit) if reservation.unit_id else "",
                        "reason": serializer.validated_data["reason"],
                        "action_url": f"/crm/reservations/{reservation.id}",
                    },
                    link_url=f"/crm/reservations/{reservation.id}",
                    fallback_channels=["in_app"],
                    fallback_title=f"Reservation Cancelled — {reservation.reservation_number}",
                    fallback_message=(
                        f"Reservation {reservation.reservation_number}"
                        f"{f' for unit {reservation.unit}' if reservation.unit_id else ''}"
                        f" has been cancelled. "
                        f"Reason: {serializer.validated_data['reason']}. "
                        f"The associated unit has been released back to inventory."
                    ),
                    fallback_category=Notification.Category.CRM_RESERVATION,
                    fallback_severity=Notification.Severity.WARNING,
                )

        return Response(UnitReservationDetailSerializer(reservation).data)

    @action(detail=True, methods=["post"])
    def extend_hold(self, request, pk=None):
        """Extend the hold expiration."""
        reservation = self.get_object()
        if reservation.status != UnitReservation.Status.HOLD:
            return Response(
                {"error": "Only HOLD reservations can have their hold extended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ReservationExtendHoldSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hours = serializer.validated_data["extend_hours"]
        old_expiry = reservation.hold_expires_at
        reservation.hold_expires_at += timezone.timedelta(hours=hours)
        reservation.save(update_fields=["hold_expires_at", "updated_at"])

        ReservationEvent.objects.create(
            reservation=reservation,
            event_type=ReservationEvent.EventType.HOLD_EXTENDED,
            performed_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
            metadata={
                "extended_by_hours": hours,
                "old_expiry": str(old_expiry),
                "new_expiry": str(reservation.hold_expires_at),
            },
        )

        return Response(UnitReservationDetailSerializer(reservation).data)


# ---------------------------------------------------------------------------
# Reservation Overview (dashboard)
# ---------------------------------------------------------------------------


class ReservationOverviewView(APIView):
    """Dashboard-level reservation metrics."""
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "crm.all"
    rbac_action = "view"

    def get(self, request):
        cache_key = _crm_overview_cache_key(request, "reservations")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        qs = _scope_queryset_for_request(
            request,
            UnitReservation.objects.all(),
            org_field="organization_id",
        )

        payload = {
            "active_holds": qs.filter(status="hold").count(),
            "pending_payments": qs.filter(status="payment_pending").count(),
            "paid": qs.filter(status="paid").count(),
            "converted": qs.filter(status="converted").count(),
            "expired": qs.filter(status="expired").count(),
            "cancelled": qs.filter(status="cancelled").count(),
            "total_converted_value": qs.filter(
                status="converted"
            ).aggregate(total=Sum("total_price"))["total"] or 0,
        }
        cache.set(cache_key, payload, timeout=CRM_OVERVIEW_CACHE_TTL_SECONDS)
        return Response(payload)

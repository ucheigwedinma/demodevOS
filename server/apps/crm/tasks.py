import logging
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.accounts.rls import iter_organization_ids, rls_context
from apps.notifications.models import Notification
from apps.notifications.services import dispatch_workflow_notification

from .analytics import compute_crm_analytics_snapshot
from .models import FollowUpRule, FollowUpTask, Lead, LeadActivity, UnitReservation

logger = logging.getLogger(__name__)

MISSED_ACTIVITY_ESCALATION_RULE_NAME = "Missed Activity Escalation"
PIPELINE_DROP_ALERT_THRESHOLD_PCT = 20.0
PIPELINE_DROP_ALERT_COOLDOWN_SECONDS = 12 * 60 * 60
MANAGEMENT_JOB_TITLE_HINTS = ("manager", "head", "director", "chief", "vp")
PAYMENT_REMINDER_LOOKAHEAD_DAYS = 2
PAYMENT_REMINDER_RECENT_HOURS = 20
PROJECT_DEMAND_DEFAULT_WINDOW_DAYS = 90
PROJECT_DEMAND_HIGH_THRESHOLD_PCT = 25.0
PROJECT_DEMAND_MIN_LEADS = 5
PROJECT_DEMAND_TOP_AREAS = 12
PROJECT_DEMAND_ALERT_COOLDOWN_SECONDS = 24 * 60 * 60
PROCUREMENT_DEMAND_DEFAULT_WINDOW_DAYS = 90
PROCUREMENT_DEMAND_BULK_THRESHOLD_PCT = 20.0
PROCUREMENT_DEMAND_MIN_LEADS = 5
PROCUREMENT_DEMAND_MIN_BULK_LEADS = 3
PROCUREMENT_DEMAND_TOP_AREAS = 12
PROCUREMENT_DEMAND_ALERT_COOLDOWN_SECONDS = 24 * 60 * 60
PROJECT_PLANNING_JOB_TITLE_HINTS = (
    "project",
    "planning",
    "development",
    "construction",
    "estate",
)
PROCUREMENT_TEAM_JOB_TITLE_HINTS = (
    "procurement",
    "supply",
    "operations",
    "furnishing",
    "commercial",
)


def _active_profiles_for_org(organization_id: int):
    return UserProfile.objects.select_related("user", "reporting_manager").filter(
        organization_id=organization_id,
        user_status=UserProfile.UserStatus.ACTIVE,
        user__is_active=True,
    )


def _manager_recipients_for_activity(activity: LeadActivity) -> list:
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

    profiles = _active_profiles_for_org(activity.lead.organization_id)

    if activity.lead.assigned_to_id:
        assigned_profile = profiles.filter(user_id=activity.lead.assigned_to_id).first()
        if assigned_profile and assigned_profile.reporting_manager_id:
            add_user(assigned_profile.reporting_manager)

    if activity.performed_by_id:
        performer_profile = profiles.filter(user_id=activity.performed_by_id).first()
        if performer_profile and performer_profile.reporting_manager_id:
            add_user(performer_profile.reporting_manager)

    for profile in profiles.filter(role="admin").order_by("user_id"):
        add_user(profile.user)

    return recipients


def _missed_activity_rule_for_org(organization_id: int):
    rule, _created = FollowUpRule.objects.get_or_create(
        organization_id=organization_id,
        name=MISSED_ACTIVITY_ESCALATION_RULE_NAME,
        defaults={
            "description": "Escalation rule for missed scheduled CRM activities.",
            "trigger_stage": Lead.PipelineStage.INQUIRY,
            "follow_up_within_hours": 1,
            "required_activity_type": LeadActivity.ActivityType.FOLLOW_UP,
            "auto_assign_to_owner": False,
            "is_active": True,
        },
    )
    if not rule.is_active:
        rule.is_active = True
        rule.save(update_fields=["is_active", "updated_at"])
    return rule


def _process_missed_activities_for_org(*, organization_id: int, now):
    grace_cutoff = now - timedelta(minutes=15)
    activities = (
        LeadActivity.objects.filter(
            lead__organization_id=organization_id,
            is_completed=False,
            scheduled_at__isnull=False,
            scheduled_at__lte=grace_cutoff,
        )
        .exclude(activity_type=LeadActivity.ActivityType.NOTE)
        .select_related("lead", "performed_by")
        .order_by("scheduled_at")
    )

    if not activities.exists():
        return {"escalated": 0, "notified": 0}

    escalation_rule = _missed_activity_rule_for_org(organization_id)
    escalated = 0
    notified = 0

    for activity in activities:
        recipients = _manager_recipients_for_activity(activity)
        if not recipients:
            continue

        link_url = f"/crm/activities-tasks?activity_id={activity.id}"
        already_notified_ids = set(
            Notification.objects.filter(
                recipient_id__in=[recipient.id for recipient in recipients],
                category=Notification.Category.CRM_LEAD,
                link_url=link_url,
            ).values_list("recipient_id", flat=True)
        )
        pending_recipients = [recipient for recipient in recipients if recipient.id not in already_notified_ids]

        if pending_recipients:
            scheduled_label = activity.scheduled_at.strftime("%b %d, %Y %I:%M %p")
            dispatch_result = dispatch_workflow_notification(
                organization=activity.lead.organization,
                event_key="crm_activity_missed_escalated",
                recipients=pending_recipients,
                context={
                    "lead_name": activity.lead.full_name,
                    "activity_subject": activity.subject,
                    "scheduled_at": scheduled_label,
                    "action_url": link_url,
                },
                link_url=link_url,
                fallback_channels=["in_app", "email"],
                fallback_title=f"Missed CRM activity: {activity.lead.full_name}",
                fallback_message=(
                    f"{activity.subject} for {activity.lead.full_name} was missed "
                    f"(scheduled {scheduled_label}). Manager escalation required."
                ),
                fallback_category=Notification.Category.CRM_LEAD,
                fallback_severity=Notification.Severity.WARNING,
            )
            notified += dispatch_result["notifications_sent"] + dispatch_result["emails_sent"]

        marker = f"[missed-activity:{activity.id}]"
        has_escalation_task = FollowUpTask.objects.filter(
            rule=escalation_rule,
            lead=activity.lead,
            notes__icontains=marker,
        ).exclude(status=FollowUpTask.Status.CANCELLED).exists()
        if not has_escalation_task:
            assignee = recipients[0] if recipients else activity.lead.assigned_to
            FollowUpTask.objects.create(
                rule=escalation_rule,
                lead=activity.lead,
                assigned_to=assignee,
                status=FollowUpTask.Status.ESCALATED,
                due_at=activity.scheduled_at or now,
                escalated_at=now,
                notes=(
                    f"{marker} Missed activity escalation for '{activity.subject}' "
                    f"(scheduled {activity.scheduled_at})."
                ),
            )
            escalated += 1

    return {"escalated": escalated, "notified": notified}


def _process_due_soon_task_reminders_for_org(*, organization_id: int, now):
    reminder_window_end = now + timedelta(minutes=60)
    reminder_recent_cutoff = now - timedelta(minutes=59)

    due_tasks = FollowUpTask.objects.filter(
        rule__organization_id=organization_id,
        status__in=[FollowUpTask.Status.PENDING, FollowUpTask.Status.IN_PROGRESS],
        assigned_to__isnull=False,
        due_at__gte=now,
        due_at__lt=reminder_window_end,
    ).select_related("lead", "assigned_to", "rule")

    reminder_notifications = 0
    for task in due_tasks:
        link_url = f"/crm/activities-tasks?task_id={task.id}"
        already_notified = Notification.objects.filter(
            recipient_id=task.assigned_to_id,
            category=Notification.Category.CRM_LEAD,
            link_url=link_url,
            created_at__gte=reminder_recent_cutoff,
        ).exists()
        if already_notified:
            continue

        due_label = task.due_at.strftime("%b %d, %Y %I:%M %p")
        dispatch_result = dispatch_workflow_notification(
            organization=task.lead.organization,
            event_key="crm_activity_due_reminder",
            recipients=[task.assigned_to],
            context={
                "lead_name": task.lead.full_name,
                "rule_name": task.rule.name,
                "due_at": due_label,
                "action_url": link_url,
            },
            link_url=link_url,
            fallback_channels=["in_app"],
            fallback_title=f"CRM task due soon: {task.lead.full_name}",
            fallback_message=(
                f"{task.rule.name} for {task.lead.full_name} is due at {due_label}."
            ),
            fallback_category=Notification.Category.CRM_LEAD,
            fallback_severity=Notification.Severity.INFO,
        )
        reminder_notifications += dispatch_result["notifications_sent"] + dispatch_result["emails_sent"]

    return reminder_notifications


@shared_task(name="crm.check_missed_activities")
def check_missed_activities():
    """Periodic sweep: escalate missed CRM activities and remind due-soon assignees."""
    now = timezone.now()
    orgs_processed = 0
    escalated = 0
    notifications_sent = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                missed_summary = _process_missed_activities_for_org(
                    organization_id=organization_id,
                    now=now,
                )
                escalated += missed_summary["escalated"]
                notifications_sent += missed_summary["notified"]
                notifications_sent += _process_due_soon_task_reminders_for_org(
                    organization_id=organization_id,
                    now=now,
                )
            orgs_processed += 1
        except Exception:
            errors += 1
            logger.exception(
                "crm.check_missed_activities.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        "crm.check_missed_activities.complete orgs_processed=%s escalated=%s notifications=%s errors=%s",
        orgs_processed,
        escalated,
        notifications_sent,
        errors,
    )
    return {
        "orgs_processed": orgs_processed,
        "escalated": escalated,
        "notifications_sent": notifications_sent,
        "errors": errors,
    }


def _management_recipients_for_org(organization_id: int) -> list:
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

    profiles = _active_profiles_for_org(organization_id)
    management_filter = Q(role="admin")
    for hint in MANAGEMENT_JOB_TITLE_HINTS:
        management_filter |= Q(job_title__icontains=hint)

    for profile in profiles.filter(management_filter).order_by("user_id"):
        add_user(profile.user)

    if recipients:
        return recipients

    for profile in profiles.filter(role="admin").order_by("user_id"):
        add_user(profile.user)
    return recipients


def _normalize_location_token(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _display_location_label(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _location_labels_from_value(value) -> dict[str, str]:
    labels: dict[str, str] = {}
    if isinstance(value, str):
        raw_tokens = [token.strip() for token in value.split(",") if token.strip()]
    elif isinstance(value, (list, tuple, set)):
        raw_tokens = [str(token).strip() for token in value if str(token).strip()]
    else:
        raw_tokens = []

    for token in raw_tokens:
        normalized = _normalize_location_token(token)
        if not normalized:
            continue
        labels.setdefault(normalized, _display_location_label(token))
    return labels


def _lead_demand_locations(lead: Lead) -> dict[str, str]:
    locations: dict[str, str] = {}

    for normalized, label in _location_labels_from_value(getattr(lead, "preferred_locations", None)).items():
        locations.setdefault(normalized, label)

    for interest in lead.project_interests.all():
        project = getattr(interest, "project", None)
        if not project:
            continue
        for value in (
            getattr(project, "location", ""),
            getattr(getattr(project, "property", None), "address", ""),
        ):
            for normalized, label in _location_labels_from_value(value).items():
                locations.setdefault(normalized, label)

    return locations


def _project_planning_recipients_for_org(organization_id: int) -> list:
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

    profiles = _active_profiles_for_org(organization_id)
    planning_filter = Q(role="admin")
    for hint in PROJECT_PLANNING_JOB_TITLE_HINTS:
        planning_filter |= Q(job_title__icontains=hint)

    for profile in profiles.filter(planning_filter).order_by("user_id"):
        add_user(profile.user)

    if recipients:
        return recipients

    for user_obj in _management_recipients_for_org(organization_id):
        add_user(user_obj)
    return recipients


def _procurement_recipients_for_org(organization_id: int) -> list:
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

    profiles = _active_profiles_for_org(organization_id)
    procurement_filter = Q(role="admin")
    for hint in PROCUREMENT_TEAM_JOB_TITLE_HINTS:
        procurement_filter |= Q(job_title__icontains=hint)

    for profile in profiles.filter(procurement_filter).order_by("user_id"):
        add_user(profile.user)

    if recipients:
        return recipients

    for user_obj in _management_recipients_for_org(organization_id):
        add_user(user_obj)
    return recipients


def _is_bulk_buyer_lead(lead: Lead) -> bool:
    if lead.lead_type == Lead.LeadType.INVESTOR:
        return True

    tags = getattr(lead, "tags", None) or []
    for tag in tags:
        token = _normalize_location_token(str(tag))
        if not token:
            continue
        if "bulk buyer" in token or token.startswith("bulk ") or "institutional" in token:
            return True
    return False


def sync_crm_project_demand_insights_for_org(
    *,
    organization_id: int,
    now=None,
    window_days: int = PROJECT_DEMAND_DEFAULT_WINDOW_DAYS,
    threshold_percent: float = PROJECT_DEMAND_HIGH_THRESHOLD_PCT,
    min_leads: int = PROJECT_DEMAND_MIN_LEADS,
    top_areas: int = PROJECT_DEMAND_TOP_AREAS,
    force: bool = False,
) -> dict:
    from apps.accounts.models import Organization
    from apps.projects.models import ProjectPlanningInsight

    now = now or timezone.now()
    window_days = min(max(int(window_days or PROJECT_DEMAND_DEFAULT_WINDOW_DAYS), 30), 365)
    min_leads = min(max(int(min_leads or PROJECT_DEMAND_MIN_LEADS), 1), 500)
    top_areas = min(max(int(top_areas or PROJECT_DEMAND_TOP_AREAS), 1), 50)
    threshold_percent = max(1.0, min(float(threshold_percent or PROJECT_DEMAND_HIGH_THRESHOLD_PCT), 100.0))

    organization = Organization.objects.filter(id=organization_id).first()
    if organization is None:
        return {
            "organization_id": organization_id,
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 1),
            "areas_evaluated": 0,
            "insights_upserted": 0,
            "high_demand_triggered": 0,
            "high_demand_areas": [],
            "notifications_sent": 0,
            "emails_sent": 0,
            "skipped": True,
            "reason": "organization_missing",
        }

    cutoff_dt = now - timedelta(days=window_days)
    cutoff_date = cutoff_dt.date()
    qualified_stages = {
        Lead.PipelineStage.QUALIFIED,
        Lead.PipelineStage.SITE_VISIT,
        Lead.PipelineStage.OFFER_MADE,
        Lead.PipelineStage.RESERVATION,
        Lead.PipelineStage.SPA_ISSUED,
        Lead.PipelineStage.CLOSED,
    }

    leads = (
        Lead.objects.filter(
            organization_id=organization_id,
            is_archived=False,
            status__in=[Lead.Status.ACTIVE, Lead.Status.WON],
        )
        .filter(
            Q(created_at__gte=cutoff_dt)
            | Q(updated_at__gte=cutoff_dt)
            | Q(inquiry_date__gte=cutoff_date)
            | Q(closed_date__gte=cutoff_date)
        )
        .prefetch_related("project_interests__project__property")
    )

    demand_map: dict[str, dict] = defaultdict(
        lambda: {
            "area_name": "",
            "lead_ids": set(),
            "qualified_lead_count": 0,
            "won_lead_count": 0,
        }
    )
    for lead in leads:
        area_labels = _lead_demand_locations(lead)
        if not area_labels:
            continue

        is_qualified_or_beyond = (
            lead.pipeline_stage in qualified_stages or lead.status == Lead.Status.WON
        )
        is_won = lead.status == Lead.Status.WON

        for normalized_area, area_label in area_labels.items():
            row = demand_map[normalized_area]
            if not row["area_name"]:
                row["area_name"] = area_label

            if lead.id in row["lead_ids"]:
                continue
            row["lead_ids"].add(lead.id)

            if is_qualified_or_beyond:
                row["qualified_lead_count"] += 1
            if is_won:
                row["won_lead_count"] += 1

    rows = []
    for row in demand_map.values():
        lead_count = len(row["lead_ids"])
        if lead_count <= 0:
            continue
        rows.append(
            {
                "area_name": row["area_name"] or "Unspecified",
                "lead_count": lead_count,
                "qualified_lead_count": int(row["qualified_lead_count"]),
                "won_lead_count": int(row["won_lead_count"]),
            }
        )

    rows.sort(
        key=lambda item: (
            -int(item["lead_count"]),
            -int(item["qualified_lead_count"]),
            -int(item["won_lead_count"]),
            str(item["area_name"]).lower(),
        )
    )

    if not rows:
        ProjectPlanningInsight.objects.filter(
            organization=organization,
            source_module=ProjectPlanningInsight.SourceModule.CRM,
        ).update(is_active=False, last_triggered_at=now, updated_at=now)
        return {
            "organization_id": organization_id,
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 1),
            "areas_evaluated": 0,
            "insights_upserted": 0,
            "high_demand_triggered": 0,
            "high_demand_areas": [],
            "notifications_sent": 0,
            "emails_sent": 0,
            "skipped": True,
            "reason": "no_demand_locations",
        }

    total_signals = sum(int(row["lead_count"]) for row in rows)
    top_rows = rows[:top_areas]
    active_demand_areas = []
    triggered_high_areas = []
    upserted_count = 0

    for row in top_rows:
        area_name = str(row["area_name"]).strip() or "Unspecified"
        share_percent = round((int(row["lead_count"]) / total_signals) * 100, 2)
        active_demand_areas.append(area_name)

        demand_defaults = {
            "source_module": ProjectPlanningInsight.SourceModule.CRM,
            "title": f"Demand signal: {area_name}",
            "summary": (
                f"{row['lead_count']} leads showed demand for {area_name} "
                f"in the last {window_days} days ({share_percent}%)."
            ),
            "demand_share_percent": share_percent,
            "lead_count": int(row["lead_count"]),
            "qualified_lead_count": int(row["qualified_lead_count"]),
            "won_lead_count": int(row["won_lead_count"]),
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 2),
            "is_active": True,
            "metadata": {
                "source": "crm.analytics",
                "min_leads_threshold": min_leads,
                "total_signals": total_signals,
            },
            "last_triggered_at": now,
        }
        insight, created = ProjectPlanningInsight.objects.update_or_create(
            organization=organization,
            insight_type=ProjectPlanningInsight.InsightType.DEMAND_ANALYTICS,
            area_name=area_name,
            defaults=demand_defaults,
        )
        if created and not insight.first_triggered_at:
            insight.first_triggered_at = now
            insight.save(update_fields=["first_triggered_at", "updated_at"])
        upserted_count += 1

        if share_percent < threshold_percent or int(row["lead_count"]) < min_leads:
            continue

        triggered_high_areas.append(
            {
                "area_name": area_name,
                "lead_count": int(row["lead_count"]),
                "share_percent": share_percent,
            }
        )
        high_defaults = {
            "source_module": ProjectPlanningInsight.SourceModule.CRM,
            "title": f"High-demand development insight: {area_name}",
            "summary": (
                f"{area_name} crossed the {threshold_percent}% demand threshold "
                f"({share_percent}% from {row['lead_count']} leads). Trigger project planning review."
            ),
            "demand_share_percent": share_percent,
            "lead_count": int(row["lead_count"]),
            "qualified_lead_count": int(row["qualified_lead_count"]),
            "won_lead_count": int(row["won_lead_count"]),
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 2),
            "is_active": True,
            "metadata": {
                "source": "crm.analytics",
                "min_leads_threshold": min_leads,
                "trigger_type": "high_demand_area",
            },
            "last_triggered_at": now,
        }
        high_insight, created = ProjectPlanningInsight.objects.update_or_create(
            organization=organization,
            insight_type=ProjectPlanningInsight.InsightType.NEW_DEVELOPMENT,
            area_name=area_name,
            defaults=high_defaults,
        )
        if created and not high_insight.first_triggered_at:
            high_insight.first_triggered_at = now
            high_insight.save(update_fields=["first_triggered_at", "updated_at"])
        upserted_count += 1

    ProjectPlanningInsight.objects.filter(
        organization=organization,
        source_module=ProjectPlanningInsight.SourceModule.CRM,
        insight_type=ProjectPlanningInsight.InsightType.DEMAND_ANALYTICS,
    ).exclude(area_name__in=active_demand_areas).update(
        is_active=False,
        last_triggered_at=now,
        updated_at=now,
    )
    ProjectPlanningInsight.objects.filter(
        organization=organization,
        source_module=ProjectPlanningInsight.SourceModule.CRM,
        insight_type=ProjectPlanningInsight.InsightType.NEW_DEVELOPMENT,
    ).exclude(area_name__in=[item["area_name"] for item in triggered_high_areas]).update(
        is_active=False,
        last_triggered_at=now,
        updated_at=now,
    )

    notifications_sent = 0
    emails_sent = 0
    if triggered_high_areas:
        recipients = _project_planning_recipients_for_org(organization_id)
        notifiable_areas = []
        for area in triggered_high_areas:
            cooldown_key = (
                "crm:projects:high-demand:"
                f"org:{organization_id}:area:{_normalize_location_token(area['area_name'])}"
            )
            if not force and cache.get(cooldown_key):
                continue
            cache.set(cooldown_key, now.isoformat(), timeout=PROJECT_DEMAND_ALERT_COOLDOWN_SECONDS)
            notifiable_areas.append(area)

        if recipients and notifiable_areas:
            area_snippets = ", ".join(
                f"{item['area_name']} ({item['share_percent']}%)"
                for item in notifiable_areas[:5]
            )
            if len(notifiable_areas) > 5:
                area_snippets = f"{area_snippets}, +{len(notifiable_areas) - 5} more"
            link_url = "/crm/analytics-reporting"
            dispatch_result = dispatch_workflow_notification(
                organization=organization,
                event_key="crm_projects_high_demand_insight",
                recipients=recipients,
                context={
                    "area_count": len(notifiable_areas),
                    "areas_summary": area_snippets,
                    "window_days": window_days,
                    "threshold_percent": round(threshold_percent, 1),
                    "action_url": link_url,
                },
                link_url=link_url,
                fallback_channels=["in_app", "email"],
                fallback_title="CRM high-demand project insight",
                fallback_message=(
                    f"High demand areas detected: {area_snippets}. "
                    "Review project planning recommendations."
                ),
                fallback_category=Notification.Category.REPORTS_READY,
                fallback_severity=Notification.Severity.WARNING,
            )
            notifications_sent += int(dispatch_result.get("notifications_sent", 0))
            emails_sent += int(dispatch_result.get("emails_sent", 0))

    return {
        "organization_id": organization_id,
        "window_days": window_days,
        "threshold_percent": round(threshold_percent, 1),
        "areas_evaluated": len(rows),
        "insights_upserted": upserted_count,
        "high_demand_triggered": len(triggered_high_areas),
        "high_demand_areas": [item["area_name"] for item in triggered_high_areas],
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "skipped": False,
        "reason": "",
    }


def sync_crm_procurement_demand_insights_for_org(
    *,
    organization_id: int,
    now=None,
    window_days: int = PROCUREMENT_DEMAND_DEFAULT_WINDOW_DAYS,
    threshold_percent: float = PROCUREMENT_DEMAND_BULK_THRESHOLD_PCT,
    min_leads: int = PROCUREMENT_DEMAND_MIN_LEADS,
    min_bulk_leads: int = PROCUREMENT_DEMAND_MIN_BULK_LEADS,
    top_areas: int = PROCUREMENT_DEMAND_TOP_AREAS,
    force: bool = False,
) -> dict:
    from apps.accounts.models import Organization
    from apps.procurement.models import ProcurementDemandInsight

    now = now or timezone.now()
    window_days = min(max(int(window_days or PROCUREMENT_DEMAND_DEFAULT_WINDOW_DAYS), 30), 365)
    min_leads = min(max(int(min_leads or PROCUREMENT_DEMAND_MIN_LEADS), 1), 500)
    min_bulk_leads = min(max(int(min_bulk_leads or PROCUREMENT_DEMAND_MIN_BULK_LEADS), 1), 500)
    top_areas = min(max(int(top_areas or PROCUREMENT_DEMAND_TOP_AREAS), 1), 50)
    threshold_percent = max(1.0, min(float(threshold_percent or PROCUREMENT_DEMAND_BULK_THRESHOLD_PCT), 100.0))

    organization = Organization.objects.filter(id=organization_id).first()
    if organization is None:
        return {
            "organization_id": organization_id,
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 1),
            "areas_evaluated": 0,
            "insights_upserted": 0,
            "package_triggers": 0,
            "triggered_areas": [],
            "notifications_sent": 0,
            "emails_sent": 0,
            "skipped": True,
            "reason": "organization_missing",
        }

    cutoff_dt = now - timedelta(days=window_days)
    cutoff_date = cutoff_dt.date()
    qualified_stages = {
        Lead.PipelineStage.QUALIFIED,
        Lead.PipelineStage.SITE_VISIT,
        Lead.PipelineStage.OFFER_MADE,
        Lead.PipelineStage.RESERVATION,
        Lead.PipelineStage.SPA_ISSUED,
        Lead.PipelineStage.CLOSED,
    }

    leads = (
        Lead.objects.filter(
            organization_id=organization_id,
            is_archived=False,
            status__in=[Lead.Status.ACTIVE, Lead.Status.WON],
        )
        .filter(
            Q(created_at__gte=cutoff_dt)
            | Q(updated_at__gte=cutoff_dt)
            | Q(inquiry_date__gte=cutoff_date)
            | Q(closed_date__gte=cutoff_date)
        )
        .prefetch_related("project_interests__project__property")
    )

    demand_map: dict[str, dict] = defaultdict(
        lambda: {
            "area_name": "",
            "lead_ids": set(),
            "qualified_lead_count": 0,
            "won_lead_count": 0,
            "bulk_buyer_lead_count": 0,
        }
    )
    for lead in leads:
        area_labels = _lead_demand_locations(lead)
        if not area_labels:
            continue

        is_qualified_or_beyond = lead.pipeline_stage in qualified_stages or lead.status == Lead.Status.WON
        is_won = lead.status == Lead.Status.WON
        is_bulk_buyer = _is_bulk_buyer_lead(lead)

        for normalized_area, area_label in area_labels.items():
            row = demand_map[normalized_area]
            if not row["area_name"]:
                row["area_name"] = area_label
            if lead.id in row["lead_ids"]:
                continue
            row["lead_ids"].add(lead.id)
            if is_qualified_or_beyond:
                row["qualified_lead_count"] += 1
            if is_won:
                row["won_lead_count"] += 1
            if is_bulk_buyer:
                row["bulk_buyer_lead_count"] += 1

    rows = []
    for row in demand_map.values():
        lead_count = len(row["lead_ids"])
        if lead_count <= 0:
            continue
        rows.append(
            {
                "area_name": row["area_name"] or "Unspecified",
                "lead_count": lead_count,
                "qualified_lead_count": int(row["qualified_lead_count"]),
                "won_lead_count": int(row["won_lead_count"]),
                "bulk_buyer_lead_count": int(row["bulk_buyer_lead_count"]),
            }
        )

    rows.sort(
        key=lambda item: (
            -int(item["lead_count"]),
            -int(item["bulk_buyer_lead_count"]),
            -int(item["qualified_lead_count"]),
            str(item["area_name"]).lower(),
        )
    )

    if not rows:
        ProcurementDemandInsight.objects.filter(
            organization=organization,
            source_module=ProcurementDemandInsight.SourceModule.CRM,
        ).update(is_active=False, last_triggered_at=now, updated_at=now)
        return {
            "organization_id": organization_id,
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 1),
            "areas_evaluated": 0,
            "insights_upserted": 0,
            "package_triggers": 0,
            "triggered_areas": [],
            "notifications_sent": 0,
            "emails_sent": 0,
            "skipped": True,
            "reason": "no_demand_locations",
        }

    total_signals = sum(int(row["lead_count"]) for row in rows)
    top_rows = rows[:top_areas]
    active_bulk_areas = []
    triggered_package_areas = []
    upserted_count = 0

    for row in top_rows:
        area_name = str(row["area_name"]).strip() or "Unspecified"
        share_percent = round((int(row["lead_count"]) / total_signals) * 100, 2)
        bulk_share_percent = round(
            (int(row["bulk_buyer_lead_count"]) / int(row["lead_count"])) * 100,
            2,
        )
        active_bulk_areas.append(area_name)

        bulk_defaults = {
            "source_module": ProcurementDemandInsight.SourceModule.CRM,
            "title": f"Bulk buyer demand signal: {area_name}",
            "summary": (
                f"{row['bulk_buyer_lead_count']} bulk-buyer leads were detected in {area_name} "
                f"({bulk_share_percent}% of {row['lead_count']} leads) within {window_days} days."
            ),
            "demand_share_percent": share_percent,
            "lead_count": int(row["lead_count"]),
            "qualified_lead_count": int(row["qualified_lead_count"]),
            "won_lead_count": int(row["won_lead_count"]),
            "bulk_buyer_lead_count": int(row["bulk_buyer_lead_count"]),
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 2),
            "min_bulk_leads": min_bulk_leads,
            "is_active": True,
            "metadata": {
                "source": "crm.analytics",
                "total_signals": total_signals,
                "bulk_share_percent": bulk_share_percent,
                "min_leads_threshold": min_leads,
                "min_bulk_leads_threshold": min_bulk_leads,
            },
            "last_triggered_at": now,
        }
        insight, created = ProcurementDemandInsight.objects.update_or_create(
            organization=organization,
            insight_type=ProcurementDemandInsight.InsightType.BULK_BUYER_DEMAND,
            area_name=area_name,
            defaults=bulk_defaults,
        )
        if created and not insight.first_triggered_at:
            insight.first_triggered_at = now
            insight.save(update_fields=["first_triggered_at", "updated_at"])
        upserted_count += 1

        should_trigger_packages = (
            int(row["lead_count"]) >= min_leads
            and int(row["bulk_buyer_lead_count"]) >= min_bulk_leads
            and bulk_share_percent >= threshold_percent
        )
        if not should_trigger_packages:
            continue

        triggered_package_areas.append(
            {
                "area_name": area_name,
                "lead_count": int(row["lead_count"]),
                "bulk_buyer_lead_count": int(row["bulk_buyer_lead_count"]),
                "bulk_share_percent": bulk_share_percent,
                "demand_share_percent": share_percent,
            }
        )

        package_defaults = {
            "source_module": ProcurementDemandInsight.SourceModule.CRM,
            "demand_share_percent": share_percent,
            "lead_count": int(row["lead_count"]),
            "qualified_lead_count": int(row["qualified_lead_count"]),
            "won_lead_count": int(row["won_lead_count"]),
            "bulk_buyer_lead_count": int(row["bulk_buyer_lead_count"]),
            "window_days": window_days,
            "threshold_percent": round(threshold_percent, 2),
            "min_bulk_leads": min_bulk_leads,
            "is_active": True,
            "metadata": {
                "source": "crm.analytics",
                "trigger_type": "bulk_buyer_demand",
                "bulk_share_percent": bulk_share_percent,
                "min_leads_threshold": min_leads,
                "min_bulk_leads_threshold": min_bulk_leads,
            },
            "last_triggered_at": now,
        }

        for insight_type, title, summary in [
            (
                ProcurementDemandInsight.InsightType.FURNISHING_PACKAGE,
                f"Furnishing package trigger: {area_name}",
                (
                    f"Recommend furnishing packages in {area_name}. "
                    f"Bulk-buyer demand reached {bulk_share_percent}%."
                ),
            ),
            (
                ProcurementDemandInsight.InsightType.ADD_ON_PACKAGE,
                f"Add-on package trigger: {area_name}",
                (
                    f"Recommend add-on packages in {area_name}. "
                    f"Bulk-buyer demand reached {bulk_share_percent}%."
                ),
            ),
        ]:
            trigger_insight, trigger_created = ProcurementDemandInsight.objects.update_or_create(
                organization=organization,
                insight_type=insight_type,
                area_name=area_name,
                defaults={
                    **package_defaults,
                    "title": title,
                    "summary": summary,
                },
            )
            if trigger_created and not trigger_insight.first_triggered_at:
                trigger_insight.first_triggered_at = now
                trigger_insight.save(update_fields=["first_triggered_at", "updated_at"])
            upserted_count += 1

    ProcurementDemandInsight.objects.filter(
        organization=organization,
        source_module=ProcurementDemandInsight.SourceModule.CRM,
        insight_type=ProcurementDemandInsight.InsightType.BULK_BUYER_DEMAND,
    ).exclude(area_name__in=active_bulk_areas).update(
        is_active=False,
        last_triggered_at=now,
        updated_at=now,
    )
    ProcurementDemandInsight.objects.filter(
        organization=organization,
        source_module=ProcurementDemandInsight.SourceModule.CRM,
        insight_type__in=[
            ProcurementDemandInsight.InsightType.FURNISHING_PACKAGE,
            ProcurementDemandInsight.InsightType.ADD_ON_PACKAGE,
        ],
    ).exclude(
        area_name__in=[item["area_name"] for item in triggered_package_areas]
    ).update(
        is_active=False,
        last_triggered_at=now,
        updated_at=now,
    )

    notifications_sent = 0
    emails_sent = 0
    if triggered_package_areas:
        recipients = _procurement_recipients_for_org(organization_id)
        notifiable_areas = []
        for area in triggered_package_areas:
            cooldown_key = (
                "crm:procurement:bulk-demand:"
                f"org:{organization_id}:area:{_normalize_location_token(area['area_name'])}"
            )
            if not force and cache.get(cooldown_key):
                continue
            cache.set(cooldown_key, now.isoformat(), timeout=PROCUREMENT_DEMAND_ALERT_COOLDOWN_SECONDS)
            notifiable_areas.append(area)

        if recipients and notifiable_areas:
            area_snippets = ", ".join(
                f"{item['area_name']} ({item['bulk_share_percent']}% bulk)"
                for item in notifiable_areas[:5]
            )
            if len(notifiable_areas) > 5:
                area_snippets = f"{area_snippets}, +{len(notifiable_areas) - 5} more"
            link_url = "/crm/analytics-reporting"
            dispatch_result = dispatch_workflow_notification(
                organization=organization,
                event_key="crm_procurement_bulk_buyer_demand",
                recipients=recipients,
                context={
                    "area_count": len(notifiable_areas),
                    "areas_summary": area_snippets,
                    "window_days": window_days,
                    "threshold_percent": round(threshold_percent, 1),
                    "min_bulk_leads": min_bulk_leads,
                    "action_url": link_url,
                },
                link_url=link_url,
                fallback_channels=["in_app", "email"],
                fallback_title="CRM bulk-buyer procurement trigger",
                fallback_message=(
                    f"Bulk buyer demand crossed threshold in: {area_snippets}. "
                    "Review furnishing and add-on package recommendations."
                ),
                fallback_category=Notification.Category.REPORTS_READY,
                fallback_severity=Notification.Severity.WARNING,
            )
            notifications_sent += int(dispatch_result.get("notifications_sent", 0))
            emails_sent += int(dispatch_result.get("emails_sent", 0))

    return {
        "organization_id": organization_id,
        "window_days": window_days,
        "threshold_percent": round(threshold_percent, 1),
        "areas_evaluated": len(rows),
        "insights_upserted": upserted_count,
        "package_triggers": len(triggered_package_areas),
        "triggered_areas": [item["area_name"] for item in triggered_package_areas],
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "skipped": False,
        "reason": "",
    }


def send_weekly_crm_analytics_report_for_org(
    *,
    organization_id: int,
    now=None,
    window_days: int = 90,
) -> dict:
    from apps.accounts.models import Organization

    now = now or timezone.now()
    organization = Organization.objects.filter(id=organization_id).first()
    if organization is None:
        return {
            "organization_id": organization_id,
            "recipients": 0,
            "notifications_sent": 0,
            "emails_sent": 0,
            "skipped": True,
            "reason": "organization_missing",
        }

    recipients = _management_recipients_for_org(organization_id)
    if not recipients:
        return {
            "organization_id": organization_id,
            "recipients": 0,
            "notifications_sent": 0,
            "emails_sent": 0,
            "skipped": True,
            "reason": "no_management_recipients",
        }

    snapshot = compute_crm_analytics_snapshot(
        organization_id=organization_id,
        window_days=window_days,
        pipeline_drop_lookback_days=7,
    )
    summary = snapshot["summary"]
    pipeline_drop = snapshot["pipeline_drop_monitor"]
    report_date = now.strftime("%b %d, %Y")
    link_url = "/crm/analytics-reporting"

    summary_lines = [
        f"Weekly CRM analytics report ({report_date})",
        f"Conversion rate: {summary['conversion_rate']}%",
        f"Sales velocity: {summary['sales_velocity_days'] or 'n/a'} days to close",
        f"Revenue forecast (weighted): {summary['weighted_forecast']}",
        f"Pipeline drop monitor: {pipeline_drop['drop_percent']}%",
    ]

    dispatch_result = dispatch_workflow_notification(
        organization=organization,
        event_key="crm_weekly_analytics_report",
        recipients=recipients,
        context={
            "report_date": report_date,
            "conversion_rate": summary["conversion_rate"],
            "sales_velocity_days": summary["sales_velocity_days"] or "n/a",
            "weighted_forecast": summary["weighted_forecast"],
            "pipeline_drop_percent": pipeline_drop["drop_percent"],
            "action_url": link_url,
            "report_summary": "\n".join(summary_lines),
        },
        link_url=link_url,
        fallback_channels=["in_app", "email"],
        fallback_title=f"Weekly CRM Analytics Report - {report_date}",
        fallback_message="\n".join(summary_lines),
        fallback_category=Notification.Category.REPORTS_READY,
        fallback_severity=Notification.Severity.INFO,
    )
    return {
        "organization_id": organization_id,
        "recipients": len(recipients),
        "notifications_sent": dispatch_result["notifications_sent"],
        "emails_sent": dispatch_result["emails_sent"],
        "skipped": False,
        "reason": "",
    }


def check_pipeline_drop_for_org(
    *,
    organization_id: int,
    now=None,
    lookback_days: int = 7,
    force: bool = False,
) -> dict:
    from apps.accounts.models import Organization

    now = now or timezone.now()
    organization = Organization.objects.filter(id=organization_id).first()
    if organization is None:
        return {
            "organization_id": organization_id,
            "alert_triggered": False,
            "suppressed": True,
            "notifications_sent": 0,
            "emails_sent": 0,
            "reason": "organization_missing",
            "pipeline_drop": {},
        }

    snapshot = compute_crm_analytics_snapshot(
        organization_id=organization_id,
        window_days=90,
        pipeline_drop_lookback_days=lookback_days,
    )
    pipeline_drop = snapshot["pipeline_drop_monitor"]
    drop_percent = float(pipeline_drop.get("drop_percent", 0.0))
    is_alert = bool(pipeline_drop.get("is_alert")) and drop_percent >= PIPELINE_DROP_ALERT_THRESHOLD_PCT
    if not is_alert:
        return {
            "organization_id": organization_id,
            "alert_triggered": False,
            "suppressed": True,
            "notifications_sent": 0,
            "emails_sent": 0,
            "reason": "threshold_not_met",
            "pipeline_drop": pipeline_drop,
        }

    recipients = _management_recipients_for_org(organization_id)
    if not recipients:
        return {
            "organization_id": organization_id,
            "alert_triggered": False,
            "suppressed": True,
            "notifications_sent": 0,
            "emails_sent": 0,
            "reason": "no_management_recipients",
            "pipeline_drop": pipeline_drop,
        }

    period_key = str(pipeline_drop.get("current_period_start", now.isoformat()))[:10]
    cache_key = f"crm:pipeline-drop-alert:org:{organization_id}:period:{period_key}"
    if not force and cache.get(cache_key):
        return {
            "organization_id": organization_id,
            "alert_triggered": False,
            "suppressed": True,
            "notifications_sent": 0,
            "emails_sent": 0,
            "reason": "cooldown_active",
            "pipeline_drop": pipeline_drop,
        }

    link_url = "/crm/analytics-reporting"
    summary_line = (
        f"Pipeline additions dropped by {drop_percent}% "
        f"over the last {pipeline_drop.get('lookback_days')} days."
    )
    dispatch_result = dispatch_workflow_notification(
        organization=organization,
        event_key="crm_pipeline_drop_alert",
        recipients=recipients,
        context={
            "drop_percent": drop_percent,
            "lookback_days": pipeline_drop.get("lookback_days"),
            "current_additions_count": pipeline_drop.get("current_additions_count"),
            "previous_additions_count": pipeline_drop.get("previous_additions_count"),
            "action_url": link_url,
            "alert_summary": summary_line,
        },
        link_url=link_url,
        fallback_channels=["in_app", "email"],
        fallback_title="CRM Pipeline Drop Alert",
        fallback_message=summary_line,
        fallback_category=Notification.Category.CRM_LEAD,
        fallback_severity=Notification.Severity.WARNING,
    )
    cache.set(
        cache_key,
        now.isoformat(),
        timeout=PIPELINE_DROP_ALERT_COOLDOWN_SECONDS,
    )
    return {
        "organization_id": organization_id,
        "alert_triggered": True,
        "suppressed": False,
        "notifications_sent": dispatch_result["notifications_sent"],
        "emails_sent": dispatch_result["emails_sent"],
        "reason": "",
        "pipeline_drop": pipeline_drop,
    }


@shared_task(name="crm.send_weekly_analytics_report")
def send_weekly_analytics_report():
    """Send weekly CRM analytics report to management recipients per organization."""
    now = timezone.now()
    orgs_processed = 0
    notifications_sent = 0
    emails_sent = 0
    skipped = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                result = send_weekly_crm_analytics_report_for_org(
                    organization_id=organization_id,
                    now=now,
                )
            orgs_processed += 1
            notifications_sent += int(result.get("notifications_sent", 0))
            emails_sent += int(result.get("emails_sent", 0))
            if result.get("skipped"):
                skipped += 1
        except Exception:
            errors += 1
            logger.exception(
                "crm.send_weekly_analytics_report.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        "crm.send_weekly_analytics_report.complete orgs=%s notifications=%s emails=%s skipped=%s errors=%s",
        orgs_processed,
        notifications_sent,
        emails_sent,
        skipped,
        errors,
    )
    return {
        "orgs_processed": orgs_processed,
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "skipped": skipped,
        "errors": errors,
    }


@shared_task(name="crm.check_pipeline_drop")
def check_pipeline_drop():
    """Monitor CRM pipeline drops and trigger management alerts."""
    now = timezone.now()
    orgs_processed = 0
    alerts_triggered = 0
    notifications_sent = 0
    emails_sent = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                result = check_pipeline_drop_for_org(
                    organization_id=organization_id,
                    now=now,
                    lookback_days=7,
                    force=False,
                )
            orgs_processed += 1
            if result.get("alert_triggered"):
                alerts_triggered += 1
            notifications_sent += int(result.get("notifications_sent", 0))
            emails_sent += int(result.get("emails_sent", 0))
        except Exception:
            errors += 1
            logger.exception(
                "crm.check_pipeline_drop.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        "crm.check_pipeline_drop.complete orgs=%s alerts=%s notifications=%s emails=%s errors=%s",
        orgs_processed,
        alerts_triggered,
        notifications_sent,
        emails_sent,
        errors,
    )
    return {
        "orgs_processed": orgs_processed,
        "alerts_triggered": alerts_triggered,
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "errors": errors,
    }


@shared_task(name="crm.sync_project_demand_insights")
def sync_project_demand_insights():
    """Sync CRM demand analytics into projects planning insights for each organization."""
    now = timezone.now()
    orgs_processed = 0
    insights_upserted = 0
    high_demand_triggered = 0
    notifications_sent = 0
    emails_sent = 0
    skipped = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                result = sync_crm_project_demand_insights_for_org(
                    organization_id=organization_id,
                    now=now,
                    window_days=PROJECT_DEMAND_DEFAULT_WINDOW_DAYS,
                    threshold_percent=PROJECT_DEMAND_HIGH_THRESHOLD_PCT,
                    min_leads=PROJECT_DEMAND_MIN_LEADS,
                    top_areas=PROJECT_DEMAND_TOP_AREAS,
                    force=False,
                )
            orgs_processed += 1
            insights_upserted += int(result.get("insights_upserted", 0))
            high_demand_triggered += int(result.get("high_demand_triggered", 0))
            notifications_sent += int(result.get("notifications_sent", 0))
            emails_sent += int(result.get("emails_sent", 0))
            if result.get("skipped"):
                skipped += 1
        except Exception:
            errors += 1
            logger.exception(
                "crm.sync_project_demand_insights.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        (
            "crm.sync_project_demand_insights.complete orgs=%s insights_upserted=%s "
            "high_demand=%s notifications=%s emails=%s skipped=%s errors=%s"
        ),
        orgs_processed,
        insights_upserted,
        high_demand_triggered,
        notifications_sent,
        emails_sent,
        skipped,
        errors,
    )
    return {
        "orgs_processed": orgs_processed,
        "insights_upserted": insights_upserted,
        "high_demand_triggered": high_demand_triggered,
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "skipped": skipped,
        "errors": errors,
    }


@shared_task(name="crm.sync_procurement_demand_insights")
def sync_procurement_demand_insights():
    """Sync CRM bulk-buyer demand analytics into procurement package insights."""
    now = timezone.now()
    orgs_processed = 0
    insights_upserted = 0
    package_triggers = 0
    notifications_sent = 0
    emails_sent = 0
    skipped = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                result = sync_crm_procurement_demand_insights_for_org(
                    organization_id=organization_id,
                    now=now,
                    window_days=PROCUREMENT_DEMAND_DEFAULT_WINDOW_DAYS,
                    threshold_percent=PROCUREMENT_DEMAND_BULK_THRESHOLD_PCT,
                    min_leads=PROCUREMENT_DEMAND_MIN_LEADS,
                    min_bulk_leads=PROCUREMENT_DEMAND_MIN_BULK_LEADS,
                    top_areas=PROCUREMENT_DEMAND_TOP_AREAS,
                    force=False,
                )
            orgs_processed += 1
            insights_upserted += int(result.get("insights_upserted", 0))
            package_triggers += int(result.get("package_triggers", 0))
            notifications_sent += int(result.get("notifications_sent", 0))
            emails_sent += int(result.get("emails_sent", 0))
            if result.get("skipped"):
                skipped += 1
        except Exception:
            errors += 1
            logger.exception(
                "crm.sync_procurement_demand_insights.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        (
            "crm.sync_procurement_demand_insights.complete orgs=%s insights_upserted=%s "
            "package_triggers=%s notifications=%s emails=%s skipped=%s errors=%s"
        ),
        orgs_processed,
        insights_upserted,
        package_triggers,
        notifications_sent,
        emails_sent,
        skipped,
        errors,
    )
    return {
        "orgs_processed": orgs_processed,
        "insights_upserted": insights_upserted,
        "package_triggers": package_triggers,
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "skipped": skipped,
        "errors": errors,
    }


def _payment_reminder_recipients_for_reservation(reservation: UnitReservation) -> list:
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

    add_user(getattr(reservation.lead, "assigned_to", None))
    for user_obj in _management_recipients_for_org(reservation.organization_id):
        add_user(user_obj)
    return recipients


def _dispatch_payment_reminders_for_org(*, organization_id: int, now):
    from apps.finance.models import PaymentInstallment

    today = now.date()
    reminder_cutoff = today + timedelta(days=PAYMENT_REMINDER_LOOKAHEAD_DAYS)
    recent_cutoff = now - timedelta(hours=PAYMENT_REMINDER_RECENT_HOURS)

    reservations = (
        UnitReservation.objects.filter(
            organization_id=organization_id,
            status=UnitReservation.Status.PAYMENT_PENDING,
            payment_plan__isnull=False,
        )
        .select_related("organization", "lead", "lead__assigned_to", "payment_plan")
        .order_by("payment_deadline", "id")
    )

    reminders_sent = 0
    notifications_sent = 0
    emails_sent = 0

    for reservation in reservations:
        installment = (
            reservation.payment_plan.installments.filter(
                due_date__lte=reminder_cutoff,
            )
            .exclude(
                status__in=[
                    PaymentInstallment.Status.PAID,
                    PaymentInstallment.Status.WAIVED,
                    PaymentInstallment.Status.CANCELLED,
                ]
            )
            .order_by("due_date", "installment_number")
            .first()
        )
        if installment is None:
            continue

        recipients = _payment_reminder_recipients_for_reservation(reservation)
        if not recipients:
            continue

        due_date = installment.due_date
        overdue_days = max((today - due_date).days, 0)
        due_label = due_date.strftime("%b %d, %Y")
        amount_due = (installment.amount - installment.paid_amount).quantize(Decimal("0.01"))
        link_url = f"/crm/reservations/{reservation.id}?installment_id={installment.id}"

        already_notified_ids = set(
            Notification.objects.filter(
                recipient_id__in=[recipient.id for recipient in recipients],
                category=Notification.Category.CRM_RESERVATION,
                link_url=link_url,
                created_at__gte=recent_cutoff,
            ).values_list("recipient_id", flat=True)
        )
        pending_recipients = [
            recipient for recipient in recipients if recipient.id not in already_notified_ids
        ]
        if not pending_recipients:
            continue

        urgency = "overdue" if overdue_days > 0 else "upcoming"
        fallback_message = (
            f"Payment reminder ({urgency}) for reservation {reservation.reservation_number}. "
            f"Outstanding amount {amount_due} due on {due_label}."
        )
        dispatch_result = dispatch_workflow_notification(
            organization=reservation.organization,
            event_key="crm_payment_reminder_due",
            recipients=pending_recipients,
            context={
                "reservation_number": reservation.reservation_number,
                "lead_name": reservation.lead.full_name,
                "due_date": due_label,
                "amount_due": str(amount_due),
                "overdue_days": overdue_days,
                "action_url": link_url,
            },
            link_url=link_url,
            fallback_channels=["in_app", "email"],
            fallback_title=f"Payment reminder: {reservation.reservation_number}",
            fallback_message=fallback_message,
            fallback_category=Notification.Category.CRM_RESERVATION,
            fallback_severity=(
                Notification.Severity.WARNING if overdue_days > 0 else Notification.Severity.INFO
            ),
        )
        reminders_sent += 1
        notifications_sent += int(dispatch_result.get("notifications_sent", 0))
        emails_sent += int(dispatch_result.get("emails_sent", 0))

    return {
        "reservations_checked": reservations.count(),
        "reminders_sent": reminders_sent,
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
    }


@shared_task(name="crm.send_payment_reminders")
def send_payment_reminders():
    """Periodic payment reminder sweep for pending CRM reservations."""
    now = timezone.now()
    orgs_processed = 0
    reservations_checked = 0
    reminders_sent = 0
    notifications_sent = 0
    emails_sent = 0
    errors = 0

    for organization_id in iter_organization_ids():
        try:
            with rls_context(organization_id, bypass=False):
                result = _dispatch_payment_reminders_for_org(
                    organization_id=organization_id,
                    now=now,
                )
            orgs_processed += 1
            reservations_checked += int(result.get("reservations_checked", 0))
            reminders_sent += int(result.get("reminders_sent", 0))
            notifications_sent += int(result.get("notifications_sent", 0))
            emails_sent += int(result.get("emails_sent", 0))
        except Exception:
            errors += 1
            logger.exception(
                "crm.send_payment_reminders.failed organization_id=%s",
                organization_id,
            )

    logger.info(
        "crm.send_payment_reminders.complete orgs=%s reservations_checked=%s reminders=%s notifications=%s emails=%s errors=%s",
        orgs_processed,
        reservations_checked,
        reminders_sent,
        notifications_sent,
        emails_sent,
        errors,
    )
    return {
        "orgs_processed": orgs_processed,
        "reservations_checked": reservations_checked,
        "reminders_sent": reminders_sent,
        "notifications_sent": notifications_sent,
        "emails_sent": emails_sent,
        "errors": errors,
    }

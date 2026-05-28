import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.analytics.cache_utils import bump_analytics_cache_version

from .cache_utils import bump_project_summary_cache_version

logger = logging.getLogger(__name__)

PROJECT_BUDGET_CATEGORY_TEMPLATES = [
    {
        "account_code": "PRJ-LAND",
        "category_name": "Land acquisition",
        "sub_type": "operating_expense",
    },
    {
        "account_code": "PRJ-DESIGN",
        "category_name": "Planning & design",
        "sub_type": "operating_expense",
    },
    {
        "account_code": "PRJ-PERMIT",
        "category_name": "Permits & approvals",
        "sub_type": "operating_expense",
    },
    {
        "account_code": "PRJ-CONSTR",
        "category_name": "Construction",
        "sub_type": "operating_expense",
    },
    {
        "account_code": "PRJ-MKTSALES",
        "category_name": "Marketing & sales",
        "sub_type": "operating_expense",
    },
    {
        "account_code": "PRJ-FINCHRG",
        "category_name": "Finance charges",
        "sub_type": "other_expense",
    },
    {
        "account_code": "PRJ-CONTG",
        "category_name": "Contingency",
        "sub_type": "operating_expense",
    },
    {
        "account_code": "PRJ-OTHER",
        "category_name": "Other",
        "sub_type": "operating_expense",
    },
]

PROJECT_COA_MAPPING_TEMPLATES = [
    {
        "field_name": "construction_cost_account",
        "account_code_prefix": "PRJ-COA-CC",
        "account_name": "Project Construction Costs",
        "account_type": "expense",
        "sub_type": "cost_of_goods_sold",
    },
    {
        "field_name": "capex_account",
        "account_code_prefix": "PRJ-COA-CX",
        "account_name": "Project Capex",
        "account_type": "asset",
        "sub_type": "fixed_asset",
    },
    {
        "field_name": "development_expense_account",
        "account_code_prefix": "PRJ-COA-DE",
        "account_name": "Project Development Expenses",
        "account_type": "expense",
        "sub_type": "operating_expense",
    },
    {
        "field_name": "sales_revenue_account",
        "account_code_prefix": "PRJ-COA-SR",
        "account_name": "Project Sales Revenue",
        "account_type": "revenue",
        "sub_type": "operating_revenue",
    },
]

PROJECT_FINANCE_ARTIFACT_TEMPLATES = [
    {
        "artifact_type": "project_budget_dashboard",
        "name": "Project Budget Dashboard",
        "menu_path": "/finance/budgets",
        "menu_group": "budget",
    },
    {
        "artifact_type": "cashflow_forecast",
        "name": "Cashflow Forecast",
        "menu_path": "/finance/dashboard",
        "menu_group": "forecast",
    },
    {
        "artifact_type": "cost_tracker",
        "name": "Cost Tracker",
        "menu_path": "/finance",
        "menu_group": "cost",
    },
    {
        "artifact_type": "variance_analysis",
        "name": "Variance Analysis",
        "menu_path": "/finance/variance-analysis",
        "menu_group": "analytics",
    },
]

PROJECT_PROCUREMENT_WORKSPACE_TEMPLATES = [
    {
        "workspace_type": "project_procurement_dashboard",
        "name": "Project Procurement Dashboard",
        "menu_path": "/procurement/overview",
        "menu_group": "dashboard",
    },
    {
        "workspace_type": "vendor_allocation_workspace",
        "name": "Vendor Allocation Workspace",
        "menu_path": "/procurement/vendors",
        "menu_group": "vendor_management",
    },
]

PROJECT_CONSTRUCTION_WORKSPACE_TEMPLATES = [
    {
        "workspace_type": "site_overview_dashboard",
        "name": "Site Overview Dashboard",
        "menu_path": "/construction/site-overview",
        "menu_group": "dashboard",
    },
    {
        "workspace_type": "site_mobilization_workspace",
        "name": "Site Mobilization",
        "menu_path": "/construction/site-mobilization",
        "menu_group": "pre_construction",
    },
    {
        "workspace_type": "construction_schedule_workspace",
        "name": "Construction Schedule",
        "menu_path": "/construction/schedule",
        "menu_group": "execution",
    },
    {
        "workspace_type": "contractor_management_workspace",
        "name": "Contractor Management",
        "menu_path": "/construction/contractor-management",
        "menu_group": "execution",
    },
]

PROJECT_POSITION_BUDGET_WIND_DOWN_NOTE = "[AUTO-ARCHIVED] Project wind-down archive"
MILESTONE_RISK_TITLE_PREFIX = "[AUTO] Milestone Delay Risk"
MILESTONE_RISK_MARKER_PREFIX = "AUTOMATION_MARKER:milestone_delay:"


def _milestone_reached(milestone) -> bool:
    return bool(getattr(milestone, "is_completed", False) or getattr(milestone, "completed_date", None))


def _milestone_due_date(milestone):
    return (
        getattr(milestone, "revised_target_date", None)
        or getattr(milestone, "target_date", None)
        or getattr(milestone, "baseline_target_date", None)
    )


def _milestone_risk_marker(milestone_id: int) -> str:
    return f"{MILESTONE_RISK_MARKER_PREFIX}{milestone_id}"


def _sync_milestone_delay_risk_indicator(milestone) -> None:
    from apps.projects.models import ProjectRiskRegisterEntry

    project = milestone.phase.project
    org = project.organization
    marker = _milestone_risk_marker(milestone.id)
    due_date = _milestone_due_date(milestone)
    reached = _milestone_reached(milestone)
    today = timezone.localdate()
    is_overdue = bool(due_date and due_date < today and not reached)

    auto_risk = (
        ProjectRiskRegisterEntry.objects.filter(
            organization=org,
            project=project,
            description__contains=marker,
        )
        .order_by("-id")
        .first()
    )

    if is_overdue:
        title = f"{MILESTONE_RISK_TITLE_PREFIX}: {milestone.name}"[:255]
        description = (
            f"{marker}\n"
            f'Milestone "{milestone.name}" is overdue (target {due_date.isoformat()}) '
            f"and remains incomplete."
        )
        target_resolution_date = today + timedelta(days=7)
        if auto_risk is None:
            ProjectRiskRegisterEntry.objects.create(
                organization=org,
                project=project,
                title=title,
                description=description,
                likelihood_key="medium",
                likelihood_score=3,
                impact_key="high",
                impact_score=4,
                risk_score=12,
                severity=ProjectRiskRegisterEntry.Severity.HIGH,
                status=ProjectRiskRegisterEntry.Status.OPEN,
                treatment=ProjectRiskRegisterEntry.Treatment.MITIGATE,
                mitigation_plan="Recover schedule and remove blocker to close overdue milestone.",
                mitigation_actions="Triggered automatically from milestone delay monitor.",
                escalation_required=True,
                identified_on=today,
                target_resolution_date=target_resolution_date,
                last_reviewed_on=today,
            )
            return

        update_fields = []
        if auto_risk.title != title:
            auto_risk.title = title
            update_fields.append("title")
        if marker not in (auto_risk.description or ""):
            auto_risk.description = description
            update_fields.append("description")
        if auto_risk.status != ProjectRiskRegisterEntry.Status.OPEN:
            auto_risk.status = ProjectRiskRegisterEntry.Status.OPEN
            update_fields.append("status")
        if auto_risk.resolved_on is not None:
            auto_risk.resolved_on = None
            update_fields.append("resolved_on")
        if auto_risk.last_reviewed_on != today:
            auto_risk.last_reviewed_on = today
            update_fields.append("last_reviewed_on")
        if auto_risk.target_resolution_date != target_resolution_date:
            auto_risk.target_resolution_date = target_resolution_date
            update_fields.append("target_resolution_date")
        if update_fields:
            update_fields.append("updated_at")
            auto_risk.save(update_fields=update_fields)
        return

    if auto_risk is None or not reached:
        return

    update_fields = []
    if auto_risk.status != ProjectRiskRegisterEntry.Status.MITIGATED:
        auto_risk.status = ProjectRiskRegisterEntry.Status.MITIGATED
        update_fields.append("status")
    if auto_risk.resolved_on != today:
        auto_risk.resolved_on = today
        update_fields.append("resolved_on")
    if auto_risk.last_reviewed_on != today:
        auto_risk.last_reviewed_on = today
        update_fields.append("last_reviewed_on")
    if update_fields:
        update_fields.append("updated_at")
        auto_risk.save(update_fields=update_fields)


def _run_milestone_reached_automation(milestone) -> None:
    project = milestone.phase.project
    org_id = project.organization_id
    project_cache_version = bump_project_summary_cache_version(org_id)
    analytics_cache_version = bump_analytics_cache_version(org_id)
    logger.info(
        (
            "Milestone reached automation triggered for project %s (%s), "
            "milestone %s (%s). cache_versions: project=%s analytics=%s"
        ),
        project.id,
        project.name,
        milestone.id,
        milestone.name,
        project_cache_version,
        analytics_cache_version,
    )


@receiver(pre_save, sender="projects.ProjectMilestone")
def capture_milestone_reached_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._automation_was_reached = False
        return
    previous = (
        sender.objects.filter(pk=instance.pk)
        .values("is_completed", "completed_date")
        .first()
    )
    instance._automation_was_reached = bool(
        previous
        and (previous["is_completed"] or previous["completed_date"])
    )


@receiver(post_save, sender="projects.ProjectMilestone")
def on_project_milestone_saved(sender, instance, created, **kwargs):
    update_fields = kwargs.get("update_fields")
    tracked_fields = {
        "is_completed",
        "completed_date",
        "target_date",
        "revised_target_date",
        "baseline_target_date",
    }
    if not created and update_fields and not tracked_fields.intersection(set(update_fields)):
        return

    _sync_milestone_delay_risk_indicator(instance)

    reached = _milestone_reached(instance)
    was_reached = bool(getattr(instance, "_automation_was_reached", False))
    if reached and (created or not was_reached):
        _run_milestone_reached_automation(instance)


@receiver(pre_save, sender="projects.ProjectPhase")
def capture_phase_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_phase_status = None
        return
    from apps.projects.models import ProjectPhase

    instance._previous_phase_status = (
        ProjectPhase.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender="projects.ProjectPhase")
def on_phase_status_change(sender, instance, created, **kwargs):
    """Notify stakeholders when a project phase transitions status."""
    if created:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    project = instance.project
    org = project.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="projects.phase",
        fallback_users=_org_admin_users(org),
    )

    dispatch_workflow_notification(
        organization=org,
        event_key="projects_phase_status_changed",
        recipients=raci.all,
        context={
            "project_name": project.name,
            "phase_name": instance.name,
            "old_status": "",
            "new_status": instance.get_status_display(),
            "action_url": f"/projects/{project.id}",
        },
        link_url=f"/projects/{project.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Project Phase Updated — {instance.name}",
        fallback_message=(
            f"Phase '{instance.name}' on project '{project.name}' "
            f"has transitioned to {instance.get_status_display()}. "
            f"Please review dependent tasks and milestones for any required follow-up."
        ),
        fallback_category=Notification.Category.PROJECT_UPDATE,
        fallback_severity=Notification.Severity.INFO,
    )

    _auto_archive_project_based_teams_if_project_completed(project)

    # --- Closed-loop: Plan → Execute ---
    # When a phase transitions to in_progress, auto-activate site mobilization
    prev_status = getattr(instance, "_previous_phase_status", None)
    if instance.status == "in_progress" and prev_status and prev_status != "in_progress":
        _activate_site_mobilization_for_phase(instance)


def _activate_site_mobilization_for_phase(phase):
    """
    Auto-activate site mobilization when a phase goes in-progress.

    - Sets actual_start_date if not already set
    - Syncs planned_start_date from phase dates
    - Updates construction schedule dates
    - Notifies project stakeholders
    """
    from apps.projects.models import ProjectConstructionSchedule, ProjectSiteMobilization

    project = phase.project
    org = project.organization
    today = timezone.localdate()

    # Get or create mobilization record
    mobilization, _ = ProjectSiteMobilization.objects.get_or_create(
        project=project,
        defaults={"organization": org},
    )

    update_fields = []

    # Set actual start date if this is the first activation
    if not mobilization.actual_start_date:
        mobilization.actual_start_date = today
        update_fields.append("actual_start_date")

    # Sync planned start from the phase if not already set
    if not mobilization.planned_start_date and phase.planned_start_date:
        mobilization.planned_start_date = phase.planned_start_date
        update_fields.append("planned_start_date")

    if update_fields:
        update_fields.append("updated_at")
        mobilization.save(update_fields=update_fields)

    # Sync construction schedule dates from the phase
    try:
        schedule, _ = ProjectConstructionSchedule.objects.get_or_create(
            project=project,
            defaults={"organization": org},
        )
        sched_updates = []
        if not schedule.planned_start_date and phase.planned_start_date:
            schedule.planned_start_date = phase.planned_start_date
            sched_updates.append("planned_start_date")
        if not schedule.actual_start_date:
            schedule.actual_start_date = today
            sched_updates.append("actual_start_date")
        if phase.planned_end_date and (not schedule.planned_end_date or phase.planned_end_date > schedule.planned_end_date):
            schedule.planned_end_date = phase.planned_end_date
            sched_updates.append("planned_end_date")
        if sched_updates:
            sched_updates.append("updated_at")
            schedule.save(update_fields=sched_updates)
    except Exception:
        logger.debug("Construction schedule sync skipped", exc_info=True)

    # Notify stakeholders
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="project_mobilization_auto_activated",
            recipients=_org_admin_users(org),
            context={
                "project_name": project.name,
                "phase_name": phase.name,
            },
            link_url="/construction/site-mobilization",
            fallback_title=f"Site Mobilization Activated — {project.name}",
            fallback_message=(
                f"Site mobilization for project '{project.name}' has been automatically activated "
                f"following the start of phase '{phase.name}'. "
                f"Construction schedule dates have been synced. "
                f"Please review the mobilization checklist and ensure all preparations are in order."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
        )
    except Exception:
        logger.debug("Mobilization activation notification skipped", exc_info=True)


# ---------------------------------------------------------------------------
# Closed-loop: Execute → Measure
# Daily site reports roll up to phase progress and cost actuals
# ---------------------------------------------------------------------------

@receiver(pre_save, sender="projects.ProjectDailySiteReport")
def capture_site_report_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_report_status = None
        return
    from apps.projects.models import ProjectDailySiteReport

    instance._previous_report_status = (
        ProjectDailySiteReport.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender="projects.ProjectDailySiteReport")
def on_site_report_submitted(sender, instance, created, **kwargs):
    """Roll up site report data to active phase when report is submitted or reviewed."""
    prev = getattr(instance, "_previous_report_status", None)
    submitted_statuses = {"submitted", "reviewed", "closed"}

    # Only trigger on status transition into submitted/reviewed/closed
    if instance.status not in submitted_statuses:
        return
    if not created and prev == instance.status:
        return

    _roll_up_site_report_to_phase(instance)


def _roll_up_site_report_to_phase(report):
    """
    Roll up daily site report data to the active in-progress phase:

    1. Update phase actual_cost from project cost entries
    2. Compute weighted average progress from recent site reports
    3. Auto-set phase actual_start_date if not set
    4. Notify stakeholders of progress update
    """
    from django.db.models import Sum

    from apps.projects.models import ProjectCostEntry, ProjectPhase

    project = report.project
    org = project.organization

    # Find the active in-progress phase (by sort_order)
    active_phase = (
        ProjectPhase.objects.filter(
            project=project,
            status=ProjectPhase.Status.IN_PROGRESS,
        )
        .order_by("sort_order")
        .first()
    )

    if not active_phase:
        return

    update_fields = []

    # 1. Set actual_start_date if this is the first report for this phase
    if not active_phase.actual_start_date:
        active_phase.actual_start_date = report.report_date
        update_fields.append("actual_start_date")

    # 2. Roll up cost actuals from ProjectCostEntry for this phase
    total_cost = (
        ProjectCostEntry.objects.filter(
            project=project,
            phase=active_phase,
        ).aggregate(total=Sum("amount"))["total"]
    )
    if total_cost is not None and active_phase.actual_cost != total_cost:
        active_phase.actual_cost = total_cost
        update_fields.append("actual_cost")

    # 2b. Roll up progress % from site reports (weighted average of recent reports)
    from apps.projects.models import ProjectDailySiteReport
    recent_reports = ProjectDailySiteReport.objects.filter(
        project=project,
        status__in=["submitted", "reviewed", "closed"],
        progress_percent__gt=0,
    ).order_by("-report_date")[:5]
    if recent_reports.exists():
        avg_progress = sum(float(r.progress_percent) for r in recent_reports) / recent_reports.count()
        # Store on the report for reference (phase doesn't have progress_percent yet)
        # Use the latest report's progress as the phase indicator
        latest_progress = float(recent_reports[0].progress_percent)
        if latest_progress > 0:
            # Update phase notes with progress
            progress_note = f"Latest reported progress: {latest_progress:.0f}%"
            if active_phase.notes and "Latest reported progress" not in active_phase.notes:
                active_phase.notes = f"{active_phase.notes}\n{progress_note}"
                update_fields.append("notes")

    # 2c. Aggregate labour stats from workforce logs
    from apps.projects.models import ProjectWorkforceLog
    from django.db.models import Avg as DbAvg
    labour_stats = ProjectWorkforceLog.objects.filter(
        project=project,
        report_date=report.report_date,
    ).aggregate(
        total_labourers=Sum("laborers_count"),
        total_skilled=Sum("skilled_count"),
        total_supervisors=Sum("supervisors_count"),
    )

    # 3. Save phase updates
    if update_fields:
        update_fields.append("updated_at")
        active_phase.save(update_fields=update_fields)

    # 4. Update the project status to in_progress if still in planning
    if project.status in ("planning",):
        from apps.projects.models import Project

        Project.objects.filter(pk=project.pk, status="planning").update(
            status=Project.Status.IN_PROGRESS,
        )

    # 5. Notify stakeholders of the progress roll-up
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        progress_text = f"{report.progress_percent}%" if report.progress_percent else ""
        dispatch_workflow_notification(
            organization=org,
            event_key="site_report_progress_rolled_up",
            recipients=_org_admin_users(org),
            context={
                "project_name": project.name,
                "phase_name": active_phase.name,
                "report_date": str(report.report_date),
                "progress": progress_text,
            },
            link_url=f"/projects/{project.id}",
            fallback_title=f"Site Report Submitted — {project.name}",
            fallback_message=(
                f"Daily site report for {report.report_date} has been submitted for "
                f"project '{project.name}'. "
                f"Phase '{active_phase.name}' actuals have been updated."
                + (f" Reported progress: {progress_text}." if progress_text else "")
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
        )
    except Exception:
        logger.debug("Site report roll-up notification skipped", exc_info=True)

    # 6. Closed-loop: Measure → Adjust — detect variances
    _detect_phase_variances(active_phase, report.report_date)


# ---------------------------------------------------------------------------
# Closed-loop: Measure → Adjust
# Detect schedule slips and cost overruns, flag for re-planning
# ---------------------------------------------------------------------------

# Thresholds
_COST_WARNING_PCT = Decimal("80")    # Warn at 80% of budget consumed
_COST_OVERRUN_PCT = Decimal("100")   # Alert at 100% budget exceeded
_SCHEDULE_WARNING_DAYS = 7           # Warn when 7 days from planned end
_SCHEDULE_OVERRUN_DAYS = 0           # Alert when past planned end


def _detect_phase_variances(phase, as_of_date):
    """
    Check for schedule slips and cost overruns on the active phase.
    Fires targeted notifications with re-planning suggestions.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    project = phase.project
    org = project.organization
    admins = _org_admin_users(org)
    if not admins:
        return

    variances = []

    # --- Schedule variance ---
    if phase.planned_end_date and phase.status == "in_progress":
        days_remaining = (phase.planned_end_date - as_of_date).days

        if days_remaining < -_SCHEDULE_OVERRUN_DAYS:
            # Phase is past its planned end date
            overdue_days = abs(days_remaining)
            variances.append({
                "type": "schedule_overrun",
                "severity": "critical",
                "title": f"Schedule Overrun — {phase.name}",
                "message": (
                    f"Phase '{phase.name}' on project '{project.name}' is {overdue_days} day(s) "
                    f"past its planned end date of {phase.planned_end_date}. "
                    f"Consider revising the phase timeline or escalating resource allocation. "
                    f"A variation order may be required to formalize the schedule change."
                ),
            })
        elif 0 <= days_remaining <= _SCHEDULE_WARNING_DAYS:
            # Phase is approaching its planned end date
            variances.append({
                "type": "schedule_warning",
                "severity": "warning",
                "title": f"Schedule At Risk — {phase.name}",
                "message": (
                    f"Phase '{phase.name}' on project '{project.name}' is due to complete "
                    f"in {days_remaining} day(s) (planned end: {phase.planned_end_date}). "
                    f"Review remaining tasks and deliverables to assess if the deadline is achievable."
                ),
            })

    # --- Start delay variance ---
    if (
        phase.planned_start_date
        and phase.actual_start_date
        and phase.actual_start_date > phase.planned_start_date
    ):
        delay_days = (phase.actual_start_date - phase.planned_start_date).days
        if delay_days > 7:
            variances.append({
                "type": "start_delay",
                "severity": "warning",
                "title": f"Phase Start Delayed — {phase.name}",
                "message": (
                    f"Phase '{phase.name}' on project '{project.name}' started {delay_days} day(s) "
                    f"later than planned (planned: {phase.planned_start_date}, "
                    f"actual: {phase.actual_start_date}). "
                    f"Downstream phases may need their timelines adjusted accordingly."
                ),
            })

    # --- Cost variance ---
    if phase.planned_budget and phase.planned_budget > 0:
        cost_pct = (phase.actual_cost / phase.planned_budget) * Decimal("100")

        if cost_pct >= _COST_OVERRUN_PCT:
            overrun_amount = phase.actual_cost - phase.planned_budget
            variances.append({
                "type": "cost_overrun",
                "severity": "critical",
                "title": f"Budget Overrun — {phase.name}",
                "message": (
                    f"Phase '{phase.name}' on project '{project.name}' has exceeded its planned "
                    f"budget. Actual cost: ₦{phase.actual_cost:,.2f} vs budget: "
                    f"₦{phase.planned_budget:,.2f} (overrun: ₦{overrun_amount:,.2f}, "
                    f"{cost_pct:.1f}%). "
                    f"Immediate review is required. Consider raising a variation order "
                    f"or re-allocating budget from other phases."
                ),
            })
        elif cost_pct >= _COST_WARNING_PCT:
            remaining = phase.planned_budget - phase.actual_cost
            variances.append({
                "type": "cost_warning",
                "severity": "warning",
                "title": f"Budget Warning — {phase.name}",
                "message": (
                    f"Phase '{phase.name}' on project '{project.name}' has consumed "
                    f"{cost_pct:.1f}% of its planned budget (₦{phase.actual_cost:,.2f} of "
                    f"₦{phase.planned_budget:,.2f}). Remaining: ₦{remaining:,.2f}. "
                    f"Monitor spending closely to avoid an overrun."
                ),
            })

    # --- Dispatch variance notifications (deduped — max 1 per type per day) ---
    if not variances:
        return

    recent_cutoff = timezone.now() - timezone.timedelta(hours=24)

    for v in variances:
        severity_map = {
            "warning": Notification.Severity.WARNING,
            "critical": Notification.Severity.CRITICAL,
        }

        # Dedup: check if same variance type was already notified today
        already_sent = Notification.objects.filter(
            organization=org,
            category=Notification.Category.PROJECT_RISK,
            title=v["title"],
            created_at__gte=recent_cutoff,
        ).exists()
        if already_sent:
            continue

        dispatch_workflow_notification(
            organization=org,
            event_key=f"project_variance_{v['type']}",
            recipients=admins,
            context={
                "project_name": project.name,
                "phase_name": phase.name,
                "variance_type": v["type"],
            },
            link_url=f"/projects/{project.id}",
            fallback_title=v["title"],
            fallback_message=v["message"],
            fallback_category=Notification.Category.PROJECT_RISK,
            fallback_severity=severity_map.get(v["severity"], Notification.Severity.WARNING),
        )

    # --- 35. Schedule Delay → Recovery Plan Recommendations ---
    schedule_variances = [v for v in variances if v["type"] in ("schedule_overrun", "start_delay", "schedule_warning")]
    if schedule_variances:
        _generate_recovery_recommendations(phase, project, org, admins, as_of_date)


def _generate_recovery_recommendations(phase, project, org, admins, as_of_date):
    """
    Analyse a delayed phase and generate specific recovery action recommendations:
    1. Resource increase — if incomplete tasks outnumber available workforce
    2. Resequencing — if parallel-capable tasks are running sequentially
    3. Fast-tracking — if successor phases can overlap
    4. Scope reduction — if overrun is severe
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    recommendations = []

    # Calculate delay magnitude
    delay_days = 0
    if phase.planned_end_date:
        delay_days = max(0, (as_of_date - phase.planned_end_date).days)

    # 1. Resource increase recommendation
    incomplete_tasks = ProjectTask.objects.filter(
        phase=phase,
        status__in=["pending", "in_progress"],
    ).count()
    completed_tasks = ProjectTask.objects.filter(phase=phase, status="completed").count()
    total_tasks = incomplete_tasks + completed_tasks

    if incomplete_tasks > 3 and delay_days > 0:
        recommendations.append({
            "action": "Increase Resources",
            "detail": (
                f"{incomplete_tasks} tasks remain incomplete with {delay_days} day(s) of delay. "
                f"Consider deploying additional crew members or a second shift to accelerate completion. "
                f"Estimated recovery: adding 50% more labour could recover ~{max(1, delay_days // 2)} day(s)."
            ),
            "priority": "high",
        })

    # 2. Resequencing — check if pending tasks have no dependencies and could run in parallel
    pending_tasks = ProjectTask.objects.filter(
        phase=phase, status="pending",
    ).order_by("sort_order")
    independent_tasks = [t for t in pending_tasks if not t.predecessors]
    if len(independent_tasks) > 1:
        task_names = ", ".join(t.name for t in independent_tasks[:4])
        recommendations.append({
            "action": "Parallel Execution",
            "detail": (
                f"{len(independent_tasks)} tasks have no predecessor dependencies and can run in parallel: "
                f"{task_names}. Starting these simultaneously could save "
                f"~{max(1, delay_days * len(independent_tasks) // (len(independent_tasks) + 1))} day(s)."
            ),
            "priority": "medium",
        })

    # 3. Fast-tracking — check if successor phases can overlap
    from .models import ProjectPhaseDependency, ProjectPhase
    successor_deps = ProjectPhaseDependency.objects.filter(
        predecessor_phase=phase,
        dependency_type="FS",
    ).select_related("successor_phase")
    for dep in successor_deps:
        succ = dep.successor_phase
        if succ.status in ("pending", "not_started"):
            recommendations.append({
                "action": "Fast-Track Successor Phase",
                "detail": (
                    f"Phase '{succ.name}' has a Finish-to-Start dependency on '{phase.name}'. "
                    f"Consider converting to Start-to-Start with lag to allow {succ.name} to begin "
                    f"before {phase.name} fully completes. This overlaps phases and can recover "
                    f"~{max(1, delay_days // 3)} day(s)."
                ),
                "priority": "medium",
            })
            break  # Only suggest one fast-track to avoid noise

    # 4. Scope reduction — if overrun is severe (>14 days)
    if delay_days > 14:
        recommendations.append({
            "action": "Scope Review",
            "detail": (
                f"Phase '{phase.name}' is {delay_days} days overdue — severe delay. "
                f"Consider deferring non-critical tasks to a later phase, reducing specification "
                f"requirements, or negotiating deadline extension with stakeholders. "
                f"A variation order may be needed to formalize scope changes."
            ),
            "priority": "critical",
        })

    # 5. Overtime authorization
    if 3 <= delay_days <= 14:
        recommendations.append({
            "action": "Authorize Overtime",
            "detail": (
                f"Moderate delay of {delay_days} day(s). Authorizing weekend work or extended shifts "
                f"for the next {min(delay_days, 7)} day(s) could recover the schedule without additional "
                f"crew mobilization cost. Estimated recovery: {max(1, delay_days * 2 // 3)} day(s)."
            ),
            "priority": "medium",
        })

    if not recommendations:
        return

    # Dedup: only send recovery plan once per day
    recent_cutoff = timezone.now() - timezone.timedelta(hours=24)
    already_sent = Notification.objects.filter(
        organization=org,
        title__startswith="Recovery Plan",
        created_at__gte=recent_cutoff,
    ).exists()
    if already_sent:
        return

    # Build recovery plan message
    plan_items = []
    for i, rec in enumerate(recommendations, 1):
        plan_items.append(f"{i}. [{rec['priority'].upper()}] {rec['action']}: {rec['detail']}")

    recovery_message = (
        f"Schedule delay detected on phase '{phase.name}' ({delay_days} day(s) overdue). "
        f"The following recovery actions are recommended:\n\n"
        + "\n\n".join(plan_items)
    )

    dispatch_workflow_notification(
        organization=org,
        event_key="schedule_recovery_plan",
        recipients=admins,
        context={
            "project_name": project.name,
            "phase_name": phase.name,
            "delay_days": delay_days,
            "recommendation_count": len(recommendations),
        },
        link_url=f"/projects/{project.id}",
        fallback_title=f"Recovery Plan — {phase.name} ({delay_days}d delay)",
        fallback_message=recovery_message,
        fallback_category=Notification.Category.PROJECT_RISK,
        fallback_severity=Notification.Severity.WARNING,
    )


# ---------------------------------------------------------------------------
# Closed-loop: Adjust → Plan
# Approved variation orders cascade back to update phase timelines and budgets
# ---------------------------------------------------------------------------

@receiver(pre_save, sender="projects.ProjectVariationOrder")
def capture_variation_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_vo_status = None
        return
    from apps.projects.models import ProjectVariationOrder

    instance._previous_vo_status = (
        ProjectVariationOrder.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender="projects.ProjectVariationOrder")
def on_variation_order_approved(sender, instance, created, **kwargs):
    """When a variation order is approved, cascade changes back to the project planner."""
    if created:
        return
    prev = getattr(instance, "_previous_vo_status", None)
    if instance.status != "approved" or prev == "approved":
        return

    _cascade_variation_to_planner(instance)


def _cascade_variation_to_planner(variation):
    """
    Apply an approved variation order back to the project planner:

    1. Add contract_value to the active phase's planned_budget
    2. If due_date extends beyond phase planned_end_date, revise the timeline
    3. Update construction schedule if affected
    4. Notify stakeholders of the planner adjustment
    """
    from apps.projects.models import ProjectConstructionSchedule, ProjectPhase

    project = variation.project
    org = project.organization

    # Find the active in-progress phase
    active_phase = (
        ProjectPhase.objects.filter(
            project=project,
            status=ProjectPhase.Status.IN_PROGRESS,
        )
        .order_by("sort_order")
        .first()
    )
    if not active_phase:
        # Fallback: apply to the last phase
        active_phase = (
            ProjectPhase.objects.filter(project=project)
            .order_by("-sort_order")
            .first()
        )
    if not active_phase:
        return

    phase_updates = []
    schedule_updates = []
    adjustments = []

    # 1. Budget adjustment — add variation contract_value to phase planned_budget
    if variation.contract_value and variation.contract_value != Decimal("0.00"):
        old_budget = active_phase.planned_budget or Decimal("0.00")
        new_budget = old_budget + variation.contract_value
        active_phase.planned_budget = new_budget
        phase_updates.append("planned_budget")
        adjustments.append(
            f"Budget adjusted from ₦{old_budget:,.2f} to ₦{new_budget:,.2f} "
            f"(+₦{variation.contract_value:,.2f})"
        )

    # 2. Schedule adjustment — if variation due_date extends the phase timeline
    if variation.due_date:
        if not active_phase.planned_end_date or variation.due_date > active_phase.planned_end_date:
            old_end = active_phase.planned_end_date

            # Preserve original dates as revised dates
            if not active_phase.revised_start_date and active_phase.planned_start_date:
                active_phase.revised_start_date = active_phase.planned_start_date
                phase_updates.append("revised_start_date")
            if not active_phase.revised_end_date and old_end:
                active_phase.revised_end_date = old_end
                phase_updates.append("revised_end_date")

            active_phase.planned_end_date = variation.due_date
            phase_updates.append("planned_end_date")

            reason = (
                f"Extended by variation order {variation.variation_number}: "
                f"{variation.title}."
            )
            if active_phase.schedule_revision_reason:
                active_phase.schedule_revision_reason += f"\n{reason}"
            else:
                active_phase.schedule_revision_reason = reason
            phase_updates.append("schedule_revision_reason")

            adjustments.append(
                f"Timeline extended from {old_end or 'unset'} to {variation.due_date}"
            )

            # Update construction schedule too
            try:
                schedule = ProjectConstructionSchedule.objects.filter(
                    project=project
                ).first()
                if schedule and (
                    not schedule.planned_end_date
                    or variation.due_date > schedule.planned_end_date
                ):
                    schedule.planned_end_date = variation.due_date
                    schedule_updates.append("planned_end_date")
                    schedule_updates.append("updated_at")
                    schedule.save(update_fields=schedule_updates)
            except Exception:
                logger.debug("Construction schedule update from VO skipped", exc_info=True)

    # 3. Save phase updates
    if phase_updates:
        phase_updates.append("updated_at")
        active_phase.save(update_fields=list(dict.fromkeys(phase_updates)))

    # 4. Planner → Construction: cascade task schedule adjustments
    if variation.due_date and active_phase.planned_end_date:
        try:
            from .models import ProjectTask
            phase_tasks = ProjectTask.objects.filter(
                phase=active_phase,
                due_date__isnull=False,
            ).order_by("due_date")
            if phase_tasks.exists():
                original_end = active_phase.revised_end_date or active_phase.planned_end_date
                if original_end and variation.due_date > original_end:
                    extension_days = (variation.due_date - original_end).days
                    for task in phase_tasks:
                        task.due_date = task.due_date + timedelta(days=extension_days)
                    ProjectTask.objects.bulk_update(phase_tasks, ["due_date"])
                    adjustments.append(f"{phase_tasks.count()} task(s) rescheduled by +{extension_days} day(s)")
        except Exception:
            logger.debug("Task schedule cascade from VO skipped", exc_info=True)

    # 5. Planner → HR: adjust workforce allocation
    if variation.due_date:
        try:
            from .models import ProjectWorkforceLog
            workforce_logs = ProjectWorkforceLog.objects.filter(
                project=project,
                report_date__gte=active_phase.planned_start_date or timezone.localdate(),
            )
            if workforce_logs.exists() and variation.due_date > (active_phase.revised_end_date or active_phase.planned_end_date or timezone.localdate()):
                adjustments.append(f"Workforce plan extended to cover new timeline through {variation.due_date}")
        except Exception:
            logger.debug("HR workforce adjustment from VO skipped", exc_info=True)

    # 6. Planner → Procurement: shift delivery timelines
    if variation.due_date:
        try:
            from apps.procurement.models import PurchaseOrder
            open_pos = PurchaseOrder.objects.filter(
                project=project,
                status__in=["draft", "approved", "issued"],
                expected_delivery_date__isnull=False,
            )
            shifted_po_count = 0
            for po in open_pos:
                if po.expected_delivery_date and active_phase.revised_end_date:
                    original_end = active_phase.revised_end_date
                    if variation.due_date > original_end:
                        extension_days = (variation.due_date - original_end).days
                        po.expected_delivery_date = po.expected_delivery_date + timedelta(days=extension_days)
                        po.save(update_fields=["expected_delivery_date", "updated_at"])
                        shifted_po_count += 1
            if shifted_po_count:
                adjustments.append(f"{shifted_po_count} PO delivery date(s) shifted")
        except Exception:
            logger.debug("Procurement delivery shift from VO skipped", exc_info=True)

    # 7. Planner → Finance: reforecast budget total
    if variation.contract_value and variation.contract_value != Decimal("0.00"):
        try:
            from apps.finance.models import Budget
            budget = Budget.objects.filter(
                project=project, organization=org,
            ).first()
            if budget:
                old_total = budget.total_amount or Decimal("0.00")
                budget.total_amount = old_total + variation.contract_value
                budget.save(update_fields=["total_amount", "updated_at"])
                adjustments.append(
                    f"Budget reforecast: ₦{old_total:,.2f} → ₦{budget.total_amount:,.2f} "
                    f"(+₦{variation.contract_value:,.2f} from variation)"
                )
            # Also update project-level budget field
            if project.budget:
                project.budget = (project.budget or Decimal("0.00")) + variation.contract_value
                project.save(update_fields=["budget", "updated_at"])
        except Exception:
            logger.debug("Finance reforecast from VO skipped", exc_info=True)

    # 8. Notify stakeholders
    if adjustments:
        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            adjustment_text = " ".join(adjustments)
            dispatch_workflow_notification(
                organization=org,
                event_key="project_planner_adjusted_from_variation",
                recipients=_org_admin_users(org),
                context={
                    "project_name": project.name,
                    "phase_name": active_phase.name,
                    "variation_number": variation.variation_number,
                    "adjustments": adjustment_text,
                },
                link_url=f"/projects/{project.id}",
                fallback_title=f"Project Planner Adjusted — {variation.variation_number}",
                fallback_message=(
                    f"Approved variation order {variation.variation_number} ('{variation.title}') "
                    f"has been automatically applied to phase '{active_phase.name}' on project "
                    f"'{project.name}'. {adjustment_text}. "
                    f"Please review the updated project plan and confirm downstream impacts."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.WARNING,
            )
        except Exception:
            logger.debug("Variation cascade notification skipped", exc_info=True)


@receiver(post_save, sender="projects.ProjectTask")
def on_task_assigned(sender, instance, created, **kwargs):
    """Notify a user when a project task is assigned to them."""
    if not instance.assigned_user_id:
        return

    update_fields = kwargs.get("update_fields")
    if not created and update_fields and "assigned_user_id" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    project = instance.phase.project if instance.phase_id else None
    org = project.organization if project else None
    if not org:
        return

    dispatch_workflow_notification(
        organization=org,
        event_key="projects_task_assigned",
        recipients=[instance.assigned_user],
        context={
            "project_name": project.name if project else "",
            "task_name": instance.name,
            "assignee_name": instance.assigned_user.get_full_name() or instance.assigned_user.email,
            "action_url": f"/projects/{project.id}" if project else "/projects",
        },
        link_url=f"/projects/{project.id}" if project else "/projects",
        fallback_channels=["in_app"],
        fallback_title=f"Project Task Assigned — {instance.name}",
        fallback_message=(
            f"You have been assigned the task '{instance.name}' "
            f"on project '{project.name if project else 'N/A'}'. "
            f"Please review the task details and update progress as you work on it."
        ),
        fallback_category=Notification.Category.DELEGATION_ASSIGNED,
        fallback_severity=Notification.Severity.INFO,
    )


# ── B. Smart Rescheduling — propagate delay to downstream tasks/phases ────


@receiver(pre_save, sender="projects.ProjectTask")
def capture_task_previous_dates(sender, instance, **kwargs):
    """Capture task dates before save for delay detection."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._prev_due_date = old.due_date
            instance._prev_status = old.status
        except sender.DoesNotExist:
            instance._prev_due_date = None
            instance._prev_status = None
    else:
        instance._prev_due_date = None
        instance._prev_status = None


@receiver(post_save, sender="projects.ProjectTask")
def on_task_delay_propagate(sender, instance, created, **kwargs):
    """When a task's due_date slips, propagate the delay to successor tasks."""
    if created:
        return
    prev_due = getattr(instance, "_prev_due_date", None)
    if not prev_due or not instance.due_date:
        return
    if instance.due_date <= prev_due:
        return  # No delay

    slip_days = (instance.due_date - prev_due).days
    if slip_days <= 0:
        return

    _propagate_task_delay(instance, slip_days)


def _propagate_task_delay(task, slip_days):
    """Walk successor dependencies and shift dates forward."""
    from .models import ProjectTask
    from apps.notifications.services import dispatch_workflow_notification
    from apps.notifications.models import Notification

    successors_json = task.successors or []
    if not successors_json:
        return

    shifted_tasks = []
    for dep in successors_json:
        successor_id = dep.get("task")
        if not successor_id:
            continue
        try:
            successor = ProjectTask.objects.select_related("phase__project").get(pk=successor_id)
        except ProjectTask.DoesNotExist:
            continue

        shifted = False
        if successor.due_date:
            successor.due_date = successor.due_date + timedelta(days=slip_days)
            shifted = True

        if shifted:
            successor.save(update_fields=["due_date", "updated_at"])
            shifted_tasks.append(successor)
            # Recurse into successor's successors
            _propagate_task_delay(successor, slip_days)

    # Send a single notification about the cascade
    if shifted_tasks and task.phase_id:
        project = task.phase.project
        org = project.organization
        task_names = ", ".join(t.name for t in shifted_tasks[:5])
        suffix = f" and {len(shifted_tasks) - 5} more" if len(shifted_tasks) > 5 else ""
        try:
            dispatch_workflow_notification(
                organization=org,
                event_key="project_schedule_cascade",
                recipients=list(org.members.filter(role__in=["admin", "manager"])[:10]),
                context={
                    "project_name": project.name,
                    "trigger_task": task.name,
                    "slip_days": slip_days,
                    "affected_tasks": task_names + suffix,
                },
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Schedule Cascade — {project.name}",
                fallback_message=(
                    f"Task '{task.name}' slipped by {slip_days} day(s). "
                    f"Downstream tasks rescheduled: {task_names}{suffix}."
                ),
                fallback_category=Notification.Category.ESCALATION_ALERT,
                fallback_severity=Notification.Severity.WARNING,
            )
        except Exception:
            logger.debug("Schedule cascade notification skipped", exc_info=True)


# ── C. Dependency Violation — block task start if predecessors incomplete ─


@receiver(pre_save, sender="projects.ProjectTask")
def check_dependency_violations(sender, instance, **kwargs):
    """
    When a task transitions to in_progress, verify all predecessor tasks
    are completed. If not, flag with a warning notification (non-blocking
    to avoid locking out legitimate overrides).
    """
    if not instance.pk:
        return  # New task, no check needed

    prev_status = getattr(instance, "_prev_status", None)
    if prev_status == instance.status:
        return  # Status didn't change
    if instance.status != "in_progress":
        return  # Only check when starting work

    predecessors_json = instance.predecessors or []
    if not predecessors_json:
        return

    from .models import ProjectTask

    incomplete = []
    for dep in predecessors_json:
        pred_id = dep.get("task")
        if not pred_id:
            continue
        try:
            pred = ProjectTask.objects.only("name", "status").get(pk=pred_id)
            if pred.status != "completed":
                incomplete.append(pred.name)
        except ProjectTask.DoesNotExist:
            continue

    if incomplete and instance.phase_id:
        from apps.notifications.services import dispatch_workflow_notification
        from apps.notifications.models import Notification

        project = instance.phase.project
        org = project.organization
        pred_names = ", ".join(incomplete[:5])
        try:
            dispatch_workflow_notification(
                organization=org,
                event_key="project_dependency_violation",
                recipients=list(org.members.filter(role__in=["admin", "manager"])[:10]),
                context={
                    "project_name": project.name,
                    "task_name": instance.name,
                    "incomplete_predecessors": pred_names,
                },
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Dependency Violation — {instance.name}",
                fallback_message=(
                    f"Task '{instance.name}' started but predecessor(s) are incomplete: "
                    f"{pred_names}. This may cause sequencing issues."
                ),
                fallback_category=Notification.Category.ESCALATION_ALERT,
                fallback_severity=Notification.Severity.WARNING,
            )
        except Exception:
            logger.debug("Dependency violation notification skipped", exc_info=True)


@receiver(post_save, sender="projects.ProjectTask")
def auto_archive_project_based_teams_on_task_changes(sender, instance, created, **kwargs):
    """Evaluate team auto-archival on completion-relevant task changes."""
    if not instance.phase_id:
        return

    update_fields = kwargs.get("update_fields")
    tracked_fields = {"status", "completed_date", "phase", "phase_id", "assigned_user", "assigned_user_id"}
    if not created and update_fields and not tracked_fields.intersection(set(update_fields)):
        return

    project = instance.phase.project
    _auto_archive_project_based_teams_if_project_completed(project)


@receiver(post_save, sender="projects.ProjectRiskRegisterEntry")
def on_risk_escalated(sender, instance, created, **kwargs):
    """Alert stakeholders when a high/critical risk is registered or escalated."""
    if instance.severity not in ("high", "critical"):
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification, resolve_raci_recipients

    project = instance.project
    org = project.organization

    raci = resolve_raci_recipients(
        organization=org,
        process_key="projects.risk",
        fallback_users=_org_admin_users(org),
    )

    dispatch_workflow_notification(
        organization=org,
        event_key="projects_risk_escalated",
        recipients=raci.all,
        context={
            "project_name": project.name,
            "risk_title": instance.title,
            "severity": instance.get_severity_display(),
            "action_url": f"/projects/{project.id}",
        },
        link_url=f"/projects/{project.id}",
        fallback_channels=["in_app", "email"],
        fallback_title=f"Project Risk Escalated — {instance.get_severity_display()} Severity",
        fallback_message=(
            f"A {instance.get_severity_display().lower()}-severity risk '{instance.title}' "
            f"has been registered on project '{project.name}'. "
            f"Immediate attention is required to assess impact and define mitigation actions."
        ),
        fallback_category=Notification.Category.PROJECT_RISK,
        fallback_severity=Notification.Severity.CRITICAL,
    )


@receiver(post_save, sender="projects.Project")
def on_project_created(sender, instance, created, **kwargs):
    """Notify org admins when a new project is created."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    project = instance
    org = project.organization

    dispatch_workflow_notification(
        organization=org,
        event_key="projects_created",
        recipients=_org_admin_users(org),
        context={
            "project_name": project.name,
            "action_url": f"/projects/{project.id}",
        },
        link_url=f"/projects/{project.id}",
        fallback_channels=["in_app"],
        fallback_title=f"New Project Created — {project.name}",
        fallback_message=(
            f"A new project '{project.name}' has been created. "
            f"Project phases, budgets, and team assignments can now be configured."
        ),
        fallback_category=Notification.Category.PROJECT_UPDATE,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="projects.Project")
def auto_archive_project_based_teams_on_project_completion(sender, instance, created, **kwargs):
    """Archive project-based teams when a project reaches 100% completion."""
    if created:
        return
    _auto_archive_project_based_teams_if_project_completed(instance)


@receiver(post_save, sender="projects.Project")
def bootstrap_project_financial_framework(sender, instance, created, **kwargs):
    """Create project financial containers on project initialization."""
    if not created:
        return

    from apps.finance.models import (
        Account,
        Budget,
        BudgetLineItem,
        ProjectAccountMapping,
        ProjectCostCenter,
        ProjectFinanceArtifact,
        ProjectLedger,
        ProjectRevenueCenter,
    )
    from apps.procurement.models import ProjectProcurementWorkspace
    from apps.projects.models import ProjectConstructionSchedule, ProjectConstructionWorkspace, ProjectSiteMobilization

    project = instance
    org = project.organization
    suffix = f"{project.id:06d}"

    ProjectLedger.objects.get_or_create(
        project=project,
        defaults={
            "organization": org,
            "code": f"PRJ-LDG-{suffix}",
            "name": f"Project Ledger - {project.name}",
        },
    )
    ProjectCostCenter.objects.get_or_create(
        project=project,
        defaults={
            "organization": org,
            "code": f"PRJ-COST-{suffix}",
            "name": f"Project Cost Center - {project.name}",
        },
    )
    ProjectRevenueCenter.objects.get_or_create(
        project=project,
        defaults={
            "organization": org,
            "code": f"PRJ-REV-{suffix}",
            "name": f"Project Revenue Center - {project.name}",
        },
    )

    budget_start_date = project.start_date or timezone.localdate()
    budget_end_date = project.target_end_date
    if not budget_end_date or budget_end_date < budget_start_date:
        budget_end_date = budget_start_date + timedelta(days=365)

    budget_container, _ = Budget.objects.get_or_create(
        project=project,
        defaults={
            "organization": org,
            "name": f"Project Budget - {project.name} ({suffix})",
            "status": Budget.Status.DRAFT,
            "period_type": Budget.PeriodType.ANNUAL,
            "start_date": budget_start_date,
            "end_date": budget_end_date,
            "total_amount": project.budget or 0,
            "notes": "Auto-created project budget container.",
        },
    )
    _initialize_project_budget_categories(org, budget_container, Account, BudgetLineItem)
    _initialize_project_chart_of_accounts_mapping(
        org,
        project,
        suffix,
        Account,
        ProjectAccountMapping,
    )
    _initialize_project_finance_artifacts(
        org,
        project,
        ProjectFinanceArtifact,
    )
    _initialize_project_procurement_workspaces(
        org,
        project,
        ProjectProcurementWorkspace,
    )
    _initialize_project_construction_workspaces(
        org,
        project,
        ProjectConstructionWorkspace,
    )
    ProjectSiteMobilization.objects.get_or_create(
        project=project,
        defaults={"organization": org},
    )
    ProjectConstructionSchedule.objects.get_or_create(
        project=project,
        defaults={"organization": org},
    )

    # Notify about the auto-bootstrapped financial framework
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="project_financial_framework_bootstrapped",
            recipients=_org_admin_users(org),
            fallback_title=f"Project Financial Framework Initialized — {project.name}",
            fallback_message=(
                f"The financial framework for project '{project.name}' has been automatically "
                f"initialized. Budget containers, cost centers, ledger accounts, procurement "
                f"workspace, and construction schedules are now ready for configuration."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
        )
    except Exception:
        pass


def _initialize_project_budget_categories(org, budget_container, AccountModel, BudgetLineItemModel):
    """Create default project budget categories as budget line items."""
    for sort_order, template in enumerate(PROJECT_BUDGET_CATEGORY_TEMPLATES):
        account, _ = AccountModel.objects.get_or_create(
            organization=org,
            code=template["account_code"],
            defaults={
                "name": template["category_name"],
                "account_type": "expense",
                "sub_type": template["sub_type"],
                "is_system": True,
                "is_active": True,
            },
        )

        BudgetLineItemModel.objects.get_or_create(
            budget=budget_container,
            account=account,
            department=None,
            cost_center=None,
            defaults={
                "budgeted_amount": Decimal("0.00"),
                "notes": template["category_name"],
                "sort_order": sort_order,
            },
        )


def _initialize_project_chart_of_accounts_mapping(
    org,
    project,
    suffix,
    AccountModel,
    ProjectAccountMappingModel,
):
    """Create project chart-of-accounts mapping and required GL accounts."""
    mapped_accounts = {}
    for template in PROJECT_COA_MAPPING_TEMPLATES:
        account, _ = AccountModel.objects.get_or_create(
            organization=org,
            code=f"{template['account_code_prefix']}-{suffix}",
            defaults={
                "name": template["account_name"],
                "account_type": template["account_type"],
                "sub_type": template["sub_type"],
                "is_system": True,
                "is_active": True,
            },
        )
        mapped_accounts[template["field_name"]] = account

    mapping, created = ProjectAccountMappingModel.objects.get_or_create(
        project=project,
        defaults={
            "organization": org,
            **mapped_accounts,
        },
    )
    if created:
        return

    update_fields = []
    if mapping.organization_id != org.id:
        mapping.organization = org
        update_fields.append("organization")

    for field_name, account in mapped_accounts.items():
        if getattr(mapping, f"{field_name}_id") != account.id:
            setattr(mapping, field_name, account)
            update_fields.append(field_name)

    if update_fields:
        update_fields.append("updated_at")
        mapping.save(update_fields=update_fields)


def _initialize_project_finance_artifacts(org, project, ProjectFinanceArtifactModel):
    """Create project finance artifacts that must exist for every project."""
    for template in PROJECT_FINANCE_ARTIFACT_TEMPLATES:
        ProjectFinanceArtifactModel.objects.get_or_create(
            project=project,
            artifact_type=template["artifact_type"],
            defaults={
                "organization": org,
                "name": template["name"],
                "menu_path": template["menu_path"],
                "menu_group": template["menu_group"],
                "is_active": True,
            },
        )


def _initialize_project_procurement_workspaces(
    org,
    project,
    ProjectProcurementWorkspaceModel,
):
    """Create project procurement workspaces that must exist for every project."""
    for template in PROJECT_PROCUREMENT_WORKSPACE_TEMPLATES:
        ProjectProcurementWorkspaceModel.objects.get_or_create(
            project=project,
            workspace_type=template["workspace_type"],
            defaults={
                "organization": org,
                "name": template["name"],
                "menu_path": template["menu_path"],
                "menu_group": template["menu_group"],
                "is_active": True,
            },
        )


def _initialize_project_construction_workspaces(
    org,
    project,
    ProjectConstructionWorkspaceModel,
):
    """Create project construction workspaces that must exist for every project."""
    for template in PROJECT_CONSTRUCTION_WORKSPACE_TEMPLATES:
        ProjectConstructionWorkspaceModel.objects.get_or_create(
            project=project,
            workspace_type=template["workspace_type"],
            defaults={
                "organization": org,
                "name": template["name"],
                "menu_path": template["menu_path"],
                "menu_group": template["menu_group"],
                "is_active": True,
            },
        )


def _org_admin_users(org):
    """Return active admin users for the given organization."""
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org,
            role="admin",
            user__is_active=True,
        ).select_related("user")
    ]


def _project_completion_percent(project):
    """Return project completion percent using tasks first, then phases as fallback."""
    from apps.projects.models import Project, ProjectPhase, ProjectTask

    task_stats = ProjectTask.objects.filter(
        organization=project.organization,
        phase__project=project,
    ).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=ProjectTask.Status.COMPLETED)),
    )

    task_total = int(task_stats["total"] or 0)
    if task_total > 0:
        return round((float(task_stats["completed"] or 0) / task_total) * 100, 2)

    phase_stats = ProjectPhase.objects.filter(
        organization=project.organization,
        project=project,
    ).aggregate(
        total=Count("id"),
        completed=Count("id", filter=Q(status=ProjectPhase.Status.COMPLETED)),
    )

    phase_total = int(phase_stats["total"] or 0)
    if phase_total > 0:
        return round((float(phase_stats["completed"] or 0) / phase_total) * 100, 2)

    return 100.0 if project.status == Project.Status.COMPLETED else 0.0


def _auto_archive_project_based_teams_if_project_completed(project):
    """
    Auto-archive project-based teams linked to a completed project.

    A team is archived when:
    - The project is complete (100%), and
    - The team has no assignments tied to other still-active projects.
    """
    from apps.hr.models import PositionAssignment, Team
    from apps.projects.models import Project, ProjectTask

    completion_percent = _project_completion_percent(project)
    if completion_percent < 100 and project.status != Project.Status.COMPLETED:
        return

    candidate_teams = Team.objects.filter(
        organization=project.organization,
        team_type=Team.TeamType.PROJECT_BASED,
        positions__assignments__is_active=True,
        positions__assignments__user__project_tasks__phase__project=project,
    ).distinct()

    if not candidate_teams.exists():
        return

    active_project_statuses = [
        Project.Status.PLANNING,
        Project.Status.IN_PROGRESS,
        Project.Status.ON_HOLD,
    ]

    archived_count = 0
    for team in candidate_teams:
        team_user_ids = list(
            PositionAssignment.objects.filter(
                organization=project.organization,
                position__team=team,
                is_active=True,
            )
            .values_list("user_id", flat=True)
            .distinct()
        )
        if not team_user_ids:
            continue

        has_other_active_project = ProjectTask.objects.filter(
            organization=project.organization,
            assigned_user_id__in=team_user_ids,
            phase__project__organization=project.organization,
            phase__project__status__in=active_project_statuses,
        ).exclude(
            phase__project=project,
        ).exists()

        if has_other_active_project:
            continue

        if team.is_active:
            team.is_active = False
            team.save(update_fields=["is_active", "updated_at"])
            archived_count += 1

    if archived_count:
        logger.info(
            "Auto-archived %s project-based team(s) for completed project %s (%s).",
            archived_count,
            project.id,
            project.name,
        )

    archived_budget_count = _archive_project_position_budgets_on_completion(project)
    if archived_budget_count:
        _notify_hr_of_project_wind_down(
            project=project,
            archived_budget_count=archived_budget_count,
        )


def _archive_project_position_budgets_on_completion(project) -> int:
    """Archive project-funded position budgets tied to the completed project."""
    from apps.hr.models import PositionBudget, Team
    from apps.projects.models import ProjectTask

    project_user_ids = list(
        ProjectTask.objects.filter(
            organization=project.organization,
            phase__project=project,
            assigned_user_id__isnull=False,
        )
        .values_list("assigned_user_id", flat=True)
        .distinct()
    )
    team_ids = list(
        Team.objects.filter(
            organization=project.organization,
            team_type=Team.TeamType.PROJECT_BASED,
            positions__assignments__is_active=True,
            positions__assignments__user_id__in=project_user_ids,
        )
        .values_list("id", flat=True)
        .distinct()
    )

    budget_qs = PositionBudget.objects.filter(
        organization=project.organization,
        budget_source=PositionBudget.BudgetSource.PROJECT_FUNDING,
    )
    budget_qs = budget_qs.filter(
        Q(position__team_id__in=team_ids) | Q(fiscal_period_label__icontains=project.name)
    ).distinct()

    archived_count = 0
    archive_stamp = timezone.localdate().isoformat()
    for budget in budget_qs:
        notes = (budget.notes or "").strip()
        if (
            budget.status == PositionBudget.Status.FROZEN
            and PROJECT_POSITION_BUDGET_WIND_DOWN_NOTE in notes
        ):
            continue

        note_parts = [notes] if notes else []
        note_parts.append(f"{PROJECT_POSITION_BUDGET_WIND_DOWN_NOTE} on {archive_stamp}.")
        budget.status = PositionBudget.Status.FROZEN
        budget.notes = " ".join(note_parts).strip()
        budget.save(update_fields=["status", "notes", "updated_at"])
        archived_count += 1

    if archived_count:
        logger.info(
            "Archived %s project-funded position budget row(s) for completed project %s (%s).",
            archived_count,
            project.id,
            project.name,
        )
    return archived_count


def _notify_hr_of_project_wind_down(*, project, archived_budget_count: int) -> None:
    """Alert HR/admin users to reassign or offboard project-linked staff."""
    from apps.accounts.models import UserProfile
    from apps.notifications.models import Notification

    org = project.organization
    admin_users = _org_admin_users(org)
    hr_profiles = (
        UserProfile.objects.select_related("user", "assigned_role")
        .filter(organization=org, user__is_active=True)
        .filter(
            Q(job_title__icontains="hr")
            | Q(assigned_role__name__icontains="hr")
            | Q(assigned_role__slug__icontains="hr")
        )
    )
    hr_users = [profile.user for profile in hr_profiles if profile.user_id]

    recipients: dict[int, object] = {}
    for user in [*admin_users, *hr_users]:
        if user and user.id:
            recipients[user.id] = user

    if not recipients:
        return

    title = f"Project Wind-Down Initiated — {project.name}"
    message = (
        f"Project '{project.name}' has reached completion and {archived_budget_count} "
        f"project-funded position budget row(s) have been archived. "
        f"Please review and reassign or offboard affected site staff accordingly."
    )
    for user in recipients.values():
        Notification.objects.create(
            recipient=user,
            organization=org,
            title=title,
            message=message,
            severity=Notification.Severity.WARNING,
            category=Notification.Category.HR_LIFECYCLE,
            link_url="/hr/budgeting",
        )


# ── BOQ → Finance Cost Rollup Signals ────────────────────────────────


@receiver(post_save, sender="procurement.PurchaseOrder")
def sync_po_committed_cost(sender, instance, **kwargs):
    """When a PO is approved/issued, update committed cost on linked cost code budgets."""
    from apps.projects.models import CostCodeBudget

    if not instance.project_id:
        return
    # Only sync when PO is in a committed state
    if instance.status not in ("approved", "issued", "partially_received", "received"):
        return
    # Aggregate PO totals by cost code budget through PO items
    for item in instance.items.filter(bom_item__isnull=False).select_related("bom_item"):
        # Find the BoqTaskMapping for this bom_item + project to get cost_code_budget
        from apps.inventory.models import BoqTaskMapping
        mapping = BoqTaskMapping.objects.filter(
            bom_item=item.bom_item,
            project=instance.project,
            cost_code_budget__isnull=False,
        ).first()
        if mapping and mapping.cost_code_budget:
            ccb = mapping.cost_code_budget
            # Recalculate committed from all POs for this cost code
            from django.db.models import Sum
            from apps.procurement.models import PurchaseOrderItem
            committed = PurchaseOrderItem.objects.filter(
                bom_item__task_mappings__cost_code_budget=ccb,
                purchase_order__project=instance.project,
                purchase_order__status__in=("approved", "issued", "partially_received", "received"),
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            if ccb.committed != committed:
                ccb.committed = committed
                ccb.save(update_fields=["committed", "updated_at"])


@receiver(post_save, sender="finance.Bill")
def sync_bill_actual_cost(sender, instance, **kwargs):
    """When a bill is approved/paid, update actual cost on linked cost code budgets."""
    from apps.projects.models import CostCodeBudget

    if not instance.project_id:
        return
    if instance.status not in ("approved", "paid"):
        return
    # Aggregate bill line items by cost_code_budget
    for line in instance.line_items.filter(cost_code_budget__isnull=False).select_related("cost_code_budget"):
        ccb = line.cost_code_budget
        from django.db.models import Sum
        from apps.finance.models import BillLineItem
        actual = BillLineItem.objects.filter(
            cost_code_budget=ccb,
            bill__project=instance.project,
            bill__status__in=("approved", "paid"),
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        if ccb.actual_cost != actual:
            ccb.actual_cost = actual
            ccb.save(update_fields=["actual_cost", "updated_at"])


@receiver(post_save, sender="projects.ProjectVariationOrder")
def sync_variation_approved_changes(sender, instance, **kwargs):
    """When a variation is approved, update approved_changes on linked cost code budget."""
    if not instance.cost_code_budget_id:
        return
    if instance.status != "approved":
        return
    from apps.projects.models import CostCodeBudget, ProjectVariationOrder
    from django.db.models import Sum
    ccb = instance.cost_code_budget
    total_changes = ProjectVariationOrder.objects.filter(
        cost_code_budget=ccb,
        status="approved",
    ).aggregate(total=Sum("contract_value"))["total"] or Decimal("0")
    if ccb.approved_changes != total_changes:
        ccb.approved_changes = total_changes
        ccb.save(update_fields=["approved_changes", "updated_at"])


# ═══════════════════════════════════════════════════════════════════════
# GROUP A — PROJECT INITIATION AUTOMATION
# ═══════════════════════════════════════════════════════════════════════


def _get_governance_settings(org):
    """Fetch ProjectGovernanceSettings for org, return None if not configured."""
    from apps.settings.models import ProjectGovernanceSettings
    return ProjectGovernanceSettings.objects.filter(organization=org).first()


# ── 1. Project Approval → Auto Project Creation (setting-gated) ──────


@receiver(post_save, sender="workflows.WorkflowInstance")
def on_workflow_approved_auto_create_project(sender, instance, **kwargs):
    """
    When a workflow instance for a Project is approved and the setting is enabled,
    auto-bootstrap the project (budget shell, workspaces, milestones).
    """
    if instance.state != "approved":
        return

    from django.contrib.contenttypes.models import ContentType
    from .models import Project

    # Check if this workflow is for a Project
    project_ct = ContentType.objects.get_for_model(Project)
    if instance.content_type_id != project_ct.id:
        return

    try:
        project = Project.objects.get(pk=instance.object_id)
    except Project.DoesNotExist:
        return

    org = project.organization
    governance = _get_governance_settings(org)
    if not governance or not governance.auto_create_project_on_approval:
        return

    # If project is still in draft/planning, activate it
    if project.status in ("draft", "planning"):
        project.status = "active"
        project.save(update_fields=["status", "updated_at"])

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="project_auto_activated_on_approval",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{project.id}",
            fallback_channels=["in_app"],
            fallback_title=f"Project Approved & Activated — {project.name}",
            fallback_message=f"Project '{project.name}' was approved via workflow and automatically activated. Budget, workspaces, and schedules have been bootstrapped.",
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Auto project activation on approval failed", exc_info=True)


# ── 2. Budget Approval → Auto Lock + Distribution (setting-gated) ────


@receiver(pre_save, sender="projects.DevelopmentBudget")
def capture_budget_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_budget_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_budget_status = None
    else:
        instance._prev_budget_status = None


@receiver(post_save, sender="projects.DevelopmentBudget")
def on_budget_approved_auto_lock(sender, instance, created, **kwargs):
    """
    When a DevelopmentBudget status changes to 'approved', auto-lock it
    and distribute into construction, procurement, and contingency.
    """
    if created:
        return
    prev = getattr(instance, "_prev_budget_status", None)
    if prev == instance.status or instance.status != "approved":
        return

    org = instance.organization
    governance = _get_governance_settings(org)
    if not governance or not governance.auto_lock_budget_on_approval:
        return

    from .models import DevelopmentBudgetCategory
    from django.utils import timezone as tz

    # Lock the budget
    instance.is_baseline = True
    instance.locked_date = tz.localdate()
    instance.save(update_fields=["is_baseline", "locked_date", "updated_at"])

    # Auto-distribute into categories if none exist
    if not instance.categories.exists():
        total = instance.equity_amount + instance.debt_amount
        contingency_pct = float(instance.contingency_pct or 5) / 100
        contingency_amount = total * Decimal(str(contingency_pct))
        construction_amount = total * Decimal("0.65") * (1 - Decimal(str(contingency_pct)))
        procurement_amount = total * Decimal("0.25") * (1 - Decimal(str(contingency_pct)))
        soft_costs = total - construction_amount - procurement_amount - contingency_amount

        for idx, (name, amount, cost_type) in enumerate([
            ("Construction", construction_amount, "hard"),
            ("Procurement & Materials", procurement_amount, "hard"),
            ("Professional Fees & Soft Costs", soft_costs, "soft"),
            ("Contingency", contingency_amount, "soft"),
        ]):
            DevelopmentBudgetCategory.objects.create(
                budget=instance, name=name, cost_type=cost_type,
                allocated_amount=amount, status="locked", sort_order=idx,
            )

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="budget_auto_locked",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Budget Locked — {instance.project.name}",
            fallback_message=f"Development budget v{instance.version} for '{instance.project.name}' has been approved and locked with {instance.categories.count()} allocation categories.",
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Budget lock notification skipped", exc_info=True)


# ── 3. Project Creation → Construction Env Setup (always active) ─────
# Already implemented in bootstrap_project_financial_framework.
# Adding: default work packages + site structure.


@receiver(post_save, sender="projects.Project")
def on_project_created_setup_construction_defaults(sender, instance, created, **kwargs):
    """Supplement the bootstrap signal with default work packages."""
    if not created:
        return

    from .models import ProjectWorkPackage

    default_packages = [
        "Mobilization & Site Setup",
        "Substructure & Foundation",
        "Superstructure",
        "Roofing & Waterproofing",
        "MEP First Fix",
        "Finishes",
        "MEP Second Fix",
        "External Works",
        "Snag List & Handover",
    ]
    for idx, name in enumerate(default_packages):
        ProjectWorkPackage.objects.get_or_create(
            organization=instance.organization,
            project=instance,
            name=name,
        )


# ── 4. Schedule Approval → Baseline Lock (always active) ─────────────


@receiver(pre_save, sender="projects.ProjectConstructionSchedule")
def capture_schedule_notes_change(sender, instance, **kwargs):
    """Detect when master_schedule_notes includes '[BASELINE]' marker."""
    instance._is_new = not instance.pk


@receiver(post_save, sender="projects.ProjectPhase")
def on_phase_baseline_snapshot(sender, instance, created, **kwargs):
    """
    When a phase has planned dates set and no baseline yet, lock the baseline.
    This creates the variance tracking reference point.
    """
    if created:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields and "planned_start_date" not in update_fields and "planned_end_date" not in update_fields:
        return

    if not instance.planned_start_date or not instance.planned_end_date:
        return

    changed = False
    if not instance.baseline_start_date:
        instance.baseline_start_date = instance.planned_start_date
        changed = True
    if not instance.baseline_end_date:
        instance.baseline_end_date = instance.planned_end_date
        changed = True

    if changed:
        instance.save(update_fields=["baseline_start_date", "baseline_end_date", "updated_at"])


# ── 5. Consultant Onboarding → Access Provisioning (setting-gated) ───


@receiver(pre_save, sender="projects.ProjectConsultant")
def capture_consultant_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_consultant_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_consultant_status = None
    else:
        instance._prev_consultant_status = None


@receiver(post_save, sender="projects.ProjectConsultant")
def on_consultant_activated_provision_access(sender, instance, created, **kwargs):
    """
    When a consultant's engagement status changes to 'active',
    auto-assign role access and notify.
    """
    prev = getattr(instance, "_prev_consultant_status", None)
    if prev == instance.status:
        return
    if instance.status != "active":
        return

    org = instance.organization
    governance = _get_governance_settings(org)
    if not governance or not governance.auto_provision_consultant_access:
        return

    # Map discipline to role label
    discipline_role_map = {
        "architectural": "Architect",
        "structural": "Structural Engineer",
        "mep": "MEP Engineer",
        "quantity_surveying": "Quantity Surveyor",
        "legal": "Legal Counsel",
        "geotechnical": "Geotechnical Engineer",
        "environmental": "Environmental Consultant",
        "project_management": "Project Manager",
        "interior_design": "Interior Designer",
        "landscape": "Landscape Architect",
    }
    role_label = discipline_role_map.get(instance.discipline, "Consultant")

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="consultant_access_provisioned",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Consultant Onboarded — {instance.firm_name}",
            fallback_message=(
                f"{instance.firm_name} ({role_label}) has been activated on project "
                f"'{instance.project.name}'. Role: {role_label}. "
                f"Access to design documents and submittals has been provisioned."
            ),
            fallback_category=Notification.Category.DELEGATION_ASSIGNED,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Consultant provisioning notification skipped", exc_info=True)


# ── 6. Risk Creation → Monitoring Engine (always active) ──────────────
# on_risk_escalated already exists above (sends notifications).
# Adding: auto-create mitigation workflow task for high/critical risks.


@receiver(post_save, sender="projects.ProjectRiskRegisterEntry")
def on_risk_created_activate_monitoring(sender, instance, created, **kwargs):
    """
    When a high/critical risk is created, auto-create a mitigation task
    assigned to the project manager.
    """
    if not created:
        return
    if instance.severity not in ("high", "critical"):
        return

    from .models import ProjectTask

    # Find the first active phase
    phase = instance.project.phases.order_by("sort_order").first()
    if not phase:
        return

    # Create a mitigation task
    ProjectTask.objects.create(
        organization=instance.organization,
        phase=phase,
        name=f"RISK MITIGATION: {instance.title[:80]}",
        description=(
            f"Auto-generated mitigation task for {instance.get_severity_display()} risk.\n\n"
            f"Risk: {instance.title}\n"
            f"Category: {instance.get_category_display() if hasattr(instance, 'get_category_display') else instance.category}\n"
            f"Impact: {instance.impact_description if hasattr(instance, 'impact_description') else ''}\n\n"
            f"Mitigation plan: {instance.mitigation_plan if hasattr(instance, 'mitigation_plan') else 'Pending review'}"
        ),
        status="pending",
        priority="critical" if instance.severity == "critical" else "high",
        work_package="Risk Management",
    )


# ── 7. Land Acquisition Complete → Project Activation (setting-gated) ─


@receiver(pre_save, sender="projects.LandAcquisition")
def capture_land_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_acquisition_status = sender.objects.get(pk=instance.pk).acquisition_status
        except sender.DoesNotExist:
            instance._prev_acquisition_status = None
    else:
        instance._prev_acquisition_status = None


@receiver(post_save, sender="projects.LandAcquisition")
def on_land_acquisition_complete_activate_project(sender, instance, created, **kwargs):
    """
    When a land acquisition is marked complete and the org setting is enabled,
    check if ALL acquisitions for the project are complete. If yes, activate the project.
    """
    prev = getattr(instance, "_prev_acquisition_status", None)
    if prev == instance.acquisition_status:
        return
    if instance.acquisition_status != "completed":
        return

    org = instance.organization
    governance = _get_governance_settings(org)
    if not governance or not governance.auto_activate_on_land_acquisition:
        return

    project = instance.project

    # Check if ALL land acquisitions for this project are complete
    from .models import LandAcquisition
    total = LandAcquisition.objects.filter(project=project).count()
    completed = LandAcquisition.objects.filter(project=project, acquisition_status="completed").count()

    if total > 0 and total == completed:
        # All parcels acquired — activate the project
        if project.status in ("planning", "draft", "pending"):
            project.status = "active"
            project.save(update_fields=["status", "updated_at"])

            try:
                from apps.notifications.models import Notification
                from apps.notifications.services import dispatch_workflow_notification

                dispatch_workflow_notification(
                    organization=org,
                    event_key="project_activated_land_complete",
                    recipients=_org_admin_users(org),
                    link_url=f"/projects/{project.id}",
                    fallback_channels=["in_app"],
                    fallback_title=f"Project Activated — {project.name}",
                    fallback_message=(
                        f"All {total} land acquisition(s) for project '{project.name}' are now complete. "
                        f"The project status has been automatically changed to Active."
                    ),
                    fallback_category=Notification.Category.PROJECT_UPDATE,
                    fallback_severity=Notification.Severity.INFO,
                )
            except Exception:
                logger.debug("Land acquisition activation notification skipped", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# GROUP B — DESIGN & PRE-CONSTRUCTION AUTOMATION
# ═══════════════════════════════════════════════════════════════════════


# ── 8. Design Submission → Review Workflow ────────────────────────────


@receiver(pre_save, sender="projects.Drawing")
def capture_drawing_previous_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._prev_approval_state = old.approval_state
        except sender.DoesNotExist:
            instance._prev_approval_state = None
    else:
        instance._prev_approval_state = None


@receiver(post_save, sender="projects.Drawing")
def on_drawing_submitted_for_review(sender, instance, created, **kwargs):
    """Route drawing to reviewers when submitted for review."""
    prev = getattr(instance, "_prev_approval_state", None)
    if not created and prev == instance.approval_state:
        return
    if instance.approval_state != "for_review":
        return

    org = instance.organization
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        # Notify consultants on this project with matching discipline + admins
        from .models import ProjectConsultant
        consultant_users = []
        consultants = ProjectConsultant.objects.filter(
            project=instance.project,
            status="active",
            discipline=instance.discipline,
        )
        for c in consultants:
            # If consultant has a linked user, notify them
            if hasattr(c, "linked_user_id") and c.linked_user_id:
                consultant_users.append(c.linked_user)

        recipients = _org_admin_users(org) + consultant_users

        dispatch_workflow_notification(
            organization=org,
            event_key="drawing_submitted_for_review",
            recipients=recipients,
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Drawing Review — {instance.drawing_number}",
            fallback_message=(
                f"Drawing '{instance.drawing_number} — {instance.title}' ({instance.get_discipline_display()}) "
                f"has been submitted for review on project '{instance.project.name}'. "
                f"Submitted by {instance.submitted_by or 'Unknown'}."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Drawing review routing skipped", exc_info=True)


# ── 9. Design Approval → Version Lock + Release ──────────────────────


@receiver(post_save, sender="projects.Drawing")
def on_drawing_approved_lock_and_release(sender, instance, created, **kwargs):
    """When a drawing is approved for construction, lock it and notify construction team."""
    prev = getattr(instance, "_prev_approval_state", None)
    if created or prev == instance.approval_state:
        return
    if instance.approval_state != "afc":
        return

    org = instance.organization

    # Mark all previous revisions as superseded
    from .models import DrawingRevision
    DrawingRevision.objects.filter(
        drawing=instance,
    ).exclude(approval_state="afc").update(approval_state="superseded")

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="drawing_approved_for_construction",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Drawing AFC — {instance.drawing_number}",
            fallback_message=(
                f"Drawing '{instance.drawing_number} — {instance.title}' has been Approved for Construction (AFC) "
                f"at revision {instance.current_revision}. Previous revisions are now superseded. "
                f"Construction team may proceed with this version."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Drawing AFC notification skipped", exc_info=True)


# ── 10. Design Revision → Change Impact Analysis ─────────────────────


@receiver(post_save, sender="projects.DrawingRevision")
def on_drawing_revision_impact_analysis(sender, instance, created, **kwargs):
    """When a new drawing revision is created, flag potential cost/schedule impact."""
    if not created:
        return

    drawing = instance.drawing
    org = drawing.organization

    # Only trigger impact analysis if the drawing was previously AFC
    if drawing.approval_state != "afc":
        return

    # Auto-create a variation order draft if there's a change description
    if instance.change_description:
        from .models import ProjectVariationOrder
        vo, vo_created = ProjectVariationOrder.objects.get_or_create(
            organization=org,
            project=drawing.project,
            title=f"Design Change: {drawing.drawing_number} {instance.revision_code}",
            defaults={
                "variation_number": f"VO-DRG-{drawing.drawing_number}-{instance.revision_code}",
                "description": (
                    f"Design revision on drawing {drawing.drawing_number} — {drawing.title}.\n\n"
                    f"Change: {instance.change_description}\n"
                    f"Submitted by: {instance.submitted_by}"
                ),
                "status": "draft",
            },
        )

        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="design_revision_impact",
                recipients=_org_admin_users(org),
                link_url=f"/projects/{drawing.project_id}",
                fallback_channels=["in_app"],
                fallback_title=f"Design Change Impact — {drawing.drawing_number}",
                fallback_message=(
                    f"Drawing '{drawing.drawing_number}' has a new revision ({instance.revision_code}) "
                    f"after being Approved for Construction. Change: {instance.change_description[:100]}. "
                    f"A draft Variation Order has been auto-created for cost/schedule impact assessment."
                ),
                fallback_category=Notification.Category.ESCALATION_ALERT,
                fallback_severity=Notification.Severity.WARNING,
            )
        except Exception:
            logger.debug("Design revision impact notification skipped", exc_info=True)


# ── 11. BOQ Finalization → Procurement Trigger ────────────────────────


@receiver(pre_save, sender="inventory.BillOfMaterials")
def capture_bom_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_bom_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_bom_status = None
    else:
        instance._prev_bom_status = None


@receiver(post_save, sender="inventory.BillOfMaterials")
def on_bom_approved_create_procurement(sender, instance, created, **kwargs):
    """When a BOM is approved, auto-create a purchase requisition from its items."""
    if created:
        return
    prev = getattr(instance, "_prev_bom_status", None)
    if prev == instance.status:
        return
    if instance.status != "approved":
        return

    org = instance.organization
    from apps.procurement.models import PurchaseRequisition, PurchaseRequisitionItem
    from apps.inventory.models import BOMItem
    from django.utils import timezone as tz

    items = BOMItem.objects.filter(bom=instance).order_by("sort_order")
    if not items.exists():
        return

    # Group items by category/section into procurement packages
    categories = {}
    for item in items:
        cat = item.category or item.section or "General"
        categories.setdefault(cat, []).append(item)

    for cat_name, cat_items in categories.items():
        pr = PurchaseRequisition.objects.create(
            organization=org,
            title=f"BOQ Procurement — {instance.name} — {cat_name}",
            requester="System (BOQ Finalization)",
            project=instance.project,
            priority="medium",
            required_date=tz.localdate() + timedelta(days=21),
            justification=f"Auto-generated from approved BOQ '{instance.bom_number} — {instance.name}', category: {cat_name}.",
        )
        for idx, item in enumerate(cat_items):
            PurchaseRequisitionItem.objects.create(
                requisition=pr,
                description=item.material_name,
                quantity=item.quantity,
                unit_of_measure=item.unit_of_measure or "ea",
                estimated_unit_price=item.unit_cost or Decimal("0"),
                sort_order=idx,
            )
        pr.recalculate_totals()

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="boq_procurement_triggered",
            recipients=_org_admin_users(org),
            link_url="/procurement/requisitions",
            fallback_channels=["in_app"],
            fallback_title=f"BOQ → Procurement — {instance.name}",
            fallback_message=(
                f"BOQ '{instance.bom_number}' has been approved. "
                f"{len(categories)} procurement package(s) created with {items.count()} line items. "
                f"Review and submit the purchase requisitions."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("BOQ procurement trigger notification skipped", exc_info=True)


# ── 12. Permit Approval → Construction Readiness ─────────────────────


@receiver(pre_save, sender="projects.ProjectPermit")
def capture_permit_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_permit_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_permit_status = None
    else:
        instance._prev_permit_status = None


@receiver(post_save, sender="projects.ProjectPermit")
def on_permit_approved_unlock_construction(sender, instance, created, **kwargs):
    """When a permit is approved, check if all critical permits are done → unlock mobilization."""
    prev = getattr(instance, "_prev_permit_status", None)
    if prev == instance.status:
        return
    if instance.status not in ("approved", "conditional"):
        return

    project = instance.project
    org = instance.organization

    # Check if all critical-path permits are approved
    from .models import ProjectPermit, ProjectSiteMobilization
    critical_permits = ProjectPermit.objects.filter(project=project, is_critical_path=True)
    all_approved = not critical_permits.filter(status__in=["not_started", "application_filed", "under_review", "clarification"]).exists()

    actions = [f"Permit '{instance.name}' approved"]

    if all_approved and critical_permits.exists():
        # Unlock site mobilization
        mobilization = ProjectSiteMobilization.objects.filter(project=project).first()
        if mobilization and not mobilization.actual_start_date:
            actions.append("All critical permits cleared — site mobilization unlocked")

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="permit_approved_construction_ready",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{project.id}",
            fallback_channels=["in_app"],
            fallback_title=f"Permit Approved — {instance.name}",
            fallback_message=". ".join(actions) + f" on project '{project.name}'.",
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Permit approval notification skipped", exc_info=True)


# ── 13. Procurement Plan Approval → Tender Release ───────────────────


@receiver(pre_save, sender="projects.ProcurementPackage")
def capture_package_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_package_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_package_status = None
    else:
        instance._prev_package_status = None


@receiver(post_save, sender="projects.ProcurementPackage")
def on_package_tendering_create_rfq(sender, instance, created, **kwargs):
    """When a procurement package moves to 'tendering', auto-create an RFQ."""
    prev = getattr(instance, "_prev_package_status", None)
    if prev == instance.status:
        return
    if instance.status != "tendering":
        return

    plan = instance.plan
    project = plan.project
    org = plan.organization

    from apps.procurement.models import RequestForQuotation

    # Create RFQ linked to this package
    rfq, rfq_created = RequestForQuotation.objects.get_or_create(
        organization=org,
        title=f"RFQ — {instance.name}",
        defaults={
            "project": project,
            "status": "open",
            "description": (
                f"Request for Quotation for procurement package '{instance.name}' "
                f"on project '{project.name}'.\n\n"
                f"Estimated budget: ₦{instance.estimated_budget:,.2f}\n"
                f"Description: {instance.description}"
            ),
            "submission_deadline": instance.tender_return_date,
        },
    )

    if rfq_created:
        # Copy bidders to RFQ as invited vendors
        for bidder in instance.bidders.all():
            # Just notify — the RFQ model handles vendor responses
            pass

        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="procurement_package_rfq_created",
                recipients=_org_admin_users(org),
                link_url="/procurement/rfqs",
                fallback_channels=["in_app"],
                fallback_title=f"RFQ Created — {instance.name}",
                fallback_message=(
                    f"Procurement package '{instance.name}' is now in tendering. "
                    f"RFQ '{rfq.title}' has been auto-created. "
                    f"Deadline: {instance.tender_return_date or 'Not set'}."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.INFO,
            )
        except Exception:
            logger.debug("Package RFQ creation notification skipped", exc_info=True)


# ── 14. Financing Secured → Budget Activation ────────────────────────


@receiver(pre_save, sender="projects.FinancingSource")
def capture_financing_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_financing_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_financing_status = None
    else:
        instance._prev_financing_status = None


@receiver(post_save, sender="projects.FinancingSource")
def on_financing_active_activate_budget(sender, instance, created, **kwargs):
    """When a financing source becomes active, activate the project budget for spending."""
    prev = getattr(instance, "_prev_financing_status", None)
    if prev == instance.status:
        return
    if instance.status != "active":
        return

    project = instance.project
    org = instance.organization

    actions = [f"Financing '{instance.name}' ({instance.get_source_type_display()}) activated"]

    # Activate the development budget if it's still in draft
    from .models import DevelopmentBudget
    draft_budgets = DevelopmentBudget.objects.filter(
        project=project, status="draft",
    )
    for budget in draft_budgets:
        budget.status = "baseline"
        budget.is_baseline = True
        budget.save(update_fields=["status", "is_baseline", "updated_at"])
        actions.append(f"Budget v{budget.version} activated to baseline")

    # Check total financing vs project budget
    from django.db.models import Sum as DbSum
    total_financing = project.financing_sources.filter(
        status="active",
    ).aggregate(total=DbSum("committed_amount"))["total"] or Decimal("0")

    if project.budget and total_financing >= project.budget:
        actions.append(f"Project fully funded (₦{total_financing:,.0f} / ₦{project.budget:,.0f})")
    elif project.budget:
        gap = project.budget - total_financing
        actions.append(f"Funding gap: ₦{gap:,.0f} remaining")

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="financing_activated_budget_enabled",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{project.id}",
            fallback_channels=["in_app"],
            fallback_title=f"Financing Active — {instance.name}",
            fallback_message=". ".join(actions) + f". Contractor payments and procurement spending are now enabled for project '{project.name}'.",
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Financing activation notification skipped", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# GROUP D — CONSTRUCTION EXECUTION AUTOMATION
# ═══════════════════════════════════════════════════════════════════════


# ── 22. Work Package Activation → Task Deployment ────────────────────


@receiver(post_save, sender="projects.ProjectWorkPackage")
def on_work_package_assigned_deploy_tasks(sender, instance, created, **kwargs):
    """When a work package gets a contractor + dates, create tasks from its scope."""
    if not instance.contractor_id or not instance.start_date:
        return
    # Only trigger when contractor is newly assigned (check if tasks already exist)
    existing_tasks = ProjectTask.objects.filter(
        phase=instance.phase,
        work_package=instance.name,
    ).exists() if instance.phase_id else False
    if existing_tasks:
        return

    if not instance.phase_id:
        return

    org = instance.organization
    # Create a default task for the work package
    ProjectTask.objects.create(
        organization=org,
        phase=instance.phase,
        name=instance.name,
        description=instance.scope_description or "",
        work_package=instance.name,
        status="pending",
        priority="medium",
        assigned_to=instance.contractor.name if instance.contractor else "",
        due_date=instance.end_date,
    )

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="work_package_activated",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Work Package Activated — {instance.name}",
            fallback_message=(
                f"Work package '{instance.name}' has been assigned to "
                f"{instance.contractor.name if instance.contractor else 'TBD'} "
                f"({instance.start_date} → {instance.end_date or 'TBD'}). "
                f"Tasks deployed to phase '{instance.phase.name}'."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Work package activation notification skipped", exc_info=True)


# ── 25. Labour Attendance → Productivity Metrics ─────────────────────


@receiver(post_save, sender="projects.ProjectWorkforceLog")
def on_workforce_log_calculate_productivity(sender, instance, created, **kwargs):
    """Calculate productivity score from workforce log data."""
    if not created:
        return

    total_workers = (
        (instance.laborers_count or 0)
        + (instance.skilled_count or 0)
        + (instance.supervisors_count or 0)
    )
    if total_workers == 0:
        return

    # Calculate productivity: output per worker based on overtime ratio
    overtime = float(instance.overtime_hours or 0)
    # Simple productivity score: 1.0 = standard, >1.0 = above avg, <1.0 = below
    # Based on: attendance present + no excessive overtime = good productivity
    if instance.daily_attendance == "present":
        base_score = Decimal("1.00")
    elif instance.daily_attendance == "late":
        base_score = Decimal("0.85")
    elif instance.daily_attendance == "half_day":
        base_score = Decimal("0.50")
    else:
        base_score = Decimal("0.00")

    # Overtime penalty (diminishing returns above 2 hours)
    if overtime > 4:
        base_score = base_score * Decimal("0.90")
    elif overtime > 2:
        base_score = base_score * Decimal("0.95")

    if instance.productivity != base_score:
        instance.productivity = base_score
        ProjectWorkforceLog.objects.filter(pk=instance.pk).update(productivity=base_score)


# ── 26. Equipment Usage → Cost Allocation ────────────────────────────


@receiver(post_save, sender="projects.EquipmentDeploymentLog")
def on_equipment_deployed_allocate_cost(sender, instance, created, **kwargs):
    """When equipment is deployed, create a cost entry for the usage."""
    if not created:
        return

    equipment = instance.equipment
    project = instance.project

    # Calculate cost from hours or daily rate
    hours = float(instance.hours_used or 0)
    hourly_rate = float(equipment.internal_hourly_rate or 0)
    daily_rate = float(equipment.internal_daily_rate or 0)

    if hours > 0 and hourly_rate > 0:
        cost = Decimal(str(hours * hourly_rate))
    elif daily_rate > 0:
        # Calculate days from deployed/returned dates
        if instance.returned_date:
            days = max(1, (instance.returned_date - instance.deployed_date).days)
        else:
            days = 1
        cost = Decimal(str(days * daily_rate))
    else:
        return  # No rate info, can't allocate

    from .models import ProjectCostEntry
    ProjectCostEntry.objects.create(
        organization=equipment.organization,
        project=project,
        phase=project.phases.filter(status="in_progress").order_by("sort_order").first(),
        category="equipment",
        description=f"Equipment: {equipment.asset_id} — {equipment.name} ({instance.hours_used}h)",
        amount=cost,
        entry_date=instance.deployed_date,
        source_reference=f"deployment-{instance.pk}",
    )


# ── 27. Inspection Failure → Issue Ticket ────────────────────────────


@receiver(pre_save, sender="projects.ProjectExecutionInspection")
def capture_inspection_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_inspection_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_inspection_status = None
    else:
        instance._prev_inspection_status = None


@receiver(post_save, sender="projects.ProjectExecutionInspection")
def on_inspection_failed_create_rework(sender, instance, created, **kwargs):
    """When an inspection fails, auto-create a rework task."""
    prev = getattr(instance, "_prev_inspection_status", None)
    if prev == instance.status:
        return
    if instance.status != "failed":
        return

    org = instance.organization
    phase = instance.phase or instance.project.phases.order_by("sort_order").first()
    if not phase:
        return

    findings = []
    if hasattr(instance, "critical_findings") and instance.critical_findings:
        findings.append(f"Critical: {instance.critical_findings}")
    if hasattr(instance, "major_findings") and instance.major_findings:
        findings.append(f"Major: {instance.major_findings}")
    if hasattr(instance, "minor_findings") and instance.minor_findings:
        findings.append(f"Minor: {instance.minor_findings}")

    task = ProjectTask.objects.create(
        organization=org,
        phase=phase,
        name=f"REWORK: {instance.inspection_number} — {instance.get_inspection_type_display()}",
        description=(
            f"Auto-created from failed inspection {instance.inspection_number}.\n\n"
            + "\n".join(findings)
            + (f"\n\nCorrective actions: {instance.corrective_actions}" if hasattr(instance, "corrective_actions") and instance.corrective_actions else "")
        ),
        status="pending",
        priority="high",
        work_package="Rework & Defects",
    )

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="inspection_failed_rework_created",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Inspection Failed — {instance.inspection_number}",
            fallback_message=(
                f"Inspection {instance.inspection_number} ({instance.get_inspection_type_display()}) "
                f"has FAILED on project '{instance.project.name}'. "
                f"A rework task has been auto-created. " + (" ".join(findings[:2]) if findings else "")
            ),
            fallback_category=Notification.Category.ESCALATION_ALERT,
            fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Inspection failure notification skipped", exc_info=True)


# ── 28. Inspection Pass → Progress Certification ─────────────────────


@receiver(post_save, sender="projects.ProjectExecutionInspection")
def on_inspection_passed_certify_progress(sender, instance, created, **kwargs):
    """When an inspection passes, check if phase milestones can be certified."""
    prev = getattr(instance, "_prev_inspection_status", None)
    if prev == instance.status:
        return
    if instance.status != "passed":
        return

    org = instance.organization
    project = instance.project

    # Check if all inspections for this phase have passed
    if instance.phase_id:
        phase = instance.phase
        total_inspections = phase.execution_inspections.count()
        passed_inspections = phase.execution_inspections.filter(status="passed").count()

        if total_inspections > 0 and total_inspections == passed_inspections:
            # All inspections passed — flag milestones as eligible
            from .models import ProjectMilestone
            pending_milestones = ProjectMilestone.objects.filter(
                project=project,
                phase=phase,
                reached=False,
            )
            milestone_names = []
            for ms in pending_milestones:
                milestone_names.append(ms.name)

            try:
                from apps.notifications.models import Notification
                from apps.notifications.services import dispatch_workflow_notification

                dispatch_workflow_notification(
                    organization=org,
                    event_key="inspection_passed_certified",
                    recipients=_org_admin_users(org),
                    link_url=f"/projects/{project.id}",
                    fallback_channels=["in_app"],
                    fallback_title=f"Phase Inspections Complete — {phase.name}",
                    fallback_message=(
                        f"All {total_inspections} inspection(s) for phase '{phase.name}' on "
                        f"project '{project.name}' have passed. "
                        + (f"Milestones eligible for certification: {', '.join(milestone_names[:3])}." if milestone_names else "Phase is ready for milestone sign-off.")
                        + " Payment applications may now proceed."
                    ),
                    fallback_category=Notification.Category.PROJECT_UPDATE,
                    fallback_severity=Notification.Severity.INFO,
                )
            except Exception:
                logger.debug("Inspection pass notification skipped", exc_info=True)


# ── 29. RFI Submission → Response Workflow ───────────────────────────


@receiver(pre_save, sender="projects.RFI")
def capture_rfi_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_rfi_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_rfi_status = None
    else:
        instance._prev_rfi_status = None


@receiver(post_save, sender="projects.RFI")
def on_rfi_submitted_route_to_consultant(sender, instance, created, **kwargs):
    """When an RFI is submitted (status=open), route to the relevant consultant."""
    if not created:
        prev = getattr(instance, "_prev_rfi_status", None)
        if prev == instance.status:
            return
    if instance.status != "open":
        return

    org = instance.organization
    project = instance.project

    # Find consultants with matching discipline
    from .models import ProjectConsultant
    discipline_map = {
        "structural": "structural",
        "electrical": "mep",
        "mechanical": "mep",
        "civil": "structural",
        "architectural": "architectural",
        "plumbing": "mep",
        "fire": "mep",
    }
    consultant_discipline = discipline_map.get(instance.discipline, instance.discipline)

    consultants = ProjectConsultant.objects.filter(
        project=project,
        status="active",
        discipline=consultant_discipline,
    )

    ball_in_court = ""
    if consultants.exists():
        ball_in_court = consultants.first().firm_name
        if not instance.ball_in_court:
            instance.ball_in_court = ball_in_court
            RFI.objects.filter(pk=instance.pk).update(ball_in_court=ball_in_court)

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        urgency_label = instance.get_urgency_display() if hasattr(instance, "get_urgency_display") else instance.urgency
        dispatch_workflow_notification(
            organization=org,
            event_key="rfi_submitted_routed",
            recipients=_org_admin_users(org),
            link_url=f"/construction/rfis",
            fallback_channels=["in_app"],
            fallback_title=f"RFI Submitted — {instance.rfi_number}",
            fallback_message=(
                f"RFI '{instance.rfi_number}: {instance.subject}' has been submitted "
                f"({instance.get_discipline_display()}, {urgency_label}). "
                + (f"Routed to: {ball_in_court}. " if ball_in_court else "No matching consultant found — manual routing required. ")
                + f"SLA: {instance.response_sla_hours}h."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.WARNING if instance.urgency == "high" else Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("RFI routing notification skipped", exc_info=True)


# ── 30. Site Instruction Issued → Scope Update ───────────────────────


@receiver(pre_save, sender="projects.SiteInstruction")
def capture_si_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_si_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_si_status = None
    else:
        instance._prev_si_status = None


@receiver(post_save, sender="projects.SiteInstruction")
def on_si_issued_update_scope(sender, instance, created, **kwargs):
    """When a site instruction is issued with cost/schedule impact, create a variation order."""
    prev = getattr(instance, "_prev_si_status", None)
    if prev == instance.status:
        return
    if instance.status != "issued":
        return

    org = instance.organization
    project = instance.project
    actions = [f"Site Instruction '{instance.si_number}' issued"]

    # If financial or schedule impact, auto-create variation order
    if (instance.has_financial_impact or instance.schedule_impact_days > 0) and not instance.linked_variation_id:
        from .models import ProjectVariationOrder
        vo = ProjectVariationOrder.objects.create(
            organization=org,
            project=project,
            variation_number=f"VO-SI-{instance.si_number}",
            title=f"SI Impact: {instance.title}",
            description=(
                f"Auto-created from Site Instruction {instance.si_number}.\n\n"
                f"{instance.description}\n\n"
                f"Cost impact: {'₦{:,.2f}'.format(instance.estimated_cost_impact) if instance.has_financial_impact else 'None'}\n"
                f"Schedule impact: {instance.schedule_impact_days} day(s)"
            ),
            status="draft",
            contract_value=instance.estimated_cost_impact if instance.has_financial_impact else Decimal("0"),
        )
        # Link the VO back to the SI
        SiteInstruction.objects.filter(pk=instance.pk).update(linked_variation=vo)
        actions.append(f"Variation Order '{vo.variation_number}' auto-created")

        if instance.has_financial_impact:
            actions.append(f"Estimated cost impact: ₦{instance.estimated_cost_impact:,.2f}")
        if instance.schedule_impact_days > 0:
            actions.append(f"Schedule impact: {instance.schedule_impact_days} day(s)")

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="site_instruction_issued",
            recipients=_org_admin_users(org),
            link_url=f"/construction/site-instructions",
            fallback_channels=["in_app"],
            fallback_title=f"Site Instruction Issued — {instance.si_number}",
            fallback_message=". ".join(actions) + f" on project '{project.name}'.",
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.WARNING if instance.has_financial_impact else Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("SI issued notification skipped", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# GROUP F — FINANCE & PAYMENTS AUTOMATION (Project-side)
# ═══════════════════════════════════════════════════════════════════════


# ── 37. Interim Valuation Submission → Certification Workflow ────────


@receiver(pre_save, sender="projects.InterimValuation")
def capture_valuation_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_valuation_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_valuation_status = None
    else:
        instance._prev_valuation_status = None


@receiver(post_save, sender="projects.InterimValuation")
def on_valuation_submitted_route_to_qs(sender, instance, created, **kwargs):
    """When a valuation is submitted, route to QS/certifier for review."""
    prev = getattr(instance, "_prev_valuation_status", None)
    if created and instance.status != "submitted":
        return
    if not created and prev == instance.status:
        return
    if instance.status != "submitted":
        return

    org = instance.organization

    # Auto-transition to under_review
    from .models import InterimValuation
    InterimValuation.objects.filter(pk=instance.pk).update(status="under_review")

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        # Route to QS consultants on the project
        from .models import ProjectConsultant
        qs_users = []
        qs_consultants = ProjectConsultant.objects.filter(
            project=instance.project,
            status="active",
            discipline="quantity_surveying",
        )
        for c in qs_consultants:
            pass  # Consultants may not have linked users yet

        dispatch_workflow_notification(
            organization=org,
            event_key="valuation_submitted_for_review",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.project_id}",
            fallback_channels=["in_app"],
            fallback_title=f"Valuation Submitted — {instance.valuation_number}",
            fallback_message=(
                f"Interim valuation '{instance.valuation_number}' for contractor "
                f"'{instance.contractor_name}' has been submitted for certification. "
                f"Gross value: ₦{instance.gross_value:,.2f}, "
                f"This period: ₦{instance.this_period_value:,.2f}. "
                f"QS review and certification is required."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Valuation submission notification skipped", exc_info=True)


# ── 38. Certification Approval → Payment Request ─────────────────────


@receiver(post_save, sender="projects.InterimValuation")
def on_valuation_certified_create_payment(sender, instance, created, **kwargs):
    """When a valuation is certified, auto-create a Bill for the net payable amount."""
    prev = getattr(instance, "_prev_valuation_status", None)
    if created or prev == instance.status:
        return
    if instance.status != "certified":
        return

    org = instance.organization
    project = instance.project

    # Don't duplicate — check if a bill already exists for this valuation
    from apps.finance.models import Bill
    existing = Bill.objects.filter(
        organization=org,
        notes__contains=instance.valuation_number,
    ).exists()
    if existing:
        return

    # Find or match a vendor for the contractor
    from apps.procurement.models import Vendor
    vendor = Vendor.objects.filter(
        organization=org,
        name__icontains=instance.contractor_name,
        is_active=True,
    ).first()

    if not vendor:
        # Can't create bill without vendor — notify admin
        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="valuation_certified_no_vendor",
                recipients=_org_admin_users(org),
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Payment Pending — {instance.valuation_number}",
                fallback_message=(
                    f"Valuation '{instance.valuation_number}' certified for ₦{instance.net_payable:,.2f} "
                    f"but no matching vendor found for '{instance.contractor_name}'. "
                    f"Create the vendor record and manually generate the bill."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.WARNING,
            )
        except Exception:
            pass
        return

    from django.utils import timezone as tz
    bill = Bill.objects.create(
        organization=org,
        vendor=vendor,
        project=project,
        purchase_order=None,
        status="draft",
        issue_date=instance.certified_date or tz.localdate(),
        due_date=(instance.certified_date or tz.localdate()) + timedelta(days=30),
        subtotal=instance.net_payable,
        tax_amount=Decimal("0"),
        total_amount=instance.net_payable,
        notes=f"Auto-generated from certified valuation {instance.valuation_number}. Retention: ₦{instance.retention_amount:,.2f} held.",
    )

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="valuation_certified_bill_created",
            recipients=_org_admin_users(org),
            link_url="/finance/bills",
            fallback_channels=["in_app"],
            fallback_title=f"Payment Bill Created — {bill.bill_number}",
            fallback_message=(
                f"Valuation '{instance.valuation_number}' certified. Bill '{bill.bill_number}' "
                f"created for ₦{instance.net_payable:,.2f} (after ₦{instance.retention_amount:,.2f} retention). "
                f"Vendor: {vendor.name}. Awaiting payment approval."
            ),
            fallback_category=Notification.Category.PROCUREMENT_ORDER,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Valuation→bill notification skipped", exc_info=True)


# ── 41. Retention Tracking → Holdback Management ────────────────────


@receiver(post_save, sender="projects.InterimValuation")
def on_valuation_auto_deduct_retention(sender, instance, created, **kwargs):
    """Auto-calculate retention deduction when valuation is saved."""
    if instance.retention_pct and instance.this_period_value:
        correct_retention = instance.this_period_value * instance.retention_pct / Decimal("100")
        correct_net = instance.this_period_value - correct_retention
        if instance.retention_amount != correct_retention or instance.net_payable != correct_net:
            from .models import InterimValuation
            InterimValuation.objects.filter(pk=instance.pk).update(
                retention_amount=correct_retention,
                net_payable=correct_net,
            )


@receiver(pre_save, sender="projects.ProjectCloseout")
def capture_closeout_previous_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._prev_closeout_status = old.status
        except sender.DoesNotExist:
            instance._prev_closeout_status = None
    else:
        instance._prev_closeout_status = None


@receiver(post_save, sender="projects.ProjectCloseout")
def on_closeout_complete_release_retention(sender, instance, created, **kwargs):
    """When project closeout is completed, release retained amounts."""
    prev = getattr(instance, "_prev_closeout_status", None)
    if prev == instance.status:
        return
    if instance.status != "completed":
        return

    org = instance.organization
    project = instance.project

    # Sum all retention held across valuations
    from .models import InterimValuation
    from django.db.models import Sum as DbSum
    total_retention = InterimValuation.objects.filter(
        project=project,
        status__in=["certified", "paid"],
    ).aggregate(total=DbSum("retention_amount"))["total"] or Decimal("0")

    # Update closeout retention fields
    from .models import ProjectCloseout
    if total_retention > 0 and not instance.retention_released:
        from django.utils import timezone as tz
        ProjectCloseout.objects.filter(pk=instance.pk).update(
            retention_held=total_retention,
            retention_released=total_retention,
            retention_release_date=tz.localdate(),
        )

        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="retention_released",
                recipients=_org_admin_users(org),
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Retention Released — {project.name}",
                fallback_message=(
                    f"Project '{project.name}' closeout completed. "
                    f"Total retention of ₦{total_retention:,.2f} has been released. "
                    f"Final account payments can now be processed."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.INFO,
            )
        except Exception:
            logger.debug("Retention release notification skipped", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# GROUP G — COMPLETION & HANDOVER AUTOMATION
# ═══════════════════════════════════════════════════════════════════════


# ── 43. Snagging List Created → Defect Assignment ────────────────────


@receiver(post_save, sender="projects.SnagListItem")
def on_snag_created_assign_defect(sender, instance, created, **kwargs):
    """When a snag item is created, auto-create a rework task and notify."""
    if not created:
        return

    closeout = instance.closeout
    project = closeout.project
    org = closeout.organization

    # Create a rework task in the last active phase
    phase = project.phases.order_by("-sort_order").first()
    if phase:
        ProjectTask.objects.create(
            organization=org,
            phase=phase,
            name=f"SNAG: {instance.location} — {instance.description[:60]}",
            description=(
                f"Snagging defect reported at: {instance.location}\n\n"
                f"{instance.description}\n\n"
                f"Contractor: {instance.responsible_contractor or 'Unassigned'}"
            ),
            status="pending",
            priority="high",
            assigned_to=instance.responsible_contractor or "",
            work_package="Snagging & Defects",
        )

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="snag_item_created",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{project.id}",
            fallback_channels=["in_app"],
            fallback_title=f"Snag Reported — {instance.location}",
            fallback_message=(
                f"New snagging defect on project '{project.name}': {instance.description[:100]}. "
                f"Location: {instance.location}. "
                + (f"Assigned to: {instance.responsible_contractor}. " if instance.responsible_contractor else "No contractor assigned. ")
                + "A rework task has been auto-created."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Snag creation notification skipped", exc_info=True)


@receiver(post_save, sender="projects.CommissioningPunchItem")
def on_punch_item_created_assign(sender, instance, created, **kwargs):
    """When a commissioning punch item is created, notify for assignment."""
    if not created:
        return

    plan = instance.plan
    project = plan.project
    org = plan.organization

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="punch_item_created",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{project.id}",
            fallback_channels=["in_app"],
            fallback_title=f"Punch Item — {instance.item_number}",
            fallback_message=(
                f"Commissioning punch item '{instance.item_number}' created: {instance.description[:100]}. "
                f"Priority: {instance.get_priority_display()}. "
                + (f"Assigned to: {instance.assigned_to}. " if instance.assigned_to else "Awaiting assignment. ")
                + f"Location: {instance.location or 'Not specified'}."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.WARNING if instance.priority == "critical" else Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Punch item notification skipped", exc_info=True)


# ── 44. All Defects Closed → Practical Completion ────────────────────


@receiver(pre_save, sender="projects.SnagListItem")
def capture_snag_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_snag_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_snag_status = None
    else:
        instance._prev_snag_status = None


@receiver(post_save, sender="projects.SnagListItem")
def on_snag_resolved_check_completion(sender, instance, created, **kwargs):
    """When a snag is resolved/accepted, check if ALL snags are done → trigger practical completion."""
    if created:
        return
    prev = getattr(instance, "_prev_snag_status", None)
    if prev == instance.status:
        return
    if instance.status not in ("resolved", "accepted"):
        return

    closeout = instance.closeout
    project = closeout.project
    org = closeout.organization

    # Check if ALL snags for this closeout are resolved/accepted
    from .models import SnagListItem
    total_snags = SnagListItem.objects.filter(closeout=closeout).count()
    closed_snags = SnagListItem.objects.filter(
        closeout=closeout,
        status__in=["resolved", "accepted"],
    ).count()

    if total_snags == 0 or total_snags != closed_snags:
        return

    # All snags resolved — update closeout
    from .models import ProjectCloseout
    from django.utils import timezone as tz
    updates = {}
    if not closeout.snags_resolved:
        updates["snags_resolved"] = True
    if not closeout.practical_completion_date:
        updates["practical_completion_date"] = tz.localdate()

    if updates:
        updates["updated_at"] = tz.now()
        ProjectCloseout.objects.filter(pk=closeout.pk).update(**updates)

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        dispatch_workflow_notification(
            organization=org,
            event_key="all_snags_resolved_practical_completion",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{project.id}",
            fallback_channels=["in_app"],
            fallback_title=f"Practical Completion — {project.name}",
            fallback_message=(
                f"All {total_snags} snagging defect(s) on project '{project.name}' have been resolved. "
                f"Practical completion date has been set. "
                f"Final inspections and handover preparation can now proceed."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Practical completion notification skipped", exc_info=True)


# Also monitor CommissioningPunchItem closures
@receiver(pre_save, sender="projects.CommissioningPunchItem")
def capture_punch_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_punch_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_punch_status = None
    else:
        instance._prev_punch_status = None


@receiver(post_save, sender="projects.CommissioningPunchItem")
def on_punch_closed_check_commissioning(sender, instance, created, **kwargs):
    """When all punch items for a commissioning plan are closed, notify."""
    if created:
        return
    prev = getattr(instance, "_prev_punch_status", None)
    if prev == instance.status:
        return
    if instance.status not in ("verified", "closed"):
        return

    plan = instance.plan
    from .models import CommissioningPunchItem
    total = CommissioningPunchItem.objects.filter(plan=plan).count()
    closed = CommissioningPunchItem.objects.filter(plan=plan, status__in=["verified", "closed"]).count()

    if total > 0 and total == closed:
        project = plan.project
        org = plan.organization

        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="commissioning_punch_items_cleared",
                recipients=_org_admin_users(org),
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Commissioning Complete — {plan.name}",
                fallback_message=(
                    f"All {total} punch item(s) for commissioning plan '{plan.name}' on project "
                    f"'{project.name}' have been resolved and verified. "
                    f"The system is ready for final handover."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.INFO,
            )
        except Exception:
            logger.debug("Commissioning completion notification skipped", exc_info=True)


# ── 45. Project Closeout → Asset Transfer to Facilities ──────────────


@receiver(post_save, sender="projects.ProjectCloseout")
def on_closeout_completed_transfer_assets(sender, instance, created, **kwargs):
    """
    When project closeout is completed, transfer project data to:
    1. Facility registry (create/link facility record)
    2. Asset component register (from warranty trackers + equipment)
    3. Maintenance schedules (from warranty dates)
    """
    prev = getattr(instance, "_prev_closeout_status", None)
    if prev == instance.status:
        return
    if instance.status != "completed":
        return

    project = instance.project
    org = instance.organization
    actions = []

    # 1. Create/link facility registry entry
    if project.property_id:
        try:
            from apps.facility_management.models import Facility

            facility, fac_created = Facility.objects.get_or_create(
                organization=org,
                property=project.property,
                defaults={
                    "facility_code": f"FAC-{project.property.code if hasattr(project.property, 'code') else project.pk}",
                    "facility_classification": "residential",
                    "ownership_type": "owned",
                },
            )
            if fac_created:
                actions.append(f"Facility registry '{facility.facility_code}' created")
            else:
                actions.append(f"Facility registry '{facility.facility_code}' linked")
        except Exception:
            logger.debug("Facility creation skipped", exc_info=True)

    # 2. Transfer warranty items to asset register
    from .models import WarrantyTracker
    warranties = WarrantyTracker.objects.filter(closeout=instance)
    assets_created = 0

    for warranty in warranties:
        try:
            from apps.properties.models import AssetComponent

            if not project.property_id:
                continue

            # Check if asset already exists
            existing = AssetComponent.objects.filter(
                organization=org,
                property=project.property,
                name=warranty.asset_system,
            ).exists()
            if existing:
                continue

            # Generate unique component_id
            last_asset = AssetComponent.objects.filter(
                component_id__startswith="AST-",
            ).order_by("-component_id").values_list("component_id", flat=True).first()
            seq = int(last_asset.split("-")[1]) + 1 if last_asset else 1

            AssetComponent.objects.create(
                organization=org,
                property=project.property,
                component_id=f"AST-{seq:04d}",
                name=warranty.asset_system,
                category="mechanical",  # default — can be refined
                description=f"Transferred from project '{project.name}' closeout. Provider: {warranty.provider}.",
                installation_date=warranty.warranty_start,
                commissioned_date=warranty.warranty_start,
                warranty_expiry=warranty.warranty_end,
                lifecycle_stage="operate",
                condition_rating="excellent",
                maintenance_frequency="quarterly",
            )
            assets_created += 1
        except Exception:
            logger.debug("Asset transfer skipped for %s", warranty.asset_system, exc_info=True)

    if assets_created:
        actions.append(f"{assets_created} asset(s) transferred to property register")

    # 3. Transfer project equipment to asset register
    from .models import ProjectEquipment
    equipment = ProjectEquipment.objects.filter(
        organization=org,
        project=project,
        ownership_type="owned",
    ) if hasattr(ProjectEquipment, "ownership_type") else ProjectEquipment.objects.none()

    # 4. Update project status to completed
    if project.status != "completed":
        project.status = "completed"
        project.save(update_fields=["status", "updated_at"])
        actions.append("Project status set to Completed")

    # 5. Mark handover as completed on closeout
    if not instance.handover_completed:
        from .models import ProjectCloseout as PC
        PC.objects.filter(pk=instance.pk).update(handover_completed=True)
        actions.append("Handover marked as completed")

    if actions:
        try:
            from apps.notifications.models import Notification
            from apps.notifications.services import dispatch_workflow_notification

            dispatch_workflow_notification(
                organization=org,
                event_key="project_closeout_asset_transfer",
                recipients=_org_admin_users(org),
                link_url=f"/projects/{project.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Project Closeout Complete — {project.name}",
                fallback_message=(
                    f"Project '{project.name}' closeout is complete. "
                    + ". ".join(actions) + ". "
                    + "All project data has been transferred to the facilities and asset management modules."
                ),
                fallback_category=Notification.Category.PROJECT_UPDATE,
                fallback_severity=Notification.Severity.INFO,
            )
        except Exception:
            logger.debug("Closeout asset transfer notification skipped", exc_info=True)


# ═══════════════════════════════════════════════════════════════════════
# WORKFLOW NOTIFICATION SIGNALS
# ═══════════════════════════════════════════════════════════════════════


# ── 1. New Project Created ────────────────────────────────────────────


@receiver(post_save, sender="projects.Project")
def on_project_created_notify(sender, instance, created, **kwargs):
    """Notify admins when a new project is created."""
    if not created:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization

        dispatch_workflow_notification(
            organization=org,
            event_key="project_created",
            recipients=_org_admin_users(org),
            link_url=f"/projects/{instance.id}",
            fallback_channels=["in_app"],
            fallback_title=f"New Project Created — {instance.name}",
            fallback_message=(
                f"A new project '{instance.name}' has been created. "
                f"Please review the project details and assign team members."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Project created notification skipped", exc_info=True)


# ── 2. Permit Status Changed ─────────────────────────────────────────


@receiver(pre_save, sender="projects.ProjectPermit")
def capture_permit_previous_status(sender, instance, **kwargs):
    """Capture previous permit status for change detection."""
    if instance.pk:
        try:
            instance._prev_permit_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_permit_status = None
    else:
        instance._prev_permit_status = None


@receiver(post_save, sender="projects.ProjectPermit")
def on_permit_status_change_notify(sender, instance, created, **kwargs):
    """Notify admins when a permit status changes."""
    if created:
        return

    prev = getattr(instance, "_prev_permit_status", None)
    if prev == instance.status:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        status_display = instance.get_status_display()

        dispatch_workflow_notification(
            organization=org,
            event_key="permit_status_changed",
            recipients=_org_admin_users(org),
            link_url="/projects/approvals-permits",
            fallback_channels=["in_app"],
            fallback_title=f"Permit {status_display} — {instance.name}",
            fallback_message=(
                f"Permit '{instance.name}' ({instance.reference}) on project "
                f"'{instance.project.name}' has been updated to {status_display}. "
                f"Please review any conditions or required follow-up actions."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Permit status change notification skipped", exc_info=True)


# ── 3. Quality Inspection Failed ─────────────────────────────────────


@receiver(pre_save, sender="projects.ProjectExecutionInspection")
def capture_inspection_previous_status(sender, instance, **kwargs):
    """Capture previous inspection status for change detection."""
    if instance.pk:
        try:
            instance._prev_inspection_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_inspection_status = None
    else:
        instance._prev_inspection_status = None


@receiver(post_save, sender="projects.ProjectExecutionInspection")
def on_inspection_failed_notify(sender, instance, created, **kwargs):
    """Notify admins when a quality inspection fails."""
    if created:
        return

    prev = getattr(instance, "_prev_inspection_status", None)
    if prev == instance.status:
        return
    if instance.status != "failed":
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization

        dispatch_workflow_notification(
            organization=org,
            event_key="inspection_failed",
            recipients=_org_admin_users(org),
            link_url="/construction/quality-control",
            fallback_channels=["in_app"],
            fallback_title=f"Quality Inspection Failed — {instance.inspection_number}",
            fallback_message=(
                f"Quality inspection '{instance.inspection_number}' on project "
                f"'{instance.project.name}' has failed. "
                f"Critical findings: {instance.critical_findings}, major: {instance.major_findings}. "
                f"Please review corrective actions immediately."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Inspection failed notification skipped", exc_info=True)


# ── 4. HSE Incident Reported ─────────────────────────────────────────


@receiver(post_save, sender="projects.HSEIncident")
def on_hse_incident_reported_notify(sender, instance, created, **kwargs):
    """Notify admins when an HSE incident is reported."""
    if not created:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization

        # Determine severity based on classification
        if instance.classification in ("major_accident", "fatality"):
            severity = Notification.Severity.CRITICAL
        elif instance.classification in ("minor_injury", "first_aid"):
            severity = Notification.Severity.WARNING
        else:
            severity = Notification.Severity.WARNING

        dispatch_workflow_notification(
            organization=org,
            event_key="hse_incident_reported",
            recipients=_org_admin_users(org),
            link_url="/construction/hse",
            fallback_channels=["in_app"],
            fallback_title=f"HSE Incident Reported — {instance.incident_number}",
            fallback_message=(
                f"HSE incident '{instance.incident_number}' ({instance.get_classification_display()}) "
                f"has been reported on project '{instance.project.name}'. "
                f"Location: {instance.location or 'Not specified'}. "
                f"Immediate review and investigation required."
            ),
            fallback_category=Notification.Category.PROJECT_RISK,
            fallback_severity=severity,
        )
    except Exception:
        logger.debug("HSE incident notification skipped", exc_info=True)


# ── 5. Stage Gate Passed / Failed ────────────────────────────────────


@receiver(pre_save, sender="projects.StageGate")
def capture_stage_gate_previous_status(sender, instance, **kwargs):
    """Capture previous stage gate status for change detection."""
    if instance.pk:
        try:
            instance._prev_gate_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_gate_status = None
    else:
        instance._prev_gate_status = None


@receiver(post_save, sender="projects.StageGate")
def on_stage_gate_decision_notify(sender, instance, created, **kwargs):
    """Notify admins when a stage gate is passed, conditionally approved, or failed."""
    if created:
        return

    prev = getattr(instance, "_prev_gate_status", None)
    if prev == instance.status:
        return
    if instance.status not in ("open", "conditional", "failed"):
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization

        if instance.status == "failed":
            title = f"Stage Gate Failed — {instance.name}"
            message = (
                f"Stage gate '{instance.name}' on project '{instance.project.name}' "
                f"has been rejected. Reason: {instance.rejection_reason or 'Not specified'}. "
                f"Please review the gate requirements and plan corrective actions."
            )
            severity = Notification.Severity.WARNING
        elif instance.status == "conditional":
            title = f"Stage Gate Passed — {instance.name}"
            message = (
                f"Stage gate '{instance.name}' on project '{instance.project.name}' "
                f"has been approved with conditions. Conditions: {instance.conditions or 'See gate details'}. "
                f"Please ensure conditions are met before proceeding."
            )
            severity = Notification.Severity.INFO
        else:
            title = f"Stage Gate Passed — {instance.name}"
            message = (
                f"Stage gate '{instance.name}' on project '{instance.project.name}' "
                f"has been passed. The project may now proceed to the next phase."
            )
            severity = Notification.Severity.INFO

        dispatch_workflow_notification(
            organization=org,
            event_key="stage_gate_decision",
            recipients=_org_admin_users(org),
            link_url="/projects/milestones-stage-gates",
            fallback_channels=["in_app"],
            fallback_title=title,
            fallback_message=message,
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=severity,
        )
    except Exception:
        logger.debug("Stage gate decision notification skipped", exc_info=True)


# ── 6. Commissioning Plan Certified ──────────────────────────────────


@receiver(pre_save, sender="projects.CommissioningPlan")
def capture_commissioning_plan_previous_status(sender, instance, **kwargs):
    """Capture previous commissioning plan status for change detection."""
    if instance.pk:
        try:
            instance._prev_plan_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_plan_status = None
    else:
        instance._prev_plan_status = None


@receiver(post_save, sender="projects.CommissioningPlan")
def on_commissioning_plan_certified_notify(sender, instance, created, **kwargs):
    """Notify admins when a commissioning plan is certified."""
    if created:
        return

    prev = getattr(instance, "_prev_plan_status", None)
    if prev == instance.status:
        return
    if instance.status != "certified":
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization

        dispatch_workflow_notification(
            organization=org,
            event_key="commissioning_plan_certified",
            recipients=_org_admin_users(org),
            link_url="/construction/testing-commissioning",
            fallback_channels=["in_app"],
            fallback_title=f"Commissioning Plan Certified — {instance.plan_number}",
            fallback_message=(
                f"Commissioning plan '{instance.plan_number}' ({instance.name}) on project "
                f"'{instance.project.name}' has been certified and handed over. "
                f"Certified by: {instance.certified_by or 'Not specified'}."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Commissioning plan certified notification skipped", exc_info=True)


# ── Daily Site Report Submitted ───────────────────────────────────────


@receiver(pre_save, sender="projects.ProjectDailySiteReport")
def capture_site_report_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._prev_report_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._prev_report_status = None
    else:
        instance._prev_report_status = None


@receiver(post_save, sender="projects.ProjectDailySiteReport")
def on_site_report_submitted(sender, instance, created, **kwargs):
    """Notify when a daily site report is submitted for review."""
    prev = getattr(instance, "_prev_report_status", None)
    if not created and prev == instance.status:
        return
    if instance.status != "submitted":
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        project_name = instance.project.name if instance.project else "N/A"
        report_date = instance.report_date.strftime("%d %B %Y") if instance.report_date else "N/A"
        shift = instance.get_shift_display() if hasattr(instance, "get_shift_display") else ""

        dispatch_workflow_notification(
            organization=org,
            event_key="site_report_submitted",
            recipients=_org_admin_users(org),
            link_url="/projects/field-operations",
            fallback_channels=["in_app"],
            fallback_title=f"Site Report Submitted — {project_name}",
            fallback_message=(
                f"Daily site report for {project_name} ({report_date}"
                + (f", {shift} shift" if shift else "")
                + ") has been submitted and is ready for review."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.debug("Site report submitted notification skipped", exc_info=True)


# ── Non-Conformance Report (NCR) Created ──────────────────────────────


@receiver(post_save, sender="projects.NonConformanceReport")
def on_ncr_created(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        ncr_number = instance.ncr_number or f"NCR-{instance.pk}"
        project_name = instance.project.name if instance.project else "N/A"
        severity_display = instance.get_severity_display() if hasattr(instance, "get_severity_display") else instance.severity
        location = instance.location or ""

        notif_severity = Notification.Severity.CRITICAL if instance.severity == "critical" else Notification.Severity.WARNING

        dispatch_workflow_notification(
            organization=org,
            event_key="ncr_created",
            recipients=_org_admin_users(org),
            link_url="/construction/quality-control",
            fallback_channels=["in_app"],
            fallback_title=f"NCR Raised — {ncr_number} ({severity_display})",
            fallback_message=(
                f"Non-Conformance Report {ncr_number} raised for {project_name}. "
                f"Title: {instance.title}. Severity: {severity_display}."
                + (f" Location: {location}." if location else "")
                + f" Root cause: {instance.get_root_cause_display() if hasattr(instance, 'get_root_cause_display') else instance.root_cause}."
            ),
            fallback_category=Notification.Category.PROJECT_UPDATE,
            fallback_severity=notif_severity,
        )
    except Exception:
        logger.debug("NCR created notification skipped", exc_info=True)


# ─────────────────────────────────────────────────────────────────────────
# Project Kickoff auto-advance
# ─────────────────────────────────────────────────────────────────────────
#
# Each time relevant project data changes, re-evaluate the kickoff step on
# the project's ProjectSetupConfig. Auto-advance forward only — never move
# the user backward. They can manually reset via the kickoff drawer.

def _evaluate_kickoff_step(setup_config) -> None:
    """Recompute and (if appropriate) advance the kickoff step."""
    if setup_config.is_complete:
        return

    from apps.projects.models import (
        ProjectPhase,
        ProjectSetupConfig as _Cfg,
        ProjectTeamMember,
    )

    SS = _Cfg.SetupStep
    order = [
        SS.BASIC_INFO,
        SS.TEAM_ALLOCATION,
        SS.PHASE_DEFINITION,
        SS.BOQ_BASELINE,
        SS.COMPLETED,
    ]

    project = setup_config.project
    team_count = ProjectTeamMember.objects.filter(project=project).count()
    phase_count = ProjectPhase.objects.filter(project=project).count()

    satisfied = [
        True,                                # basic_info — project exists, always passes
        team_count >= 1,
        phase_count >= 1,
        bool(setup_config.boq_initialized),
    ]

    target_idx = 4  # COMPLETED if all four prereqs pass
    for i, ok in enumerate(satisfied):
        if not ok:
            target_idx = i
            break

    try:
        current_idx = order.index(setup_config.current_step)
    except ValueError:
        current_idx = 0

    # Only advance forward.
    if target_idx <= current_idx:
        return

    setup_config.current_step = order[target_idx]
    update_fields = ["current_step", "updated_at"]
    if target_idx == 4:
        setup_config.is_complete = True
        setup_config.completed_at = timezone.now()
        update_fields.extend(["is_complete", "completed_at"])
    setup_config.save(update_fields=update_fields)


def _setup_config_for(project):
    if project is None:
        return None
    try:
        return project.setup_config
    except Exception:
        return None


@receiver(post_save, sender="projects.ProjectTeamMember")
def kickoff_advance_on_team_member(sender, instance, created, **kwargs):
    if not created:
        return
    setup = _setup_config_for(getattr(instance, "project", None))
    if setup:
        try:
            _evaluate_kickoff_step(setup)
        except Exception:
            logger.debug("kickoff advance on team member failed", exc_info=True)


@receiver(post_save, sender="projects.ProjectPhase")
def kickoff_advance_on_phase(sender, instance, created, **kwargs):
    if not created:
        return
    setup = _setup_config_for(getattr(instance, "project", None))
    if setup:
        try:
            _evaluate_kickoff_step(setup)
        except Exception:
            logger.debug("kickoff advance on phase failed", exc_info=True)


@receiver(post_save, sender="inventory.BillOfMaterials")
def kickoff_initialize_boq(sender, instance, created, **kwargs):
    if not getattr(instance, "project_id", None):
        return
    setup = _setup_config_for(getattr(instance, "project", None))
    if not setup:
        return
    try:
        if not setup.boq_initialized:
            setup.boq_initialized = True
            setup.save(update_fields=["boq_initialized", "updated_at"])
        _evaluate_kickoff_step(setup)
    except Exception:
        logger.debug("kickoff BoQ flip failed", exc_info=True)


@receiver(post_save, sender="projects.Project")
def kickoff_re_evaluate_on_project_save(sender, instance, created, **kwargs):
    """Re-check on project edits (e.g., property linked, GPS set) — basic_info passes
    automatically but we still re-evaluate in case downstream state changed."""
    if created:
        return
    setup = _setup_config_for(instance)
    if setup:
        try:
            _evaluate_kickoff_step(setup)
        except Exception:
            logger.debug("kickoff re-eval on project save failed", exc_info=True)

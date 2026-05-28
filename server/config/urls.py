from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.iam_views import AccessPolicyViewSet, AccessRequestViewSet, AccessReviewCampaignViewSet, APIKeyDirectoryView, ApplicationTokenViewSet, AuditEventsView, AuthSessionsView, ConnectorCatalogueView, ConnectorInstallationViewSet, DataScopeListView, DormantAccountsView, IdentityProviderViewSet, LoginMethodsView, MFASettingsView, PasswordPolicyView, PrivilegeRiskView, RoleScopeViewSet, ServiceAccountViewSet, UserGroupViewSet, UserManagementViewSet, WebhookViewSet
from apps.accounts.mfa_views import (
    MFAStatusView,
    PasskeyAuthOptionsView,
    PasskeyListDeleteView,
    PasskeyRegisterOptionsView,
    PasskeyRegisterVerifyView,
    RecoveryCodesCountView,
    RecoveryCodesRegenerateView,
    TOTPConfirmView,
    TOTPDisableView,
    TOTPSetupView,
)
from apps.accounts.oauth_views import OAuthAuthorizeView, OAuthCallbackView
from apps.accounts.platform_permissions import require_platform_permission
from apps.accounts.platform_views import RunOperationView
from apps.accounts.views import (
    AccessibilityPreferencesView,
    AccountSecurityView,
    AddOnCatalogView,
    CalendarSchedulingPreferencesView,
    CancelAddOnView,
    ChangePasswordView,
    CheckCompanyView,
    CompanySetupView,
    CompleteOnboardingView,
    CompleteTourView,
    DataExportPreferencesView,
    ForgotPasswordView,
    GettingStartedStatusView,
    InviteStaffView,
    LoginView,
    LogoutOtherSessionsView,
    NotificationPreferencesView,
    OrganizationSubscriptionView,
    PrivacyVisibilityView,
    PurchaseAddOnView,
    RegisterView,
    RequestDemoView,
    ResetPasswordView,
    SendEmailOTPView,
    SessionAwareTokenRefreshView,
    StartTrialView,
    SubscriptionCancelView,
    SubscriptionCheckoutView,
    SubscriptionEventListView,
    SubscriptionPaymentMethodView,
    SubscriptionReactivateView,
    TaskWorkflowPreferencesView,
    UserIntegrationsView,
    UserMeView,
    UserProfilePhotoView,
    UserProfileSettingsView,
    ValidateInvitationView,
    VerifyEmailView,
    VerifyOTPView,
    WorkspacePreferencesView,
)


def health_check(request):
    return JsonResponse({"status": "ok"})


def version_view(request):
    """Public endpoint exposing the current developerOS release info."""
    from .version import version_info
    return JsonResponse(version_info())


@require_platform_permission("telemetry.view_activity")
def activity_feed(request):
    """Cross-module activity feed from audit log."""
    from auditlog.models import LogEntry
    from django.contrib.contenttypes.models import ContentType

    from apps.accounts.models import UserProfile

    module_filter = request.GET.get("module", "")
    org_filter = request.GET.get("organization", "")
    limit = min(int(request.GET.get("limit", "30")), 100)

    qs = LogEntry.objects.select_related("content_type", "actor", "actor__profile", "actor__profile__organization").order_by("-timestamp")

    if org_filter:
        user_ids = UserProfile.objects.filter(
            organization_id=org_filter
        ).values_list("user_id", flat=True)
        qs = qs.filter(actor_id__in=user_ids)

    if module_filter:
        # Map module name to app_label
        module_map = {
            "crm": "crm", "finance": "finance", "hr": "hr",
            "projects": "projects", "properties": "properties",
            "procurement": "procurement", "accounts": "accounts",
            "documents": "documents", "inventory": "inventory",
            "support": "support_desk", "partners": "partners",
            "workflows": "workflows", "notifications": "notifications",
        }
        app_label = module_map.get(module_filter.lower(), module_filter.lower())
        ct_ids = ContentType.objects.filter(app_label=app_label).values_list("id", flat=True)
        qs = qs.filter(content_type_id__in=ct_ids)

    entries = qs[:limit]

    action_labels = {0: "created", 1: "updated", 2: "deleted"}
    severity_map = {0: "info", 1: "info", 2: "warning"}

    # Module display names
    module_labels = {
        "crm": "CRM", "finance": "Finance", "hr": "HR",
        "projects": "Projects", "properties": "Properties",
        "procurement": "Procurement", "accounts": "Accounts",
        "documents": "Documents", "inventory": "Inventory",
        "support_desk": "Support", "partners": "Partners",
        "workflows": "Workflows", "notifications": "Notifications",
        "analytics": "Analytics", "settings": "Settings",
        "compliance": "Compliance",
    }

    items = []
    for e in entries:
        app = e.content_type.app_label if e.content_type else "system"
        model_name = e.content_type.model if e.content_type else "record"
        module_display = module_labels.get(app, app.replace("_", " ").title())
        model_display = e.content_type.name if e.content_type else model_name

        # Determine severity
        severity = severity_map.get(e.action, "info")
        obj_repr = e.object_repr or model_display

        # Build description
        action_label = action_labels.get(e.action, "modified")
        description = f"{model_display} {action_label}: {obj_repr}"

        items.append({
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "module": module_display,
            "app_label": app,
            "model": model_display,
            "action": action_label,
            "object_repr": obj_repr,
            "description": description,
            "severity": severity,
            "actor": e.actor.get_full_name() or e.actor.email if e.actor else None,
            "tenant": getattr(getattr(getattr(e.actor, "profile", None), "organization", None), "name", None) if e.actor else None,
        })

    return JsonResponse({"items": items})


@require_platform_permission("telemetry.view_workflows")
def workflow_monitor(request):
    """Automation & Workflow Engine Monitor for the control center."""
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Count
    from django.utils import timezone

    from apps.workflows.models import WorkflowInstance, WorkflowStep

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    all_instances = WorkflowInstance.objects.all()
    today_instances = all_instances.filter(created_at__gte=today_start)

    # Core metrics
    total_today = today_instances.count()
    completed_today = today_instances.filter(state__in=["approved", "rejected"]).count()
    failed_today = today_instances.filter(state__in=["rejected", "cancelled", "escalated"]).count()

    # Delayed = pending/in_progress with SLA-breached steps
    delayed = WorkflowStep.objects.filter(
        sla_breached=True, decision="pending"
    ).count()

    # Active workflows
    active = all_instances.filter(state__in=["pending", "in_progress"]).count()

    # Top triggering events (content types that generate the most workflows)
    top_triggers = (
        all_instances
        .values("content_type__app_label", "content_type__model")
        .annotate(count=Count("id"))
        .order_by("-count")[:6]
    )
    triggers = []
    for t in top_triggers:
        app = t["content_type__app_label"] or "system"
        model = t["content_type__model"] or "record"
        ct = ContentType.objects.filter(app_label=app, model=model).first()
        label = ct.name if ct else model
        triggers.append({
            "app_label": app,
            "model": model,
            "label": label,
            "count": t["count"],
        })

    # Recent workflow instances for drill-down
    recent = []
    for inst in all_instances.select_related("template", "submitted_by", "content_type").order_by("-created_at")[:10]:
        steps = []
        for step in inst.steps.order_by("sequence"):
            steps.append({
                "sequence": step.sequence,
                "name": step.name,
                "decision": step.decision,
                "sla_breached": step.sla_breached,
            })
        recent.append({
            "id": inst.id,
            "template_name": inst.template.name if inst.template else "Unknown",
            "state": inst.state,
            "content_type": inst.content_type.name if inst.content_type else "",
            "object_id": inst.object_id,
            "submitted_by": inst.submitted_by.get_full_name() or inst.submitted_by.email if inst.submitted_by else None,
            "submitted_at": inst.submitted_at.isoformat() if inst.submitted_at else None,
            "created_at": inst.created_at.isoformat(),
            "steps": steps,
        })

    # Celery periodic tasks health
    from django_celery_beat.models import PeriodicTask
    celery_tasks = []
    for t in PeriodicTask.objects.filter(enabled=True).order_by("name"):
        celery_tasks.append({
            "name": t.name,
            "task": t.task,
            "last_run": t.last_run_at.isoformat() if t.last_run_at else None,
            "enabled": t.enabled,
        })

    return JsonResponse({
        "total_today": total_today,
        "completed_today": completed_today,
        "failed_today": failed_today,
        "delayed_jobs": delayed,
        "active_workflows": active,
        "top_triggers": triggers,
        "recent_instances": recent,
        "celery_tasks": celery_tasks,
        "celery_task_count": len(celery_tasks),
    })


@require_platform_permission("telemetry.view_metrics")
def alerts_risk_center(request):
    """Alerts & Risk Center — aggregates platform, tenant, and security risks."""
    import time
    from datetime import timedelta

    from django.contrib.auth import get_user_model
    from django.db.models import Count, Max
    from django.utils import timezone

    from apps.accounts.models import Organization, UserAuthSession, UserProfile, UserSecurityEvent

    User = get_user_model()
    now = timezone.now()
    alerts = []

    def add(category, severity, title, detail, metric=None):
        alerts.append({
            "category": category,
            "severity": severity,
            "title": title,
            "detail": detail,
            "metric": metric,
            "timestamp": now.isoformat(),
        })

    # ═══ A. SYSTEM ALERTS ═══

    # API latency check
    start = time.time()
    User.objects.first()
    latency_ms = round((time.time() - start) * 1000 * 3, 1)  # p95 estimate
    if latency_ms > 1500:
        add("system", "critical", "API latency spike", f"P95 latency at {latency_ms}ms (threshold: 1500ms)", f"{latency_ms}ms")
    elif latency_ms > 500:
        add("system", "warning", "Elevated API latency", f"P95 latency at {latency_ms}ms", f"{latency_ms}ms")

    # Celery health
    try:
        from django_celery_beat.models import PeriodicTask
        stale_tasks = PeriodicTask.objects.filter(
            enabled=True,
            last_run_at__lt=now - timedelta(hours=24),
        ).count()
        if stale_tasks > 0:
            add("system", "warning", "Background jobs stale", f"{stale_tasks} scheduled task(s) haven't run in 24h", str(stale_tasks))
    except Exception:
        add("system", "critical", "Worker queue unavailable", "Cannot query Celery beat tasks")

    # Storage check
    import os
    media_root = getattr(__import__("django.conf", fromlist=["settings"]).settings, "MEDIA_ROOT", "")
    if media_root and os.path.exists(media_root):
        total_bytes = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fns in os.walk(media_root) for f in fns
            if os.path.isfile(os.path.join(dp, f))
        )
        gb = total_bytes / (1024**3)
        if gb > 10:
            add("system", "critical", "Storage nearing limit", f"Media storage at {gb:.1f} GB", f"{gb:.1f} GB")
        elif gb > 5:
            add("system", "warning", "Storage usage high", f"Media storage at {gb:.1f} GB", f"{gb:.1f} GB")

    # ═══ B. REVENUE ALERTS ═══

    # Expiring trials
    from apps.accounts.models import OrganizationSubscription
    try:
        expiring = OrganizationSubscription.objects.filter(
            status="trialing",
            trial_end__lte=now + timedelta(days=3),
            trial_end__gt=now,
        ).count()
        if expiring > 0:
            add("revenue", "warning", "Trials expiring soon", f"{expiring} tenant trial(s) expiring within 3 days", str(expiring))

        expired = OrganizationSubscription.objects.filter(
            status="trialing",
            trial_end__lt=now,
        ).count()
        if expired > 0:
            add("revenue", "critical", "Expired trials", f"{expired} tenant trial(s) have expired without conversion", str(expired))
    except Exception:
        pass

    # ═══ C. TENANT HEALTH ALERTS ═══

    # Inactive tenants (no login in 14 days)
    active_orgs = Organization.objects.exclude(
        name__startswith="Workspace-"
    ).exclude(is_platform_org=True)

    for org in active_orgs:
        member_ids = UserProfile.objects.filter(organization=org).values_list("user_id", flat=True)
        last_activity = UserAuthSession.objects.filter(
            user_id__in=member_ids,
            revoked_at__isnull=True,
        ).aggregate(last=Max("last_seen_at"))["last"]

        if last_activity is None or last_activity < now - timedelta(days=14):
            days = (now - last_activity).days if last_activity else "never"
            add("tenant_health", "warning", f"Inactive tenant: {org.name}",
                f"No user activity in {days} days" if isinstance(days, int) else "No user has ever logged in",
                f"{days}d" if isinstance(days, int) else "N/A")

    # Low user count tenants
    for org in active_orgs:
        user_count = UserProfile.objects.filter(organization=org).count()
        if user_count <= 1:
            add("tenant_health", "info", f"Single-user tenant: {org.name}",
                "Only 1 user — low engagement risk", "1 user")

    # ═══ D. SECURITY ALERTS ═══

    # Failed logins in last 24h
    try:
        failed_logins = UserSecurityEvent.objects.filter(
            event_type="login_failed",
            created_at__gte=now - timedelta(hours=24),
        ).count()
        if failed_logins > 50:
            add("security", "critical", "High failed login volume", f"{failed_logins} failed login attempts in 24h", str(failed_logins))
        elif failed_logins > 10:
            add("security", "warning", "Elevated failed logins", f"{failed_logins} failed login attempts in 24h", str(failed_logins))

        # Suspicious IPs (same IP hitting multiple orgs)
        suspicious_ips = (
            UserSecurityEvent.objects.filter(
                event_type="login_failed",
                created_at__gte=now - timedelta(hours=24),
            )
            .exclude(ip_address="")
            .values("ip_address")
            .annotate(count=Count("id"))
            .filter(count__gte=10)
        )
        for ip_entry in suspicious_ips[:3]:
            add("security", "critical", f"Suspicious IP: {ip_entry['ip_address']}",
                f"{ip_entry['count']} failed attempts from this IP in 24h",
                str(ip_entry["count"]))
    except Exception:
        pass

    # ═══ E. USAGE & COST ALERTS ═══

    # High storage consumers per org
    # (Simplified — in production, track per-org storage)
    for org in active_orgs:
        member_count = UserProfile.objects.filter(organization=org).count()
        if member_count > 20:
            add("usage", "info", f"High user count: {org.name}",
                f"{member_count} users — monitor for resource scaling", str(member_count))

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda a: severity_order.get(a["severity"], 3))

    # Summary counts
    summary = {
        "total": len(alerts),
        "critical": sum(1 for a in alerts if a["severity"] == "critical"),
        "warning": sum(1 for a in alerts if a["severity"] == "warning"),
        "info": sum(1 for a in alerts if a["severity"] == "info"),
        "by_category": {},
    }
    for a in alerts:
        cat = a["category"]
        summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

    return JsonResponse({"alerts": alerts, "summary": summary})


@require_platform_permission("telemetry.view_metrics")
def telemetry_metrics(request):
    """Core telemetry metrics for the control center dashboard."""
    import time

    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from apps.accounts.models import Organization, UserAuthSession

    User = get_user_model()
    now = timezone.now()

    # Active tenants (organizations, excluding platform org and bootstrap workspaces)
    active_tenants = Organization.objects.exclude(
        name__startswith="Workspace-"
    ).exclude(
        is_platform_org=True
    ).count()

    # Active users
    total_users = User.objects.filter(is_active=True).count()
    # Real-time: sessions active in last 15 minutes
    realtime_users = UserAuthSession.objects.filter(
        revoked_at__isnull=True,
        last_seen_at__gte=now - timezone.timedelta(minutes=15),
    ).values("user").distinct().count()
    # Daily: sessions active in last 24 hours
    daily_users = UserAuthSession.objects.filter(
        revoked_at__isnull=True,
        last_seen_at__gte=now - timezone.timedelta(hours=24),
    ).values("user").distinct().count()

    # API response time (simulate p95 — in production, pull from APM)
    start = time.time()
    # Quick DB query to measure round-trip
    User.objects.first()
    db_latency_ms = round((time.time() - start) * 1000, 1)
    p95_latency = max(db_latency_ms * 3, 45)  # Estimate p95 as ~3x single query

    # Error rate (placeholder — in production, pull from logging/Sentry)
    error_rate = 0.0

    # Background job queue health (Celery)
    celery_status = "unknown"
    pending_tasks = 0
    try:
        from django_celery_beat.models import PeriodicTask
        pending_tasks = PeriodicTask.objects.filter(enabled=True).count()
        celery_status = "healthy"
    except Exception:
        celery_status = "unavailable"

    # Storage usage
    import os
    media_root = getattr(__import__("django.conf", fromlist=["settings"]).settings, "MEDIA_ROOT", "")
    storage_bytes = 0
    file_count = 0
    if media_root and os.path.exists(media_root):
        for dirpath, dirnames, filenames in os.walk(media_root):
            file_count += len(filenames)
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    storage_bytes += os.path.getsize(fp)

    def fmt_bytes(b):
        if b < 1024: return f"{b} B"
        if b < 1024**2: return f"{b/1024:.1f} KB"
        if b < 1024**3: return f"{b/1024**2:.1f} MB"
        return f"{b/1024**3:.2f} GB"

    return JsonResponse({
        "active_tenants": active_tenants,
        "total_users": total_users,
        "realtime_users": realtime_users,
        "daily_users": daily_users,
        "p95_latency_ms": round(p95_latency, 1),
        "error_rate_pct": error_rate,
        "celery_status": celery_status,
        "pending_tasks": pending_tasks,
        "storage_bytes": storage_bytes,
        "storage_formatted": fmt_bytes(storage_bytes),
        "file_count": file_count,
    })


urlpatterns = [
    path("api/health/", health_check, name="health_check"),
    path("api/version/", version_view, name="version"),
    path("api/telemetry/metrics/", telemetry_metrics, name="telemetry_metrics"),
    path("api/telemetry/activity-feed/", activity_feed, name="activity_feed"),
    path("api/telemetry/workflow-monitor/", workflow_monitor, name="workflow_monitor"),
    path("api/telemetry/alerts/", alerts_risk_center, name="alerts_risk_center"),
    path("admin/", admin.site.urls),
    # Auth
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", SessionAwareTokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("api/auth/verify-otp/send-email/", SendEmailOTPView.as_view(), name="send_email_otp"),
    path("api/auth/verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    # MFA management
    path("api/auth/mfa/status/", MFAStatusView.as_view(), name="mfa_status"),
    path("api/auth/mfa/totp/setup/", TOTPSetupView.as_view(), name="mfa_totp_setup"),
    path("api/auth/mfa/totp/confirm/", TOTPConfirmView.as_view(), name="mfa_totp_confirm"),
    path("api/auth/mfa/totp/disable/", TOTPDisableView.as_view(), name="mfa_totp_disable"),
    path("api/auth/mfa/recovery-codes/", RecoveryCodesCountView.as_view(), name="mfa_recovery_count"),
    path("api/auth/mfa/recovery-codes/regenerate/", RecoveryCodesRegenerateView.as_view(), name="mfa_recovery_regenerate"),
    path("api/auth/mfa/passkeys/", PasskeyListDeleteView.as_view(), name="mfa_passkey_list"),
    path("api/auth/mfa/passkeys/register/", PasskeyRegisterOptionsView.as_view(), name="mfa_passkey_register_options"),
    path("api/auth/mfa/passkeys/register/verify/", PasskeyRegisterVerifyView.as_view(), name="mfa_passkey_register_verify"),
    path("api/auth/mfa/passkeys/auth-options/", PasskeyAuthOptionsView.as_view(), name="mfa_passkey_auth_options"),
    path("api/auth/forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("api/auth/reset-password/", ResetPasswordView.as_view(), name="reset_password"),
    path("api/auth/validate-invitation/", ValidateInvitationView.as_view(), name="validate_invitation"),
    # OAuth (federated login)
    path("api/auth/oauth/authorize/", OAuthAuthorizeView.as_view(), name="oauth_authorize"),
    path("api/auth/oauth/callback/", OAuthCallbackView.as_view(), name="oauth_callback"),
    path("api/auth/me/", UserMeView.as_view(), name="user_me"),
    path("api/auth/profile/", UserProfileSettingsView.as_view(), name="user_profile_settings"),
    path("api/auth/profile/photo/", UserProfilePhotoView.as_view(), name="user_profile_photo"),
    path("api/auth/account-security/", AccountSecurityView.as_view(), name="account_security"),
    path("api/auth/change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("api/auth/sessions/logout-others/", LogoutOtherSessionsView.as_view(), name="logout_other_sessions"),
    path("api/auth/notification-preferences/", NotificationPreferencesView.as_view(), name="notification_preferences"),
    path("api/auth/privacy-visibility/", PrivacyVisibilityView.as_view(), name="privacy_visibility"),
    path("api/auth/workspace-preferences/", WorkspacePreferencesView.as_view(), name="workspace_preferences"),
    path("api/auth/task-workflow-preferences/", TaskWorkflowPreferencesView.as_view(), name="task_workflow_preferences"),
    path("api/auth/calendar-scheduling-preferences/", CalendarSchedulingPreferencesView.as_view(), name="calendar_scheduling_preferences"),
    path("api/auth/data-export-preferences/", DataExportPreferencesView.as_view(), name="data_export_preferences"),
    path("api/auth/accessibility-preferences/", AccessibilityPreferencesView.as_view(), name="accessibility_preferences"),
    path("api/auth/integrations/", UserIntegrationsView.as_view(), name="user_integrations"),
    path("api/auth/complete-tour/", CompleteTourView.as_view(), name="complete_tour"),
    path("api/auth/setup-company/", CompanySetupView.as_view(), name="setup_company"),
    path("api/auth/check-company/", CheckCompanyView.as_view(), name="check_company"),
    path("api/auth/check-company-public/", CheckCompanyView.as_view(permission_classes=[AllowAny]), name="check_company_public"),
    path("api/auth/invite-staff/", InviteStaffView.as_view(), name="invite_staff"),
    path("api/auth/complete-onboarding/", CompleteOnboardingView.as_view(), name="complete_onboarding"),
    path("api/auth/getting-started-status/", GettingStartedStatusView.as_view(), name="getting_started_status"),
    path("api/auth/request-demo/", RequestDemoView.as_view(), name="request_demo"),
    # Platform / Subscription
    path("api/platform/subscription/", OrganizationSubscriptionView.as_view(), name="platform_subscription"),
    path("api/platform/subscription/events/", SubscriptionEventListView.as_view(), name="platform_subscription_events"),
    path("api/platform/subscription/start-trial/", StartTrialView.as_view(), name="platform_start_trial"),
    path("api/platform/subscription/checkout/", SubscriptionCheckoutView.as_view(), name="platform_subscription_checkout"),
    path("api/platform/subscription/cancel/", SubscriptionCancelView.as_view(), name="platform_subscription_cancel"),
    path("api/platform/subscription/reactivate/", SubscriptionReactivateView.as_view(), name="platform_subscription_reactivate"),
    path("api/platform/subscription/payment-method/", SubscriptionPaymentMethodView.as_view(), name="platform_subscription_payment_method"),
    path("api/platform/subscription/add-ons/", AddOnCatalogView.as_view(), name="platform_addon_catalog"),
    path("api/platform/subscription/add-ons/purchase/", PurchaseAddOnView.as_view(), name="platform_addon_purchase"),
    path("api/platform/subscription/add-ons/<int:pk>/cancel/", CancelAddOnView.as_view(), name="platform_addon_cancel"),
    path("api/platform/operations/run/", RunOperationView.as_view(), name="platform_operations_run"),
    # IAM
    path("api/iam/users/", UserManagementViewSet.as_view({"get": "list", "post": "create"}), name="iam_user_list"),
    path("api/iam/users/invitations/", UserManagementViewSet.as_view({"get": "invitations"}), name="iam_user_invitations"),
    path("api/iam/users/lifecycle/", UserManagementViewSet.as_view({"get": "lifecycle"}), name="iam_user_lifecycle"),
    path("api/iam/users/linked-employees/", UserManagementViewSet.as_view({"get": "linked_employees"}), name="iam_user_linked_employees"),
    path("api/iam/users/<int:pk>/", UserManagementViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_user_detail"),
    path("api/iam/users/<int:pk>/suspend/", UserManagementViewSet.as_view({"post": "suspend"}), name="iam_user_suspend"),
    path("api/iam/users/<int:pk>/activate/", UserManagementViewSet.as_view({"post": "activate"}), name="iam_user_activate"),
    # IAM — User Groups
    path("api/iam/user-groups/", UserGroupViewSet.as_view({"get": "list", "post": "create"}), name="iam_user_group_list"),
    path("api/iam/user-groups/<int:pk>/", UserGroupViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_user_group_detail"),
    # IAM — Access Requests
    path("api/iam/access-requests/", AccessRequestViewSet.as_view({"get": "list", "post": "create"}), name="iam_access_request_list"),
    path("api/iam/access-requests/expiring/", AccessRequestViewSet.as_view({"get": "expiring"}), name="iam_access_request_expiring"),
    path("api/iam/access-requests/<int:pk>/", AccessRequestViewSet.as_view({"get": "retrieve", "patch": "partial_update"}), name="iam_access_request_detail"),
    path("api/iam/access-requests/<int:pk>/approve/", AccessRequestViewSet.as_view({"post": "approve"}), name="iam_access_request_approve"),
    path("api/iam/access-requests/<int:pk>/reject/", AccessRequestViewSet.as_view({"post": "reject"}), name="iam_access_request_reject"),
    path("api/iam/access-requests/<int:pk>/revoke/", AccessRequestViewSet.as_view({"post": "revoke"}), name="iam_access_request_revoke"),
    path("api/iam/access-requests/<int:pk>/cancel/", AccessRequestViewSet.as_view({"post": "cancel"}), name="iam_access_request_cancel"),
    # IAM — Auth & Security (Cluster 7)
    path("api/iam/auth/password-policy/", PasswordPolicyView.as_view({"get": "retrieve", "patch": "partial_update"}), name="iam_auth_password_policy"),
    path("api/iam/auth/login-methods/", LoginMethodsView.as_view({"get": "retrieve", "patch": "partial_update"}), name="iam_auth_login_methods"),
    path("api/iam/auth/sessions/", AuthSessionsView.as_view({"get": "list"}), name="iam_auth_sessions_list"),
    path("api/iam/auth/sessions/<uuid:pk>/revoke/", AuthSessionsView.as_view({"post": "revoke"}), name="iam_auth_session_revoke"),
    # IAM — Audit events feed (Cluster 6)
    path("api/iam/audit/events/", AuditEventsView.as_view({"get": "list"}), name="iam_audit_events_list"),
    # IAM — Compliance (Cluster 9)
    path("api/iam/compliance/access-reviews/", AccessReviewCampaignViewSet.as_view({"get": "list", "post": "create"}), name="iam_compliance_review_list"),
    path("api/iam/compliance/access-reviews/<int:pk>/", AccessReviewCampaignViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_compliance_review_detail"),
    path("api/iam/compliance/access-reviews/<int:pk>/start/", AccessReviewCampaignViewSet.as_view({"post": "start"}), name="iam_compliance_review_start"),
    path("api/iam/compliance/access-reviews/<int:pk>/complete/", AccessReviewCampaignViewSet.as_view({"post": "complete"}), name="iam_compliance_review_complete"),
    path("api/iam/compliance/access-reviews/<int:pk>/cancel/", AccessReviewCampaignViewSet.as_view({"post": "cancel"}), name="iam_compliance_review_cancel"),
    path("api/iam/compliance/access-reviews/<int:pk>/items/", AccessReviewCampaignViewSet.as_view({"get": "items"}), name="iam_compliance_review_items"),
    path("api/iam/compliance/access-reviews/<int:pk>/items/<int:item_id>/decide/", AccessReviewCampaignViewSet.as_view({"post": "decide_item"}), name="iam_compliance_review_decide"),
    path("api/iam/compliance/dormant-accounts/", DormantAccountsView.as_view({"get": "list"}), name="iam_compliance_dormant"),
    path("api/iam/compliance/privilege-risk/", PrivilegeRiskView.as_view({"get": "list"}), name="iam_compliance_privilege_risk"),
    # IAM — Federation / Identity Providers (Cluster 8)
    path("api/iam/identity-providers/", IdentityProviderViewSet.as_view({"get": "list", "post": "create"}), name="iam_identity_provider_list"),
    path("api/iam/identity-providers/<int:pk>/", IdentityProviderViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_identity_provider_detail"),
    path("api/iam/identity-providers/<int:pk>/test/", IdentityProviderViewSet.as_view({"post": "test"}), name="iam_identity_provider_test"),
    path("api/iam/identity-providers/<int:pk>/sync/", IdentityProviderViewSet.as_view({"post": "sync_now"}), name="iam_identity_provider_sync"),
    # IAM — Access Policies (Cluster 4)
    path("api/iam/access-policies/", AccessPolicyViewSet.as_view({"get": "list", "post": "create"}), name="iam_access_policy_list"),
    path("api/iam/access-policies/<int:pk>/", AccessPolicyViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_access_policy_detail"),
    path("api/iam/access-policies/<int:pk>/test/", AccessPolicyViewSet.as_view({"post": "test"}), name="iam_access_policy_test"),
    # IAM — Webhooks (Cluster 2)
    path("api/iam/webhooks/", WebhookViewSet.as_view({"get": "list", "post": "create"}), name="iam_webhook_list"),
    path("api/iam/webhooks/<int:pk>/", WebhookViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_webhook_detail"),
    path("api/iam/webhooks/<int:pk>/test/", WebhookViewSet.as_view({"post": "test"}), name="iam_webhook_test"),
    path("api/iam/webhooks/<int:pk>/deliveries/", WebhookViewSet.as_view({"get": "deliveries"}), name="iam_webhook_deliveries"),
    # IAM — Application Tokens (Cluster 2)
    path("api/iam/app-tokens/", ApplicationTokenViewSet.as_view({"get": "list", "post": "create"}), name="iam_app_token_list"),
    path("api/iam/app-tokens/<int:pk>/", ApplicationTokenViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_app_token_detail"),
    path("api/iam/app-tokens/<int:pk>/regenerate/", ApplicationTokenViewSet.as_view({"post": "regenerate"}), name="iam_app_token_regenerate"),
    # IAM — Integrations / Connectors (Cluster 2)
    path("api/iam/connectors/", ConnectorCatalogueView.as_view({"get": "list"}), name="iam_connector_catalogue"),
    path("api/iam/connector-installations/", ConnectorInstallationViewSet.as_view({"get": "list", "post": "create"}), name="iam_connector_install_list"),
    path("api/iam/connector-installations/<int:pk>/", ConnectorInstallationViewSet.as_view({"patch": "partial_update", "delete": "destroy"}), name="iam_connector_install_detail"),
    # IAM — Data-access scope (Cluster 3.4)
    path("api/iam/data-scopes/", DataScopeListView.as_view({"get": "list"}), name="iam_data_scopes"),
    path("api/iam/role-scopes/", RoleScopeViewSet.as_view({"get": "list", "post": "create"}), name="iam_role_scopes_list"),
    path("api/iam/role-scopes/<int:pk>/", RoleScopeViewSet.as_view({"delete": "destroy"}), name="iam_role_scopes_detail"),
    # IAM — API Keys
    path("api/iam/api-keys/", APIKeyDirectoryView.as_view({"get": "list"}), name="iam_api_key_list"),
    # IAM — Service Accounts
    path("api/iam/service-accounts/", ServiceAccountViewSet.as_view({"get": "list", "post": "create"}), name="iam_sa_list"),
    path("api/iam/service-accounts/<int:pk>/", ServiceAccountViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="iam_sa_detail"),
    path("api/iam/service-accounts/<int:pk>/keys/", ServiceAccountViewSet.as_view({"post": "create_key"}), name="iam_sa_create_key"),
    path("api/iam/service-accounts/<int:pk>/keys/<int:key_id>/", ServiceAccountViewSet.as_view({"delete": "revoke_key"}), name="iam_sa_revoke_key"),
    # IAM — MFA Settings
    path("api/iam/mfa-settings/", MFASettingsView.as_view({"get": "retrieve", "patch": "partial_update"}), name="iam_mfa_settings"),
    # API modules
    path("api/properties/", include("apps.properties.urls")),
    path("api/projects/", include("apps.projects.urls")),
    path("api/finance/", include("apps.finance.urls")),
    path("api/crm/", include("apps.crm.urls")),
    path("api/partners/", include("apps.partners.urls")),
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/documents/", include("apps.documents.urls")),
    path("api/compliance/", include("apps.compliance.urls")),
    path("api/valuations/", include("apps.valuations.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/procurement/", include("apps.procurement.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    path("api/materials/", include("apps.inventory.urls_materials")),
    path("api/bom/", include("apps.inventory.urls_bom")),
    path("api/rate-library/", include("apps.inventory.urls_rates")),
    path("api/boq-mapping/", include("apps.inventory.urls_mapping")),
    path("api/boq-category-mapping/", include("apps.inventory.urls_category_mapping")),
    path("api/material-requisitions/", include("apps.inventory.urls_requisitions")),
    path("api/material-issues/", include("apps.inventory.urls_issue")),
    path("api/material-transfers/", include("apps.inventory.urls_transfers")),
    path("api/material-returns/", include("apps.inventory.urls_returns")),
    path("api/procurement-integration/", include("apps.inventory.urls_procurement_integration")),
    path("api/hr/", include("apps.hr.urls")),
    path("api/settings/", include("apps.settings.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/workflows/", include("apps.workflows.urls")),
    path("api/support-desk/", include("apps.support_desk.urls")),
    path("api/facility-management/", include("apps.facility_management.urls")),
    path("api/meetings/", include("apps.meetings.urls")),
    path("api/search/", include("apps.search.urls")),
    path("api/workspace/", include("apps.workspace.urls")),
    path("api/calendar/", include("apps.calendar.urls")),
    path("api/internal-tasks/", include("apps.internal_tasks.urls")),
    # Schema & docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static

    urlpatterns = [
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

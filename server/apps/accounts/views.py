import hashlib
from datetime import timedelta
from zoneinfo import available_timezones

from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import (
    USER_NOTIFICATION_CATEGORIES,
    USER_NOTIFICATION_CHANNELS,
    USER_NOTIFICATION_FREQUENCIES,
    UserNotificationPreference,
    default_user_notification_category_preferences,
)
from apps.settings.permissions import HasRolePermission

from .models import (
    WORKSPACE_DASHBOARD_WIDGET_KEYS,
    ActiveSubscriptionAddOn,
    OrganizationSubscription,
    SubscriptionEvent,
    UserAuthSession,
    UserIntegrationConnection,
    UserProfile,
    UserSecurityEvent,
)
from .security import MFAReauthRequired, log_user_security_event
from .serializers import (
    AccessibilityPreferencesUpdateSerializer,
    AccountSecurityUpdateSerializer,
    CalendarSchedulingPreferencesUpdateSerializer,
    ChangePasswordSerializer,
    CheckCompanySerializer,
    CompanySetupSerializer,
    CompleteOnboardingSerializer,
    CompleteTourSerializer,
    DataExportPreferencesUpdateSerializer,
    DemoRequestSerializer,
    ForgotPasswordSerializer,
    InviteStaffSerializer,
    LoginSerializer,
    NotificationPreferencesUpdateSerializer,
    OrganizationSubscriptionSerializer,
    PaymentMethodUpdateSerializer,
    PrivacyVisibilityUpdateSerializer,
    PurchaseAddOnSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    SubscriptionAddOnSerializer,
    SubscriptionCancelSerializer,
    SubscriptionCheckoutSerializer,
    SubscriptionEventSerializer,
    TaskWorkflowPreferencesUpdateSerializer,
    UserIntegrationActionSerializer,
    UserMeSerializer,
    UserProfileSettingsSerializer,
    ValidateInvitationSerializer,
    VerifyEmailSerializer,
    VerifyOTPSerializer,
    WorkspacePreferencesUpdateSerializer,
)
from .throttles import AuthRateThrottle, OTPRateThrottle, PasswordResetRateThrottle, SensitiveActionThrottle

WORKSPACE_WIDGET_CATALOG = [
    {
        "key": "alerts",
        "label": "Alerts & Escalations",
        "description": "Critical exceptions, warnings, and attention-required signals.",
    },
    {
        "key": "portfolio_kpis",
        "label": "Portfolio KPI Strip",
        "description": "High-level portfolio value and unit performance indicators.",
    },
    {
        "key": "operational_signals",
        "label": "Operational Signals",
        "description": "Sales velocity, approvals, SLA health, and contract exposure.",
    },
    {
        "key": "team_workload",
        "label": "Team Workload Snapshot",
        "description": "Manager workload and at-risk execution visibility.",
    },
    {
        "key": "valuation_trend",
        "label": "Valuation Trend",
        "description": "Portfolio valuation movement over time.",
    },
    {
        "key": "project_status",
        "label": "Project Status",
        "description": "Project stage distribution and occupancy mix.",
    },
    {
        "key": "active_projects",
        "label": "Active Projects",
        "description": "Live projects, progress, and execution risk.",
    },
    {
        "key": "cash_flow_activity",
        "label": "Cash Flow Activity",
        "description": "Receivables, payables, and recent billing activity.",
    },
]
WORKSPACE_WIDGET_META = {row["key"]: row for row in WORKSPACE_WIDGET_CATALOG}
_WORKSPACE_WIDGET_SCHEMA_PAYLOAD = "|".join(
    [
        *WORKSPACE_DASHBOARD_WIDGET_KEYS,
        *[
            f"{row['key']}:{row['label']}:{row['description']}"
            for row in WORKSPACE_WIDGET_CATALOG
        ],
    ]
)
WORKSPACE_WIDGET_SCHEMA_VERSION = hashlib.sha1(
    _WORKSPACE_WIDGET_SCHEMA_PAYLOAD.encode("utf-8")
).hexdigest()[:12]
TASK_REMINDER_TIMING_OPTIONS = [
    {"value": 0, "label": "At due time"},
    {"value": 15, "label": "15 minutes before"},
    {"value": 30, "label": "30 minutes before"},
    {"value": 60, "label": "1 hour before"},
    {"value": 240, "label": "4 hours before"},
    {"value": 1440, "label": "1 day before"},
]
TASK_DUE_DATE_OFFSET_OPTIONS = [
    {"value": 0, "label": "Same day"},
    {"value": 1, "label": "1 day"},
    {"value": 2, "label": "2 days"},
    {"value": 3, "label": "3 days"},
    {"value": 5, "label": "5 days"},
    {"value": 7, "label": "7 days"},
    {"value": 14, "label": "14 days"},
]
CALENDAR_WORKING_DAY_OPTIONS = [
    {"value": 1, "label": "Monday"},
    {"value": 2, "label": "Tuesday"},
    {"value": 3, "label": "Wednesday"},
    {"value": 4, "label": "Thursday"},
    {"value": 5, "label": "Friday"},
    {"value": 6, "label": "Saturday"},
    {"value": 7, "label": "Sunday"},
]
ALL_CALENDAR_TIMEZONE_OPTIONS = tuple(sorted(available_timezones()))
DATA_ROWS_PER_PAGE_OPTIONS = [10, 25, 50, 100, 200]
WORKSPACE_PREFERENCES_CACHE_TTL_SECONDS = 300


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


class LoginView(generics.CreateAPIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class VerifyOTPView(generics.CreateAPIView):
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.save()
        return Response(tokens, status=status.HTTP_200_OK)


class SessionAwareTokenRefreshView(APIView):
    """
    Refresh access token with session validation and token blacklisting.

    Checks the refresh token's `sid` claim to verify the session hasn't
    been revoked, then delegates to SimpleJWT's standard serializer which
    handles rotation + blacklisting (BLACKLIST_AFTER_ROTATION=True).
    """
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request, *args, **kwargs):
        from rest_framework_simplejwt.exceptions import TokenError
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer
        from rest_framework_simplejwt.tokens import RefreshToken

        raw_token = request.data.get("refresh")
        if not raw_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate session before allowing refresh
        try:
            token = RefreshToken(raw_token)
        except TokenError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        sid = token.payload.get("sid")
        if sid:
            from .models import UserAuthSession
            if not UserAuthSession.objects.filter(
                sid=sid, revoked_at__isnull=True
            ).exists():
                try:
                    token.blacklist()
                except Exception:
                    pass
                return Response(
                    {"detail": "Session has expired or been revoked."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        # Delegate to SimpleJWT — handles rotation + blacklisting
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"detail": "Token is invalid or has been used."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(serializer.validated_data)


class SendEmailOTPView(APIView):
    """Send (or re-send) the email OTP for an existing MFA session."""

    permission_classes = [AllowAny]
    throttle_classes = [OTPRateThrottle]

    def post(self, request):

        from django.contrib.auth import get_user_model

        from .emails import send_otp_email
        from .serializers import OTP_CACHE_PREFIX

        otp_session = request.data.get("otp_session")
        if not otp_session:
            return Response(
                {"detail": "Missing otp_session."}, status=status.HTTP_400_BAD_REQUEST
            )

        data = cache.get(f"{OTP_CACHE_PREFIX}{otp_session}")
        if not data:
            return Response(
                {"detail": "Session expired. Please log in again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        User = get_user_model()
        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid session."}, status=status.HTTP_400_BAD_REQUEST
            )

        from threading import Thread
        Thread(target=lambda: send_otp_email(user, data["otp"]), daemon=True).start()
        return Response({"detail": "Verification code sent to your email."})


class VerifyEmailView(generics.CreateAPIView):
    serializer_class = VerifyEmailSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class ForgotPasswordView(generics.CreateAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class ResetPasswordView(generics.CreateAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class ValidateInvitationView(generics.CreateAPIView):
    serializer_class = ValidateInvitationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserMeSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class UserProfileSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSettingsSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileSettingsSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSettingsSerializer(request.user, context={"request": request}).data)


class UserProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        photo = request.FILES.get("photo")
        if photo is None:
            return Response(
                {"detail": "No photo file was provided. Use the `photo` field."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = str(getattr(photo, "content_type", "") or "")
        if not content_type.startswith("image/"):
            return Response(
                {"detail": "Only image uploads are allowed for profile photos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_size_bytes = 8 * 1024 * 1024
        if photo.size > max_size_bytes:
            return Response(
                {"detail": "Profile photo exceeds 8MB size limit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        previous_photo_name = profile.profile_photo.name if profile.profile_photo else None
        profile.profile_photo = photo
        profile.save(update_fields=["profile_photo"])

        if previous_photo_name and previous_photo_name != profile.profile_photo.name:
            profile.profile_photo.storage.delete(previous_photo_name)

        return Response(
            {
                "detail": "Profile photo uploaded successfully.",
                "profile_photo_url": request.build_absolute_uri(profile.profile_photo.url),
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not profile.profile_photo:
            return Response(
                {"detail": "Profile photo is already empty.", "profile_photo_url": None},
                status=status.HTTP_200_OK,
            )

        profile.profile_photo.delete(save=False)
        profile.profile_photo = None
        profile.save(update_fields=["profile_photo"])
        return Response(
            {"detail": "Profile photo removed successfully.", "profile_photo_url": None},
            status=status.HTTP_200_OK,
        )


class AccountSecurityView(APIView):
    permission_classes = [IsAuthenticated]

    def _serialize_event(self, event):
        return {
            "id": event.id,
            "event_type": event.event_type,
            "event_type_display": event.get_event_type_display(),
            "status": event.status,
            "status_display": event.get_status_display(),
            "provider": event.provider,
            "ip_address": event.ip_address,
            "device_label": event.device_label,
            "user_agent": event.user_agent,
            "detail": event.detail,
            "occurred_at": event.occurred_at,
        }

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        org = profile.organization

        oauth_rows = request.user.oauth_connections.order_by("-connected_at")
        linked_providers = [
            {
                "id": row.id,
                "provider": row.provider,
                "provider_display": row.get_provider_display(),
                "email": row.email,
                "connected_at": row.connected_at,
                "last_login_at": row.last_login_at,
            }
            for row in oauth_rows
        ]

        current_sid = str(request.auth.get("sid")) if request.auth and request.auth.get("sid") else None
        session_rows = UserAuthSession.objects.filter(
            user=request.user,
            revoked_at__isnull=True,
        ).order_by("-last_seen_at")[:25]
        active_sessions = [
            {
                "sid": str(row.sid),
                "auth_provider": row.auth_provider,
                "auth_provider_display": row.get_auth_provider_display(),
                "ip_address": row.ip_address,
                "device_label": row.device_label,
                "user_agent": row.user_agent,
                "created_at": row.created_at,
                "last_seen_at": row.last_seen_at,
                "is_current": str(row.sid) == current_sid,
            }
            for row in session_rows
        ]

        event_qs = UserSecurityEvent.objects.filter(user=request.user)
        login_history = [
            self._serialize_event(row)
            for row in event_qs.filter(
                event_type=UserSecurityEvent.EventType.LOGIN_SUCCESS
            )[:30]
        ]
        failed_logins = [
            self._serialize_event(row)
            for row in event_qs.filter(
                event_type__in=[
                    UserSecurityEvent.EventType.LOGIN_FAILED,
                    UserSecurityEvent.EventType.OTP_FAILED,
                ]
            )[:30]
        ]

        device_history_map = {}
        for row in session_rows:
            key = row.device_label or row.user_agent or str(row.sid)
            existing = device_history_map.get(key)
            if existing is None or existing["last_seen_at"] < row.last_seen_at:
                device_history_map[key] = {
                    "device_label": row.device_label or "Unknown device",
                    "ip_address": row.ip_address,
                    "user_agent": row.user_agent,
                    "first_seen_at": row.created_at,
                    "last_seen_at": row.last_seen_at,
                    "auth_provider": row.auth_provider,
                    "auth_provider_display": row.get_auth_provider_display(),
                }

        device_history = sorted(
            device_history_map.values(),
            key=lambda row: row["last_seen_at"],
            reverse=True,
        )[:20]

        mfa_policy = org.mfa_enforcement if org else "required_all"
        mfa_policy_display = org.get_mfa_enforcement_display() if org else "Required for All Users"

        return {
            "username": request.user.username,
            "email": request.user.email,
            "mfa_enabled": profile.mfa_enabled,
            "passkey_enabled": profile.passkey_enabled,
            "mfa_policy": mfa_policy,
            "mfa_policy_display": mfa_policy_display,
            "linked_providers": linked_providers,
            "active_sessions": active_sessions,
            "login_history": login_history,
            "failed_login_attempts": failed_logins,
            "device_history": device_history,
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        serializer = AccountSecurityUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request))


class ChangePasswordView(generics.CreateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated, MFAReauthRequired]
    throttle_classes = [SensitiveActionThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        current_sid = request.auth.get("sid") if request.auth else None
        sessions_qs = UserAuthSession.objects.filter(user=request.user, revoked_at__isnull=True)
        if current_sid:
            sessions_qs = sessions_qs.exclude(sid=current_sid)
        revoked_count = sessions_qs.update(
            revoked_at=timezone.now(),
            revoke_reason="password_changed",
        )

        log_user_security_event(
            user=request.user,
            principal=request.user.email,
            event_type=UserSecurityEvent.EventType.PASSWORD_CHANGED,
            status=UserSecurityEvent.Status.SUCCESS,
            request=request,
            detail="Password changed successfully.",
            metadata={"revoked_sessions": revoked_count},
        )
        return Response(
            {
                **result,
                "revoked_sessions": revoked_count,
            },
            status=status.HTTP_200_OK,
        )


class LogoutOtherSessionsView(APIView):
    permission_classes = [IsAuthenticated, MFAReauthRequired]

    def post(self, request):
        current_sid = request.auth.get("sid") if request.auth else None
        sessions_qs = UserAuthSession.objects.filter(user=request.user, revoked_at__isnull=True)
        if current_sid:
            sessions_qs = sessions_qs.exclude(sid=current_sid)
        revoked_count = sessions_qs.update(
            revoked_at=timezone.now(),
            revoke_reason="logout_other_devices",
        )

        log_user_security_event(
            user=request.user,
            principal=request.user.email,
            event_type=UserSecurityEvent.EventType.SESSION_REVOKED_OTHERS,
            status=UserSecurityEvent.Status.SUCCESS,
            request=request,
            detail="User revoked other active sessions.",
            metadata={"revoked_sessions": revoked_count},
        )
        return Response(
            {
                "detail": "Other active sessions have been logged out.",
                "revoked_sessions": revoked_count,
            },
            status=status.HTTP_200_OK,
        )


class NotificationPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    _channel_options = [
        {"key": key, "label": label}
        for key, label in USER_NOTIFICATION_CHANNELS
    ]
    _frequency_options = [
        {"key": key, "label": label}
        for key, label in USER_NOTIFICATION_FREQUENCIES
    ]
    _valid_channel_keys = {row["key"] for row in _channel_options}
    _valid_frequency_keys = {row["key"] for row in _frequency_options}

    def _normalize_category_preferences(self, raw):
        defaults = default_user_notification_category_preferences()
        normalized = {}
        changed = False

        for key, _label in USER_NOTIFICATION_CATEGORIES:
            default_row = defaults[key]
            source_row = raw.get(key, {}) if isinstance(raw, dict) else {}

            enabled = source_row.get("enabled", default_row["enabled"])
            if not isinstance(enabled, bool):
                enabled = default_row["enabled"]
                changed = True

            channels = source_row.get("channels", default_row["channels"])
            if not isinstance(channels, list):
                channels = list(default_row["channels"])
                changed = True
            channels = [channel for channel in channels if channel in self._valid_channel_keys]
            deduped_channels = []
            for channel in channels:
                if channel not in deduped_channels:
                    deduped_channels.append(channel)
            if not deduped_channels:
                deduped_channels = list(default_row["channels"])
            channels = deduped_channels

            frequency = source_row.get("frequency", default_row["frequency"])
            if frequency not in self._valid_frequency_keys:
                frequency = default_row["frequency"]
                changed = True

            normalized_row = {
                "enabled": enabled,
                "channels": channels,
                "frequency": frequency,
            }
            normalized[key] = normalized_row
            if source_row != normalized_row:
                changed = True

        if not isinstance(raw, dict) or set(raw.keys()) != set(normalized.keys()):
            changed = True

        return normalized, changed

    def _payload(self, request):
        preference, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
        normalized, changed = self._normalize_category_preferences(preference.category_preferences)
        if changed:
            preference.category_preferences = normalized
            preference.save(update_fields=["category_preferences", "updated_at"])

        category_rows = []
        for key, label in USER_NOTIFICATION_CATEGORIES:
            row = normalized[key]
            category_rows.append(
                {
                    "key": key,
                    "label": label,
                    "enabled": row["enabled"],
                    "channels": row["channels"],
                    "frequency": row["frequency"],
                }
            )

        return {
            "channel_in_app_enabled": preference.channel_in_app_enabled,
            "channel_email_enabled": preference.channel_email_enabled,
            "channel_push_enabled": preference.channel_push_enabled,
            "channel_sms_enabled": preference.channel_sms_enabled,
            "channel_options": self._channel_options,
            "frequency_options": self._frequency_options,
            "categories": category_rows,
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        preference, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferencesUpdateSerializer(
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = []
        for field in [
            "channel_in_app_enabled",
            "channel_email_enabled",
            "channel_push_enabled",
            "channel_sms_enabled",
        ]:
            if field in data and getattr(preference, field) != data[field]:
                setattr(preference, field, data[field])
                update_fields.append(field)

        if "categories" in data:
            normalized, _changed = self._normalize_category_preferences(preference.category_preferences)
            for row in data["categories"]:
                key = row["key"]
                current = dict(normalized.get(key, {}))
                if "enabled" in row:
                    current["enabled"] = row["enabled"]
                if "channels" in row:
                    current["channels"] = row["channels"]
                if "frequency" in row:
                    current["frequency"] = row["frequency"]
                normalized[key] = current

            normalized, _ = self._normalize_category_preferences(normalized)
            if preference.category_preferences != normalized:
                preference.category_preferences = normalized
                update_fields.append("category_preferences")

        if update_fields:
            if "updated_at" not in update_fields:
                update_fields.append("updated_at")
            preference.save(update_fields=update_fields)

        return Response(self._payload(request))


class PrivacyVisibilityView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        visibility_options = [
            {
                "value": value,
                "label": label,
            }
            for value, label in UserProfile.ProfileVisibility.choices
        ]
        return {
            "profile_visibility": profile.profile_visibility,
            "email_visibility": profile.email_visibility,
            "phone_visibility": profile.phone_visibility,
            "activity_visibility": profile.activity_visibility,
            "online_status_visibility": profile.online_status_visibility,
            "search_discoverable": profile.search_discoverable,
            "visibility_options": visibility_options,
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        serializer = PrivacyVisibilityUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request))


class WorkspacePreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def _cache_key(self, user_id: int) -> str:
        return (
            f"accounts:workspace-preferences:"
            f"schema:{WORKSPACE_WIDGET_SCHEMA_VERSION}:user:{user_id}"
        )

    def _normalize_widget_preferences(self, profile):
        raw_order = profile.workspace_dashboard_widget_order
        if not isinstance(raw_order, list):
            raw_order = []

        raw_visibility = profile.workspace_dashboard_widget_visibility
        if not isinstance(raw_visibility, dict):
            raw_visibility = {}

        normalized_order = []
        seen = set()
        for key in raw_order:
            if key in WORKSPACE_WIDGET_META and key not in seen:
                normalized_order.append(key)
                seen.add(key)

        for key in WORKSPACE_DASHBOARD_WIDGET_KEYS:
            if key not in seen:
                normalized_order.append(key)
                seen.add(key)

        normalized_visibility = {
            key: bool(raw_visibility.get(key, True))
            for key in WORKSPACE_DASHBOARD_WIDGET_KEYS
        }

        changed = (
            profile.workspace_dashboard_widget_order != normalized_order
            or profile.workspace_dashboard_widget_visibility != normalized_visibility
        )
        return normalized_order, normalized_visibility, changed

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        widget_order, widget_visibility, changed = self._normalize_widget_preferences(profile)
        if changed:
            profile.workspace_dashboard_widget_order = widget_order
            profile.workspace_dashboard_widget_visibility = widget_visibility
            profile.save(
                update_fields=[
                    "workspace_dashboard_widget_order",
                    "workspace_dashboard_widget_visibility",
                ]
            )

        widgets = [
            {
                "key": key,
                "label": WORKSPACE_WIDGET_META[key]["label"],
                "description": WORKSPACE_WIDGET_META[key]["description"],
                "visible": widget_visibility.get(key, True),
            }
            for key in widget_order
            if key in WORKSPACE_WIDGET_META
        ]

        return {
            "theme": profile.workspace_theme,
            "layout_density": profile.workspace_layout_density,
            "sidebar_behavior": profile.workspace_sidebar_behavior,
            "default_landing_page": profile.workspace_default_landing_page,
            "default_dashboard": profile.workspace_default_dashboard,
            "widgets": widgets,
            "theme_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.WorkspaceTheme.choices
            ],
            "layout_density_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.WorkspaceDensity.choices
            ],
            "sidebar_behavior_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.WorkspaceSidebarBehavior.choices
            ],
            "landing_page_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.WorkspaceLandingPage.choices
            ],
            "dashboard_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.WorkspaceDashboard.choices
            ],
        }

    def get(self, request):
        cache_key = self._cache_key(request.user.id)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        payload = self._payload(request)
        cache.set(cache_key, payload, timeout=WORKSPACE_PREFERENCES_CACHE_TTL_SECONDS)
        return Response(payload)

    def patch(self, request):
        serializer = WorkspacePreferencesUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        cache_key = self._cache_key(request.user.id)
        cache.delete(cache_key)
        payload = self._payload(request)
        cache.set(cache_key, payload, timeout=WORKSPACE_PREFERENCES_CACHE_TTL_SECONDS)
        return Response(payload)


class TaskWorkflowPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        reminder_options = [dict(option) for option in TASK_REMINDER_TIMING_OPTIONS]
        if all(option["value"] != profile.task_reminder_minutes_before for option in reminder_options):
            reminder_options.insert(
                0,
                {
                    "value": profile.task_reminder_minutes_before,
                    "label": f"{profile.task_reminder_minutes_before} minutes before",
                },
            )

        due_date_options = [dict(option) for option in TASK_DUE_DATE_OFFSET_OPTIONS]
        if all(option["value"] != profile.task_default_due_date_offset_days for option in due_date_options):
            due_date_options.insert(
                0,
                {
                    "value": profile.task_default_due_date_offset_days,
                    "label": f"{profile.task_default_due_date_offset_days} day offset",
                },
            )

        return {
            "default_task_view": profile.task_default_view,
            "task_reminder_minutes_before": profile.task_reminder_minutes_before,
            "task_default_due_date_offset_days": profile.task_default_due_date_offset_days,
            "auto_follow_assigned_tasks": profile.task_auto_follow_assigned_tasks,
            "auto_subscribe_project_updates": profile.task_auto_subscribe_project_updates,
            "approval_delegation_rule": profile.task_approval_delegation_rule,
            "default_task_view_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.TaskDefaultView.choices
            ],
            "task_reminder_timing_options": reminder_options,
            "default_due_date_offset_options": due_date_options,
            "approval_delegation_rule_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.ApprovalDelegationRule.choices
            ],
            "delegations_path": "/settings/workflows/delegations",
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        serializer = TaskWorkflowPreferencesUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request))


class CalendarSchedulingPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        timezone_override = (profile.calendar_timezone_override or "").strip()
        timezone_options = list(ALL_CALENDAR_TIMEZONE_OPTIONS)
        if timezone_override and timezone_override not in timezone_options:
            timezone_options.insert(0, timezone_override)

        return {
            "working_hours_start": profile.calendar_working_hours_start,
            "working_hours_end": profile.calendar_working_hours_end,
            "working_days": profile.calendar_working_days,
            "default_meeting_duration_minutes": profile.calendar_default_meeting_duration_minutes,
            "meeting_buffer_minutes": profile.calendar_meeting_buffer_minutes,
            "timezone_override": timezone_override,
            "calendar_sync_google": profile.calendar_sync_google_enabled,
            "calendar_sync_outlook": profile.calendar_sync_outlook_enabled,
            "calendar_sync_ical": profile.calendar_sync_ical_enabled,
            "default_reminder_minutes": profile.calendar_default_reminder_minutes,
            "working_day_options": [dict(option) for option in CALENDAR_WORKING_DAY_OPTIONS],
            "timezone_options": timezone_options,
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        serializer = CalendarSchedulingPreferencesUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request))


class DataExportPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        report_filters = profile.data_default_report_filters
        if not isinstance(report_filters, dict):
            report_filters = {}

        column_visibility = profile.data_column_visibility
        if not isinstance(column_visibility, dict):
            column_visibility = {}
        normalized_column_visibility = {
            str(key): bool(value) for key, value in column_visibility.items() if str(key).strip()
        }

        saved_views = profile.data_saved_views
        if not isinstance(saved_views, list):
            saved_views = []
        normalized_saved_views = []
        seen_names = set()
        for row in saved_views:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "")).strip()
            if not name:
                continue
            lookup = name.lower()
            if lookup in seen_names:
                continue
            seen_names.add(lookup)
            normalized_saved_views.append(
                {
                    "id": str(row.get("id", "")).strip(),
                    "name": name,
                    "filters": row.get("filters", {}) if isinstance(row.get("filters"), dict) else {},
                    "column_visibility": (
                        {
                            str(key): bool(value)
                            for key, value in row.get("column_visibility", {}).items()
                            if str(key).strip()
                        }
                        if isinstance(row.get("column_visibility"), dict)
                        else {}
                    ),
                    "rows_per_page": (
                        int(row["rows_per_page"])
                        if isinstance(row.get("rows_per_page"), int)
                        else None
                    ),
                }
            )

        rows_per_page_options = list(DATA_ROWS_PER_PAGE_OPTIONS)
        if profile.data_rows_per_page not in rows_per_page_options:
            rows_per_page_options.insert(0, profile.data_rows_per_page)

        return {
            "default_export_format": profile.data_default_export_format,
            "default_report_filters": report_filters,
            "rows_per_page": profile.data_rows_per_page,
            "column_visibility": normalized_column_visibility,
            "saved_views": normalized_saved_views,
            "export_format_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.DataExportFormat.choices
            ],
            "rows_per_page_options": rows_per_page_options,
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        serializer = DataExportPreferencesUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request))


class AccessibilityPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return {
            "font_size": profile.accessibility_font_size,
            "high_contrast_mode": profile.accessibility_high_contrast_mode,
            "reduced_motion": profile.accessibility_reduced_motion,
            "screen_reader_support": profile.accessibility_screen_reader_support,
            "keyboard_navigation": profile.accessibility_keyboard_navigation,
            "font_size_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.AccessibilityFontSize.choices
            ],
        }

    def get(self, request):
        return Response(self._payload(request))

    def patch(self, request):
        serializer = AccessibilityPreferencesUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self._payload(request))


class UserIntegrationsView(APIView):
    permission_classes = [IsAuthenticated]

    def _payload(self, request):
        connections = {
            row.provider: row
            for row in UserIntegrationConnection.objects.filter(user=request.user)
        }
        integrations = []
        for provider, label in UserIntegrationConnection.Provider.choices:
            row = connections.get(provider)
            status_value = row.status if row else "disconnected"
            supports_token_refresh = provider != UserIntegrationConnection.Provider.WEBHOOKS
            is_connected = row is not None and row.status == UserIntegrationConnection.Status.CONNECTED
            integrations.append(
                {
                    "provider": provider,
                    "provider_display": label,
                    "status": status_value,
                    "status_display": (
                        row.get_status_display()
                        if row
                        else "Disconnected"
                    ),
                    "account_label": row.account_label if row else "",
                    "webhook_url": row.webhook_url if row else "",
                    "connected_at": row.connected_at if row else None,
                    "revoked_at": row.revoked_at if row else None,
                    "last_token_refresh_at": row.last_token_refresh_at if row else None,
                    "token_expires_at": row.token_expires_at if row else None,
                    "supports_token_refresh": supports_token_refresh,
                    "supports_webhook_url": provider == UserIntegrationConnection.Provider.WEBHOOKS,
                    "is_connected": is_connected,
                }
            )

        return {
            "integrations": integrations,
        }

    def get(self, request):
        return Response(self._payload(request))

    def post(self, request):
        serializer = UserIntegrationActionSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        provider = validated["provider"]
        action = validated["action"]
        account_label = validated.get("account_label", "").strip()
        webhook_url = validated.get("webhook_url", "").strip()
        token_expires_in_minutes = validated.get("token_expires_in_minutes")
        now = timezone.now()

        connection = UserIntegrationConnection.objects.filter(
            user=request.user,
            provider=provider,
        ).first()

        if action == UserIntegrationActionSerializer.ACTION_CONNECT:
            created = connection is None
            if connection is None:
                connection = UserIntegrationConnection(user=request.user, provider=provider)
            connection.status = UserIntegrationConnection.Status.CONNECTED
            connection.revoked_at = None
            connection.connected_at = now
            if "account_label" in validated:
                connection.account_label = account_label
            if provider == UserIntegrationConnection.Provider.WEBHOOKS and webhook_url:
                connection.webhook_url = webhook_url
            if provider != UserIntegrationConnection.Provider.WEBHOOKS:
                connection.last_token_refresh_at = now
                if token_expires_in_minutes is not None:
                    connection.token_expires_at = now + timedelta(minutes=token_expires_in_minutes)
                elif connection.token_expires_at is None:
                    connection.token_expires_at = now + timedelta(days=90)
            connection.save()

            log_user_security_event(
                user=request.user,
                principal=request.user.email,
                event_type=UserSecurityEvent.EventType.PROVIDER_LINKED,
                status=UserSecurityEvent.Status.SUCCESS,
                request=request,
                provider=provider,
                detail=f"{connection.get_provider_display()} integration {'connected' if created else 'reconnected'}.",
            )
            payload = self._payload(request)
            payload["detail"] = f"{connection.get_provider_display()} connected."
            return Response(payload, status=status.HTTP_200_OK)

        if connection is None:
            return Response(
                {"detail": "Integration is not connected yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action == UserIntegrationActionSerializer.ACTION_REVOKE:
            connection.status = UserIntegrationConnection.Status.REVOKED
            connection.revoked_at = now
            if provider == UserIntegrationConnection.Provider.WEBHOOKS:
                connection.webhook_url = ""
            connection.save(update_fields=["status", "revoked_at", "webhook_url", "updated_at"])
            payload = self._payload(request)
            payload["detail"] = f"{connection.get_provider_display()} revoked."
            return Response(payload, status=status.HTTP_200_OK)

        if action == UserIntegrationActionSerializer.ACTION_REFRESH_TOKEN:
            if connection.status != UserIntegrationConnection.Status.CONNECTED:
                return Response(
                    {"detail": "Integration must be connected before refreshing token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            connection.last_token_refresh_at = now
            if token_expires_in_minutes is not None:
                connection.token_expires_at = now + timedelta(minutes=token_expires_in_minutes)
            elif connection.token_expires_at is None:
                connection.token_expires_at = now + timedelta(days=90)
            else:
                remaining = connection.token_expires_at - now
                extension = remaining if remaining.total_seconds() > 0 else timedelta(days=90)
                connection.token_expires_at = now + extension
            connection.save(update_fields=["last_token_refresh_at", "token_expires_at", "updated_at"])
            payload = self._payload(request)
            payload["detail"] = f"{connection.get_provider_display()} token refreshed."
            return Response(payload, status=status.HTTP_200_OK)

        return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)


class CompleteTourView(generics.CreateAPIView):
    serializer_class = CompleteTourSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class CompanySetupView(generics.CreateAPIView):
    serializer_class = CompanySetupSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


class CheckCompanyView(generics.CreateAPIView):
    serializer_class = CheckCompanySerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class InviteStaffView(generics.CreateAPIView):
    serializer_class = InviteStaffSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class CompleteOnboardingView(generics.CreateAPIView):
    serializer_class = CompleteOnboardingSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class GettingStartedStatusView(APIView):
    """Return setup-task completion status for the Getting Started checklist."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import Invitation
        from apps.projects.models import Project

        profile = getattr(request.user, "profile", None)
        org = getattr(profile, "organization", None) if profile else None

        profile_complete = bool(
            profile
            and (profile.profile_photo or profile.job_title)
        )

        first_project_created = bool(
            org and Project.objects.filter(organization=org).exists()
        )

        team_invited = bool(
            org
            and (
                UserProfile.objects.filter(organization=org).count() > 1
                or Invitation.objects.filter(organization=org).exists()
            )
        )

        return Response(
            {
                "profile_complete": profile_complete,
                "first_project_created": first_project_created,
                "team_invited": team_invited,
            }
        )


# ---------------------------------------------------------------------------
# Organization Subscription
# ---------------------------------------------------------------------------


class OrganizationSubscriptionView(generics.RetrieveAPIView):
    """Retrieve the current org's subscription."""

    serializer_class = OrganizationSubscriptionSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "view"

    def get_object(self):
        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        subscription = OrganizationSubscription.objects.select_related(
            "edition", "organization"
        ).get(organization=org)

        # Compute seats_used from actual active users
        subscription.seats_used = UserProfile.objects.filter(
            organization=org,
            user_status="active",
        ).count()

        # Compute storage_used_gb from file models
        subscription.storage_used_gb = self._compute_storage_gb(org)

        return subscription

    @staticmethod
    def _compute_storage_gb(org):
        from decimal import Decimal

        from django.core.files.storage import default_storage
        from django.db.models import Sum

        from apps.hr.models import HRDocument
        from apps.projects.models import ProjectDailySiteReportPhoto, ProjectSupportingAttachment
        from apps.properties.models import PropertyDocument, PropertyImage

        total_bytes = 0

        # HRDocument — has file_size tracked (fast aggregate)
        hr_total = (
            HRDocument.objects.filter(organization=org).aggregate(
                total=Sum("file_size")
            )["total"]
            or 0
        )
        total_bytes += hr_total

        # Other file models — read sizes from storage backend
        file_queries = [
            (ProjectSupportingAttachment.objects.filter(organization=org), "file"),
            (ProjectDailySiteReportPhoto.objects.filter(organization=org), "image"),
            (PropertyImage.objects.filter(organization=org), "image"),
            (PropertyDocument.objects.filter(organization=org), "file"),
        ]
        for qs, field_name in file_queries:
            for name in qs.values_list(field_name, flat=True):
                if name:
                    try:
                        total_bytes += default_storage.size(name)
                    except Exception:
                        pass

        # Convert bytes → GB
        if total_bytes == 0:
            return Decimal("0.00")
        return (Decimal(str(total_bytes)) / Decimal(str(1024**3))).quantize(
            Decimal("0.01")
        )


class SubscriptionEventListView(generics.ListAPIView):
    """List subscription events for the current org."""

    serializer_class = SubscriptionEventSerializer
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "view"

    def get_queryset(self):
        profile = getattr(self.request.user, "profile", None)
        org = getattr(profile, "organization", None)
        return (
            SubscriptionEvent.objects.filter(subscription__organization=org)
            .select_related("from_edition", "to_edition", "actor")
            .order_by("-occurred_at")
        )


class StartTrialView(APIView):
    """Start a 14-day trial on the Growth plan for the requesting user's org."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request):
        profile = getattr(request.user, "profile", None)
        org = getattr(profile, "organization", None)

        if not org:
            return Response(
                {"detail": "No organization found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if getattr(profile, "role", None) != "admin":
            return Response(
                {"detail": "Only organization admins can start a trial."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if getattr(profile, "is_demo_account", False):
            return Response(
                {"detail": "Demo accounts already have an active trial."},
                status=status.HTTP_409_CONFLICT,
            )

        # Idempotent: return existing subscription if one exists
        existing = OrganizationSubscription.objects.filter(organization=org).first()
        if existing:
            serializer = OrganizationSubscriptionSerializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)

        from apps.settings.models import PlatformEdition

        edition_key = request.data.get("edition_key", "growth")
        edition = PlatformEdition.objects.filter(
            key=edition_key, is_active=True, is_custom=False
        ).first()
        if edition is None:
            return Response(
                {"detail": f"Edition '{edition_key}' not found or not available for trial."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        trial_end = now + timedelta(days=14)

        subscription = OrganizationSubscription.objects.create(
            organization=org,
            edition=edition,
            status=OrganizationSubscription.Status.TRIALING,
            trial_start=now,
            trial_end=trial_end,
            current_period_start=now,
            current_period_end=trial_end,
        )

        org.subscription_tier = edition.key
        org.save(update_fields=["subscription_tier"])

        SubscriptionEvent.objects.create(
            subscription=subscription,
            event_type=SubscriptionEvent.EventType.TRIAL_STARTED,
            to_edition=edition,
            actor=request.user,
            metadata={"source": "self_signup", "trial_days": 14},
        )

        from apps.notifications.models import Notification

        from .emails import send_trial_confirmation_email

        send_trial_confirmation_email(request.user, edition.name, trial_end)

        Notification.objects.create(
            recipient=request.user,
            organization=org,
            title="Your trial is active",
            message=(
                f"Your 14-day free trial of the {edition.name} plan is now active. "
                f"Explore all features before it ends on "
                f"{trial_end.strftime('%B %d, %Y')}."
            ),
            severity=Notification.Severity.INFO,
            category=Notification.Category.SYSTEM,
            link_url="/settings/subscription",
        )

        serializer = OrganizationSubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def _get_subscription_or_error(request):
    """Shared helper: resolve org, check admin role, fetch subscription."""
    profile = getattr(request.user, "profile", None)
    org = getattr(profile, "organization", None)
    if not org:
        return None, None, Response(
            {"detail": "No organization found."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if getattr(profile, "role", None) != "admin":
        return None, None, Response(
            {"detail": "Only organization admins can manage subscriptions."},
            status=status.HTTP_403_FORBIDDEN,
        )
    sub = (
        OrganizationSubscription.objects.filter(organization=org)
        .select_related("edition")
        .first()
    )
    if not sub:
        return None, org, Response(
            {"detail": "No subscription found."},
            status=status.HTTP_404_NOT_FOUND,
        )
    return sub, org, None


def _payment_summary(card_digits: str) -> str:
    """Derive a display string like 'Visa ending 4242' from raw card digits."""
    last_four = card_digits[-4:]
    brand = {"4": "Visa", "5": "Mastercard", "3": "Amex", "6": "Discover"}.get(
        card_digits[0], "Card"
    )
    return f"{brand} ending {last_four}"


class SubscriptionCheckoutView(APIView):
    """
    Unified checkout: upgrade, downgrade, renew, activate from trial,
    or first purchase.  Simulated payment (no real gateway).
    """

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request):
        from apps.notifications.models import Notification
        from apps.settings.models import PlatformEdition

        profile = getattr(request.user, "profile", None)
        org = getattr(profile, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if getattr(profile, "role", None) != "admin":
            return Response(
                {"detail": "Only organization admins can manage subscriptions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SubscriptionCheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_edition = PlatformEdition.objects.get(
            key=data["edition_key"], is_active=True, is_custom=False
        )
        new_cycle = data["billing_cycle"]
        card_data = data["payment"]
        now = timezone.now()
        period_end = now + timedelta(days=365 if new_cycle == "annual" else 30)

        sub = (
            OrganizationSubscription.objects.filter(organization=org)
            .select_related("edition")
            .first()
        )

        if sub is None:
            # First purchase — no trial existed
            sub = OrganizationSubscription.objects.create(
                organization=org,
                edition=new_edition,
                status=OrganizationSubscription.Status.ACTIVE,
                billing_cycle=new_cycle,
                current_period_start=now,
                current_period_end=period_end,
                payment_method_summary=_payment_summary(card_data["card_number"]),
                auto_renew=True,
            )
            SubscriptionEvent.objects.create(
                subscription=sub,
                event_type=SubscriptionEvent.EventType.ACTIVATED,
                to_edition=new_edition,
                actor=request.user,
                metadata={"billing_cycle": new_cycle, "source": "checkout"},
            )
        else:
            old_edition = sub.edition

            # Determine event type
            if sub.status in ("expired", "cancelled"):
                event_type = SubscriptionEvent.EventType.RENEWED
            elif sub.status == "trialing":
                event_type = SubscriptionEvent.EventType.ACTIVATED
            elif new_edition.tier_level > old_edition.tier_level:
                event_type = SubscriptionEvent.EventType.UPGRADED
            elif new_edition.tier_level < old_edition.tier_level:
                event_type = SubscriptionEvent.EventType.DOWNGRADED
            else:
                event_type = SubscriptionEvent.EventType.RENEWED

            sub.edition = new_edition
            sub.status = OrganizationSubscription.Status.ACTIVE
            sub.billing_cycle = new_cycle
            sub.current_period_start = now
            sub.current_period_end = period_end
            sub.payment_method_summary = _payment_summary(card_data["card_number"])
            sub.auto_renew = True
            sub.cancelled_at = None
            sub.cancel_reason = ""
            sub.save(
                update_fields=[
                    "edition",
                    "status",
                    "billing_cycle",
                    "current_period_start",
                    "current_period_end",
                    "payment_method_summary",
                    "auto_renew",
                    "cancelled_at",
                    "cancel_reason",
                    "updated_at",
                ]
            )

            SubscriptionEvent.objects.create(
                subscription=sub,
                event_type=event_type,
                from_edition=old_edition if old_edition != new_edition else None,
                to_edition=new_edition,
                actor=request.user,
                metadata={
                    "billing_cycle": new_cycle,
                    "previous_billing_cycle": sub.billing_cycle,
                    "source": "checkout",
                },
            )

        org.subscription_tier = new_edition.key
        org.save(update_fields=["subscription_tier"])

        Notification.objects.create(
            recipient=request.user,
            organization=org,
            title="Subscription updated",
            message=f"Your subscription has been updated to {new_edition.name} ({new_cycle}).",
            severity=Notification.Severity.INFO,
            category=Notification.Category.SYSTEM,
            link_url="/settings/subscription",
        )

        return Response(
            OrganizationSubscriptionSerializer(sub).data,
            status=status.HTTP_200_OK,
        )


class SubscriptionCancelView(APIView):
    """Cancel the current subscription."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request):
        from apps.notifications.models import Notification

        sub, org, err = _get_subscription_or_error(request)
        if err:
            return err

        if sub.status in ("cancelled", "expired"):
            return Response(
                {"detail": "Subscription is already cancelled or expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubscriptionCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        now = timezone.now()
        sub.cancelled_at = now
        sub.cancel_reason = data.get("reason", "")
        sub.auto_renew = False
        sub.status = OrganizationSubscription.Status.CANCELLED

        if data.get("cancel_immediately", False):
            sub.current_period_end = now

        sub.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancel_reason",
                "auto_renew",
                "current_period_end",
                "updated_at",
            ]
        )

        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEvent.EventType.CANCELLED,
            from_edition=sub.edition,
            actor=request.user,
            metadata={
                "reason": data.get("reason", ""),
                "immediate": data.get("cancel_immediately", False),
            },
        )

        Notification.objects.create(
            recipient=request.user,
            organization=org,
            title="Subscription cancelled",
            message=f"Your {sub.edition.name} subscription has been cancelled.",
            severity=Notification.Severity.WARNING,
            category=Notification.Category.SYSTEM,
            link_url="/settings/subscription",
        )

        return Response(
            OrganizationSubscriptionSerializer(sub).data,
            status=status.HTTP_200_OK,
        )


class SubscriptionReactivateView(APIView):
    """Re-enable a cancelled subscription that hasn't expired yet."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request):
        sub, org, err = _get_subscription_or_error(request)
        if err:
            return err

        if sub.status != "cancelled":
            return Response(
                {"detail": "Only cancelled subscriptions can be reactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        if sub.current_period_end and sub.current_period_end < now:
            return Response(
                {"detail": "This subscription has expired. Use checkout to renew instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub.status = OrganizationSubscription.Status.ACTIVE
        sub.cancelled_at = None
        sub.cancel_reason = ""
        sub.auto_renew = True
        sub.save(
            update_fields=[
                "status",
                "cancelled_at",
                "cancel_reason",
                "auto_renew",
                "updated_at",
            ]
        )

        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEvent.EventType.REACTIVATED,
            to_edition=sub.edition,
            actor=request.user,
            metadata={"source": "self_service"},
        )

        return Response(
            OrganizationSubscriptionSerializer(sub).data,
            status=status.HTTP_200_OK,
        )


class SubscriptionPaymentMethodView(APIView):
    """Update payment method on an existing subscription."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request):
        sub, org, err = _get_subscription_or_error(request)
        if err:
            return err

        serializer = PaymentMethodUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        card_data = serializer.validated_data["payment"]

        sub.payment_method_summary = _payment_summary(card_data["card_number"])
        sub.save(update_fields=["payment_method_summary", "updated_at"])

        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEvent.EventType.PAYMENT_RECOVERED,
            actor=request.user,
            metadata={"action": "payment_method_updated"},
        )

        return Response(
            OrganizationSubscriptionSerializer(sub).data,
            status=status.HTTP_200_OK,
        )


class AddOnCatalogView(generics.ListAPIView):
    """List all active subscription add-ons."""

    serializer_class = SubscriptionAddOnSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from apps.settings.models import SubscriptionAddOn

        return SubscriptionAddOn.objects.filter(is_active=True)


class PurchaseAddOnView(APIView):
    """Purchase a subscription add-on for the current org."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request):
        from apps.settings.models import SubscriptionAddOn

        sub, org, err = _get_subscription_or_error(request)
        if err:
            return err

        serializer = PurchaseAddOnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = serializer.validated_data["add_on_key"]

        try:
            add_on = SubscriptionAddOn.objects.get(key=key, is_active=True)
        except SubscriptionAddOn.DoesNotExist:
            return Response(
                {"detail": f"Add-on '{key}' not found or not available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if ActiveSubscriptionAddOn.objects.filter(
            subscription=sub, add_on=add_on
        ).exists():
            return Response(
                {"detail": "This add-on is already active."},
                status=status.HTTP_409_CONFLICT,
            )

        ActiveSubscriptionAddOn.objects.create(subscription=sub, add_on=add_on)

        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEvent.EventType.ACTIVATED,
            actor=request.user,
            metadata={"add_on": key, "add_on_name": add_on.name, "price": str(add_on.monthly_price)},
        )

        # Re-fetch to include the new add-on in the response
        sub.refresh_from_db()
        return Response(
            OrganizationSubscriptionSerializer(sub).data,
            status=status.HTTP_201_CREATED,
        )


class CancelAddOnView(APIView):
    """Remove an active subscription add-on."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    throttle_classes = [SensitiveActionThrottle]
    rbac_sub_module = "settings.subscriptions"
    rbac_action = "manage"

    def post(self, request, pk):
        sub, org, err = _get_subscription_or_error(request)
        if err:
            return err

        try:
            active_addon = ActiveSubscriptionAddOn.objects.select_related(
                "add_on"
            ).get(pk=pk, subscription=sub)
        except ActiveSubscriptionAddOn.DoesNotExist:
            return Response(
                {"detail": "Add-on not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        add_on = active_addon.add_on
        active_addon.delete()

        SubscriptionEvent.objects.create(
            subscription=sub,
            event_type=SubscriptionEvent.EventType.CANCELLED,
            actor=request.user,
            metadata={"add_on": add_on.key, "add_on_name": add_on.name},
        )

        sub.refresh_from_db()
        return Response(
            OrganizationSubscriptionSerializer(sub).data,
            status=status.HTTP_200_OK,
        )


class RequestDemoView(generics.CreateAPIView):
    """Public endpoint for leads to request a product demo."""

    serializer_class = DemoRequestSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        demo_request = serializer.save()
        from .tasks import provision_demo_org_task

        provision_demo_org_task.delay(demo_request.id)

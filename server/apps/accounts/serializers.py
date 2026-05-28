import base64
import logging
import secrets
import uuid
from zoneinfo import available_timezones

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import (
    USER_NOTIFICATION_CATEGORIES,
    USER_NOTIFICATION_CHANNELS,
    USER_NOTIFICATION_FREQUENCIES,
)
from apps.settings.models import Department, Role

from .emails import send_invitation_email, send_otp_email, send_password_reset_email, send_verification_email
from .models import (
    WORKSPACE_DASHBOARD_WIDGET_KEYS,
    ActiveSubscriptionAddOn,
    Invitation,
    Organization,
    OrganizationSubscription,
    SubscriptionEvent,
    UserAuthSession,
    UserIntegrationConnection,
    UserProfile,
    UserSecurityEvent,
)
from .org_name_utils import extract_email_domain, find_similar_organizations, normalize_org_name
from .security import issue_tokens_for_user, log_user_security_event
from .turnstile import HoneypotMixin

User = get_user_model()
logger = logging.getLogger(__name__)
ALL_TIMEZONE_OPTIONS = tuple(sorted(available_timezones()))
DEFAULT_LANGUAGE_OPTIONS = tuple(
    {
        "value": str(code).strip().lower(),
        "label": str(label).strip(),
    }
    for code, label in getattr(settings, "LANGUAGES", ())
)


def _bootstrap_org_name_for_user(user: User) -> str:
    return f"Workspace-{user.pk}"


def _is_bootstrap_org_for_user(org: Organization | None, user: User) -> bool:
    if org is None:
        return False
    prefix = _bootstrap_org_name_for_user(user)
    return org.name == prefix or org.name.startswith(f"{prefix}-")


def _mfa_required_for_user(user):
    """Return True if the org MFA policy requires OTP for this user."""
    profile = getattr(user, "profile", None)
    if not profile or not profile.organization:
        return True  # default: require MFA when org context is missing

    policy = profile.organization.mfa_enforcement

    if policy == "disabled":
        return False
    if policy == "required_all":
        return True
    if policy == "required_admins":
        return profile.role == "admin"
    # "optional" — honour per-user flag
    return profile.mfa_enabled

OTP_CACHE_PREFIX = "otp_session:"
OTP_TTL = 300  # 5 minutes

RESET_CACHE_PREFIX = "pw_reset:"
RESET_TTL = 900  # 15 minutes

VERIFY_CACHE_PREFIX = "email_verify:"
VERIFY_TTL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterSerializer(HoneypotMixin, serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10)
    org_name = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    invitation_token = serializers.CharField(required=False, allow_blank=True)
    hp_field = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_org_name(self, value):
        value = value.strip()
        if not value:
            return value
        normalized = normalize_org_name(value)
        if Organization.objects.filter(normalized_name=normalized).exclude(
            name__startswith="Workspace-"
        ).exists():
            raise serializers.ValidationError(
                "This company already exists on developerOS. "
                "Contact your company administrator to receive an invitation."
            )
        if Organization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "This company already exists on developerOS. "
                "Contact your company administrator to receive an invitation."
            )
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        full_name = validated_data["full_name"].strip()
        parts = full_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
        invitation_token = validated_data.get("invitation_token", "")
        org_name = validated_data.get("org_name", "").strip()

        # Check for valid invitation
        invitation = None
        if invitation_token:
            try:
                invitation = Invitation.objects.get(
                    token=invitation_token,
                    status="pending",
                )
            except (Invitation.DoesNotExist, ValueError):
                pass

        # Create user — inactive unless invited
        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=first_name,
            last_name=last_name,
            is_active=bool(invitation),
        )

        # Profile is auto-created by signal; update if invited
        if invitation:
            # Enforce seat limit at acceptance time
            from apps.settings.quotas import check_seat_quota

            check_seat_quota(invitation.organization)

            # Apply pre-provisioned name if the inviter set it and user didn't override
            if invitation.first_name and not first_name:
                user.first_name = invitation.first_name
            if invitation.last_name and not last_name:
                user.last_name = invitation.last_name
            if invitation.first_name or invitation.last_name:
                user.save(update_fields=["first_name", "last_name"])

            profile = user.profile
            bootstrap_org = profile.organization
            profile.organization = invitation.organization
            profile.role = "member"
            if invitation.role_id:
                profile.assigned_role_id = invitation.role_id
            if invitation.department_id:
                profile.department_id = invitation.department_id
            if invitation.job_title:
                profile.job_title = invitation.job_title
            profile.save()
            invitation.status = "accepted"
            invitation.save()

            # If registration came from invitation flow, remove the temporary
            # bootstrap workspace created at user creation time.
            if (
                bootstrap_org
                and _is_bootstrap_org_for_user(bootstrap_org, user)
                and not bootstrap_org.members.exists()
            ):
                bootstrap_org.delete()
        else:
            # Rename bootstrap org to the user-chosen org name
            if org_name:
                profile = user.profile
                org = profile.organization
                if org:
                    org.name = org_name
                    org.created_by = user
                    domain = extract_email_domain(validated_data["email"])
                    if domain:
                        org.email_domain = domain
                    org.save(update_fields=["name", "created_by", "email_domain"])
                    profile.role = "admin"
                    profile.save(update_fields=["role"])

            # Generate email verification token
            token = str(uuid.uuid4())
            cache.set(
                f"{VERIFY_CACHE_PREFIX}{token}",
                {"user_id": user.pk},
                timeout=VERIFY_TTL,
            )
            org_details = {}
            if org_name:
                profile = user.profile
                if profile.organization:
                    org_details = {
                        "org_name": profile.organization.name,
                        "org_id": profile.organization.id,
                    }
            send_verification_email(user, token, **org_details)

        return {
            "message": "Account created. Please check your email to verify your account."
            if not invitation
            else "Account created. You can now log in.",
        }


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        key = f"{VERIFY_CACHE_PREFIX}{value}"
        data = cache.get(key)
        if data is None:
            raise serializers.ValidationError("Verification link has expired or is invalid.")
        return value

    def create(self, validated_data):
        key = f"{VERIFY_CACHE_PREFIX}{validated_data['token']}"
        data = cache.get(key)
        cache.delete(key)

        user = User.objects.get(pk=data["user_id"])
        user.is_active = True
        user.save()

        from apps.notifications.models import Notification

        profile = getattr(user, "profile", None)
        org = getattr(profile, "organization", None) if profile else None
        Notification.objects.create(
            recipient=user,
            organization=org,
            title="Welcome to developerOS",
            message="Your email has been verified and your account is active. Welcome aboard!",
            severity=Notification.Severity.INFO,
            category=Notification.Category.SYSTEM,
            link_url="/",
        )

        return {"message": "Email verified successfully."}


# ---------------------------------------------------------------------------
# Login & OTP
# ---------------------------------------------------------------------------

class LoginSerializer(HoneypotMixin, serializers.Serializer):
    credential = serializers.CharField()
    password = serializers.CharField(write_only=True)
    hp_field = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs):
        credential = attrs["credential"].strip()
        request = self.context.get("request")

        # Look up by email or username
        try:
            if "@" in credential:
                user_obj = User.objects.get(email__iexact=credential)
            else:
                user_obj = User.objects.get(username__iexact=credential)
        except User.DoesNotExist:
            log_user_security_event(
                principal=credential,
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=UserAuthSession.AuthProvider.PASSWORD,
                request=request,
                detail="Credential not found.",
            )
            raise serializers.ValidationError({"detail": "Invalid credentials."}) from None

        user = authenticate(
            request=request,
            username=user_obj.username,
            password=attrs["password"],
        )
        if user is None:
            log_user_security_event(
                user=user_obj,
                principal=credential,
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=UserAuthSession.AuthProvider.PASSWORD,
                request=request,
                detail="Incorrect password.",
            )
            raise serializers.ValidationError({"detail": "Invalid credentials."})
        if not user.is_active:
            log_user_security_event(
                user=user,
                principal=credential,
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=UserAuthSession.AuthProvider.PASSWORD,
                request=request,
                detail="Inactive account attempted login.",
            )
            raise serializers.ValidationError({"detail": "Please verify your email before logging in."})

        # Enforce IAM user_status
        profile = getattr(user, "profile", None)
        if profile and profile.user_status in ("suspended", "locked"):
            log_user_security_event(
                user=user,
                principal=credential,
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=UserAuthSession.AuthProvider.PASSWORD,
                request=request,
                detail=f"Blocked by user status: {profile.user_status}.",
            )
            raise serializers.ValidationError(
                {"detail": "Your account has been suspended. Contact your administrator."}
            )

        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        remember_me = validated_data.get("remember_me", False)

        # Skip OTP if MFA is not required for this user
        if not _mfa_required_for_user(user):
            tokens = issue_tokens_for_user(
                user=user,
                request=self.context.get("request"),
                remember_me=remember_me,
                provider=UserAuthSession.AuthProvider.PASSWORD,
            )
            log_user_security_event(
                user=user,
                principal=user.email,
                event_type=UserSecurityEvent.EventType.LOGIN_SUCCESS,
                status=UserSecurityEvent.Status.SUCCESS,
                provider=UserAuthSession.AuthProvider.PASSWORD,
                request=self.context.get("request"),
                detail="Password authentication successful.",
                metadata={"session_id": tokens["session_id"]},
            )
            return tokens

        # MFA required — create session
        from .mfa import get_available_mfa_methods

        available_methods = get_available_mfa_methods(user)

        otp = f"{secrets.randbelow(1_000_000):06d}"
        session_id = str(uuid.uuid4())

        cache.set(
            f"{OTP_CACHE_PREFIX}{session_id}",
            {
                "user_id": user.pk,
                "otp": otp,
                "attempts": 0,
                "remember_me": remember_me,
                "provider": UserAuthSession.AuthProvider.PASSWORD,
            },
            timeout=OTP_TTL,
        )

        # Only auto-send email OTP if no stronger method is configured
        primary = available_methods[0] if available_methods else "email"
        if primary == "email":
            from threading import Thread


            def _send():
                try:
                    send_otp_email(user, otp)
                except Exception:
                    pass

            Thread(target=_send, daemon=True).start()

        log_user_security_event(
            user=user,
            principal=user.email,
            event_type=UserSecurityEvent.EventType.OTP_CHALLENGE,
            status=UserSecurityEvent.Status.INFO,
            provider=UserAuthSession.AuthProvider.PASSWORD,
            request=self.context.get("request"),
            detail="MFA challenge created for login.",
        )

        return {
            "otp_session": session_id,
            "available_methods": available_methods,
        }


class VerifyOTPSerializer(serializers.Serializer):
    otp_session = serializers.CharField()
    code = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    method = serializers.ChoiceField(
        choices=["email", "totp", "recovery", "passkey"],
        default="email",
    )
    credential = serializers.JSONField(required=False)

    def validate(self, attrs):
        key = f"{OTP_CACHE_PREFIX}{attrs['otp_session']}"
        data = cache.get(key)
        request = self.context.get("request")
        method = attrs.get("method", "email")

        if data is None:
            log_user_security_event(
                principal="otp-session-expired",
                event_type=UserSecurityEvent.EventType.OTP_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                request=request,
                detail="MFA session expired before verification.",
            )
            raise serializers.ValidationError(
                {"detail": "Session expired. Please log in again."}
            )

        if data["attempts"] >= 5:
            cache.delete(key)
            if data.get("user_id"):
                try:
                    user = User.objects.get(pk=data["user_id"])
                except User.DoesNotExist:
                    user = None
                log_user_security_event(
                    user=user,
                    principal=user.email if user else "",
                    event_type=UserSecurityEvent.EventType.OTP_FAILED,
                    status=UserSecurityEvent.Status.FAILED,
                    provider=data.get("provider", ""),
                    request=request,
                    detail="MFA verification exceeded max attempts.",
                )
            raise serializers.ValidationError(
                {"detail": "Too many failed attempts. Please log in again."}
            )

        # Resolve user
        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            cache.delete(key)
            raise serializers.ValidationError({"detail": "Invalid session."}) from None

        code = attrs.get("code", "")
        verified = False

        if method == "email":
            verified = bool(code and data["otp"] == code)
        elif method == "totp":
            from .mfa import verify_totp_code
            from .models import TOTPDevice

            device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
            if device and verify_totp_code(device.secret, code):
                device.last_used_at = timezone.now()
                device.save(update_fields=["last_used_at"])
                verified = True
        elif method == "recovery":
            from .mfa import verify_recovery_code

            if verify_recovery_code(user, code):
                verified = True
        elif method == "passkey":
            credential_data = attrs.get("credential")
            if not credential_data:
                raise serializers.ValidationError(
                    {"credential": "Required for passkey verification."}
                )
            verified = self._verify_passkey(attrs, user, credential_data)

        if not verified:
            data["attempts"] += 1
            cache.set(key, data, timeout=OTP_TTL)
            log_user_security_event(
                user=user,
                principal=user.email,
                event_type=UserSecurityEvent.EventType.OTP_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=data.get("provider", ""),
                request=request,
                detail=f"Invalid {method} verification.",
                metadata={"attempts": data["attempts"], "method": method},
            )
            error_messages = {
                "email": "Invalid verification code.",
                "totp": "Invalid authenticator code.",
                "recovery": "Invalid recovery code.",
                "passkey": "Passkey verification failed.",
            }
            raise serializers.ValidationError(
                {"detail": error_messages.get(method, "Verification failed.")}
            )

        cache.delete(key)
        attrs["user_id"] = data["user_id"]
        attrs["remember_me"] = data.get("remember_me", False)
        attrs["provider"] = data.get("provider", UserAuthSession.AuthProvider.PASSWORD)
        attrs["mfa_method"] = method
        return attrs

    def _verify_passkey(self, attrs, user, credential_data):
        """Verify a WebAuthn assertion for passkey-based MFA."""
        from webauthn import verify_authentication_response
        from webauthn.helpers import bytes_to_base64url

        from .mfa import get_webauthn_origin, get_webauthn_rp_id
        from .models import WebAuthnCredential

        challenge_key = f"webauthn_auth:{attrs['otp_session']}"
        stored_challenge = cache.get(challenge_key)
        if not stored_challenge:
            raise serializers.ValidationError(
                {"detail": "Passkey challenge expired. Request new options."}
            )
        cache.delete(challenge_key)

        # Match credential by ID
        webauthn_cred = None
        for cred in WebAuthnCredential.objects.filter(user=user):
            if bytes_to_base64url(cred.credential_id) == credential_data.get("id"):
                webauthn_cred = cred
                break

        if not webauthn_cred:
            return False

        try:
            verification = verify_authentication_response(
                credential=credential_data,
                expected_challenge=base64.b64decode(stored_challenge),
                expected_rp_id=get_webauthn_rp_id(),
                expected_origin=get_webauthn_origin(),
                credential_public_key=webauthn_cred.public_key,
                credential_current_sign_count=webauthn_cred.sign_count,
            )
            webauthn_cred.sign_count = verification.new_sign_count
            webauthn_cred.last_used_at = timezone.now()
            webauthn_cred.save(update_fields=["sign_count", "last_used_at"])
            return True
        except Exception:
            return False

    def create(self, validated_data):
        user = User.objects.get(pk=validated_data["user_id"])

        # Re-check IAM status before minting tokens (status may have changed since login)
        profile = getattr(user, "profile", None)
        if profile and profile.user_status in ("suspended", "locked"):
            raise serializers.ValidationError(
                {"detail": "Your account has been suspended. Contact your administrator."}
            )

        mfa_method = validated_data.get("mfa_method", "email")
        tokens = issue_tokens_for_user(
            user=user,
            request=self.context.get("request"),
            remember_me=validated_data.get("remember_me", False),
            provider=validated_data.get("provider", UserAuthSession.AuthProvider.PASSWORD),
            mfa_verified=True,
            mfa_method=mfa_method,
        )
        log_user_security_event(
            user=user,
            principal=user.email,
            event_type=UserSecurityEvent.EventType.LOGIN_SUCCESS,
            status=UserSecurityEvent.Status.SUCCESS,
            provider=validated_data.get("provider", UserAuthSession.AuthProvider.PASSWORD),
            request=self.context.get("request"),
            detail=f"MFA verification successful ({mfa_method}).",
            metadata={"session_id": tokens["session_id"], "mfa_method": mfa_method},
        )
        return tokens


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def create(self, validated_data):
        email = validated_data["email"].lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return silently to prevent email enumeration
            return {"message": "If an account exists, a reset link has been sent."}

        token = str(uuid.uuid4())
        cache.set(
            f"{RESET_CACHE_PREFIX}{token}",
            {"user_id": user.pk},
            timeout=RESET_TTL,
        )

        send_password_reset_email(user, token)

        return {"message": "If an account exists, a reset link has been sent."}


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=10)

    def validate_token(self, value):
        key = f"{RESET_CACHE_PREFIX}{value}"
        data = cache.get(key)
        if data is None:
            raise serializers.ValidationError("Reset link has expired or is invalid.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        key = f"{RESET_CACHE_PREFIX}{validated_data['token']}"
        data = cache.get(key)
        cache.delete(key)

        user = User.objects.get(pk=data["user_id"])
        user.set_password(validated_data["password"])
        user.save()

        return {"message": "Password has been reset successfully."}


# ---------------------------------------------------------------------------
# User Profile / Me
# ---------------------------------------------------------------------------

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "industry", "size"]


class UserMeSerializer(serializers.Serializer):
    """Read-only serializer for the current user's profile + onboarding state."""

    def to_representation(self, user):
        from apps.settings.models import TIER_MODULE_MAP, Module, ModuleActivationSettings

        profile, _ = UserProfile.objects.get_or_create(user=user)
        request = self.context.get("request")

        profile_photo_url = None
        if profile.profile_photo:
            if request:
                profile_photo_url = request.build_absolute_uri(profile.profile_photo.url)
            else:
                profile_photo_url = profile.profile_photo.url

        full_name = user.get_full_name() or user.username
        display_name = profile.preferred_display_name or full_name

        def enabled_modules_for_org(org):
            activation, _ = ModuleActivationSettings.objects.get_or_create(
                organization=org,
                defaults={
                    "enabled_modules": list(TIER_MODULE_MAP.get(org.subscription_tier, set())),
                },
            )
            # During trial: unlock all modules so user can discover the full platform
            sub = getattr(org, "subscription", None)
            if sub and sub.status == "trialing":
                return sorted(m.value for m in Module)
            return sorted(activation.get_enabled_modules())

        def addon_modules_for_org(org):
            """Modules not included in the org's tier — shown with add-on badges."""
            from apps.settings.models import ADDON_ONLY_MODULES

            tier_modules = TIER_MODULE_MAP.get(org.subscription_tier, set())
            all_modules = {m.value for m in Module}
            return sorted((all_modules - tier_modules - {Module.SETTINGS}) | ADDON_ONLY_MODULES)

        # Subscription summary (used by frontend for trial prompt logic)
        def subscription_summary(org):
            if not org:
                return None
            try:
                sub = org.subscription  # OneToOneField reverse
                return {
                    "status": sub.status,
                    "edition_key": sub.edition.key,
                    "edition_name": sub.edition.name,
                    "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
                }
            except OrganizationSubscription.DoesNotExist:
                return None

        def _is_bootstrap_org(org):
            """A bootstrap org has never been configured by the user."""
            return org.name.startswith("Workspace-")

        # Superusers bypass all onboarding and org requirements
        if user.is_superuser:
            org_data = None
            if profile.organization:
                org_data = {
                    "id": profile.organization.id,
                    "name": profile.organization.name,
                    "industry": profile.organization.industry,
                    "size": profile.organization.size,
                    "role": "admin",
                    "assigned_role": None,
                    "permissions": ["*"],
                    "enabled_modules": sorted([m.value for m in Module]),
                    "addon_modules": [],
                    "is_setup_complete": True,
                }
            return {
                "id": user.pk,
                "email": user.email,
                "full_name": full_name,
                "display_name": display_name,
                "profile_photo_url": profile_photo_url,
                "is_superuser": True,
                "is_demo_account": False,
                "has_completed_tour": True,
                "has_completed_onboarding": True,
                "default_language": (profile.default_language or "").strip().lower() or None,
                "organization": org_data,
                "subscription": subscription_summary(profile.organization),
            }

        org_data = None
        if profile.organization:
            from apps.settings.permissions import get_user_permissions

            assigned_role_data = None
            if profile.assigned_role:
                assigned_role_data = {
                    "id": profile.assigned_role.id,
                    "name": profile.assigned_role.name,
                    "slug": profile.assigned_role.slug,
                }

            org_data = {
                "id": profile.organization.id,
                "name": profile.organization.name,
                "industry": profile.organization.industry,
                "size": profile.organization.size,
                "role": profile.role,
                "assigned_role": assigned_role_data,
                "permissions": get_user_permissions(user),
                "enabled_modules": enabled_modules_for_org(profile.organization),
                "addon_modules": addon_modules_for_org(profile.organization),
                "is_setup_complete": not _is_bootstrap_org(profile.organization),
            }
        return {
            "id": user.pk,
            "email": user.email,
            "full_name": full_name,
            "display_name": display_name,
            "profile_photo_url": profile_photo_url,
            "is_superuser": False,
            "is_demo_account": profile.is_demo_account,
            "has_completed_tour": profile.has_completed_tour,
            "has_completed_onboarding": profile.has_completed_onboarding,
            "default_language": (profile.default_language or "").strip().lower() or None,
            "organization": org_data,
            "subscription": subscription_summary(profile.organization),
        }


class UserProfileSettingsSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False)
    preferred_display_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    job_title = serializers.CharField(max_length=100, required=False, allow_blank=True)
    department_id = serializers.IntegerField(required=False, allow_null=True)
    business_unit = serializers.CharField(max_length=150, required=False, allow_blank=True)
    employee_id = serializers.CharField(max_length=64, required=False, allow_blank=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    secondary_phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    office_location = serializers.CharField(max_length=150, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True)
    profile_visibility = serializers.ChoiceField(
        choices=UserProfile.ProfileVisibility.choices,
        required=False,
    )
    approval_signature = serializers.CharField(required=False, allow_blank=True)
    default_language = serializers.CharField(max_length=16, required=False, allow_blank=True)

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Full name cannot be empty.")
        return value

    def validate_email(self, value):
        value = value.lower().strip()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and User.objects.exclude(pk=user.pk).filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_department_id(self, value):
        if value is None:
            return value
        request = self.context.get("request")
        profile = getattr(getattr(request, "user", None), "profile", None)
        org = profile.organization if profile else None
        if not org:
            raise serializers.ValidationError(
                "Department cannot be assigned because your account has no organization."
            )
        if not Department.objects.filter(id=value, division__organization=org).exists():
            raise serializers.ValidationError(
                "Selected department does not exist in your organization."
            )
        return value

    def validate_timezone(self, value):
        value = value.strip()
        if value and value not in available_timezones():
            raise serializers.ValidationError(
                "Use a valid IANA timezone (for example, Africa/Lagos or America/New_York)."
            )
        return value

    def to_representation(self, user):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        request = self.context.get("request")

        profile_photo_url = None
        if profile.profile_photo:
            if request:
                profile_photo_url = request.build_absolute_uri(profile.profile_photo.url)
            else:
                profile_photo_url = profile.profile_photo.url

        full_name = user.get_full_name() or user.username
        organization_name = profile.organization.name if profile.organization else ""

        department_options = []
        if profile.organization:
            departments = (
                Department.objects.filter(division__organization=profile.organization, is_active=True)
                .select_related("division")
                .order_by("division__name", "name")
            )
            department_options = [
                {
                    "id": dep.id,
                    "name": dep.name,
                    "division_name": dep.division.name if dep.division else "",
                }
                for dep in departments
            ]

        timezone_value = profile.timezone or settings.TIME_ZONE
        timezone_options = list(ALL_TIMEZONE_OPTIONS)
        if timezone_value and timezone_value not in timezone_options:
            timezone_options.insert(0, timezone_value)

        default_language = (profile.default_language or settings.LANGUAGE_CODE or "").strip().lower()
        language_options = [dict(option) for option in DEFAULT_LANGUAGE_OPTIONS]
        if default_language and all(option["value"] != default_language for option in language_options):
            language_options.insert(
                0,
                {
                    "value": default_language,
                    "label": default_language,
                },
            )

        return {
            "id": user.pk,
            "profile_photo_url": profile_photo_url,
            "full_name": full_name,
            "display_name": profile.preferred_display_name or full_name,
            "preferred_display_name": profile.preferred_display_name,
            "job_title": profile.job_title,
            "department_id": profile.department_id,
            "department_name": profile.department.name if profile.department else "",
            "department_options": department_options,
            "organization_name": organization_name,
            "business_unit": profile.business_unit,
            "employee_id": profile.employee_id,
            "bio": profile.bio,
            "email": user.email,
            "phone": profile.phone,
            "secondary_phone": profile.secondary_phone,
            "office_location": profile.office_location,
            "timezone": timezone_value,
            "timezone_options": timezone_options,
            "profile_visibility": profile.profile_visibility,
            "profile_visibility_options": [
                {
                    "value": value,
                    "label": label,
                }
                for value, label in UserProfile.ProfileVisibility.choices
            ],
            "approval_signature": profile.approval_signature,
            "default_language": default_language,
            "language_options": language_options,
        }

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)

        user_fields = []
        if "full_name" in validated_data:
            full_name = validated_data["full_name"]
            name_parts = full_name.split(None, 1)
            first_name = name_parts[0] if name_parts else ""
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            if user.first_name != first_name:
                user.first_name = first_name
                user_fields.append("first_name")
            if user.last_name != last_name:
                user.last_name = last_name
                user_fields.append("last_name")

        if "email" in validated_data:
            new_email = validated_data["email"]
            previous_email = user.email
            if user.email != new_email:
                user.email = new_email
                user_fields.append("email")
            # Keep username aligned only when it still mirrors the previous email.
            if user.username == previous_email and user.username != new_email:
                user.username = new_email
                user_fields.append("username")

        if user_fields:
            user.save(update_fields=user_fields)

        profile_fields = []
        mutable_profile_fields = [
            "preferred_display_name",
            "job_title",
            "business_unit",
            "employee_id",
            "bio",
            "phone",
            "secondary_phone",
            "office_location",
            "timezone",
            "profile_visibility",
            "approval_signature",
            "default_language",
        ]

        for field in mutable_profile_fields:
            if field in validated_data:
                value = validated_data[field]
                if getattr(profile, field) != value:
                    setattr(profile, field, value)
                    profile_fields.append(field)

        if "department_id" in validated_data and profile.department_id != validated_data["department_id"]:
            profile.department_id = validated_data["department_id"]
            profile_fields.append("department_id")

        if profile_fields:
            profile.save(update_fields=profile_fields)

        return user


class AccountSecurityUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    mfa_enabled = serializers.BooleanField(required=False)
    passkey_enabled = serializers.BooleanField(required=False)

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Username cannot be empty.")
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and User.objects.exclude(pk=user.pk).filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)

        user_fields = []
        if "username" in validated_data and user.username != validated_data["username"]:
            user.username = validated_data["username"]
            user_fields.append("username")
        if user_fields:
            user.save(update_fields=user_fields)

        profile_fields = []
        for field in ["mfa_enabled", "passkey_enabled"]:
            if field in validated_data and getattr(profile, field) != validated_data[field]:
                setattr(profile, field, validated_data[field])
                profile_fields.append(field)
        if profile_fields:
            profile.save(update_fields=profile_fields)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=10)
    confirm_password = serializers.CharField(write_only=True, min_length=10)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Password confirmation does not match."}
            )

        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from current password."}
            )

        validate_password(attrs["new_password"], user)
        return attrs

    def create(self, validated_data):
        from .audit import audit_emit
        from .models import UserSecurityEvent
        from .security import record_password_change

        request = self.context["request"]
        user = request.user
        user.set_password(validated_data["new_password"])
        user.save(update_fields=["password"])
        record_password_change(user, new_password=validated_data["new_password"])
        audit_emit(
            event_type=UserSecurityEvent.EventType.PASSWORD_CHANGED,
            request=request,
            status=UserSecurityEvent.Status.SUCCESS,
            severity=UserSecurityEvent.Severity.LOW,
            target_type="user",
            target_id=str(user.id),
        )
        return {"detail": "Password changed successfully."}


NOTIFICATION_CHANNEL_KEYS = [key for key, _label in USER_NOTIFICATION_CHANNELS]
NOTIFICATION_FREQUENCY_KEYS = [key for key, _label in USER_NOTIFICATION_FREQUENCIES]
NOTIFICATION_CATEGORY_KEYS = [key for key, _label in USER_NOTIFICATION_CATEGORIES]


class NotificationPreferenceCategoryUpdateSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=NOTIFICATION_CATEGORY_KEYS)
    enabled = serializers.BooleanField(required=False)
    channels = serializers.ListField(
        child=serializers.ChoiceField(choices=NOTIFICATION_CHANNEL_KEYS),
        required=False,
        allow_empty=True,
    )
    frequency = serializers.ChoiceField(
        choices=NOTIFICATION_FREQUENCY_KEYS,
        required=False,
    )

    def validate_channels(self, value):
        deduped = []
        for channel in value:
            if channel not in deduped:
                deduped.append(channel)
        return deduped


class NotificationPreferencesUpdateSerializer(serializers.Serializer):
    channel_in_app_enabled = serializers.BooleanField(required=False)
    channel_email_enabled = serializers.BooleanField(required=False)
    channel_push_enabled = serializers.BooleanField(required=False)
    channel_sms_enabled = serializers.BooleanField(required=False)
    categories = NotificationPreferenceCategoryUpdateSerializer(many=True, required=False)

    def validate_categories(self, value):
        seen_keys = set()
        for row in value:
            key = row["key"]
            if key in seen_keys:
                raise serializers.ValidationError(
                    f"Duplicate category '{key}' is not allowed."
                )
            seen_keys.add(key)
        return value


WORKSPACE_WIDGET_KEYS = list(WORKSPACE_DASHBOARD_WIDGET_KEYS)


class WorkspaceWidgetPreferenceUpdateSerializer(serializers.Serializer):
    key = serializers.ChoiceField(choices=WORKSPACE_WIDGET_KEYS)
    visible = serializers.BooleanField(required=False)


class WorkspacePreferencesUpdateSerializer(serializers.Serializer):
    theme = serializers.ChoiceField(choices=UserProfile.WorkspaceTheme.choices, required=False)
    layout_density = serializers.ChoiceField(
        choices=UserProfile.WorkspaceDensity.choices,
        required=False,
    )
    sidebar_behavior = serializers.ChoiceField(
        choices=UserProfile.WorkspaceSidebarBehavior.choices,
        required=False,
    )
    default_landing_page = serializers.ChoiceField(
        choices=UserProfile.WorkspaceLandingPage.choices,
        required=False,
    )
    default_dashboard = serializers.ChoiceField(
        choices=UserProfile.WorkspaceDashboard.choices,
        required=False,
    )
    widgets = WorkspaceWidgetPreferenceUpdateSerializer(many=True, required=False)

    def validate_widgets(self, value):
        seen_keys = set()
        for row in value:
            key = row["key"]
            if key in seen_keys:
                raise serializers.ValidationError(
                    f"Duplicate widget key '{key}' is not allowed."
                )
            seen_keys.add(key)
        return value

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)

        fields = []
        scalar_field_map = {
            "theme": "workspace_theme",
            "layout_density": "workspace_layout_density",
            "sidebar_behavior": "workspace_sidebar_behavior",
            "default_landing_page": "workspace_default_landing_page",
            "default_dashboard": "workspace_default_dashboard",
        }

        for request_field, model_field in scalar_field_map.items():
            if request_field in validated_data and getattr(profile, model_field) != validated_data[request_field]:
                setattr(profile, model_field, validated_data[request_field])
                fields.append(model_field)

        if "widgets" in validated_data:
            current_visibility = profile.workspace_dashboard_widget_visibility
            if not isinstance(current_visibility, dict):
                current_visibility = {}
            normalized_visibility = {
                key: bool(current_visibility.get(key, True))
                for key in WORKSPACE_WIDGET_KEYS
            }

            ordered_keys = []
            seen = set()
            for row in validated_data["widgets"]:
                key = row["key"]
                if key in seen:
                    continue
                seen.add(key)
                ordered_keys.append(key)
                if "visible" in row:
                    normalized_visibility[key] = row["visible"]

            for key in WORKSPACE_WIDGET_KEYS:
                if key not in seen:
                    ordered_keys.append(key)

            if profile.workspace_dashboard_widget_order != ordered_keys:
                profile.workspace_dashboard_widget_order = ordered_keys
                fields.append("workspace_dashboard_widget_order")
            if profile.workspace_dashboard_widget_visibility != normalized_visibility:
                profile.workspace_dashboard_widget_visibility = normalized_visibility
                fields.append("workspace_dashboard_widget_visibility")

        if fields:
            profile.save(update_fields=fields)

        return user


class TaskWorkflowPreferencesUpdateSerializer(serializers.Serializer):
    default_task_view = serializers.ChoiceField(
        choices=UserProfile.TaskDefaultView.choices,
        required=False,
    )
    task_reminder_minutes_before = serializers.IntegerField(
        min_value=0,
        max_value=10080,
        required=False,
    )
    task_default_due_date_offset_days = serializers.IntegerField(
        min_value=0,
        max_value=60,
        required=False,
    )
    auto_follow_assigned_tasks = serializers.BooleanField(required=False)
    auto_subscribe_project_updates = serializers.BooleanField(required=False)
    approval_delegation_rule = serializers.ChoiceField(
        choices=UserProfile.ApprovalDelegationRule.choices,
        required=False,
    )

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        fields = []
        field_map = {
            "default_task_view": "task_default_view",
            "task_reminder_minutes_before": "task_reminder_minutes_before",
            "task_default_due_date_offset_days": "task_default_due_date_offset_days",
            "auto_follow_assigned_tasks": "task_auto_follow_assigned_tasks",
            "auto_subscribe_project_updates": "task_auto_subscribe_project_updates",
            "approval_delegation_rule": "task_approval_delegation_rule",
        }
        for request_field, model_field in field_map.items():
            if request_field in validated_data and getattr(profile, model_field) != validated_data[request_field]:
                setattr(profile, model_field, validated_data[request_field])
                fields.append(model_field)
        if fields:
            profile.save(update_fields=fields)
        return user


class CalendarSchedulingPreferencesUpdateSerializer(serializers.Serializer):
    working_hours_start = serializers.TimeField(required=False)
    working_hours_end = serializers.TimeField(required=False)
    working_days = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=7),
        required=False,
        allow_empty=False,
    )
    default_meeting_duration_minutes = serializers.IntegerField(
        min_value=5,
        max_value=480,
        required=False,
    )
    meeting_buffer_minutes = serializers.IntegerField(
        min_value=0,
        max_value=180,
        required=False,
    )
    timezone_override = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
    )
    calendar_sync_google = serializers.BooleanField(required=False)
    calendar_sync_outlook = serializers.BooleanField(required=False)
    calendar_sync_ical = serializers.BooleanField(required=False)
    default_reminder_minutes = serializers.IntegerField(
        min_value=0,
        max_value=1440 * 7,  # up to 1 week
        required=False,
    )

    def validate_working_days(self, value):
        deduped = []
        for day in value:
            if day not in deduped:
                deduped.append(day)
        return deduped

    def validate_timezone_override(self, value):
        value = value.strip()
        if value and value not in available_timezones():
            raise serializers.ValidationError(
                "Use a valid IANA timezone (for example, Africa/Lagos or America/New_York)."
            )
        return value

    def validate(self, attrs):
        user = getattr(self, "instance", None)
        profile = None
        if user is not None:
            profile, _ = UserProfile.objects.get_or_create(user=user)

        start = attrs.get(
            "working_hours_start",
            profile.calendar_working_hours_start if profile else None,
        )
        end = attrs.get(
            "working_hours_end",
            profile.calendar_working_hours_end if profile else None,
        )
        if start is not None and end is not None and end <= start:
            raise serializers.ValidationError(
                {"working_hours_end": "Working hours end must be later than working hours start."}
            )

        return attrs

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        fields = []
        field_map = {
            "working_hours_start": "calendar_working_hours_start",
            "working_hours_end": "calendar_working_hours_end",
            "working_days": "calendar_working_days",
            "default_meeting_duration_minutes": "calendar_default_meeting_duration_minutes",
            "meeting_buffer_minutes": "calendar_meeting_buffer_minutes",
            "timezone_override": "calendar_timezone_override",
            "calendar_sync_google": "calendar_sync_google_enabled",
            "calendar_sync_outlook": "calendar_sync_outlook_enabled",
            "calendar_sync_ical": "calendar_sync_ical_enabled",
            "default_reminder_minutes": "calendar_default_reminder_minutes",
        }
        for request_field, model_field in field_map.items():
            if request_field in validated_data and getattr(profile, model_field) != validated_data[request_field]:
                setattr(profile, model_field, validated_data[request_field])
                fields.append(model_field)
        if fields:
            profile.save(update_fields=fields)
        return user


class DataExportSavedViewSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_blank=True, max_length=64)
    name = serializers.CharField(max_length=120)
    filters = serializers.DictField(required=False)
    column_visibility = serializers.DictField(
        child=serializers.BooleanField(),
        required=False,
    )
    rows_per_page = serializers.IntegerField(min_value=5, max_value=500, required=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Saved view name cannot be empty.")
        return value


class DataExportPreferencesUpdateSerializer(serializers.Serializer):
    default_export_format = serializers.ChoiceField(
        choices=UserProfile.DataExportFormat.choices,
        required=False,
    )
    default_report_filters = serializers.DictField(required=False)
    rows_per_page = serializers.IntegerField(min_value=5, max_value=500, required=False)
    column_visibility = serializers.DictField(
        child=serializers.BooleanField(),
        required=False,
    )
    saved_views = DataExportSavedViewSerializer(many=True, required=False)

    def validate_default_report_filters(self, value):
        normalized = {}
        for key, raw_value in value.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            normalized[normalized_key] = raw_value
        return normalized

    def validate_saved_views(self, value):
        seen_names = set()
        normalized = []
        for row in value:
            normalized_row = dict(row)
            name = str(normalized_row.get("name", "")).strip()
            if not name:
                continue
            lookup = name.lower()
            if lookup in seen_names:
                raise serializers.ValidationError(f"Duplicate saved view name '{name}' is not allowed.")
            seen_names.add(lookup)
            normalized_row["name"] = name
            normalized.append(normalized_row)
        return normalized

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        fields = []
        field_map = {
            "default_export_format": "data_default_export_format",
            "default_report_filters": "data_default_report_filters",
            "rows_per_page": "data_rows_per_page",
            "column_visibility": "data_column_visibility",
            "saved_views": "data_saved_views",
        }
        for request_field, model_field in field_map.items():
            if request_field in validated_data and getattr(profile, model_field) != validated_data[request_field]:
                setattr(profile, model_field, validated_data[request_field])
                fields.append(model_field)
        if fields:
            profile.save(update_fields=fields)
        return user


class AccessibilityPreferencesUpdateSerializer(serializers.Serializer):
    font_size = serializers.ChoiceField(
        choices=UserProfile.AccessibilityFontSize.choices,
        required=False,
    )
    high_contrast_mode = serializers.BooleanField(required=False)
    reduced_motion = serializers.BooleanField(required=False)
    screen_reader_support = serializers.BooleanField(required=False)
    keyboard_navigation = serializers.BooleanField(required=False)

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        fields = []
        field_map = {
            "font_size": "accessibility_font_size",
            "high_contrast_mode": "accessibility_high_contrast_mode",
            "reduced_motion": "accessibility_reduced_motion",
            "screen_reader_support": "accessibility_screen_reader_support",
            "keyboard_navigation": "accessibility_keyboard_navigation",
        }
        for request_field, model_field in field_map.items():
            if request_field in validated_data and getattr(profile, model_field) != validated_data[request_field]:
                setattr(profile, model_field, validated_data[request_field])
                fields.append(model_field)
        if fields:
            profile.save(update_fields=fields)
        return user


class UserIntegrationActionSerializer(serializers.Serializer):
    ACTION_CONNECT = "connect"
    ACTION_REVOKE = "revoke"
    ACTION_REFRESH_TOKEN = "refresh_token"

    ACTION_CHOICES = (
        (ACTION_CONNECT, "Connect"),
        (ACTION_REVOKE, "Revoke"),
        (ACTION_REFRESH_TOKEN, "Refresh token"),
    )

    provider = serializers.ChoiceField(choices=UserIntegrationConnection.Provider.choices)
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    account_label = serializers.CharField(max_length=200, required=False, allow_blank=True)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    token_expires_in_minutes = serializers.IntegerField(min_value=5, max_value=525600, required=False)

    def validate_account_label(self, value):
        return value.strip()

    def validate_webhook_url(self, value):
        return value.strip()

    def validate(self, attrs):
        action = attrs.get("action")
        provider = attrs.get("provider")
        webhook_url = attrs.get("webhook_url", "")

        if (
            action == self.ACTION_CONNECT
            and provider == UserIntegrationConnection.Provider.WEBHOOKS
            and not webhook_url
        ):
            raise serializers.ValidationError(
                {"webhook_url": "Webhook URL is required when connecting webhooks."}
            )

        if action == self.ACTION_REFRESH_TOKEN and provider == UserIntegrationConnection.Provider.WEBHOOKS:
            raise serializers.ValidationError(
                {"provider": "Webhooks integration does not support token refresh."}
            )

        return attrs


class PrivacyVisibilityUpdateSerializer(serializers.Serializer):
    profile_visibility = serializers.ChoiceField(
        choices=UserProfile.ProfileVisibility.choices,
        required=False,
    )
    email_visibility = serializers.ChoiceField(
        choices=UserProfile.ProfileVisibility.choices,
        required=False,
    )
    phone_visibility = serializers.ChoiceField(
        choices=UserProfile.ProfileVisibility.choices,
        required=False,
    )
    activity_visibility = serializers.ChoiceField(
        choices=UserProfile.ProfileVisibility.choices,
        required=False,
    )
    online_status_visibility = serializers.ChoiceField(
        choices=UserProfile.ProfileVisibility.choices,
        required=False,
    )
    search_discoverable = serializers.BooleanField(required=False)

    def update(self, user, validated_data):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        fields = []
        for field in [
            "profile_visibility",
            "email_visibility",
            "phone_visibility",
            "activity_visibility",
            "online_status_visibility",
            "search_discoverable",
        ]:
            if field in validated_data and getattr(profile, field) != validated_data[field]:
                setattr(profile, field, validated_data[field])
                fields.append(field)
        if fields:
            profile.save(update_fields=fields)
        return user


# ---------------------------------------------------------------------------
# Onboarding: Tour
# ---------------------------------------------------------------------------

class CompleteTourSerializer(serializers.Serializer):
    def create(self, validated_data):
        user = self.context["request"].user
        profile = user.profile
        profile.has_completed_tour = True
        profile.save()
        return {"message": "Tour completed."}


# ---------------------------------------------------------------------------
# Onboarding: Company Setup
# ---------------------------------------------------------------------------

class CompanySetupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True)
    size = serializers.ChoiceField(
        choices=["1-10", "11-50", "51-200", "201-500", "500+"],
        required=False,
    )

    def validate_name(self, value):
        user = self.context["request"].user
        current_org = getattr(getattr(user, "profile", None), "organization", None)
        normalized = normalize_org_name(value)
        qs = Organization.objects.exclude(name__startswith="Workspace-")
        if current_org:
            qs = qs.exclude(pk=current_org.pk)
        if qs.filter(normalized_name=normalized).exists():
            raise serializers.ValidationError(
                "This company already exists on developerOS. "
                "Please contact your company administrator to receive an invitation to join."
            )
        if qs.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "This company already exists on developerOS. "
                "Please contact your company administrator to receive an invitation to join."
            )
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        profile = user.profile
        existing_org = getattr(profile, "organization", None)

        if _is_bootstrap_org_for_user(existing_org, user):
            org = existing_org
            org.name = validated_data["name"]
            org.industry = validated_data.get("industry", "")
            org.size = validated_data.get("size", "")
            if org.created_by_id is None:
                org.created_by = user
            domain = extract_email_domain(user.email)
            if domain:
                org.email_domain = domain
            org.save(update_fields=["name", "industry", "size", "created_by", "email_domain"])
        else:
            domain = extract_email_domain(user.email)
            org = Organization.objects.create(
                name=validated_data["name"],
                industry=validated_data.get("industry", ""),
                size=validated_data.get("size", ""),
                created_by=user,
                email_domain=domain,
            )

        profile.organization = org
        profile.role = "admin"
        profile.save()

        return {
            "id": org.id,
            "name": org.name,
            "message": "Company created successfully.",
        }


# ---------------------------------------------------------------------------
# Onboarding: Check Company Name
# ---------------------------------------------------------------------------

class CheckCompanySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField(required=False, allow_blank=True, default="")

    def create(self, validated_data):
        name = validated_data["name"]
        email = validated_data.get("email", "")
        normalized = normalize_org_name(name)

        # 1. Exact normalized match → hard block
        exact_match = (
            Organization.objects
            .filter(normalized_name=normalized)
            .exclude(name__startswith="Workspace-")
            .first()
        )
        if not exact_match:
            exact_match = (
                Organization.objects
                .filter(name__iexact=name)
                .exclude(name__startswith="Workspace-")
                .first()
            )

        if exact_match:
            return {
                "exists": True,
                "match_type": "exact",
                "message": "This company already exists. Contact your company admin to get invited.",
                "suggestions": [],
                "domain_matches": [],
            }

        # 2. Fuzzy similar matches → soft warning
        suggestions = []
        try:
            similar = find_similar_organizations(name, threshold=0.4, limit=5)
            suggestions = [{"id": o.id, "name": o.name} for o in similar]
        except Exception:
            logger.debug("Fuzzy org match failed for name=%s", name, exc_info=True)

        # 3. Email domain matches
        domain_matches = []
        if email:
            domain = extract_email_domain(email)
            if domain:
                orgs = (
                    Organization.objects
                    .filter(email_domain=domain)
                    .exclude(name__startswith="Workspace-")
                    [:5]
                )
                domain_matches = [{"id": o.id, "name": o.name} for o in orgs]

        if suggestions or domain_matches:
            return {
                "exists": False,
                "match_type": "similar",
                "message": "Similar companies found. Is yours one of these?",
                "suggestions": suggestions,
                "domain_matches": domain_matches,
            }

        return {
            "exists": False,
            "match_type": "none",
            "message": "Company name is available.",
            "suggestions": [],
            "domain_matches": [],
        }


# ---------------------------------------------------------------------------
# Onboarding: Invite Staff
# ---------------------------------------------------------------------------

class InviteStaffSerializer(serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=20,
    )
    role_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    department_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    job_title = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_emails(self, value):
        return [e.lower() for e in value]

    def validate(self, attrs):
        user = self.context["request"].user
        profile = getattr(user, "profile", None)
        org = profile.organization if profile else None

        # Only admins (org creators) can invite staff
        if not profile or profile.role != "admin":
            raise serializers.ValidationError(
                {"detail": "Only organization administrators can invite staff."}
            )

        role_id = attrs.get("role_id")
        if role_id is not None and org and not Role.objects.filter(
            id=role_id, organization=org
        ).exists():
            raise serializers.ValidationError(
                {"role_id": "Selected role does not exist in your organization."}
            )

        department_id = attrs.get("department_id")
        if department_id is not None and org and not Department.objects.filter(
            id=department_id, division__organization=org
        ).exists():
            raise serializers.ValidationError(
                {
                    "department_id": (
                        "Selected department does not exist in your organization."
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        from apps.settings.quotas import check_seat_quota

        user = self.context["request"].user
        profile = user.profile
        org = profile.organization

        if not org:
            raise serializers.ValidationError(
                {"detail": "You must set up a company before inviting staff."}
            )

        invited = []
        for email in validated_data["emails"]:
            # Skip if already a user or already invited
            if User.objects.filter(email=email).exists():
                continue
            if Invitation.objects.filter(email=email, organization=org, status="pending").exists():
                continue

            check_seat_quota(org)

            inv = Invitation.objects.create(
                email=email,
                organization=org,
                invited_by=user,
                role_id=validated_data.get("role_id"),
                department_id=validated_data.get("department_id"),
                job_title=validated_data.get("job_title", "").strip(),
            )
            send_invitation_email(email, org.name, user.get_full_name(), str(inv.token))
            invited.append(email)

        return {"invited": invited, "message": f"{len(invited)} invitation(s) sent."}


# ---------------------------------------------------------------------------
# Onboarding: Complete
# ---------------------------------------------------------------------------

class CompleteOnboardingSerializer(serializers.Serializer):
    def create(self, validated_data):
        user = self.context["request"].user
        profile = user.profile
        profile.has_completed_onboarding = True
        profile.save()
        return {"message": "Onboarding completed."}


# ---------------------------------------------------------------------------
# Invitation Validation (for signup page)
# ---------------------------------------------------------------------------

class ValidateInvitationSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        try:
            Invitation.objects.get(token=value, status="pending")
        except (Invitation.DoesNotExist, ValueError):
            raise serializers.ValidationError("This invitation is invalid or has expired.") from None
        return value

    def create(self, validated_data):
        inv = Invitation.objects.get(token=validated_data["token"])
        return {
            "email": inv.email,
            "organization_name": inv.organization.name,
            "first_name": inv.first_name,
            "last_name": inv.last_name,
            "role_id": inv.role_id,
            "department_id": inv.department_id,
            "job_title": inv.job_title,
        }


# ---------------------------------------------------------------------------
# Organization Subscription
# ---------------------------------------------------------------------------


class SubscriptionAddOnSerializer(serializers.ModelSerializer):
    class Meta:
        from apps.settings.models import SubscriptionAddOn

        model = SubscriptionAddOn
        fields = [
            "id", "key", "name", "add_on_type", "module_key",
            "storage_gb", "monthly_price", "description", "is_active",
        ]


class ActiveSubscriptionAddOnSerializer(serializers.ModelSerializer):
    add_on = SubscriptionAddOnSerializer(read_only=True)

    class Meta:
        model = ActiveSubscriptionAddOn
        fields = ["id", "add_on", "activated_at"]


class PurchaseAddOnSerializer(serializers.Serializer):
    add_on_key = serializers.CharField(max_length=50)


class OrganizationSubscriptionSerializer(serializers.ModelSerializer):
    edition_name = serializers.CharField(source="edition.name", read_only=True)
    edition_key = serializers.CharField(source="edition.key", read_only=True)
    effective_max_users = serializers.IntegerField(read_only=True)
    effective_max_storage_gb = serializers.IntegerField(read_only=True)
    active_add_ons = ActiveSubscriptionAddOnSerializer(many=True, read_only=True)

    class Meta:
        model = OrganizationSubscription
        fields = [
            "id", "organization", "edition", "edition_name", "edition_key",
            "status", "billing_cycle",
            "current_period_start", "current_period_end",
            "trial_start", "trial_end",
            "seats_purchased", "seats_used", "effective_max_users",
            "storage_used_gb", "effective_max_storage_gb",
            "cancelled_at", "cancel_reason",
            "payment_method_summary", "auto_renew",
            "active_add_ons",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "organization", "seats_used", "storage_used_gb",
            "created_at", "updated_at",
        ]


class SubscriptionEventSerializer(serializers.ModelSerializer):
    from_edition_name = serializers.CharField(
        source="from_edition.name", read_only=True, default=None,
    )
    to_edition_name = serializers.CharField(
        source="to_edition.name", read_only=True, default=None,
    )
    actor_email = serializers.EmailField(
        source="actor.email", read_only=True, default=None,
    )

    class Meta:
        model = SubscriptionEvent
        fields = [
            "id", "subscription", "event_type",
            "from_edition", "from_edition_name",
            "to_edition", "to_edition_name",
            "metadata", "actor", "actor_email", "occurred_at",
        ]
        read_only_fields = fields


class SimulatedPaymentSerializer(serializers.Serializer):
    """Validates mock card form data (no real gateway)."""

    card_number = serializers.CharField(min_length=13, max_length=19)
    expiry_month = serializers.IntegerField(min_value=1, max_value=12)
    expiry_year = serializers.IntegerField(min_value=2024, max_value=2040)
    cvc = serializers.CharField(min_length=3, max_length=4)
    cardholder_name = serializers.CharField(max_length=200)

    def validate_card_number(self, value):
        digits = value.replace(" ", "").replace("-", "")
        if not digits.isdigit():
            raise serializers.ValidationError("Card number must contain only digits.")
        if len(digits) < 13 or len(digits) > 19:
            raise serializers.ValidationError("Invalid card number length.")
        return digits

    def validate_cvc(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("CVC must contain only digits.")
        return value


class SubscriptionCheckoutSerializer(serializers.Serializer):
    """Checkout payload for upgrade, downgrade, renew, or first purchase."""

    edition_key = serializers.CharField(max_length=30)
    billing_cycle = serializers.ChoiceField(choices=["monthly", "annual"])
    payment = SimulatedPaymentSerializer()

    def validate_edition_key(self, value):
        from apps.settings.models import PlatformEdition

        if not PlatformEdition.objects.filter(
            key=value, is_active=True, is_custom=False
        ).exists():
            raise serializers.ValidationError(
                f"Edition '{value}' is not available."
            )
        return value


class SubscriptionCancelSerializer(serializers.Serializer):
    """Cancellation payload with optional reason."""

    reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    cancel_immediately = serializers.BooleanField(default=False)


class PaymentMethodUpdateSerializer(serializers.Serializer):
    """Update payment method with new card details."""

    payment = SimulatedPaymentSerializer()


class DemoRequestSerializer(serializers.Serializer):
    """Public serializer for demo request form submissions."""

    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    company_name = serializers.CharField(max_length=200)
    company_size = serializers.CharField(max_length=50, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)

    # Read-only response fields
    id = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        from .models import DemoRequest

        return DemoRequest.objects.create(**validated_data)

import logging
import secrets
import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers

from .emails import send_otp_email
from .models import OAuthConnection, UserAuthSession, UserSecurityEvent
from .oauth import (
    AUTHORIZE_URL_BUILDERS,
    CODE_EXCHANGERS,
    OAuthProviderConfigurationError,
    generate_oauth_state,
    validate_oauth_state,
)
from .security import issue_tokens_for_user, log_user_security_event
from .serializers import OTP_CACHE_PREFIX, OTP_TTL, _mfa_required_for_user

User = get_user_model()
logger = logging.getLogger(__name__)


class OAuthAuthorizeSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["google", "microsoft"])

    def create(self, validated_data):
        provider = validated_data["provider"]
        state_data = generate_oauth_state(provider)
        url_builder = AUTHORIZE_URL_BUILDERS.get(provider)
        if url_builder is None:
            raise serializers.ValidationError({"detail": "Unsupported OAuth provider."})
        try:
            redirect_url = url_builder(
                state=state_data["state"],
                code_verifier=state_data["code_verifier"],
            )
        except OAuthProviderConfigurationError as exc:
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        return {"redirect_url": redirect_url}


class OAuthCallbackSerializer(serializers.Serializer):
    code = serializers.CharField()
    state = serializers.CharField()

    def validate_state(self, value):
        state_data = validate_oauth_state(value)
        if state_data is None:
            raise serializers.ValidationError(
                "Invalid or expired OAuth state. Please try again."
            )
        self._state_data = state_data
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        provider = self._state_data["provider"]
        code_verifier = self._state_data["code_verifier"]
        code = validated_data["code"]

        exchanger = CODE_EXCHANGERS.get(provider)
        if exchanger is None:
            raise serializers.ValidationError({"detail": "Unsupported OAuth provider."})
        try:
            provider_info = exchanger(code, code_verifier)
        except OAuthProviderConfigurationError as exc:
            logger.warning("OAuth provider not configured provider=%s", provider)
            raise serializers.ValidationError({"detail": str(exc)}) from exc
        except Exception:
            logger.exception("OAuth code exchange failed for provider=%s", provider)
            log_user_security_event(
                principal="oauth-callback",
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=provider,
                request=request,
                detail="OAuth code exchange failed.",
            )
            raise serializers.ValidationError(
                {"detail": "Authentication with the provider failed. Please try again."}
            ) from None

        email = provider_info["email"]
        if not email:
            log_user_security_event(
                principal="oauth-no-email",
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=provider,
                request=request,
                detail="OAuth provider did not return an email.",
            )
            raise serializers.ValidationError(
                {"detail": "No email returned from the provider. Please use an account with a verified email."}
            )

        if not provider_info.get("email_verified", False):
            log_user_security_event(
                principal=email,
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=provider,
                request=request,
                detail="OAuth email is not verified.",
            )
            raise serializers.ValidationError(
                {"detail": "Your email is not verified with the provider. Please verify it first."}
            )

        # 1. Check for existing OAuthConnection
        connection_created = False
        try:
            connection = OAuthConnection.objects.select_related("user").get(
                provider=provider,
                provider_user_id=provider_info["sub"],
            )
            user = connection.user
            connection.last_login_at = timezone.now()
            connection.access_token_hash = provider_info.get("access_token_hash", "")
            connection.save(update_fields=["last_login_at", "access_token_hash"])
        except OAuthConnection.DoesNotExist:
            # 2. Try to match by email
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                # 3. Create new user
                name = provider_info.get("name", "")
                parts = name.split(None, 1) if name else ["User"]
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True,
                )

            OAuthConnection.objects.create(
                user=user,
                provider=provider,
                provider_user_id=provider_info["sub"],
                email=email,
                display_name=provider_info.get("name", ""),
                access_token_hash=provider_info.get("access_token_hash", ""),
                last_login_at=timezone.now(),
            )
            connection_created = True

        # Activate if needed (provider verified their email)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])

        # Enforce IAM user_status
        profile = getattr(user, "profile", None)
        if profile and profile.user_status in ("suspended", "locked"):
            log_user_security_event(
                user=user,
                principal=email,
                event_type=UserSecurityEvent.EventType.LOGIN_FAILED,
                status=UserSecurityEvent.Status.FAILED,
                provider=provider,
                request=request,
                detail=f"Blocked by user status: {profile.user_status}.",
            )
            raise serializers.ValidationError(
                {"detail": "Your account has been suspended. Contact your administrator."}
            )

        # Enforce org MFA policy
        if _mfa_required_for_user(user):
            otp = f"{secrets.randbelow(1_000_000):06d}"
            session_id = str(uuid.uuid4())
            cache.set(
                f"{OTP_CACHE_PREFIX}{session_id}",
                {
                    "user_id": user.pk,
                    "otp": otp,
                    "attempts": 0,
                    "remember_me": False,
                    "provider": provider,
                },
                timeout=OTP_TTL,
            )
            from threading import Thread
            Thread(target=lambda: send_otp_email(user, otp), daemon=True).start()
            log_user_security_event(
                user=user,
                principal=user.email,
                event_type=UserSecurityEvent.EventType.OTP_CHALLENGE,
                status=UserSecurityEvent.Status.INFO,
                provider=provider,
                request=request,
                detail="OTP challenge created for OAuth login.",
            )
            return {"otp_session": session_id}

        # MFA not required — mint JWT tokens directly
        provider_map = {
            "google": UserAuthSession.AuthProvider.GOOGLE,
            "microsoft": UserAuthSession.AuthProvider.MICROSOFT,
        }
        auth_provider = provider_map.get(provider, UserAuthSession.AuthProvider.PASSWORD)
        tokens = issue_tokens_for_user(
            user=user,
            request=request,
            remember_me=False,
            provider=auth_provider,
        )
        log_user_security_event(
            user=user,
            principal=user.email,
            event_type=UserSecurityEvent.EventType.LOGIN_SUCCESS,
            status=UserSecurityEvent.Status.SUCCESS,
            provider=provider,
            request=request,
            detail="OAuth authentication successful.",
            metadata={"session_id": tokens["session_id"]},
        )
        if connection_created:
            log_user_security_event(
                user=user,
                principal=user.email,
                event_type=UserSecurityEvent.EventType.PROVIDER_LINKED,
                status=UserSecurityEvent.Status.INFO,
                provider=provider,
                request=request,
                detail=f"{provider.title()} provider linked to account.",
            )
        return tokens

"""
Serializers for MFA endpoints: TOTP setup, recovery codes, passkey, status.
"""

import base64

from rest_framework import serializers
from webauthn import generate_authentication_options, generate_registration_options, verify_registration_response
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .mfa import (
    confirm_totp,
    generate_recovery_codes,
    get_available_mfa_methods,
    get_webauthn_origin,
    get_webauthn_rp_id,
    get_webauthn_rp_name,
    remaining_recovery_codes,
    setup_totp,
    user_has_totp,
)
from .models import TOTPDevice, WebAuthnCredential

# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------


class TOTPSetupSerializer(serializers.Serializer):
    """Initiate TOTP setup — returns secret + QR code."""

    def create(self, validated_data):
        user = self.context["request"].user
        # Don't allow re-setup if already confirmed (must disable first)
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            raise serializers.ValidationError(
                {"detail": "TOTP is already configured. Disable it first to reconfigure."}
            )
        secret, uri, qr_base64 = setup_totp(user)
        return {
            "secret": secret,
            "uri": uri,
            "qr_code": qr_base64,
        }


class TOTPConfirmSerializer(serializers.Serializer):
    """Confirm TOTP setup with first verification code."""

    code = serializers.CharField(min_length=6, max_length=6)

    def create(self, validated_data):
        user = self.context["request"].user
        if confirm_totp(user, validated_data["code"]):
            codes = generate_recovery_codes(user)
            return {
                "detail": "TOTP authenticator activated.",
                "recovery_codes": codes,
                "recovery_code_count": len(codes),
            }
        raise serializers.ValidationError({"code": "Invalid verification code."})


class TOTPDisableSerializer(serializers.Serializer):
    """Disable TOTP — requires current password."""

    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value

    def create(self, validated_data):
        from .mfa import disable_totp

        user = self.context["request"].user
        disable_totp(user)
        return {"detail": "TOTP authenticator disabled."}


# ---------------------------------------------------------------------------
# Recovery Codes
# ---------------------------------------------------------------------------


class RecoveryCodesRegenerateSerializer(serializers.Serializer):
    """Regenerate recovery codes — requires current password."""

    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        codes = generate_recovery_codes(user)
        return {
            "recovery_codes": codes,
            "recovery_code_count": len(codes),
        }


# ---------------------------------------------------------------------------
# WebAuthn / Passkeys
# ---------------------------------------------------------------------------


class PasskeyRegisterOptionsSerializer(serializers.Serializer):
    """Generate WebAuthn registration options."""

    def create(self, validated_data):
        user = self.context["request"].user

        existing_creds = WebAuthnCredential.objects.filter(user=user)
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in existing_creds
        ]

        options = generate_registration_options(
            rp_id=get_webauthn_rp_id(),
            rp_name=get_webauthn_rp_name(),
            user_id=str(user.pk).encode(),
            user_name=user.email,
            user_display_name=user.get_full_name() or user.email,
            exclude_credentials=exclude_credentials,
            authenticator_selection=AuthenticatorSelectionCriteria(
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.PREFERRED,
            ),
        )

        # Store challenge in cache for verification
        from django.core.cache import cache

        challenge_key = f"webauthn_reg:{user.pk}"
        cache.set(challenge_key, base64.b64encode(options.challenge).decode(), timeout=300)

        from webauthn.helpers import options_to_json

        return {"options": options_to_json(options)}


class PasskeyRegisterVerifySerializer(serializers.Serializer):
    """Verify WebAuthn registration response."""

    credential = serializers.JSONField()
    name = serializers.CharField(max_length=100, default="Passkey")

    def create(self, validated_data):
        from django.core.cache import cache

        user = self.context["request"].user
        challenge_key = f"webauthn_reg:{user.pk}"
        stored_challenge = cache.get(challenge_key)
        if not stored_challenge:
            raise serializers.ValidationError(
                {"detail": "Registration session expired. Please try again."}
            )
        cache.delete(challenge_key)

        try:
            verification = verify_registration_response(
                credential=validated_data["credential"],
                expected_challenge=base64.b64decode(stored_challenge),
                expected_rp_id=get_webauthn_rp_id(),
                expected_origin=get_webauthn_origin(),
            )
        except Exception as e:
            raise serializers.ValidationError({"detail": f"Registration failed: {e}"}) from e

        WebAuthnCredential.objects.create(
            user=user,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            name=validated_data.get("name", "Passkey"),
            aaguid=str(verification.aaguid) if verification.aaguid else "",
        )

        # Mark passkey enabled on profile
        profile = getattr(user, "profile", None)
        if profile:
            profile.passkey_enabled = True
            profile.save(update_fields=["passkey_enabled"])

        # Generate recovery codes if this is the first MFA method
        result = {"detail": "Passkey registered successfully."}
        if not user_has_totp(user) and remaining_recovery_codes(user) == 0:
            codes = generate_recovery_codes(user)
            result["recovery_codes"] = codes
            result["recovery_code_count"] = len(codes)

        return result


class PasskeyAuthOptionsSerializer(serializers.Serializer):
    """Generate WebAuthn authentication options (used during login MFA step)."""

    otp_session = serializers.CharField()

    def create(self, validated_data):
        from django.core.cache import cache

        from .serializers import OTP_CACHE_PREFIX

        otp_session = validated_data["otp_session"]
        session_data = cache.get(f"{OTP_CACHE_PREFIX}{otp_session}")
        if not session_data:
            raise serializers.ValidationError(
                {"detail": "Session expired. Please log in again."}
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            user = User.objects.get(pk=session_data["user_id"])
        except User.DoesNotExist as err:
            raise serializers.ValidationError({"detail": "Invalid session."}) from err

        credentials = WebAuthnCredential.objects.filter(user=user)
        allow_credentials = [
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in credentials
        ]

        options = generate_authentication_options(
            rp_id=get_webauthn_rp_id(),
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )

        challenge_key = f"webauthn_auth:{otp_session}"
        cache.set(challenge_key, base64.b64encode(options.challenge).decode(), timeout=300)

        from webauthn.helpers import options_to_json

        return {"options": options_to_json(options)}


# ---------------------------------------------------------------------------
# MFA Status
# ---------------------------------------------------------------------------


class MFAStatusSerializer(serializers.Serializer):
    """Read-only MFA status for the current user."""

    def to_representation(self, instance):
        user = self.context["request"].user
        totp_device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        passkey_count = WebAuthnCredential.objects.filter(user=user).count()
        passkeys = [
            {
                "id": cred.pk,
                "name": cred.name,
                "created_at": cred.created_at.isoformat(),
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
            }
            for cred in WebAuthnCredential.objects.filter(user=user).order_by("-created_at")
        ]

        return {
            "mfa_enabled": getattr(getattr(user, "profile", None), "mfa_enabled", False),
            "totp_configured": totp_device is not None,
            "totp_last_used": totp_device.last_used_at.isoformat() if totp_device and totp_device.last_used_at else None,
            "passkey_count": passkey_count,
            "passkeys": passkeys,
            "recovery_codes_remaining": remaining_recovery_codes(user),
            "available_methods": get_available_mfa_methods(user),
        }

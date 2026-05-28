"""
Views for MFA management: TOTP, recovery codes, passkeys, status.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .mfa import remaining_recovery_codes
from .mfa_serializers import (
    MFAStatusSerializer,
    PasskeyAuthOptionsSerializer,
    PasskeyRegisterOptionsSerializer,
    PasskeyRegisterVerifySerializer,
    RecoveryCodesRegenerateSerializer,
    TOTPConfirmSerializer,
    TOTPDisableSerializer,
    TOTPSetupSerializer,
)
from .models import WebAuthnCredential
from .throttles import MFAManagementThrottle, OTPRateThrottle

# ---------------------------------------------------------------------------
# TOTP
# ---------------------------------------------------------------------------


class TOTPSetupView(generics.CreateAPIView):
    """POST — initiate TOTP setup, returns secret + QR code."""

    serializer_class = TOTPSetupSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAManagementThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class TOTPConfirmView(generics.CreateAPIView):
    """POST — confirm TOTP setup with first code. Returns recovery codes."""

    serializer_class = TOTPConfirmSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAManagementThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class TOTPDisableView(generics.CreateAPIView):
    """POST — disable TOTP (requires password)."""

    serializer_class = TOTPDisableSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAManagementThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Recovery Codes
# ---------------------------------------------------------------------------


class RecoveryCodesCountView(APIView):
    """GET — returns count of remaining unused recovery codes."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "remaining": remaining_recovery_codes(request.user),
        })


class RecoveryCodesRegenerateView(generics.CreateAPIView):
    """POST — regenerate all recovery codes (requires password)."""

    serializer_class = RecoveryCodesRegenerateSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAManagementThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Passkeys / WebAuthn
# ---------------------------------------------------------------------------


class PasskeyRegisterOptionsView(generics.CreateAPIView):
    """POST — generate WebAuthn registration options."""

    serializer_class = PasskeyRegisterOptionsSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAManagementThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class PasskeyRegisterVerifyView(generics.CreateAPIView):
    """POST — verify WebAuthn registration response."""

    serializer_class = PasskeyRegisterVerifySerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAManagementThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_201_CREATED)


class PasskeyListDeleteView(APIView):
    """GET — list passkeys; DELETE — remove a passkey by ID."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        creds = WebAuthnCredential.objects.filter(user=request.user).order_by("-created_at")
        return Response([
            {
                "id": c.pk,
                "name": c.name,
                "created_at": c.created_at.isoformat(),
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            }
            for c in creds
        ])

    def delete(self, request):
        pk = request.query_params.get("id")
        if not pk:
            return Response({"detail": "Missing id parameter."}, status=400)
        deleted, _ = WebAuthnCredential.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return Response({"detail": "Passkey not found."}, status=404)
        # Update profile flag if no passkeys remain
        if not WebAuthnCredential.objects.filter(user=request.user).exists():
            profile = getattr(request.user, "profile", None)
            if profile:
                profile.passkey_enabled = False
                profile.save(update_fields=["passkey_enabled"])
        return Response({"detail": "Passkey removed."})


class PasskeyAuthOptionsView(generics.CreateAPIView):
    """POST — generate WebAuthn authentication options (during login MFA step)."""

    serializer_class = PasskeyAuthOptionsSerializer
    permission_classes = []  # unauthenticated (pre-login)
    throttle_classes = [OTPRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# MFA Status
# ---------------------------------------------------------------------------


class MFAStatusView(APIView):
    """GET — returns full MFA status for the current user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MFAStatusSerializer(instance=None, context={"request": request})
        return Response(serializer.data)

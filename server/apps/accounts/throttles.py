from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RealIPMixin:
    """
    Extract the real client IP from X-Forwarded-For when behind a reverse proxy
    (NPM Proxy Manager → Docker network).  Falls back to REMOTE_ADDR.
    """

    def get_ident(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            # First IP in the chain is the real client
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class AuthRateThrottle(RealIPMixin, AnonRateThrottle):
    """5 requests/minute for login and registration."""
    scope = "auth"


class OTPRateThrottle(RealIPMixin, AnonRateThrottle):
    """5 requests/minute for OTP verification."""
    scope = "otp"


class PasswordResetRateThrottle(RealIPMixin, AnonRateThrottle):
    """3 requests/minute for password reset requests."""
    scope = "password_reset"


class MFAManagementThrottle(RealIPMixin, UserRateThrottle):
    """10 requests/minute for authenticated MFA setup/management endpoints."""
    scope = "mfa_management"


class SensitiveActionThrottle(RealIPMixin, UserRateThrottle):
    """5 requests/minute for sensitive authenticated actions."""
    scope = "sensitive_action"

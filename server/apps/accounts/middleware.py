import os

from django.http import HttpResponseForbidden
from django.urls import reverse

from .rls import reset_rls_context, set_rls_context


class AdminProtectionMiddleware:
    """
    Protect admin interfaces: Django admin (/admin/) and console API (/api/iam/).

    - MFA required for staff accessing /admin/
    - IP whitelisting via ADMIN_ALLOWED_IPS for /admin/
    - IP whitelisting via CONSOLE_ALLOWED_IPS for /api/iam/
    """

    # Paths that require console-level IP whitelisting
    CONSOLE_API_PREFIXES = ("/api/iam/",)

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_allowed_ips = self._parse_ips("ADMIN_ALLOWED_IPS")
        self.console_allowed_ips = self._parse_ips("CONSOLE_ALLOWED_IPS")

    def __call__(self, request):
        path = request.path
        admin_prefix = reverse("admin:index")

        # --- Django admin protection ---
        if path.startswith(admin_prefix):
            if self.admin_allowed_ips:
                client_ip = self._get_client_ip(request)
                if client_ip not in self.admin_allowed_ips:
                    return HttpResponseForbidden("Access denied: IP not allowed.")

            user = getattr(request, "user", None)
            if user and user.is_authenticated and user.is_staff:
                profile = getattr(user, "profile", None)
                if profile and not profile.mfa_enabled:
                    return HttpResponseForbidden(
                        "Admin access requires MFA. "
                        "Please enable two-factor authentication on your account first."
                    )

        # --- Console API IP whitelist ---
        if self.console_allowed_ips and any(
            path.startswith(p) for p in self.CONSOLE_API_PREFIXES
        ):
            client_ip = self._get_client_ip(request)
            if client_ip not in self.console_allowed_ips:
                return HttpResponseForbidden("Access denied: IP not allowed.")

        return self.get_response(request)

    @staticmethod
    def _parse_ips(env_var):
        raw = os.environ.get(env_var, "").strip()
        return {ip.strip() for ip in raw.split(",") if ip.strip()} if raw else set()

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class OrganizationMiddleware:
    """
    Set ``request.organization`` from the authenticated user's profile.

    Must be placed **after** ``AuthenticationMiddleware`` so that
    ``request.user`` is available.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    # Paths where superusers should see cross-tenant data
    # Paths where RLS should be bypassed (platform console + auth)
    PLATFORM_SCOPED_PREFIXES = (
        "/api/iam/",
        "/api/telemetry/",
        "/api/analytics/health/",
        "/admin/",
    )

    # Auth paths always bypass RLS (user not yet resolved)
    AUTH_PREFIXES = (
        "/api/auth/",
        "/api/health/",
    )

    def __call__(self, request):
        request.organization = None
        organization_id = None
        bypass_rls = False

        # Auth endpoints always bypass RLS
        if any(request.path.startswith(p) for p in self.AUTH_PREFIXES):
            bypass_rls = True

        if hasattr(request, "user") and request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile:
                request.organization = profile.organization
                organization_id = profile.organization_id
            # Superusers bypass RLS on platform/console endpoints
            if request.user.is_superuser:
                if any(request.path.startswith(p) for p in self.PLATFORM_SCOPED_PREFIXES):
                    bypass_rls = True

        set_rls_context(organization_id, bypass=bypass_rls)
        try:
            return self.get_response(request)
        finally:
            # Reset to operational defaults for any reused DB connection.
            reset_rls_context(bypass=True)

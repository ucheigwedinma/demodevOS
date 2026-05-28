"""Access-policy enforcement middleware.

NOT auto-wired into MIDDLEWARE. To enable, add this to
``config/settings/base.py``::

    MIDDLEWARE = [
        ...,
        "apps.accounts.middleware.AdminProtectionMiddleware",
        "apps.accounts.middleware.OrganizationMiddleware",
        "apps.accounts.policy_middleware.AccessPolicyMiddleware",
    ]

Position it AFTER auth + org middleware so ``request.user`` and
``request.user.profile.organization`` are populated.

The middleware:
  * Skips unauthenticated requests
  * Skips a small, hard-coded allowlist of paths (auth endpoints,
    health checks) so a buggy policy can't lock anyone out of login
  * Calls policy_engine.evaluate_request once
  * Translates the Decision into HTTP semantics:
      - allow         → request proceeds untouched
      - warn          → proceeds + adds X-DeveloperOS-Policy-Warning header
      - deny          → 403 with structured JSON body
      - step_up_mfa   → 403 with code=mfa_required
"""

from __future__ import annotations

import logging

from django.http import JsonResponse

logger = logging.getLogger(__name__)


# Paths that must NEVER be policy-gated (otherwise a buggy deny could
# lock all users out of login + recovery).
SKIP_PATH_PREFIXES = (
    "/api/auth/",
    "/api/login",
    "/api/register",
    "/api/password",
    "/api/health",
    "/api/platform/health",
    "/admin/",
    "/static/",
    "/media/",
)


class AccessPolicyMiddleware:
    """Per-request enforcement of AccessPolicy rules. Opt-in."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._should_evaluate(request):
            return self.get_response(request)

        try:
            from .policy_engine import evaluate_request
            decision = evaluate_request(request)
        except Exception:
            # Fail-open at the middleware level too
            logger.exception("policy middleware: evaluate_request raised; falling through")
            return self.get_response(request)

        if decision.action == "deny":
            return JsonResponse({
                "detail": decision.message or "Access denied by organization policy.",
                "code": "access_policy_denied",
                "policy_id": decision.matched_policy_id,
                "policy_name": decision.matched_policy_name,
            }, status=403)

        if decision.action == "step_up_mfa":
            return JsonResponse({
                "detail": decision.message or "MFA verification required for this action.",
                "code": "mfa_required",
                "policy_id": decision.matched_policy_id,
                "policy_name": decision.matched_policy_name,
            }, status=403)

        response = self.get_response(request)

        if decision.action == "warn":
            # Non-blocking warning; frontend may surface as a banner
            response["X-DeveloperOS-Policy-Warning"] = decision.message or "Policy warning"
            response["X-DeveloperOS-Policy-Id"] = str(decision.matched_policy_id or "")

        return response

    def _should_evaluate(self, request) -> bool:
        if request.path.startswith(SKIP_PATH_PREFIXES):
            return False
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return True

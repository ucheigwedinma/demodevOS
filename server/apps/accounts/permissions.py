"""DRF permission classes for IAM-related auth surfaces.

Currently exports HasAppTokenScope — used to gate endpoints that
should only respond to ApplicationToken-authenticated requests with
specific scopes. Other token kinds (JWT, API key) bypass the check
since they're already gated by RBAC at the user level.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class HasAppTokenScope(BasePermission):
    """Require the active ApplicationToken to carry one of ``required_scopes``.

    Usage on a view:

        from apps.accounts.permissions import HasAppTokenScope

        class MyView(APIView):
            permission_classes = [HasAppTokenScope]
            required_scopes = ["read:invoices"]   # any one of these

    Behaviour:
      * Requests authenticated via JWT or API key bypass this check —
        the assumption is that user-level RBAC handles them. This
        permission only constrains ApplicationToken authentications.
      * If required_scopes is empty / missing, the token must be valid
        but no scope check is performed.
      * The token is considered to satisfy the scope if its
        ``scopes`` array contains the required scope OR is empty
        (empty = full org scope by convention).

    The view's ``required_scopes`` attribute is checked first; if
    absent, the permission falls back to the view's
    ``required_scope`` (singular) attribute as a convenience.
    """

    message = "Application token does not carry the required scope for this endpoint."

    def has_permission(self, request, view):
        from apps.accounts.models import ApplicationToken

        # Only constrain AppToken auth; let other auths through.
        if not isinstance(request.auth, ApplicationToken):
            return True

        token = request.auth
        token_scopes = token.scopes or []
        # Empty scopes on a token = full org scope by convention
        if not token_scopes:
            return True

        required = list(getattr(view, "required_scopes", []) or [])
        single = getattr(view, "required_scope", None)
        if single:
            required.append(single)
        if not required:
            return True

        # Caller satisfies the requirement if ANY of the required
        # scopes is present in the token's scopes.
        return any(scope in token_scopes for scope in required)

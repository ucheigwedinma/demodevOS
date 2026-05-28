"""
Platform-level permission checking for console endpoints.

Usage in views:

    from apps.accounts.platform_permissions import HasPlatformPermission

    class MyView(APIView):
        permission_classes = [IsAuthenticated, HasPlatformPermission]
        platform_permission = "iam.view_users"

    # Or for multiple permissions (any match):
    class MyView(APIView):
        permission_classes = [IsAuthenticated, HasPlatformPermission]
        platform_permissions = ["iam.view_users", "iam.edit_users"]

    # Or as a decorator:
    @require_platform_permission("operations.execute")
    def my_view(request):
        ...
"""

from functools import wraps

from django.http import JsonResponse
from rest_framework.permissions import BasePermission


def _get_user_platform_permissions(user):
    """Return the set of platform permission slugs for a user."""
    if not user or not user.is_authenticated:
        return set()

    # Superusers with no platform_role still get full access (backwards compat)
    profile = getattr(user, "profile", None)
    if not profile:
        return set() if not user.is_superuser else {"*"}

    platform_role = profile.platform_role
    if not platform_role:
        # No platform role assigned = no console access
        # Exception: superusers get full access
        return {"*"} if user.is_superuser else set()

    if platform_role.tier == "owner":
        return {"*"}  # Wildcard — owner bypasses all checks

    return platform_role.permission_slugs


def has_platform_permission(user, permission_slug):
    """Check if a user has a specific platform permission."""
    perms = _get_user_platform_permissions(user)
    return "*" in perms or permission_slug in perms


def has_any_platform_permission(user, permission_slugs):
    """Check if a user has ANY of the given platform permissions."""
    perms = _get_user_platform_permissions(user)
    if "*" in perms:
        return True
    return bool(perms & set(permission_slugs))


class HasPlatformPermission(BasePermission):
    """
    DRF permission class for platform/console endpoints.

    Set `platform_permission` (single) or `platform_permissions` (list)
    on the view class.
    """

    message = "You do not have the required platform permission."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Get required permission(s) from the view
        single = getattr(view, "platform_permission", None)
        multiple = getattr(view, "platform_permissions", None)

        if single:
            return has_platform_permission(request.user, single)
        if multiple:
            return has_any_platform_permission(request.user, multiple)

        # No permission specified = just check user has ANY platform role
        profile = getattr(request.user, "profile", None)
        if request.user.is_superuser:
            return True
        return profile and profile.platform_role_id is not None


def _authenticate_jwt(request):
    """Authenticate JWT for plain Django views (not DRF)."""
    from rest_framework_simplejwt.authentication import JWTAuthentication

    auth = JWTAuthentication()
    try:
        result = auth.authenticate(request)
        if result:
            request.user, request.auth = result
    except Exception:
        pass


def require_platform_permission(*permission_slugs):
    """
    Decorator for function-based views.

    @require_platform_permission("operations.execute")
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                _authenticate_jwt(request)
            if not request.user or not request.user.is_authenticated:
                return JsonResponse(
                    {"detail": "Authentication required."},
                    status=401,
                )
            if not has_any_platform_permission(request.user, permission_slugs):
                return JsonResponse(
                    {"detail": "You do not have the required platform permission."},
                    status=403,
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

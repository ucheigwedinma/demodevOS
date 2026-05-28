from django.core.cache import cache
from rest_framework.permissions import BasePermission

from .contextual_access import evaluate_contextual_access

PERMISSION_DECISION_CACHE_TTL_SECONDS = 60
USER_PERMISSION_LIST_CACHE_TTL_SECONDS = 60
MODULE_ACTIVATION_CACHE_TTL_SECONDS = 120


def _get_cache_version(version_key: str) -> int:
    cached = cache.get(version_key)
    if isinstance(cached, int) and cached > 0:
        return cached
    cache.set(version_key, 1, timeout=None)
    return 1


def _bump_cache_version(version_key: str) -> int:
    if cache.add(version_key, 2, timeout=None):
        return 2
    try:
        return cache.incr(version_key)
    except ValueError:
        cache.set(version_key, 2, timeout=None)
        return 2


def _role_permission_version_key(role_id: int) -> str:
    return f"rbac:role:{role_id}:permissions:version"


def _module_activation_version_key(org_id: int) -> str:
    return f"rbac:org:{org_id}:module-activation:version"


def bump_role_permission_cache_version(role_id: int | None) -> None:
    if role_id:
        _bump_cache_version(_role_permission_version_key(role_id))


def bump_org_module_activation_cache_version(org_id: int | None) -> None:
    if org_id:
        _bump_cache_version(_module_activation_version_key(org_id))


class HasRolePermission(BasePermission):
    """
    DRF permission class for RBAC enforcement.

    Usage on views::

        permission_classes = [IsAuthenticated, HasRolePermission]
        rbac_sub_module = "finance.bills"

    Org admins (profile.role == "admin") bypass all checks.
    Members need an assigned_role with matching RolePermission rows.
    """

    # Default mapping from DRF ViewSet actions to RBAC actions.
    DEFAULT_ACTION_MAP = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }

    message = "Permission denied."

    def has_permission(self, request, view):
        user = request.user
        if user.is_superuser:
            return True

        if not hasattr(user, "profile"):
            return False

        profile = user.profile

        # Console/admin operations require MFA
        if not profile.mfa_enabled:
            self.message = (
                "This action requires multi-factor authentication. "
                "Please enable MFA on your account first."
            )
            return False

        sub_module = getattr(view, "rbac_sub_module", None)
        required_action = getattr(view, "rbac_action", None)
        if required_action is None:
            action_map = getattr(view, "rbac_action_map", self.DEFAULT_ACTION_MAP)
            view_action = getattr(view, "action", None)
            required_action = action_map.get(view_action)

        if not sub_module or not required_action:
            return False

        module_key = sub_module.split(".", 1)[0]
        if not _is_module_enabled_for_profile(profile, module_key):
            return False

        decision = evaluate_contextual_access(
            user=user,
            request=request,
            module=module_key,
            sub_module=sub_module,
            action=required_action,
        )
        if not decision.allowed:
            return False

        # Org admins bypass role-level permission checks,
        # but still respect module activation.
        if profile.role == "admin":
            return True

        # No assigned role = no permissions (deny by default)
        if not profile.assigned_role_id:
            return False

        return _user_has_permission(
            profile.assigned_role_id, sub_module, required_action
        )

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


def _user_has_permission(role_id: int, sub_module: str, action: str) -> bool:
    """Check if a role has a specific permission."""
    from .models import RolePermission

    role_version = _get_cache_version(_role_permission_version_key(role_id))
    cache_key = f"rbac:decision:{role_id}:{role_version}:{sub_module}:{action}"
    cached = cache.get(cache_key)
    if isinstance(cached, bool):
        return cached

    allowed = RolePermission.objects.filter(
        role_id=role_id,
        permission__sub_module=sub_module,
        permission__action=action,
    ).exists() or RolePermission.objects.filter(
        role_id=role_id,
        permission__isnull=True,
        sub_module=sub_module,
        action=action,
    ).exists()
    cache.set(cache_key, allowed, timeout=PERMISSION_DECISION_CACHE_TTL_SECONDS)
    return allowed


def _is_module_enabled_for_profile(profile, module_key: str) -> bool:
    from .models import TIER_MODULE_MAP, Module, ModuleActivationSettings

    if module_key == Module.SETTINGS:
        return True

    org = getattr(profile, "organization", None)
    if not org:
        return False

    org_id = getattr(org, "id", None)
    if not org_id:
        return False

    # During trial: all modules are unlocked for discovery
    sub = getattr(org, "subscription", None)
    if sub and sub.status == "trialing":
        return True

    module_version = _get_cache_version(_module_activation_version_key(org_id))
    cache_key = (
        f"rbac:module-enabled:{org_id}:{org.subscription_tier}:{module_version}:{module_key}"
    )
    cached = cache.get(cache_key)
    if isinstance(cached, bool):
        return cached

    try:
        activation = ModuleActivationSettings.objects.get(organization=org)
        is_enabled = activation.is_module_enabled(module_key)
    except ModuleActivationSettings.DoesNotExist:
        allowed = set(TIER_MODULE_MAP.get(org.subscription_tier, set()))
        allowed.add(Module.SETTINGS)
        is_enabled = module_key in allowed

    cache.set(cache_key, is_enabled, timeout=MODULE_ACTIVATION_CACHE_TTL_SECONDS)
    return is_enabled


def get_user_permissions(user) -> list[str]:
    """
    Return all permission strings for a user's assigned role.
    Org admins get ["*"]. Members get ["sub_module.action", ...].
    """
    if not hasattr(user, "profile"):
        return []

    profile = user.profile

    if profile.role == "admin":
        return ["*"]

    if not profile.assigned_role_id:
        return []

    from .models import RolePermission

    role_version = _get_cache_version(
        _role_permission_version_key(profile.assigned_role_id)
    )
    org_id = getattr(profile, "organization_id", 0) or 0
    cache_key = (
        f"rbac:user-permissions:{user.id}:{org_id}:{profile.role}:"
        f"{profile.assigned_role_id}:{role_version}"
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    perms = RolePermission.objects.filter(role_id=profile.assigned_role_id).select_related(
        "permission"
    )

    permission_keys = [
        rp.permission.key if rp.permission_id else f"{rp.sub_module}.{rp.action}"
        for rp in perms
    ]
    cache.set(
        cache_key,
        permission_keys,
        timeout=USER_PERMISSION_LIST_CACHE_TTL_SECONDS,
    )
    return permission_keys

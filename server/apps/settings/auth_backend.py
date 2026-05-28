"""
Custom authentication backend that bridges the custom RBAC system
(Role / RolePermission) with Django's built-in permission framework
used by the admin site.

Install in settings.AUTHENTICATION_BACKENDS:
    "apps.settings.auth_backend.RbacBackend",

Permission format checked by this backend:
    "<app_label>.<action>_<model>"   (Django's default codename format)

The backend does NOT handle authentication — it only handles authorization
(has_perm / has_module_perms).  Authentication stays with ModelBackend.
"""

from django.contrib.auth.backends import BaseBackend


class RbacBackend(BaseBackend):
    """
    Map Django admin permission checks to the custom RBAC system.

    Django admin calls ``user.has_perm("app_label.codename")`` for every
    add/change/delete/view action.  This backend intercepts those checks
    and evaluates them against the user's assigned RBAC role.

    Superusers are handled by Django's ModelBackend (returns True for
    everything), so this backend only needs to handle non-superusers.
    """

    # Map Django admin permission prefixes to RBAC actions.
    _DJANGO_TO_RBAC_ACTION = {
        "view": "view",
        "add": "create",
        "change": "edit",
        "delete": "delete",
    }

    # Map Django app_label.model to RBAC sub_module.
    # Populated lazily on first use.
    _app_model_to_sub_module: dict[str, str] | None = None

    @classmethod
    def _build_mapping(cls):
        """Build the app_label.model → RBAC sub_module mapping."""
        from .rbac_defaults import PERMISSION_REGISTRY

        mapping: dict[str, str] = {}

        # Module-level mapping: app_label → list of sub_modules
        _MODULE_APP_MAP = {
            "properties": "properties",
            "projects": "projects",
            "finance": "finance",
            "procurement": "procurement",
            "documents": "documents",
            "analytics": "analytics",
            "crm": "crm",
            "compliance": "compliance",
            "hr": "hr",
            "accounts": "iam",
            "settings": "settings",
            "notifications": "settings",
            "workflows": "settings",
            "support_desk": "support_desk",
            "inventory": "procurement",
            "partners": "settings",
            "valuations": "properties",
        }

        for module_cfg in PERMISSION_REGISTRY:
            module_key = module_cfg["module"]
            for sm_cfg in module_cfg["sub_modules"]:
                sub_module = sm_cfg["key"]  # e.g. "finance.bills"
                # Store sub_module by its own key for direct lookup
                mapping[sub_module] = sub_module

        # Store the module-level fallback mapping too
        mapping["_app_map"] = _MODULE_APP_MAP  # type: ignore[assignment]
        cls._app_model_to_sub_module = mapping

    def _get_sub_module_for_model(self, app_label, model_name):
        """Resolve app_label + model_name to an RBAC sub_module string."""
        if self._app_model_to_sub_module is None:
            self._build_mapping()

        app_map = self._app_model_to_sub_module.get("_app_map", {})
        rbac_module = app_map.get(app_label, app_label)

        # Try direct sub_module matches (e.g. "finance.bills" for Bill model)
        from .rbac_defaults import PERMISSION_REGISTRY

        for module_cfg in PERMISSION_REGISTRY:
            if module_cfg["module"] != rbac_module:
                continue
            for sm_cfg in module_cfg["sub_modules"]:
                sub_module = sm_cfg["key"]
                # Match: sub_module's last part matches model name
                sm_suffix = sub_module.split(".")[-1]
                if sm_suffix == model_name or sm_suffix == f"{model_name}s":
                    return sub_module
            # Fallback: use the ".all" sub_module if it exists
            for sm_cfg in module_cfg["sub_modules"]:
                if sm_cfg["key"].endswith(".all"):
                    return sm_cfg["key"]
            # Last resort: first sub_module in the module
            if module_cfg["sub_modules"]:
                return module_cfg["sub_modules"][0]["key"]

        return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        Check a Django-style permission string against the RBAC system.
        Returns True/False, or None to defer to other backends.
        """
        if not user_obj.is_active:
            return False

        # Superusers are handled by ModelBackend
        if user_obj.is_superuser:
            return None

        profile = getattr(user_obj, "profile", None)
        if not profile:
            return False

        # Org admins bypass RBAC (same as HasRolePermission)
        if profile.role == "admin":
            return True

        if not profile.assigned_role_id:
            return False

        # Parse Django permission string: "app_label.action_modelname"
        if "." not in perm:
            return None

        app_label, codename = perm.split(".", 1)

        # Extract action prefix and model name
        rbac_action = None
        model_name = None
        for django_prefix, rbac_act in self._DJANGO_TO_RBAC_ACTION.items():
            if codename.startswith(f"{django_prefix}_"):
                rbac_action = rbac_act
                model_name = codename[len(django_prefix) + 1:]
                break

        if not rbac_action or not model_name:
            return None  # Defer to other backends

        sub_module = self._get_sub_module_for_model(app_label, model_name)
        if not sub_module:
            return None  # Unknown model, defer

        from .permissions import _user_has_permission

        return _user_has_permission(
            profile.assigned_role_id, sub_module, rbac_action
        )

    def has_module_perms(self, user_obj, app_label):
        """
        Return True if the user has any permission in the given app.
        Used by Django admin to show/hide app sections in the sidebar.
        """
        if not user_obj.is_active:
            return False

        if user_obj.is_superuser:
            return None

        profile = getattr(user_obj, "profile", None)
        if not profile:
            return False

        if profile.role == "admin":
            return True

        if not profile.assigned_role_id:
            return False

        # Check if the user's role has any permission in any sub_module
        # that maps to this app_label

        if self._app_model_to_sub_module is None:
            self._build_mapping()

        app_map = self._app_model_to_sub_module.get("_app_map", {})
        rbac_module = app_map.get(app_label)
        if not rbac_module:
            return None

        from .models import RolePermission

        return RolePermission.objects.filter(
            role_id=profile.assigned_role_id,
            module=rbac_module,
        ).exists()

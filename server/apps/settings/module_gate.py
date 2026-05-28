"""
Mixin for DRF views that checks whether the relevant module is activated
for the requesting user's organization before allowing access.

Usage:
    class BillViewSet(ModuleGateMixin, viewsets.ModelViewSet):
        required_module = "finance"
"""

from rest_framework.exceptions import PermissionDenied


class ModuleGateMixin:
    """
    Add to any ViewSet or APIView to enforce module activation.
    Set ``required_module`` to the Module enum value (e.g. ``"finance"``).
    Superusers bypass the check.
    """

    required_module: str = ""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if not self.required_module:
            return

        if request.user.is_superuser:
            return

        profile = getattr(request.user, "profile", None)
        org = getattr(profile, "organization", None) if profile else None
        if not org:
            return

        from .models import ModuleActivationSettings

        try:
            activation = ModuleActivationSettings.objects.get(organization=org)
            if not activation.is_module_enabled(self.required_module):
                raise PermissionDenied(
                    f"The '{self.required_module}' module is not enabled "
                    f"for your organization."
                )
        except ModuleActivationSettings.DoesNotExist:
            # No activation settings yet → all modules available (backward compat)
            pass

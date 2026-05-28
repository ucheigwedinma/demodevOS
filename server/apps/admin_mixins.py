"""
Shared admin mixins for org-scoped FK filtering and list-view scoping.

Usage:
    from apps.admin_mixins import OrgScopedAdminMixin

    class MyModelAdmin(OrgScopedAdminMixin, ModelAdmin):
        ...

    # For models without a direct ``organization`` FK:
    class DepartmentAdmin(OrgScopedAdminMixin, ModelAdmin):
        org_lookup = "division__organization"
"""

from django.core.exceptions import FieldDoesNotExist


class OrgScopedAdminMixin:
    """Scopes Django admin list views and FK dropdowns by organization.

    List views:
        Non-superusers only see records belonging to their organization.
        The lookup path defaults to ``organization`` and can be overridden
        per admin class via the ``org_lookup`` attribute.

    FK dropdowns:
        Detects the organization from:
        1. The object being edited (if it has an ``organization`` FK), or
        2. The requesting user's profile organization.
    """

    # Override per admin class for models that reach org indirectly.
    org_lookup = "organization"

    # Map of model label (app_label.modelname) → queryset filter for org scoping.
    # Subclasses can extend via `extra_org_fk_filters`.
    ORG_FK_FILTERS = {
        "settings.department": lambda org: {"division__organization": org},
        "settings.division": lambda org: {"organization": org},
        "settings.costcenter": lambda org: {"organization": org},
        "settings.profitcenter": lambda org: {"organization": org},
        "settings.role": lambda org: {"organization": org},
        "hr.employeerecord": lambda org: {"organization": org},
        "hr.team": lambda org: {"department__division__organization": org},
        "hr.positionrole": lambda org: {"organization": org},
        "hr.position": lambda org: {"department__division__organization": org},
        "hr.vacancy": lambda org: {"organization": org},
        "hr.payrollrun": lambda org: {"organization": org},
        "projects.project": lambda org: {"organization": org},
        "finance.account": lambda org: {"organization": org},
        "finance.budget": lambda org: {"organization": org},
        "inventory.warehouse": lambda org: {"organization": org},
        "inventory.inventoryitem": lambda org: {"organization": org},
        "procurement.vendor": lambda org: {"organization": org},
        "crm.lead": lambda org: {"organization": org},
        "accounts.organization": lambda org: {"pk": org.pk},
    }

    extra_org_fk_filters: dict = {}

    # ------------------------------------------------------------------
    # List-view scoping
    # ------------------------------------------------------------------

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        profile = getattr(request.user, "profile", None)
        org = profile.organization if profile else None
        if org is None:
            return qs.none()

        # Only filter if the model actually has the lookup field.
        first_field = self.org_lookup.split("__")[0]
        try:
            self.model._meta.get_field(first_field)
        except FieldDoesNotExist:
            return qs

        return qs.filter(**{self.org_lookup: org})

    # ------------------------------------------------------------------
    # FK dropdown scoping
    # ------------------------------------------------------------------

    def _get_org_for_request(self, request):
        """Determine the relevant organization for FK filtering.

        Priority:
        1. Organization from the object being edited (via URL object_id)
        2. Organization selected in the current form POST data
        3. The requesting user's profile organization
        """
        # Try to get org from the object being edited
        obj_org = self._get_org_from_edited_object(request)
        if obj_org is not None:
            return obj_org

        # On add-form POST (e.g. validation failure re-render), use the
        # organization the user selected in the form.
        if request.method == "POST":
            org_id = request.POST.get("organization")
            if org_id:
                from apps.accounts.models import Organization
                try:
                    return Organization.objects.get(pk=org_id)
                except (Organization.DoesNotExist, ValueError):
                    pass

        # Fall back to user's own org (works for both regular users and
        # superusers — gives superusers a sensible default on add forms).
        profile = getattr(request.user, "profile", None)
        return profile.organization if profile else None

    def _get_org_from_edited_object(self, request):
        """Extract organization from the object currently being edited."""
        resolver = getattr(request, "resolver_match", None)
        if resolver is None:
            return None
        object_id = resolver.kwargs.get("object_id")
        if not object_id:
            return None

        # Get the model being edited
        model = getattr(self, "model", None)
        if model is None:
            return None

        try:
            obj = model.objects.get(pk=object_id)
        except (model.DoesNotExist, ValueError):
            return None

        # Direct organization FK
        org = getattr(obj, "organization", None)
        if org is not None:
            return org

        # For UserProfile-like models: check organization via the model itself
        org_id = getattr(obj, "organization_id", None)
        if org_id is not None:
            return org

        # Try common traversals for models without direct org FK
        # e.g. Department → division.organization
        division = getattr(obj, "division", None)
        if division is not None:
            org = getattr(division, "organization", None)
            if org is not None:
                return org

        return None

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        org = self._get_org_for_request(request)
        if org is not None:
            related_model = db_field.related_model
            label = related_model._meta.label_lower
            all_filters = {**self.ORG_FK_FILTERS, **self.extra_org_fk_filters}
            if label in all_filters:
                filt = all_filters[label](org)
                kwargs["queryset"] = related_model.objects.filter(**filt)
            # For auth.User FKs, scope to users with profiles in this org
            elif label == "auth.user":
                from apps.accounts.models import UserProfile
                user_ids = UserProfile.objects.filter(
                    organization=org,
                ).values_list("user_id", flat=True)
                kwargs["queryset"] = related_model.objects.filter(pk__in=user_ids)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

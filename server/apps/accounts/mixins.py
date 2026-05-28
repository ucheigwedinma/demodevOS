from django.core.exceptions import ImproperlyConfigured


class OrgScopedMixin:
    """
    DRF view mixin that auto-filters querysets by the requesting user's
    organization and auto-assigns the organization on create.

    Usage::

        class PropertyViewSet(OrgScopedMixin, viewsets.ModelViewSet):
            queryset = Property.objects.all()
            serializer_class = PropertySerializer

    Superusers bypass the filter and see all organizations' data.
    """

    org_field = "organization"

    def _resolve_request_org(self):
        request = getattr(self, "request", None)
        if request is None:
            return None

        org = getattr(request, "organization", None)
        if org is not None:
            return org

        user = getattr(request, "user", None)
        profile = getattr(user, "profile", None)
        return getattr(profile, "organization", None)

    def _infer_queryset_from_serializer(self):
        serializer_class = getattr(self, "serializer_class", None)
        if serializer_class is None and hasattr(self, "get_serializer_class"):
            serializer_class = self.get_serializer_class()
        meta = getattr(serializer_class, "Meta", None)
        model = getattr(meta, "model", None)
        if model is None:
            return None
        return model._default_manager.all()

    def _base_queryset(self):
        queryset = getattr(self, "queryset", None)
        if queryset is not None:
            return queryset.all() if hasattr(queryset, "all") else queryset

        inferred = self._infer_queryset_from_serializer()
        if inferred is not None:
            return inferred

        raise ImproperlyConfigured(
            f"{self.__class__.__name__} must define `queryset` or use a serializer with `Meta.model`."
        )

    def get_queryset(self):
        qs = self._base_queryset()
        org = self._resolve_request_org()
        if org is None:
            return qs.none()
        return qs.filter(**{self.org_field: org})

    def perform_create(self, serializer):
        org = self._resolve_request_org()
        if org is None:
            raise ImproperlyConfigured(
                f"{self.__class__.__name__} could not resolve organization for create."
            )
        serializer.save(**{self.org_field: org})

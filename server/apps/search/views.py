from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import FloatField, Q, Value
from django.db.models.functions import Greatest
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# ── Declarative search configuration ───────────────────────────────────
# Each entry: (category_key, label, app_label.ModelName, search_fields,
#              title_template, subtitle_template, href_template, module_key,
#              select_related)
#
# title_template / subtitle_template: field name or tuple for f-string.
# href_template: python format string with {id}.

SEARCH_CATEGORIES = [
    {
        "key": "projects",
        "label": "Projects",
        "model": "projects.Project",
        "fields": ["name", "description", "location"],
        "title": "name",
        "subtitle": "status",
        "href": "/projects/{id}",
        "module": "projects",
        "select_related": [],
    },
    {
        "key": "employees",
        "label": "Employees",
        "model": "hr.EmployeeRecord",
        "fields": ["user__first_name", "user__last_name", "user__email"],
        "title": ("user__first_name", "user__last_name"),
        "subtitle": "employment_status",
        "href": "/hr/employees",
        "module": "hr",
        "select_related": ["user"],
    },
    {
        "key": "documents",
        "label": "Documents",
        "model": "documents.Document",
        "fields": ["title", "document_number", "project_code"],
        "title": "title",
        "subtitle": "document_number",
        "href": "/documents/repository",
        "module": "documents",
        "select_related": [],
    },
    {
        "key": "properties",
        "label": "Properties",
        "model": "properties.Property",
        "fields": ["name", "address", "description"],
        "title": "name",
        "subtitle": "property_type",
        "href": "/properties/{id}",
        "module": "properties",
        "select_related": [],
    },
    {
        "key": "units",
        "label": "Units",
        "model": "properties.Unit",
        "fields": ["unit_number", "property__name", "location_description"],
        "title": "unit_number",
        "subtitle_fk": ("property", "name"),
        "href": "/units/{id}",
        "module": "properties",
        "select_related": ["property"],
    },
    {
        "key": "leads",
        "label": "Leads",
        "model": "crm.Lead",
        "fields": ["first_name", "last_name", "email", "phone"],
        "title": ("first_name", "last_name"),
        "subtitle": "email",
        "href": "/crm/leads",
        "module": "crm",
        "select_related": [],
    },
    {
        "key": "invoices",
        "label": "Invoices",
        "model": "finance.Invoice",
        "fields": ["invoice_number", "customer__name"],
        "title": "invoice_number",
        "subtitle_fk": ("customer", "name"),
        "href": "/finance/invoices",
        "module": "finance",
        "select_related": ["customer"],
    },
    {
        "key": "bills",
        "label": "Bills",
        "model": "finance.Bill",
        "fields": ["bill_number", "vendor__name"],
        "title": "bill_number",
        "subtitle_fk": ("vendor", "name"),
        "href": "/finance/bills",
        "module": "finance",
        "select_related": ["vendor"],
    },
    {
        "key": "vendors",
        "label": "Vendors",
        "model": "procurement.Vendor",
        "fields": ["name"],
        "title": "name",
        "subtitle": "category",
        "href": "/procurement/vendors",
        "module": "procurement",
        "select_related": [],
    },
    {
        "key": "tickets",
        "label": "Support Tickets",
        "model": "support_desk.SupportTicket",
        "fields": ["ticket_id", "subject", "description"],
        "title": "subject",
        "subtitle": "ticket_id",
        "href": "/support-desk/tickets",
        "module": "support_desk",
        "select_related": [],
    },
]

LIMIT_PER_CATEGORY = 5
MIN_SIMILARITY = 0.3


def _get_model(model_path: str):
    """Lazily resolve 'app_label.ModelName' → Django model class."""
    from django.apps import apps

    app_label, model_name = model_path.split(".")
    return apps.get_model(app_label, model_name)


def _get_title(obj, config: dict) -> str:
    title_spec = config["title"]
    if isinstance(title_spec, tuple):
        parts = []
        for field in title_spec:
            val = obj
            for part in field.split("__"):
                val = getattr(val, part, "")
            parts.append(str(val or ""))
        return " ".join(parts).strip()
    val = obj
    for part in title_spec.split("__"):
        val = getattr(val, part, "")
    return str(val or "")


def _get_subtitle(obj, config: dict) -> str:
    if "subtitle_fk" in config:
        fk_name, attr = config["subtitle_fk"]
        related = getattr(obj, fk_name, None)
        return str(getattr(related, attr, "")) if related else ""
    field = config.get("subtitle", "")
    if not field:
        return ""
    return str(getattr(obj, field, "") or "")


def _get_href(obj, config: dict) -> str:
    return config["href"].format(id=obj.pk)


def _build_trigram_queryset(model, query, fields, org):
    """
    Build queryset annotated with trigram similarity across fields.
    Only considers fields that are direct (not FK traversals) for trigram.
    Falls back to icontains for FK fields.
    """
    direct_fields = [f for f in fields if "__" not in f]
    fk_fields = [f for f in fields if "__" in f]

    qs = model.objects.filter(organization=org)

    # Trigram similarity on direct fields
    if direct_fields:
        similarities = [
            TrigramWordSimilarity(Value(query), f) for f in direct_fields
        ]
        if len(similarities) == 1:
            qs = qs.annotate(similarity=similarities[0])
        else:
            qs = qs.annotate(similarity=Greatest(*similarities, output_field=FloatField()))
        qs = qs.filter(similarity__gte=MIN_SIMILARITY).order_by("-similarity")
    else:
        # No direct fields — annotate dummy similarity
        qs = qs.annotate(similarity=Value(0.0, output_field=FloatField()))

    # If FK fields exist, also include icontains matches
    if fk_fields:
        fk_q = Q()
        for f in fk_fields:
            fk_q |= Q(**{f"{f}__icontains": query})
        fk_qs = model.objects.filter(organization=org).filter(fk_q)
        fk_qs = fk_qs.annotate(similarity=Value(0.5, output_field=FloatField()))
        # Union, deduplicate by pk
        qs = qs | fk_qs
        qs = qs.order_by("-similarity")

    return qs


def _build_icontains_queryset(model, query, fields, org):
    """Fallback: simple icontains across all fields."""
    q_filter = Q()
    for f in fields:
        q_filter |= Q(**{f"{f}__icontains": query})
    return model.objects.filter(organization=org).filter(q_filter)


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response(
                {"query": query, "categories": []},
                status=status.HTTP_200_OK,
            )

        org = request.user.profile.organization

        # Module gating
        enabled_modules = set()
        is_superuser = request.user.is_superuser
        if not is_superuser:
            try:
                enabled_modules = org.module_activation_settings.get_enabled_modules()
            except Exception:
                enabled_modules = set()

        categories = []

        for config in SEARCH_CATEGORIES:
            module_key = config.get("module")
            if module_key and not is_superuser and module_key not in enabled_modules:
                continue

            model = _get_model(config["model"])
            fields = config["fields"]
            select = config.get("select_related", [])

            # Primary: trigram search
            qs = _build_trigram_queryset(model, query, fields, org)
            if select:
                qs = qs.select_related(*select)
            results = list(qs.distinct()[:LIMIT_PER_CATEGORY])

            # Fallback: supplement with icontains if we got fewer than LIMIT
            if len(results) < LIMIT_PER_CATEGORY:
                seen_pks = {r.pk for r in results}
                fallback_qs = _build_icontains_queryset(model, query, fields, org)
                if select:
                    fallback_qs = fallback_qs.select_related(*select)
                fallback_qs = fallback_qs.exclude(pk__in=seen_pks)
                remaining = LIMIT_PER_CATEGORY - len(results)
                results.extend(list(fallback_qs[:remaining]))

            if not results:
                continue

            # Count total matches for "View all"
            total_q = Q()
            for f in fields:
                total_q |= Q(**{f"{f}__icontains": query})
            total_count = model.objects.filter(organization=org).filter(total_q).count()

            category_data = {
                "key": config["key"],
                "label": config["label"],
                "total_count": total_count,
                "results": [
                    {
                        "id": obj.pk,
                        "title": _get_title(obj, config),
                        "subtitle": _get_subtitle(obj, config),
                        "href": _get_href(obj, config),
                    }
                    for obj in results
                ],
            }
            categories.append(category_data)

        return Response({"query": query, "categories": categories})

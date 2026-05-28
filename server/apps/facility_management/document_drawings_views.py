from __future__ import annotations

from collections import Counter

from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import parsers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.properties.models import Inspection, WorkOrder
from apps.settings.permissions import HasRolePermission

from .document_drawings_serializers import (
    FacilityDocumentDetailSerializer,
    FacilityDocumentListSerializer,
    FacilityDocumentWriteSerializer,
)
from .document_drawings_workflows import (
    ensure_facility_document_defaults,
    ensure_generated_maintenance_log_for_work_order,
    run_documents_drawings_automation,
)
from .models import Facility, FacilityDocument, FacilityUnitSpace


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


def _facility_for_property(property_obj):
    return getattr(property_obj, "facility_registry", None) if property_obj else None


class FacilityDocumentFilter(filters.FilterSet):
    review_due_after = filters.DateFilter(field_name="review_due_date", lookup_expr="gte")
    review_due_before = filters.DateFilter(field_name="review_due_date", lookup_expr="lte")
    expiry_after = filters.DateFilter(field_name="expiry_date", lookup_expr="gte")
    expiry_before = filters.DateFilter(field_name="expiry_date", lookup_expr="lte")

    class Meta:
        model = FacilityDocument
        fields = [
            "property",
            "facility",
            "facility_space",
            "asset_component",
            "linked_work_order",
            "linked_inspection",
            "document_type",
            "status",
            "source",
        ]


class FacilityDocumentsOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        now = timezone.now()
        documents = list(
            FacilityDocument.objects.filter(organization=org)
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "asset_component",
                "linked_work_order",
                "linked_inspection",
                "uploaded_by",
            )
            .order_by("document_type", "title", "-created_at")
        )

        type_counts = Counter(document.document_type for document in documents)
        review_due_documents = [
            document for document in documents if document.status == FacilityDocument.Status.REVIEW_DUE
        ]
        expired_documents = [
            document for document in documents if document.status == FacilityDocument.Status.EXPIRED
        ]
        generated_logs = [
            document
            for document in documents
            if document.document_type == FacilityDocument.DocumentType.MAINTENANCE_LOG
            and document.source == FacilityDocument.Source.GENERATED
        ]
        recent_blueprints = sorted(
            [
                document
                for document in documents
                if document.document_type in {
                    FacilityDocument.DocumentType.BLUEPRINT,
                    FacilityDocument.DocumentType.DRAWING,
                }
            ],
            key=lambda document: (document.updated_at, document.created_at, document.id),
            reverse=True,
        )
        certificates = [
            document
            for document in documents
            if document.document_type == FacilityDocument.DocumentType.COMPLIANCE_CERTIFICATE
        ]

        payload = {
            "generated_at": now.isoformat(),
            "kpis": {
                "total_documents": len(documents),
                "blueprints_drawings": type_counts[FacilityDocument.DocumentType.BLUEPRINT]
                + type_counts[FacilityDocument.DocumentType.DRAWING],
                "equipment_manuals": type_counts[FacilityDocument.DocumentType.EQUIPMENT_MANUAL],
                "maintenance_logs": type_counts[FacilityDocument.DocumentType.MAINTENANCE_LOG],
                "generated_maintenance_logs": len(generated_logs),
                "compliance_certificates": len(certificates),
                "review_due_documents": len(review_due_documents),
                "expired_documents": len(expired_documents),
            },
            "document_type_breakdown": [
                {"key": key, "count": count}
                for key, count in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            "review_watchlist": FacilityDocumentListSerializer(
                sorted(
                    [*expired_documents, *review_due_documents],
                    key=lambda document: (
                        document.status != FacilityDocument.Status.EXPIRED,
                        document.expiry_date or document.review_due_date or today,
                        document.id,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "maintenance_log_watchlist": FacilityDocumentListSerializer(
                sorted(
                    generated_logs,
                    key=lambda document: (
                        document.issued_date or today,
                        document.id,
                    ),
                    reverse=True,
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "blueprint_watchlist": FacilityDocumentListSerializer(
                recent_blueprints[:8],
                many=True,
                context={"request": request},
            ).data,
        }
        return Response(payload)


class FacilityDocumentsLookupsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        facilities = Facility.objects.filter(organization=org).select_related("property").order_by("facility_code")
        spaces = (
            FacilityUnitSpace.objects.filter(organization=org)
            .select_related("facility", "zone", "zone__floor", "unit", "unit__property")
            .order_by("facility__facility_code", "zone__floor__floor_number", "zone__name", "unit__unit_number")
        )
        assets = (
            org.org_asset_components.select_related("property", "facility", "facility_space")
            .order_by("component_id")
        )
        work_orders = (
            WorkOrder.objects.filter(organization=org, property__facility_registry__isnull=False)
            .select_related("property", "facility", "facility_space", "asset_component")
            .order_by("-created_at")
        )
        inspections = (
            Inspection.objects.filter(organization=org, property__facility_registry__isnull=False)
            .select_related("property", "unit")
            .order_by("-scheduled_date", "-id")
        )

        work_order_rows = []
        for work_order in work_orders[:400]:
            property_facility = _facility_for_property(work_order.property)
            resolved_facility = work_order.facility or property_facility
            work_order_rows.append(
                {
                    "id": work_order.id,
                    "title": work_order.title,
                    "status": work_order.status,
                    "facility": resolved_facility.id if resolved_facility else None,
                    "facility_code": resolved_facility.facility_code if resolved_facility else "",
                }
            )

        inspection_rows = []
        for inspection in inspections[:300]:
            resolved_facility = _facility_for_property(inspection.property)
            inspection_rows.append(
                {
                    "id": inspection.id,
                    "title": inspection.title,
                    "status": inspection.status,
                    "scheduled_date": inspection.scheduled_date.isoformat(),
                    "facility": resolved_facility.id if resolved_facility else None,
                    "facility_code": resolved_facility.facility_code if resolved_facility else "",
                }
            )

        asset_rows = []
        for asset in assets[:500]:
            resolved_facility = asset.facility or _facility_for_property(asset.property)
            asset_rows.append(
                {
                    "id": asset.id,
                    "component_id": asset.component_id,
                    "label": asset.name,
                    "facility": resolved_facility.id if resolved_facility else None,
                    "facility_code": resolved_facility.facility_code if resolved_facility else "",
                }
            )

        payload = {
            "facilities": [
                {
                    "id": facility.id,
                    "facility_code": facility.facility_code,
                    "property_name": facility.property.name,
                }
                for facility in facilities[:300]
            ],
            "spaces": [
                {
                    "id": space.id,
                    "facility": space.facility_id,
                    "facility_code": space.facility.facility_code,
                    "zone_code": space.zone.zone_code,
                    "unit_number": space.unit.unit_number,
                    "space_label": space.space_label,
                    "property_name": space.unit.property.name,
                }
                for space in spaces[:500]
            ],
            "assets": asset_rows,
            "work_orders": work_order_rows,
            "inspections": inspection_rows,
        }
        return Response(payload)


class FacilityDocumentsWorkflowView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "edit"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        result = run_documents_drawings_automation(org)
        return Response(result, status=status.HTTP_200_OK)


class FacilityDocumentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "create",
        "update": "edit",
        "partial_update": "edit",
        "destroy": "delete",
    }
    queryset = FacilityDocument.objects.all()
    filterset_class = FacilityDocumentFilter
    search_fields = [
        "title",
        "description",
        "reference_number",
        "version_label",
        "property__name",
        "facility__facility_code",
        "asset_component__name",
    ]
    ordering_fields = ["created_at", "updated_at", "document_type", "status", "review_due_date", "expiry_date"]
    ordering = ["document_type", "title", "-created_at"]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "asset_component",
                "linked_work_order",
                "linked_inspection",
                "uploaded_by",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityDocumentListSerializer
        if self.action == "retrieve":
            return FacilityDocumentDetailSerializer
        return FacilityDocumentWriteSerializer

    def perform_create(self, serializer):
        document = serializer.save(organization=self._resolve_request_org())
        ensure_facility_document_defaults(document, actor=self.request.user)
        if document.linked_work_order_id:
            ensure_generated_maintenance_log_for_work_order(document.linked_work_order)

    def perform_update(self, serializer):
        document = serializer.save()
        ensure_facility_document_defaults(document, actor=self.request.user)
        if document.linked_work_order_id:
            ensure_generated_maintenance_log_for_work_order(document.linked_work_order)

    def perform_destroy(self, instance):
        if instance.file:
            storage = instance.file.storage
            name = instance.file.name
            instance.delete()
            if name:
                storage.delete(name)
            return
        instance.delete()

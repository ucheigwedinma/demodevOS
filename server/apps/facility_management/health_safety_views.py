from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import parsers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.mixins import OrgScopedMixin
from apps.compliance.models import ComplianceRequirement, ComplianceViolation
from apps.properties.models import Inspection
from apps.settings.permissions import HasRolePermission

from .health_safety_serializers import (
    FacilityComplianceChecklistDetailSerializer,
    FacilityComplianceChecklistListSerializer,
    FacilityComplianceChecklistWriteSerializer,
    FacilityComplianceViolationListSerializer,
    FacilityHealthSafetyInspectionDetailSerializer,
    FacilityHealthSafetyInspectionListSerializer,
    FacilityHealthSafetyInspectionWriteSerializer,
    FacilityIncidentDetailSerializer,
    FacilityIncidentListSerializer,
    FacilityIncidentWriteSerializer,
    FacilityRegulatoryDocumentDetailSerializer,
    FacilityRegulatoryDocumentListSerializer,
    FacilityRegulatoryDocumentWriteSerializer,
    FacilitySafetyAuditLogSerializer,
)
from .health_safety_workflows import (
    ensure_checklist_defaults,
    ensure_corrective_work_order_for_incident,
    ensure_follow_up_inspection_for_checklist,
    ensure_follow_up_inspection_for_incident,
    ensure_health_safety_inspection_defaults,
    ensure_incident_defaults,
    ensure_regulatory_document_defaults,
    run_health_safety_compliance_automation,
    sync_incident_from_inspection,
    sync_incident_from_related_records,
    sync_property_compliance_for_checklist,
    sync_property_compliance_for_regulatory_document,
    sync_violation_for_checklist,
    sync_violation_for_inspection,
    sync_violation_for_regulatory_document,
)
from .models import (
    Facility,
    FacilityComplianceChecklist,
    FacilityIncident,
    FacilityRegulatoryDocument,
    FacilitySafetyAuditLog,
    FacilityUnitSpace,
)


def _resolve_user_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "organization", None)


class FacilityIncidentFilter(filters.FilterSet):
    occurred_after = filters.IsoDateTimeFilter(field_name="occurred_at", lookup_expr="gte")
    occurred_before = filters.IsoDateTimeFilter(field_name="occurred_at", lookup_expr="lte")

    class Meta:
        model = FacilityIncident
        fields = [
            "property",
            "facility",
            "facility_space",
            "category",
            "severity",
            "status",
            "requires_regulatory_report",
            "work_order",
        ]


class FacilityHealthSafetyInspectionFilter(filters.FilterSet):
    facility = filters.NumberFilter(field_name="property__facility_registry_id")
    facility_space = filters.NumberFilter(field_name="unit__facility_space_id")
    scheduled_after = filters.DateFilter(field_name="scheduled_date", lookup_expr="gte")
    scheduled_before = filters.DateFilter(field_name="scheduled_date", lookup_expr="lte")

    class Meta:
        model = Inspection
        fields = [
            "property",
            "facility",
            "facility_space",
            "inspection_type",
            "status",
            "rating",
            "risk_level",
            "compliance_status",
        ]


class FacilityComplianceChecklistFilter(filters.FilterSet):
    due_after = filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_before = filters.DateFilter(field_name="due_date", lookup_expr="lte")

    class Meta:
        model = FacilityComplianceChecklist
        fields = [
            "property",
            "facility",
            "facility_space",
            "linked_incident",
            "linked_inspection",
            "compliance_requirement",
            "checklist_type",
            "status",
        ]


class FacilityRegulatoryDocumentFilter(filters.FilterSet):
    expiry_after = filters.DateFilter(field_name="expiry_date", lookup_expr="gte")
    expiry_before = filters.DateFilter(field_name="expiry_date", lookup_expr="lte")
    review_due_after = filters.DateFilter(field_name="review_due_date", lookup_expr="gte")
    review_due_before = filters.DateFilter(field_name="review_due_date", lookup_expr="lte")

    class Meta:
        model = FacilityRegulatoryDocument
        fields = [
            "property",
            "facility",
            "compliance_requirement",
            "status",
        ]


class FacilitySafetyAuditLogFilter(filters.FilterSet):
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = FacilitySafetyAuditLog
        fields = [
            "property",
            "facility",
            "entity_type",
            "event_type",
            "entity_id",
        ]


class FacilityHealthSafetyOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        today = timezone.localdate()
        now = timezone.now()

        incidents = list(
            FacilityIncident.objects.filter(organization=org)
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "work_order",
                "follow_up_inspection",
            )
            .order_by("-occurred_at", "-id")
        )
        inspections = list(
            Inspection.objects.filter(organization=org, property__facility_registry__isnull=False)
            .select_related("property", "unit", "unit__facility_space", "unit__facility_space__facility")
            .order_by("scheduled_date", "id")
        )
        checklists = list(
            FacilityComplianceChecklist.objects.filter(organization=org)
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "linked_incident",
                "linked_inspection",
                "compliance_requirement",
            )
            .prefetch_related("items")
            .order_by("due_date", "id")
        )
        documents = list(
            FacilityRegulatoryDocument.objects.filter(organization=org)
            .select_related("property", "facility", "property_document", "uploaded_by", "compliance_requirement")
            .order_by("expiry_date", "-id")
        )
        open_violations = list(
            ComplianceViolation.objects.filter(
                organization=org,
                property__facility_registry__isnull=False,
            )
            .exclude(status__in=[ComplianceViolation.Status.RESOLVED, ComplianceViolation.Status.CLOSED])
            .select_related("property")
            .order_by("due_date", "-reported_date", "-id")
        )
        audit_logs = list(
            FacilitySafetyAuditLog.objects.filter(organization=org)
            .select_related("property", "facility", "actor")
            .order_by("-created_at", "-id")
        )

        open_incidents = [
            incident
            for incident in incidents
            if incident.status in {FacilityIncident.Status.OPEN, FacilityIncident.Status.INVESTIGATING}
        ]
        critical_incidents = [
            incident for incident in incidents if incident.severity == FacilityIncident.Severity.CRITICAL
        ]
        overdue_inspections = [
            inspection
            for inspection in inspections
            if inspection.status not in {Inspection.Status.COMPLETED, Inspection.Status.CANCELLED}
            and inspection.scheduled_date < today
        ]
        scheduled_inspections = [
            inspection
            for inspection in inspections
            if inspection.status in {Inspection.Status.SCHEDULED, Inspection.Status.IN_PROGRESS}
        ]
        open_checklists = [
            checklist
            for checklist in checklists
            if checklist.status not in {
                FacilityComplianceChecklist.Status.COMPLETED,
                FacilityComplianceChecklist.Status.CANCELLED,
            }
        ]
        overdue_checklists = [
            checklist
            for checklist in checklists
            if checklist.status == FacilityComplianceChecklist.Status.OVERDUE
            or (
                checklist.status not in {
                    FacilityComplianceChecklist.Status.COMPLETED,
                    FacilityComplianceChecklist.Status.CANCELLED,
                }
                and checklist.due_date < today
            )
        ]
        expiring_documents = [
            document for document in documents if document.status == FacilityRegulatoryDocument.Status.EXPIRING_SOON
        ]
        expired_documents = [
            document for document in documents if document.status == FacilityRegulatoryDocument.Status.EXPIRED
        ]
        recent_audit_events = [event for event in audit_logs if event.created_at >= now - timedelta(days=7)]

        payload = {
            "generated_at": now.isoformat(),
            "kpis": {
                "open_incidents": len(open_incidents),
                "critical_incidents": len(critical_incidents),
                "investigating_incidents": sum(
                    1 for incident in incidents if incident.status == FacilityIncident.Status.INVESTIGATING
                ),
                "scheduled_inspections": len(scheduled_inspections),
                "overdue_inspections": len(overdue_inspections),
                "open_checklists": len(open_checklists),
                "overdue_checklists": len(overdue_checklists),
                "total_regulatory_documents": len(documents),
                "expiring_documents": len(expiring_documents),
                "expired_documents": len(expired_documents),
                "open_violations": len(open_violations),
                "audit_events_7d": len(recent_audit_events),
            },
            "incident_watchlist": FacilityIncidentListSerializer(
                sorted(
                    open_incidents,
                    key=lambda incident: (
                        incident.severity != FacilityIncident.Severity.CRITICAL,
                        incident.status != FacilityIncident.Status.INVESTIGATING,
                        incident.occurred_at,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "inspection_watchlist": FacilityHealthSafetyInspectionListSerializer(
                sorted(
                    scheduled_inspections,
                    key=lambda inspection: (
                        inspection.status != Inspection.Status.IN_PROGRESS,
                        inspection.scheduled_date,
                        inspection.id,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "checklist_watchlist": FacilityComplianceChecklistListSerializer(
                sorted(
                    open_checklists,
                    key=lambda checklist: (
                        checklist.status != FacilityComplianceChecklist.Status.OVERDUE,
                        checklist.due_date,
                        checklist.id,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "document_watchlist": FacilityRegulatoryDocumentListSerializer(
                sorted(
                    [*expired_documents, *expiring_documents],
                    key=lambda document: (
                        document.status != FacilityRegulatoryDocument.Status.EXPIRED,
                        document.expiry_date or today,
                        document.id,
                    ),
                )[:8],
                many=True,
                context={"request": request},
            ).data,
            "violation_watchlist": FacilityComplianceViolationListSerializer(
                open_violations[:8],
                many=True,
                context={"request": request},
            ).data,
            "audit_log_watchlist": FacilitySafetyAuditLogSerializer(
                audit_logs[:8],
                many=True,
                context={"request": request},
            ).data,
        }
        return Response(payload)


class FacilityHealthSafetyLookupsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "view"

    def get(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        User = request.user.__class__
        users = User.objects.filter(profile__organization=org, is_active=True).select_related("profile").order_by(
            "first_name",
            "last_name",
            "email",
        )
        facilities = Facility.objects.filter(organization=org).select_related("property").order_by("facility_code")
        spaces = (
            FacilityUnitSpace.objects.filter(organization=org)
            .select_related("facility", "zone", "zone__floor", "unit", "unit__property")
            .order_by("facility__facility_code", "zone__floor__floor_number", "zone__name", "unit__unit_number")
        )
        requirements = ComplianceRequirement.objects.filter(organization=org, is_active=True).order_by(
            "category",
            "name",
        )
        incidents = (
            FacilityIncident.objects.filter(organization=org)
            .select_related("property", "facility", "facility_space", "facility_space__unit")
            .exclude(status=FacilityIncident.Status.CLOSED)
            .order_by("-occurred_at", "-id")
        )
        inspections = (
            Inspection.objects.filter(organization=org, property__facility_registry__isnull=False)
            .select_related("property", "unit", "unit__facility_space", "unit__facility_space__facility")
            .order_by("-scheduled_date", "-id")
        )

        payload = {
            "users": [
                {
                    "id": user.id,
                    "label": user.get_full_name().strip() or user.email or user.username,
                    "email": user.email or "",
                }
                for user in users[:200]
            ],
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
                    "zone_name": space.zone.name,
                    "unit_number": space.unit.unit_number,
                    "space_label": space.space_label,
                    "property_name": space.unit.property.name,
                }
                for space in spaces[:500]
            ],
            "compliance_requirements": [
                {
                    "id": requirement.id,
                    "name": requirement.name,
                    "category": requirement.category,
                    "category_display": requirement.get_category_display(),
                }
                for requirement in requirements[:300]
            ],
            "incidents": FacilityIncidentListSerializer(
                incidents[:200],
                many=True,
                context={"request": request},
            ).data,
            "inspections": FacilityHealthSafetyInspectionListSerializer(
                inspections[:200],
                many=True,
                context={"request": request},
            ).data,
        }
        return Response(payload)


class FacilityHealthSafetyWorkflowView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action = "edit"

    def post(self, request):
        org = _resolve_user_org(request)
        if org is None:
            return Response({"detail": "Organization context required."}, status=400)

        result = run_health_safety_compliance_automation(org, actor=request.user)
        return Response(result, status=status.HTTP_200_OK)


class FacilityIncidentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
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
    queryset = FacilityIncident.objects.all()
    filterset_class = FacilityIncidentFilter
    search_fields = ["incident_code", "title", "description", "reported_by", "assigned_to"]
    ordering_fields = ["occurred_at", "created_at", "severity", "status"]
    ordering = ["-occurred_at", "-id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "work_order",
                "follow_up_inspection",
            )
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityIncidentListSerializer
        if self.action == "retrieve":
            return FacilityIncidentDetailSerializer
        return FacilityIncidentWriteSerializer

    def perform_create(self, serializer):
        incident = serializer.save(organization=self._resolve_request_org())
        ensure_incident_defaults(incident, actor=self.request.user)
        ensure_follow_up_inspection_for_incident(incident, actor=self.request.user)
        ensure_corrective_work_order_for_incident(incident, actor=self.request.user)
        sync_incident_from_related_records(incident, actor=self.request.user)
        incident.refresh_from_db()
        FacilitySafetyAuditLog.objects.create(
            organization=incident.organization,
            property=incident.property,
            facility=incident.facility,
            entity_type=FacilitySafetyAuditLog.EntityType.INCIDENT,
            event_type=FacilitySafetyAuditLog.EventType.INCIDENT_REPORTED,
            entity_id=incident.id,
            actor=self.request.user,
            summary=f"Reported incident {incident.incident_code or incident.id}.",
            details={"incident_id": incident.id, "severity": incident.severity, "category": incident.category},
        )

    def perform_update(self, serializer):
        incident = serializer.save()
        ensure_incident_defaults(incident, actor=self.request.user)
        ensure_follow_up_inspection_for_incident(incident, actor=self.request.user)
        ensure_corrective_work_order_for_incident(incident, actor=self.request.user)
        sync_incident_from_related_records(incident, actor=self.request.user)


class FacilityHealthSafetyInspectionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
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
    queryset = Inspection.objects.all()
    filterset_class = FacilityHealthSafetyInspectionFilter
    search_fields = ["title", "findings", "inspector", "property__name", "unit__unit_number"]
    ordering_fields = ["scheduled_date", "completed_date", "created_at", "status", "risk_level"]
    ordering = ["scheduled_date", "id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(property__facility_registry__isnull=False)
            .select_related("property", "unit", "unit__facility_space", "unit__facility_space__facility")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityHealthSafetyInspectionListSerializer
        if self.action == "retrieve":
            return FacilityHealthSafetyInspectionDetailSerializer
        return FacilityHealthSafetyInspectionWriteSerializer

    def _link_incident(self, serializer, inspection):
        incident = getattr(serializer, "linked_incident", None)
        if incident and incident.follow_up_inspection_id != inspection.id:
            incident.follow_up_inspection = inspection
            incident.save(update_fields=["follow_up_inspection", "updated_at"])

    def _audit_inspection(self, inspection):
        event_type = (
            FacilitySafetyAuditLog.EventType.INSPECTION_COMPLETED
            if inspection.status == Inspection.Status.COMPLETED
            else FacilitySafetyAuditLog.EventType.INSPECTION_SCHEDULED
        )
        summary = (
            f"Completed inspection {inspection.title}."
            if inspection.status == Inspection.Status.COMPLETED
            else f"Scheduled inspection {inspection.title}."
        )
        FacilitySafetyAuditLog.objects.create(
            organization=inspection.organization,
            property=inspection.property,
            facility=getattr(inspection.property, "facility_registry", None),
            entity_type=FacilitySafetyAuditLog.EntityType.INSPECTION,
            event_type=event_type,
            entity_id=inspection.id,
            actor=self.request.user,
            summary=summary,
            details={"inspection_id": inspection.id, "status": inspection.status},
        )

    def perform_create(self, serializer):
        inspection = serializer.save(organization=self._resolve_request_org())
        self._link_incident(serializer, inspection)
        ensure_health_safety_inspection_defaults(inspection, actor=self.request.user)
        sync_violation_for_inspection(inspection, actor=self.request.user)
        sync_incident_from_inspection(inspection, actor=self.request.user)
        self._audit_inspection(inspection)

    def perform_update(self, serializer):
        inspection = serializer.save()
        self._link_incident(serializer, inspection)
        ensure_health_safety_inspection_defaults(inspection, actor=self.request.user)
        sync_violation_for_inspection(inspection, actor=self.request.user)
        sync_incident_from_inspection(inspection, actor=self.request.user)


class FacilityComplianceChecklistViewSet(OrgScopedMixin, viewsets.ModelViewSet):
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
    queryset = FacilityComplianceChecklist.objects.all()
    filterset_class = FacilityComplianceChecklistFilter
    search_fields = ["title", "notes", "responsible_person", "property__name"]
    ordering_fields = ["due_date", "created_at", "status", "checklist_type"]
    ordering = ["due_date", "id"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "property",
                "facility",
                "facility_space",
                "facility_space__unit",
                "linked_incident",
                "linked_inspection",
                "compliance_requirement",
            )
            .prefetch_related("items")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityComplianceChecklistListSerializer
        if self.action == "retrieve":
            return FacilityComplianceChecklistDetailSerializer
        return FacilityComplianceChecklistWriteSerializer

    def _audit_checklist(self, checklist):
        event_type = (
            FacilitySafetyAuditLog.EventType.CHECKLIST_COMPLETED
            if checklist.status == FacilityComplianceChecklist.Status.COMPLETED
            else FacilitySafetyAuditLog.EventType.CHECKLIST_CREATED
        )
        summary = (
            f"Completed checklist {checklist.title}."
            if checklist.status == FacilityComplianceChecklist.Status.COMPLETED
            else f"Created checklist {checklist.title}."
        )
        FacilitySafetyAuditLog.objects.create(
            organization=checklist.organization,
            property=checklist.property,
            facility=checklist.facility,
            entity_type=FacilitySafetyAuditLog.EntityType.CHECKLIST,
            event_type=event_type,
            entity_id=checklist.id,
            actor=self.request.user,
            summary=summary,
            details={"checklist_id": checklist.id, "status": checklist.status},
        )

    def perform_create(self, serializer):
        checklist = serializer.save(organization=self._resolve_request_org())
        ensure_checklist_defaults(checklist, actor=self.request.user)
        sync_property_compliance_for_checklist(checklist, actor=self.request.user)
        sync_violation_for_checklist(checklist, actor=self.request.user)
        ensure_follow_up_inspection_for_checklist(checklist, actor=self.request.user)
        checklist.refresh_from_db()
        self._audit_checklist(checklist)

    def perform_update(self, serializer):
        checklist = serializer.save()
        ensure_checklist_defaults(checklist, actor=self.request.user)
        sync_property_compliance_for_checklist(checklist, actor=self.request.user)
        sync_violation_for_checklist(checklist, actor=self.request.user)
        ensure_follow_up_inspection_for_checklist(checklist, actor=self.request.user)


class FacilityRegulatoryDocumentViewSet(OrgScopedMixin, viewsets.ModelViewSet):
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
    queryset = FacilityRegulatoryDocument.objects.all()
    filterset_class = FacilityRegulatoryDocumentFilter
    search_fields = [
        "property_document__title",
        "property_document__description",
        "reference_number",
        "issuing_authority",
        "property__name",
    ]
    ordering_fields = ["expiry_date", "review_due_date", "created_at", "status"]
    ordering = ["expiry_date", "-id"]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("property", "facility", "property_document", "uploaded_by", "compliance_requirement")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return FacilityRegulatoryDocumentListSerializer
        if self.action == "retrieve":
            return FacilityRegulatoryDocumentDetailSerializer
        return FacilityRegulatoryDocumentWriteSerializer

    def _audit_document_upload(self, document):
        FacilitySafetyAuditLog.objects.create(
            organization=document.organization,
            property=document.property,
            facility=document.facility,
            entity_type=FacilitySafetyAuditLog.EntityType.DOCUMENT,
            event_type=FacilitySafetyAuditLog.EventType.REGULATORY_DOCUMENT_UPLOADED,
            entity_id=document.id,
            actor=self.request.user,
            summary=f"Uploaded regulatory document {document.property_document.title}.",
            details={"document_id": document.id, "status": document.status},
        )

    def perform_create(self, serializer):
        document = serializer.save(organization=self._resolve_request_org())
        ensure_regulatory_document_defaults(document, actor=self.request.user)
        sync_property_compliance_for_regulatory_document(document, actor=self.request.user)
        sync_violation_for_regulatory_document(document, actor=self.request.user)
        document.refresh_from_db()
        self._audit_document_upload(document)

    def perform_update(self, serializer):
        document = serializer.save()
        ensure_regulatory_document_defaults(document, actor=self.request.user)
        sync_property_compliance_for_regulatory_document(document, actor=self.request.user)
        sync_violation_for_regulatory_document(document, actor=self.request.user)

    def perform_destroy(self, instance):
        instance.property_document.delete()


class FacilitySafetyAuditLogViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "properties.properties"
    rbac_action_map = {
        "list": "view",
        "retrieve": "view",
    }
    queryset = FacilitySafetyAuditLog.objects.all()
    serializer_class = FacilitySafetyAuditLogSerializer
    filterset_class = FacilitySafetyAuditLogFilter
    search_fields = ["summary", "details", "property__name", "facility__facility_code"]
    ordering_fields = ["created_at", "event_type", "entity_type"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        return super().get_queryset().select_related("property", "facility", "actor")

from django.db.models import Count
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.mixins import OrgScopedMixin
from apps.settings.permissions import HasRolePermission

from .models import ComplianceAudit, ComplianceRequirement, ComplianceViolation, PropertyCompliance
from .serializers import (
    ComplianceAuditDetailSerializer,
    ComplianceAuditListSerializer,
    ComplianceAuditWriteSerializer,
    ComplianceRequirementDetailSerializer,
    ComplianceRequirementListSerializer,
    ComplianceRequirementWriteSerializer,
    ComplianceViolationDetailSerializer,
    ComplianceViolationListSerializer,
    ComplianceViolationWriteSerializer,
    PropertyComplianceDetailSerializer,
    PropertyComplianceListSerializer,
    PropertyComplianceWriteSerializer,
)

# ---------------------------------------------------------------------------
# Compliance Requirement
# ---------------------------------------------------------------------------

class ComplianceRequirementFilter(filters.FilterSet):
    class Meta:
        model = ComplianceRequirement
        fields = ["category", "renewal_frequency", "is_mandatory", "is_active"]


class ComplianceRequirementViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "compliance.all"
    filterset_class = ComplianceRequirementFilter
    search_fields = ["name", "description", "regulatory_reference"]
    ordering_fields = ["name", "category", "created_at"]
    ordering = ["category", "name"]
    queryset = ComplianceRequirement.objects.all()

    def get_queryset(self):
        return super().get_queryset().annotate(
            property_count=Count("property_records")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return ComplianceRequirementListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ComplianceRequirementWriteSerializer
        return ComplianceRequirementDetailSerializer


# ---------------------------------------------------------------------------
# Property Compliance Tracker
# ---------------------------------------------------------------------------

class PropertyComplianceFilter(filters.FilterSet):
    expiry_before = filters.DateFilter(field_name="expiry_date", lookup_expr="lte")
    expiry_after = filters.DateFilter(field_name="expiry_date", lookup_expr="gte")

    class Meta:
        model = PropertyCompliance
        fields = ["property", "requirement", "status"]


class PropertyComplianceViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "compliance.all"
    filterset_class = PropertyComplianceFilter
    search_fields = ["certificate_number", "issuing_authority", "responsible_person"]
    ordering_fields = ["expiry_date", "next_review_date", "created_at"]
    ordering = ["-created_at"]
    queryset = PropertyCompliance.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related("property", "requirement")

    def get_serializer_class(self):
        if self.action == "list":
            return PropertyComplianceListSerializer
        if self.action in ("create", "update", "partial_update"):
            return PropertyComplianceWriteSerializer
        return PropertyComplianceDetailSerializer


# ---------------------------------------------------------------------------
# Compliance Violation
# ---------------------------------------------------------------------------

class ComplianceViolationFilter(filters.FilterSet):
    reported_before = filters.DateFilter(field_name="reported_date", lookup_expr="lte")
    reported_after = filters.DateFilter(field_name="reported_date", lookup_expr="gte")

    class Meta:
        model = ComplianceViolation
        fields = ["property", "violation_type", "severity", "status"]


class ComplianceViolationViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "compliance.all"
    filterset_class = ComplianceViolationFilter
    search_fields = ["title", "description", "assigned_to", "corrective_action"]
    ordering_fields = ["reported_date", "due_date", "severity", "created_at"]
    ordering = ["-reported_date"]
    queryset = ComplianceViolation.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related("property", "compliance_item")

    def get_serializer_class(self):
        if self.action == "list":
            return ComplianceViolationListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ComplianceViolationWriteSerializer
        return ComplianceViolationDetailSerializer


# ---------------------------------------------------------------------------
# Compliance Audit
# ---------------------------------------------------------------------------

class ComplianceAuditFilter(filters.FilterSet):
    scheduled_before = filters.DateFilter(field_name="scheduled_date", lookup_expr="lte")
    scheduled_after = filters.DateFilter(field_name="scheduled_date", lookup_expr="gte")

    class Meta:
        model = ComplianceAudit
        fields = ["property", "audit_type", "status", "overall_rating", "follow_up_required"]


class ComplianceAuditViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "compliance.all"
    filterset_class = ComplianceAuditFilter
    search_fields = ["title", "auditor", "scope", "findings"]
    ordering_fields = ["scheduled_date", "completed_date", "created_at"]
    ordering = ["-scheduled_date"]
    queryset = ComplianceAudit.objects.all()

    def get_queryset(self):
        return super().get_queryset().select_related("property")

    def get_serializer_class(self):
        if self.action == "list":
            return ComplianceAuditListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ComplianceAuditWriteSerializer
        return ComplianceAuditDetailSerializer

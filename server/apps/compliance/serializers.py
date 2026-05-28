from rest_framework import serializers

from .models import ComplianceAudit, ComplianceRequirement, ComplianceViolation, PropertyCompliance

# ---------------------------------------------------------------------------
# Compliance Requirement
# ---------------------------------------------------------------------------

class ComplianceRequirementListSerializer(serializers.ModelSerializer):
    property_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ComplianceRequirement
        fields = [
            "id", "name", "category", "regulatory_reference",
            "renewal_frequency", "is_mandatory", "is_active",
            "property_count", "created_at", "updated_at",
        ]


class ComplianceRequirementDetailSerializer(serializers.ModelSerializer):
    property_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ComplianceRequirement
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ComplianceRequirementWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceRequirement
        fields = [
            "id", "name", "category", "description",
            "regulatory_reference", "renewal_frequency",
            "is_mandatory", "is_active",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Property Compliance Tracker
# ---------------------------------------------------------------------------

class PropertyComplianceListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    requirement_category = serializers.CharField(source="requirement.category", read_only=True)

    class Meta:
        model = PropertyCompliance
        fields = [
            "id", "property", "property_name",
            "requirement", "requirement_name", "requirement_category",
            "status", "certificate_number", "issuing_authority",
            "expiry_date", "next_review_date", "responsible_person",
            "created_at", "updated_at",
        ]


class PropertyComplianceDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    requirement_name = serializers.CharField(source="requirement.name", read_only=True)
    requirement_category = serializers.CharField(source="requirement.category", read_only=True)

    class Meta:
        model = PropertyCompliance
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PropertyComplianceWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyCompliance
        fields = [
            "id", "property", "requirement", "status",
            "certificate_number", "issuing_authority",
            "issue_date", "expiry_date",
            "last_reviewed_date", "next_review_date",
            "responsible_person", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Compliance Violation
# ---------------------------------------------------------------------------

class ComplianceViolationListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = ComplianceViolation
        fields = [
            "id", "property", "property_name",
            "compliance_item", "title", "violation_type",
            "severity", "status",
            "reported_date", "due_date", "resolved_date",
            "fine_amount", "assigned_to",
            "created_at", "updated_at",
        ]


class ComplianceViolationDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = ComplianceViolation
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ComplianceViolationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceViolation
        fields = [
            "id", "property", "compliance_item",
            "title", "description", "violation_type",
            "severity", "status",
            "reported_date", "due_date", "resolved_date",
            "corrective_action", "fine_amount",
            "assigned_to", "notes",
        ]
        read_only_fields = ("id",)


# ---------------------------------------------------------------------------
# Compliance Audit
# ---------------------------------------------------------------------------

class ComplianceAuditListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = ComplianceAudit
        fields = [
            "id", "property", "property_name",
            "title", "audit_type", "status",
            "scheduled_date", "completed_date",
            "auditor", "overall_rating", "follow_up_required",
            "created_at", "updated_at",
        ]


class ComplianceAuditDetailSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = ComplianceAudit
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ComplianceAuditWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAudit
        fields = [
            "id", "property", "title", "audit_type", "status",
            "scheduled_date", "completed_date", "auditor",
            "scope", "findings", "overall_rating",
            "follow_up_required", "follow_up_notes", "notes",
        ]
        read_only_fields = ("id",)

from rest_framework import serializers

from .models import (
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    OnboardingTemplateStage,
    PartnerEntitlement,
    PartnerOnboardingApproval,
    PartnerOnboardingAuditLog,
    PartnerOnboardingCase,
    PartnerOnboardingIntakeDocument,
    PartnerOnboardingStageProgress,
)


class OnboardingTemplateStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingTemplateStage
        fields = [
            "id",
            "template",
            "sequence",
            "code",
            "name",
            "description",
            "is_required",
            "approval_required",
            "approval_role_label",
            "sla_hours",
            "auto_complete",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OnboardingTemplateDocumentRequirementSerializer(serializers.ModelSerializer):
    stage_code = serializers.CharField(source="applies_to_stage.code", read_only=True, allow_null=True)
    stage_name = serializers.CharField(source="applies_to_stage.name", read_only=True, allow_null=True)

    class Meta:
        model = OnboardingTemplateDocumentRequirement
        fields = [
            "id",
            "template",
            "sequence",
            "code",
            "name",
            "description",
            "is_required",
            "applies_to_stage",
            "stage_code",
            "stage_name",
            "accepted_sources",
            "allowed_extensions",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "stage_code", "stage_name", "created_at", "updated_at"]

    def validate(self, attrs):
        template = attrs.get("template") or getattr(self.instance, "template", None)
        stage = attrs.get("applies_to_stage") or getattr(self.instance, "applies_to_stage", None)
        if stage and template and stage.template_id != template.id:
            raise serializers.ValidationError(
                {"applies_to_stage": "Selected stage must belong to the same onboarding template."}
            )
        return attrs


class OnboardingTemplateSerializer(serializers.ModelSerializer):
    stages = OnboardingTemplateStageSerializer(many=True, read_only=True)
    stage_count = serializers.SerializerMethodField()

    class Meta:
        model = OnboardingTemplate
        fields = [
            "id",
            "organization",
            "partner_type",
            "code",
            "name",
            "description",
            "version",
            "is_default",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "stage_count",
            "stages",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "stage_count",
            "stages",
        ]

    def get_stage_count(self, obj):
        return obj.stages.count()


class PartnerOnboardingIntakeDocumentSerializer(serializers.ModelSerializer):
    requirement_code = serializers.CharField(source="requirement.code", read_only=True, allow_null=True)
    requirement_name = serializers.CharField(source="requirement.name", read_only=True, allow_null=True)
    stage_code = serializers.CharField(source="template_stage.code", read_only=True, allow_null=True)
    stage_name = serializers.CharField(source="template_stage.name", read_only=True, allow_null=True)
    submitted_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    linked_repository_document_title = serializers.CharField(
        source="linked_repository_document.title",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PartnerOnboardingIntakeDocument
        fields = [
            "id",
            "case",
            "requirement",
            "requirement_code",
            "requirement_name",
            "template_stage",
            "stage_code",
            "stage_name",
            "document_code",
            "document_name",
            "source_channel",
            "file",
            "external_reference_url",
            "external_reference_number",
            "received_at",
            "status",
            "submitted_by",
            "submitted_by_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "review_notes",
            "linked_repository_document",
            "linked_repository_document_title",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "submitted_by",
            "submitted_by_name",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "requirement_code",
            "requirement_name",
            "stage_code",
            "stage_name",
            "linked_repository_document_title",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        case = attrs.get("case") or getattr(self.instance, "case", None)
        requirement = attrs.get("requirement", getattr(self.instance, "requirement", None))
        stage = attrs.get("template_stage", getattr(self.instance, "template_stage", None))

        if requirement:
            if case and not case.template_id:
                raise serializers.ValidationError({"requirement": "Case has no onboarding template."})
            if case and requirement.template_id != case.template_id:
                raise serializers.ValidationError(
                    {"requirement": "Requirement must belong to the case onboarding template."}
                )

            if not attrs.get("document_code") and not getattr(self.instance, "document_code", ""):
                attrs["document_code"] = requirement.code
            if not attrs.get("document_name") and not getattr(self.instance, "document_name", ""):
                attrs["document_name"] = requirement.name

            if not stage:
                attrs["template_stage"] = requirement.applies_to_stage
            elif requirement.applies_to_stage_id and stage.id != requirement.applies_to_stage_id:
                raise serializers.ValidationError(
                    {"template_stage": "Template stage must match the linked requirement stage."}
                )

        if stage and case and case.template_id and stage.template_id != case.template_id:
            raise serializers.ValidationError({"template_stage": "Template stage must belong to the case template."})

        status_value = attrs.get("status", getattr(self.instance, "status", None))
        if status_value in [
            PartnerOnboardingIntakeDocument.ReviewStatus.APPROVED,
            PartnerOnboardingIntakeDocument.ReviewStatus.WAIVED,
        ]:
            has_file = bool(attrs.get("file") or getattr(self.instance, "file", None))
            has_ref_url = bool(
                attrs.get("external_reference_url", getattr(self.instance, "external_reference_url", "")).strip()
            )
            has_ref_no = bool(
                attrs.get("external_reference_number", getattr(self.instance, "external_reference_number", "")).strip()
            )
            if not any([has_file, has_ref_url, has_ref_no]):
                raise serializers.ValidationError(
                    "Approved/waived intake records must include a file or a source reference."
                )

        return attrs

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="any")

    def get_submitted_by_name(self, obj):
        if not obj.submitted_by_id or not obj.submitted_by:
            return None
        return obj.submitted_by.get_full_name() or obj.submitted_by.email

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by_id or not obj.reviewed_by:
            return None
        return obj.reviewed_by.get_full_name() or obj.reviewed_by.email


class PartnerOnboardingStageProgressSerializer(serializers.ModelSerializer):
    stage_sequence = serializers.IntegerField(source="template_stage.sequence", read_only=True)
    stage_code = serializers.CharField(source="template_stage.code", read_only=True)
    stage_name = serializers.CharField(source="template_stage.name", read_only=True)

    class Meta:
        model = PartnerOnboardingStageProgress
        fields = [
            "id",
            "case",
            "template_stage",
            "stage_sequence",
            "stage_code",
            "stage_name",
            "status",
            "is_required",
            "started_at",
            "completed_at",
            "completed_by",
            "notes",
            "evidence_links",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "case",
            "template_stage",
            "stage_sequence",
            "stage_code",
            "stage_name",
            "started_at",
            "completed_at",
            "completed_by",
            "created_at",
            "updated_at",
        ]


class PartnerOnboardingApprovalSerializer(serializers.ModelSerializer):
    stage_code = serializers.CharField(source="stage_progress.template_stage.code", read_only=True)
    stage_name = serializers.CharField(source="stage_progress.template_stage.name", read_only=True)

    class Meta:
        model = PartnerOnboardingApproval
        fields = [
            "id",
            "case",
            "stage_progress",
            "stage_code",
            "stage_name",
            "decision",
            "approver_role_label",
            "comments",
            "metadata",
            "decided_by",
            "decided_at",
        ]
        read_only_fields = ["id", "case", "decided_by", "decided_at", "stage_code", "stage_name"]


class PartnerEntitlementSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, allow_null=True)
    spv_name = serializers.CharField(source="spv_entity.name", read_only=True, allow_null=True)

    class Meta:
        model = PartnerEntitlement
        fields = [
            "id",
            "case",
            "organization",
            "portal_role",
            "project",
            "project_name",
            "spv_entity",
            "spv_name",
            "contract_reference",
            "investment_vehicle_reference",
            "budget_scope",
            "can_view_other_investors",
            "can_edit",
            "can_approve",
            "can_comment",
            "can_download_documents",
            "is_active",
            "effective_from",
            "expires_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "case",
            "organization",
            "created_by",
            "created_at",
            "updated_at",
            "project_name",
            "spv_name",
        ]


class PartnerOnboardingAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, allow_null=True)

    class Meta:
        model = PartnerOnboardingAuditLog
        fields = [
            "id",
            "case",
            "event_type",
            "actor",
            "actor_email",
            "actor_role_label",
            "ip_address",
            "message",
            "payload",
            "created_at",
        ]
        read_only_fields = fields


class PartnerOnboardingCaseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOnboardingCase
        fields = [
            "id",
            "partner_type",
            "status",
            "template",
            "title",
            "contact_name",
            "contact_email",
            "contact_phone",
            "lead",
            "vendor",
            "investor",
            "customer",
            "project",
            "spv_entity",
            "contract_reference",
            "investment_vehicle_reference",
            "assigned_owner",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        template = attrs.get("template")
        partner_type = attrs.get("partner_type") or getattr(self.instance, "partner_type", None)
        if template and partner_type and template.partner_type != partner_type:
            raise serializers.ValidationError(
                {"template": "Template partner type must match onboarding case partner type."}
            )

        lead = attrs.get("lead", getattr(self.instance, "lead", None))
        vendor = attrs.get("vendor", getattr(self.instance, "vendor", None))
        investor = attrs.get("investor", getattr(self.instance, "investor", None))
        contact_name = attrs.get("contact_name", getattr(self.instance, "contact_name", ""))
        contact_email = attrs.get("contact_email", getattr(self.instance, "contact_email", ""))

        if not any([lead, vendor, investor, contact_name, contact_email]):
            raise serializers.ValidationError(
                "Provide at least one source reference (lead/vendor/investor) or contact identity details."
            )

        return attrs


class PartnerOnboardingCaseListSerializer(serializers.ModelSerializer):
    partner_type_display = serializers.CharField(source="get_partner_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    current_stage_name = serializers.CharField(source="current_stage.name", read_only=True, allow_null=True)
    template_name = serializers.CharField(source="template.name", read_only=True, allow_null=True)
    lead_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.name", read_only=True, allow_null=True)
    investor_name = serializers.CharField(source="investor.name", read_only=True, allow_null=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, allow_null=True)
    assigned_owner_name = serializers.SerializerMethodField()
    required_stage_total = serializers.SerializerMethodField()
    required_stage_completed = serializers.SerializerMethodField()
    completion_percent = serializers.SerializerMethodField()
    has_erp_profile = serializers.SerializerMethodField()
    required_document_total = serializers.SerializerMethodField()
    approved_document_total = serializers.SerializerMethodField()
    pending_document_review_count = serializers.SerializerMethodField()
    missing_required_document_count = serializers.SerializerMethodField()
    intake_gate_passed = serializers.SerializerMethodField()

    class Meta:
        model = PartnerOnboardingCase
        fields = [
            "id",
            "organization",
            "partner_type",
            "partner_type_display",
            "status",
            "status_display",
            "template",
            "template_name",
            "title",
            "contact_name",
            "contact_email",
            "lead",
            "lead_name",
            "vendor",
            "vendor_name",
            "investor",
            "investor_name",
            "customer",
            "customer_name",
            "project",
            "spv_entity",
            "contract_reference",
            "investment_vehicle_reference",
            "current_stage",
            "current_stage_name",
            "portal_access_granted",
            "portal_access_granted_at",
            "assigned_owner",
            "assigned_owner_name",
            "required_stage_total",
            "required_stage_completed",
            "completion_percent",
            "required_document_total",
            "approved_document_total",
            "pending_document_review_count",
            "missing_required_document_count",
            "intake_gate_passed",
            "has_erp_profile",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _count_required(self, obj):
        return obj.stage_progress.filter(is_required=True).count()

    def _count_completed(self, obj):
        return obj.stage_progress.filter(
            is_required=True,
            status__in=[
                PartnerOnboardingStageProgress.Status.COMPLETED,
                PartnerOnboardingStageProgress.Status.WAIVED,
            ],
        ).count()

    def get_required_stage_total(self, obj):
        return self._count_required(obj)

    def get_required_stage_completed(self, obj):
        return self._count_completed(obj)

    def get_completion_percent(self, obj):
        total = self._count_required(obj)
        if total == 0:
            return 0
        return round((self._count_completed(obj) / total) * 100, 2)

    def get_has_erp_profile(self, obj):
        return obj.has_erp_profile

    def _required_document_queryset(self, obj):
        if not obj.template_id:
            return OnboardingTemplateDocumentRequirement.objects.none()
        return obj.template.document_requirements.filter(is_required=True)

    def _document_gate_stats(self, obj):
        cache = getattr(self, "_document_gate_cache", None)
        if cache is None:
            cache = {}
            self._document_gate_cache = cache

        cached = cache.get(obj.id)
        if cached is not None:
            return cached

        requirement_ids = list(self._required_document_queryset(obj).values_list("id", flat=True))
        required_total = len(requirement_ids)
        approved_total = 0
        if requirement_ids:
            approved_total = (
                obj.intake_documents.filter(
                    requirement_id__in=requirement_ids,
                    status__in=[
                        PartnerOnboardingIntakeDocument.ReviewStatus.APPROVED,
                        PartnerOnboardingIntakeDocument.ReviewStatus.WAIVED,
                    ],
                )
                .values("requirement_id")
                .distinct()
                .count()
            )

        pending_count = obj.intake_documents.filter(
            status__in=[
                PartnerOnboardingIntakeDocument.ReviewStatus.RECEIVED,
                PartnerOnboardingIntakeDocument.ReviewStatus.UNDER_REVIEW,
            ]
        ).count()

        stats = {
            "required_total": required_total,
            "approved_total": approved_total,
            "missing_total": max(required_total - approved_total, 0),
            "pending_count": pending_count,
        }
        cache[obj.id] = stats
        return stats

    def get_required_document_total(self, obj):
        return self._document_gate_stats(obj)["required_total"]

    def get_approved_document_total(self, obj):
        return self._document_gate_stats(obj)["approved_total"]

    def get_missing_required_document_count(self, obj):
        return self._document_gate_stats(obj)["missing_total"]

    def get_pending_document_review_count(self, obj):
        return self._document_gate_stats(obj)["pending_count"]

    def get_intake_gate_passed(self, obj):
        return self._document_gate_stats(obj)["missing_total"] == 0

    def get_lead_name(self, obj):
        if obj.lead_id and obj.lead:
            return obj.lead.full_name
        return None

    def get_assigned_owner_name(self, obj):
        if obj.assigned_owner_id and obj.assigned_owner:
            first = obj.assigned_owner.first_name or ""
            last = obj.assigned_owner.last_name or ""
            return f"{first} {last}".strip() or obj.assigned_owner.email
        return None


class PartnerOnboardingCaseDetailSerializer(PartnerOnboardingCaseListSerializer):
    stage_progress = PartnerOnboardingStageProgressSerializer(many=True, read_only=True)
    approvals = PartnerOnboardingApprovalSerializer(many=True, read_only=True)
    entitlements = PartnerEntitlementSerializer(many=True, read_only=True)
    required_documents = serializers.SerializerMethodField()
    intake_documents = PartnerOnboardingIntakeDocumentSerializer(many=True, read_only=True)

    def get_required_documents(self, obj):
        if not obj.template_id:
            return []
        queryset = obj.template.document_requirements.all().order_by("sequence", "id")
        return OnboardingTemplateDocumentRequirementSerializer(queryset, many=True).data

    class Meta(PartnerOnboardingCaseListSerializer.Meta):
        fields = PartnerOnboardingCaseListSerializer.Meta.fields + [
            "contact_phone",
            "notes",
            "stage_progress",
            "approvals",
            "entitlements",
            "required_documents",
            "intake_documents",
        ]

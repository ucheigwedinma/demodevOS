from rest_framework import serializers

from .audit import event_summary
from .models import (
    ControlledVocabularyTerm,
    Document,
    DocumentApproval,
    DocumentAuditEvent,
    DocumentBusinessUnitMembership,
    DocumentComment,
    DocumentDomain,
    DocumentExpiry,
    DocumentGenerationRecord,
    DocumentGovernanceCharter,
    DocumentOwnerRole,
    DocumentProjectMembership,
    DocumentRetentionPolicy,
    DocumentRoleScope,
    DocumentSearchIndex,
    DocumentSignatureRequest,
    DocumentType,
    DocumentVersion,
    DocumentWorkflowInstance,
    DocumentWorkflowPhase,
    DocumentWorkflowRule,
    DocumentWorkflowStep,
    DocumentWorkflowTemplate,
    DocumentWorkflowTemplateStep,
)


class DocumentGovernanceCharterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentGovernanceCharter
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class DocumentDomainSerializer(serializers.ModelSerializer):
    term_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = DocumentDomain
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class DocumentTypeOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = ["id", "code", "name", "category_code", "description", "is_active"]


class DocumentOwnerRoleOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentOwnerRole
        fields = ["id", "code", "name", "description", "is_active"]


class DocumentWorkflowPhaseOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentWorkflowPhase
        fields = ["id", "code", "name", "numbering_code", "description", "sort_order", "is_active"]


class DocumentRetentionPolicyOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRetentionPolicy
        fields = ["id", "code", "name", "retention_years", "is_indefinite", "description", "is_active"]


class ControlledVocabularyTermSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source="domain.name", read_only=True)
    domain_code = serializers.CharField(source="domain.code", read_only=True)

    class Meta:
        model = ControlledVocabularyTerm
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ControlledVocabularyDictionaryTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlledVocabularyTerm
        fields = [
            "id",
            "term",
            "term_key",
            "definition",
            "usage_guidance",
            "synonyms",
            "status",
            "is_required",
            "sort_order",
        ]


class DocumentDomainDictionarySerializer(serializers.ModelSerializer):
    vocabulary_terms = ControlledVocabularyDictionaryTermSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentDomain
        fields = [
            "id",
            "code",
            "name",
            "description",
            "sort_order",
            "is_active",
            "vocabulary_terms",
        ]


class DocumentMetadataSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    land_name = serializers.CharField(source="land.name", read_only=True, default=None)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, default=None)
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)
    category = serializers.CharField(source="document_type.category_code", read_only=True, default="GEN")
    document_type_name = serializers.CharField(source="document_type.name", read_only=True)
    phase_name = serializers.CharField(source="phase.name", read_only=True)
    contract_value = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    project_risk_rating = serializers.CharField(source="project.risk_rating", read_only=True, default=None)
    business_unit_division_name = serializers.CharField(
        source="business_unit_division.name",
        read_only=True,
        default=None,
    )
    business_unit_department_name = serializers.CharField(
        source="business_unit_department.name",
        read_only=True,
        default=None,
    )
    index_status = serializers.SerializerMethodField()
    indexed_at = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "document_number",
            "status",
            "confidentiality_level",
            "project",
            "project_name",
            "land",
            "land_name",
            "unit",
            "unit_number",
            "vendor",
            "vendor_name",
            "client",
            "client_name",
            "document_type",
            "document_type_name",
            "category",
            "phase",
            "phase_name",
            "contract_value",
            "project_risk_rating",
            "business_unit_division",
            "business_unit_division_name",
            "business_unit_department",
            "business_unit_department_name",
            "created_at",
            "index_status",
            "indexed_at",
        ]

    def get_index_status(self, obj: Document) -> str | None:
        try:
            return obj.search_index.index_status
        except DocumentSearchIndex.DoesNotExist:
            return None

    def get_indexed_at(self, obj: Document):
        try:
            return obj.search_index.indexed_at
        except DocumentSearchIndex.DoesNotExist:
            return None


class DocumentSearchResultSerializer(DocumentMetadataSerializer):
    search_rank = serializers.FloatField(read_only=True, default=0)
    snippet = serializers.SerializerMethodField()
    matching_clauses = serializers.SerializerMethodField()

    class Meta(DocumentMetadataSerializer.Meta):
        fields = DocumentMetadataSerializer.Meta.fields + [
            "search_rank",
            "snippet",
            "matching_clauses",
        ]

    def get_snippet(self, obj: Document) -> str:
        query_text = (self.context.get("query_text") or "").strip()
        try:
            content = obj.search_index.combined_text
        except DocumentSearchIndex.DoesNotExist:
            content = ""
        if not content:
            return ""
        if not query_text:
            return content[:240]

        low_content = content.lower()
        low_query = query_text.lower()
        idx = low_content.find(low_query)
        if idx < 0:
            return content[:240]
        start = max(0, idx - 80)
        end = min(len(content), idx + len(query_text) + 160)
        snippet = content[start:end].strip()
        if start > 0:
            snippet = f"...{snippet}"
        if end < len(content):
            snippet = f"{snippet}..."
        return snippet

    def get_matching_clauses(self, obj: Document) -> list[str]:
        clause_query = (self.context.get("clause_query") or "").strip().lower()
        if not clause_query:
            return []

        try:
            clauses = obj.search_index.indexed_clauses or []
        except DocumentSearchIndex.DoesNotExist:
            return []
        matches = [clause for clause in clauses if clause_query in clause.lower()]
        return matches[:10]


class DocumentSearchIndexSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = DocumentSearchIndex
        fields = [
            "id",
            "document",
            "document_number",
            "document_title",
            "document_version",
            "index_status",
            "indexed_at",
            "error_message",
            "updated_at",
        ]


class DocumentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "document_number",
            "project_code",
            "document_type",
            "confidentiality_level",
            "owner_role",
            "contract_value",
            "business_unit_division",
            "business_unit_department",
            "project",
            "land",
            "unit",
            "client",
            "vendor",
            "phase",
            "current_version",
            "status",
            "sequence_number",
            "revision_number",
            "retention_policy",
            "created_at",
        ]
        read_only_fields = (
            "id",
            "document_number",
            "current_version",
            "sequence_number",
            "revision_number",
            "created_at",
        )

    def validate(self, attrs):
        division = attrs.get(
            "business_unit_division",
            getattr(self.instance, "business_unit_division", None),
        )
        department = attrs.get(
            "business_unit_department",
            getattr(self.instance, "business_unit_department", None),
        )

        if department and division and department.division_id != division.id:
            raise serializers.ValidationError(
                {"business_unit_department": "Selected department does not belong to selected division."}
            )
        return attrs


class DocumentVersionSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)

    class Meta:
        model = DocumentVersion
        fields = [
            "id",
            "document",
            "document_number",
            "version_major",
            "version_minor",
            "file_path",
            "change_summary",
            "uploaded_by",
            "uploaded_by_name",
            "approval_status",
            "uploaded_at",
        ]
        read_only_fields = ("id", "uploaded_at")


class DocumentApprovalSerializer(serializers.ModelSerializer):
    document_version_label = serializers.SerializerMethodField()
    role_name = serializers.CharField(source="role.name", read_only=True)
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = DocumentApproval
        fields = [
            "id",
            "document_version",
            "document_version_label",
            "role",
            "role_name",
            "user",
            "user_name",
            "decision",
            "comments",
            "timestamp",
        ]
        read_only_fields = ("id", "timestamp")
        extra_kwargs = {
            "user": {"required": False},
            "role": {"required": False},
        }

    def get_document_version_label(self, obj: DocumentApproval) -> str:
        return str(obj.document_version)


class DocumentExpirySerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)

    class Meta:
        model = DocumentExpiry
        fields = [
            "id",
            "document",
            "document_number",
            "trigger_category",
            "expiry_date",
            "alert_90_days",
            "alert_30_days",
            "alert_expired",
            "alert_90_days_sent_at",
            "alert_30_days_sent_at",
            "expired_alert_sent_at",
            "escalated_at",
            "last_checked_at",
        ]
        read_only_fields = (
            "id",
            "alert_90_days_sent_at",
            "alert_30_days_sent_at",
            "expired_alert_sent_at",
            "escalated_at",
            "last_checked_at",
        )


class DocumentCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)
    document_number = serializers.CharField(source="document.document_number", read_only=True)

    class Meta:
        model = DocumentComment
        fields = [
            "id",
            "document",
            "document_number",
            "document_version",
            "author",
            "author_name",
            "comment",
            "created_at",
        ]
        read_only_fields = ("id", "author", "created_at")


class DocumentAuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_email = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    summary = serializers.SerializerMethodField()
    document_number = serializers.SerializerMethodField()
    document_title = serializers.SerializerMethodField()
    version_label = serializers.SerializerMethodField()

    class Meta:
        model = DocumentAuditEvent
        fields = [
            "id",
            "document",
            "document_number",
            "document_title",
            "document_version",
            "version_label",
            "event_type",
            "event_type_display",
            "summary",
            "actor",
            "actor_name",
            "actor_email",
            "actor_role",
            "actor_role_name",
            "ip_address",
            "payload",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj: DocumentAuditEvent) -> str:
        actor = obj.actor
        if not actor:
            return "System"
        full_name = actor.get_full_name().strip()
        return full_name or actor.email or actor.username

    def get_actor_email(self, obj: DocumentAuditEvent) -> str | None:
        return obj.actor.email if obj.actor else None

    def get_document_number(self, obj: DocumentAuditEvent) -> str:
        if obj.document_id:
            return obj.document.document_number
        return obj.document_number_snapshot

    def get_document_title(self, obj: DocumentAuditEvent) -> str:
        if obj.document_id:
            return obj.document.title
        return obj.document_title_snapshot

    def get_version_label(self, obj: DocumentAuditEvent) -> str:
        if obj.document_version_id:
            return f"v{obj.document_version.version_major}.{obj.document_version.version_minor}"
        return obj.version_label_snapshot

    def get_summary(self, obj: DocumentAuditEvent) -> str:
        return event_summary(obj)


class DocumentShareRequestSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(
        choices=[
            ("email", "Email"),
            ("link", "Share Link"),
            ("portal", "Portal Access"),
        ],
        default="email",
    )
    recipient = serializers.EmailField(required=False)
    recipient_name = serializers.CharField(required=False, allow_blank=True, max_length=160)
    expires_at = serializers.DateTimeField(required=False)
    allow_download = serializers.BooleanField(required=False, default=True)
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    def validate(self, attrs):
        channel = attrs.get("channel", "email")
        if channel == "email" and not attrs.get("recipient"):
            raise serializers.ValidationError({"recipient": "Recipient email is required for email sharing."})
        return attrs


class DocumentRoleScopeSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    allowed_confidentiality_levels = serializers.ListField(
        child=serializers.ChoiceField(choices=Document.ConfidentialityLevel.choices),
        required=False,
    )

    class Meta:
        model = DocumentRoleScope
        fields = [
            "id",
            "role",
            "role_name",
            "project_scope",
            "business_unit_scope",
            "allowed_confidentiality_levels",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class DocumentProjectMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = DocumentProjectMembership
        fields = [
            "id",
            "user",
            "user_name",
            "project",
            "project_name",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class DocumentBusinessUnitMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = DocumentBusinessUnitMembership
        fields = [
            "id",
            "user",
            "user_name",
            "division",
            "division_name",
            "department",
            "department_name",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")

    def validate(self, attrs):
        user = attrs.get(
            "user",
            getattr(self.instance, "user", None),
        )
        division = attrs.get(
            "division",
            getattr(self.instance, "division", None),
        )
        department = attrs.get(
            "department",
            getattr(self.instance, "department", None),
        )
        if not division and not department:
            raise serializers.ValidationError("Either division or department must be provided.")
        if department and division and department.division_id != division.id:
            raise serializers.ValidationError(
                {"department": "Selected department does not belong to selected division."}
            )
        if user:
            duplicate_qs = DocumentBusinessUnitMembership.objects.filter(
                user=user,
                division=division,
                department=department,
            )
            if self.instance:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                raise serializers.ValidationError(
                    "This business unit membership already exists for the user."
                )
        return attrs


class DocumentWorkflowTemplateStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentWorkflowTemplateStep
        fields = [
            "id",
            "template",
            "sequence",
            "approver_label",
            "approver_role_slug",
            "is_active",
            "created_at",
        ]
        read_only_fields = ("id", "created_at")


class DocumentWorkflowTemplateSerializer(serializers.ModelSerializer):
    steps = DocumentWorkflowTemplateStepSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentWorkflowTemplate
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_default",
            "is_active",
            "steps",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class DocumentWorkflowTemplateWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentWorkflowTemplate
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")


class DocumentWorkflowRuleSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)
    document_type_name = serializers.CharField(source="document_type.name", read_only=True, default=None)
    allowed_confidentiality_levels = serializers.ListField(
        child=serializers.ChoiceField(choices=Document.ConfidentialityLevel.choices),
        required=False,
    )
    allowed_project_risk_ratings = serializers.ListField(
        child=serializers.ChoiceField(choices=DocumentWorkflowRule.ProjectRiskRating.choices),
        required=False,
    )

    class Meta:
        model = DocumentWorkflowRule
        fields = [
            "id",
            "name",
            "template",
            "template_name",
            "document_type",
            "document_type_name",
            "min_contract_value",
            "max_contract_value",
            "allowed_confidentiality_levels",
            "allowed_project_risk_ratings",
            "priority",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        min_value = attrs.get("min_contract_value", getattr(self.instance, "min_contract_value", None))
        max_value = attrs.get("max_contract_value", getattr(self.instance, "max_contract_value", None))
        if min_value is not None and max_value is not None and min_value > max_value:
            raise serializers.ValidationError(
                {"max_contract_value": "max_contract_value must be greater than min_contract_value."}
            )
        return attrs


class DocumentWorkflowStepSerializer(serializers.ModelSerializer):
    decided_by_name = serializers.CharField(source="decided_by.get_full_name", read_only=True, default=None)

    class Meta:
        model = DocumentWorkflowStep
        fields = [
            "id",
            "workflow_instance",
            "sequence",
            "approver_label",
            "approver_role_slug",
            "decision",
            "decided_by",
            "decided_by_name",
            "comments",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "workflow_instance",
            "sequence",
            "approver_label",
            "approver_role_slug",
            "decided_by",
            "decided_by_name",
            "decided_at",
            "created_at",
            "updated_at",
        )


class DocumentWorkflowInstanceSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True)
    matched_rule_name = serializers.CharField(source="matched_rule.name", read_only=True, default=None)
    steps = DocumentWorkflowStepSerializer(many=True, read_only=True)

    class Meta:
        model = DocumentWorkflowInstance
        fields = [
            "id",
            "document",
            "document_number",
            "document_title",
            "template",
            "template_name",
            "matched_rule",
            "matched_rule_name",
            "state",
            "submitted_at",
            "completed_at",
            "steps",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "document",
            "template",
            "matched_rule",
            "state",
            "submitted_at",
            "completed_at",
            "steps",
            "created_at",
            "updated_at",
        )


class WorkflowDecisionSerializer(serializers.Serializer):
    step_id = serializers.IntegerField()
    decision = serializers.ChoiceField(
        choices=[
            DocumentWorkflowStep.Decision.APPROVED,
            DocumentWorkflowStep.Decision.REJECTED,
        ]
    )
    comments = serializers.CharField(required=False, allow_blank=True)


class DocumentSearchIndexContentSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)
    version_label = serializers.SerializerMethodField()

    class Meta:
        model = DocumentSearchIndex
        fields = [
            "id",
            "document",
            "document_number",
            "document_title",
            "document_version",
            "version_label",
            "index_status",
            "indexed_at",
            "updated_at",
            "extracted_text",
            "ocr_text",
            "clause_text",
            "indexed_clauses",
            "error_message",
        ]

    def get_version_label(self, obj: DocumentSearchIndex) -> str:
        if not obj.document_version_id:
            return ""
        return f"v{obj.document_version.version_major}.{obj.document_version.version_minor}"


class DocumentSignatureRequestSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)
    version_label = serializers.SerializerMethodField()
    requested_by_name = serializers.CharField(
        source="requested_by.get_full_name",
        read_only=True,
        default=None,
    )
    provider_display = serializers.CharField(source="get_provider_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = DocumentSignatureRequest
        fields = [
            "id",
            "document",
            "document_number",
            "document_title",
            "document_version",
            "version_label",
            "provider",
            "provider_display",
            "status",
            "status_display",
            "provider_envelope_id",
            "signing_url",
            "signers",
            "subject",
            "message",
            "provider_payload",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "sent_at",
            "completed_at",
            "cancelled_at",
            "updated_at",
        ]
        read_only_fields = (
            "id",
            "provider_envelope_id",
            "signing_url",
            "provider_payload",
            "requested_by",
            "requested_by_name",
            "requested_at",
            "sent_at",
            "completed_at",
            "cancelled_at",
            "updated_at",
        )
        extra_kwargs = {
            "provider": {"required": False},
        }

    def get_version_label(self, obj: DocumentSignatureRequest) -> str:
        version = obj.document_version
        if not version:
            return ""
        return f"v{version.version_major}.{version.version_minor}"

    def validate_signers(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("signers must be a list.")
        normalized = []
        for row in value:
            if not isinstance(row, dict):
                raise serializers.ValidationError("Each signer must be an object.")
            email = str(row.get("email", "")).strip()
            name = str(row.get("name", "")).strip()
            if not email:
                raise serializers.ValidationError("Each signer requires an email.")
            normalized.append(
                {
                    "name": name or email,
                    "email": email,
                    "role": str(row.get("role", "")).strip(),
                    "order": int(row.get("order", 1) or 1),
                    "status": str(row.get("status", "pending")).strip() or "pending",
                }
            )
        return normalized

    def validate(self, attrs):
        document = attrs.get("document", getattr(self.instance, "document", None))
        document_version = attrs.get("document_version", getattr(self.instance, "document_version", None))
        if document_version and document and document_version.document_id != document.id:
            raise serializers.ValidationError(
                {"document_version": "document_version does not belong to selected document."}
            )
        return attrs


class DocumentSignatureDecisionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True)
    signed_file = serializers.FileField(required=False)

    def validate_signed_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="document")


class DocumentGenerationRecordSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source="document.document_number", read_only=True, default="")
    document_title = serializers.CharField(source="document.title", read_only=True, default="")
    version_label = serializers.SerializerMethodField()
    requested_by_name = serializers.CharField(
        source="requested_by.get_full_name",
        read_only=True,
        default=None,
    )

    class Meta:
        model = DocumentGenerationRecord
        fields = [
            "id",
            "generation_kind",
            "title",
            "template_code",
            "document",
            "document_number",
            "document_title",
            "document_version",
            "version_label",
            "branding_snapshot",
            "context_payload",
            "file_path",
            "requested_by",
            "requested_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_version_label(self, obj: DocumentGenerationRecord) -> str:
        version = obj.document_version
        if not version:
            return ""
        return f"v{version.version_major}.{version.version_minor}"


class DocumentGenerationRequestSerializer(serializers.Serializer):
    generation_kind = serializers.ChoiceField(choices=DocumentGenerationRecord.GenerationKind.choices)
    title = serializers.CharField(max_length=255)
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    body = serializers.CharField(required=False, allow_blank=True, default="")
    template_code = serializers.CharField(required=False, allow_blank=True, max_length=120, default="")
    variables = serializers.JSONField(required=False, default=dict)

    project_code = serializers.CharField(required=False, allow_blank=True, max_length=10, default="")
    contract_value = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        default="0.00",
    )
    project = serializers.PrimaryKeyRelatedField(queryset=Document._meta.get_field("project").remote_field.model.objects.all(), required=False, allow_null=True, default=None)
    land = serializers.PrimaryKeyRelatedField(queryset=Document._meta.get_field("land").remote_field.model.objects.all(), required=False, allow_null=True, default=None)
    unit = serializers.PrimaryKeyRelatedField(queryset=Document._meta.get_field("unit").remote_field.model.objects.all(), required=False, allow_null=True, default=None)
    client = serializers.PrimaryKeyRelatedField(queryset=Document._meta.get_field("client").remote_field.model.objects.all(), required=False, allow_null=True, default=None)
    vendor = serializers.PrimaryKeyRelatedField(queryset=Document._meta.get_field("vendor").remote_field.model.objects.all(), required=False, allow_null=True, default=None)
    business_unit_division = serializers.PrimaryKeyRelatedField(
        queryset=Document._meta.get_field("business_unit_division").remote_field.model.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )
    business_unit_department = serializers.PrimaryKeyRelatedField(
        queryset=Document._meta.get_field("business_unit_department").remote_field.model.objects.all(),
        required=False,
        allow_null=True,
        default=None,
    )

    def validate(self, attrs):
        division = attrs.get("business_unit_division")
        department = attrs.get("business_unit_department")
        if department and division and department.division_id != division.id:
            raise serializers.ValidationError(
                {"business_unit_department": "Selected department does not belong to selected division."}
            )
        return attrs

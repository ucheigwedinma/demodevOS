from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from .models import (
    SupportAutomationRule,
    SupportAutomationRun,
    SupportCommunicationLog,
    SupportKnowledgeArticle,
    SupportSlaPolicy,
    SupportTicket,
    SupportTicketAttachment,
    SupportTicketComment,
)
from .sla import format_sla_target_hours, get_ticket_sla_targets, get_ticket_sla_timeline


def _user_display(user) -> str:
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


def _contact_display(contact) -> str:
    if not contact:
        return ""
    return getattr(contact, "display_name", "") or contact.email or contact.phone or ""


class SupportTicketAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketAttachment
        fields = [
            "id",
            "label",
            "file",
            "file_url",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj):
        return _user_display(obj.uploaded_by)

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url


class SupportTicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketComment
        fields = [
            "id",
            "comment_type",
            "body",
            "author",
            "author_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        return _user_display(obj.author)


class SupportTicketLinkedSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    contact_account_name = serializers.SerializerMethodField()
    assigned_agent_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    sla_breached = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_id",
            "subject",
            "requester_name",
            "customer_name",
            "contact_account_name",
            "department_name",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "assigned_agent_name",
            "created_at",
            "updated_at",
            "sla_deadline",
            "sla_breached",
        ]
        read_only_fields = fields

    def get_requester_name(self, obj):
        return _user_display(obj.requester)

    def get_contact_account_name(self, obj):
        return _contact_display(obj.contact_account)

    def get_assigned_agent_name(self, obj):
        return _user_display(obj.assigned_agent)

    def get_sla_breached(self, obj):
        return obj.is_sla_breached()


class SupportTicketListSerializer(serializers.ModelSerializer):
    requester_name = serializers.SerializerMethodField()
    requester_email = serializers.EmailField(source="requester.email", read_only=True, default="")
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True, default="")
    invoice_property_name = serializers.CharField(source="invoice.property.name", read_only=True, default="")
    contact_account_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    team_name = serializers.CharField(source="team.name", read_only=True, default="")
    team_emoji = serializers.CharField(source="team.emoji", read_only=True, default="")
    team_color = serializers.CharField(source="team.color", read_only=True, default="")
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    assigned_agent_name = serializers.SerializerMethodField()
    sla_breached = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_id",
            "subject",
            "description",
            "requester",
            "requester_name",
            "requester_email",
            "customer",
            "customer_name",
            "invoice",
            "invoice_number",
            "invoice_property_name",
            "contact_account",
            "contact_account_name",
            "department",
            "department_name",
            "team",
            "team_name",
            "team_emoji",
            "team_color",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "assigned_agent",
            "assigned_agent_name",
            "created_at",
            "updated_at",
            "sla_deadline",
            "first_response_at",
            "resolved_at",
            "closed_at",
            "escalated_at",
            "sla_breached",
        ]
        read_only_fields = fields

    def get_requester_name(self, obj):
        return _user_display(obj.requester)

    def get_contact_account_name(self, obj):
        return _contact_display(obj.contact_account)

    def get_assigned_agent_name(self, obj):
        return _user_display(obj.assigned_agent)

    def get_sla_breached(self, obj):
        return obj.is_sla_breached()


class SupportTicketDetailSerializer(SupportTicketListSerializer):
    internal_notes = serializers.SerializerMethodField()
    requester_replies = serializers.SerializerMethodField()
    attachments = SupportTicketAttachmentSerializer(many=True, read_only=True)
    linked_tickets = SupportTicketLinkedSerializer(many=True, read_only=True)

    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields + [
            "organization",
            "resolution_notes",
            "customer_satisfaction_score",
            "internal_notes",
            "requester_replies",
            "attachments",
            "linked_tickets",
        ]

    def get_internal_notes(self, obj):
        notes = obj.comments.filter(comment_type=SupportTicketComment.CommentType.INTERNAL_NOTE)
        return SupportTicketCommentSerializer(notes, many=True, context=self.context).data

    def get_requester_replies(self, obj):
        replies = obj.comments.filter(comment_type=SupportTicketComment.CommentType.REQUESTER_REPLY)
        return SupportTicketCommentSerializer(replies, many=True, context=self.context).data


class SupportTicketWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "subject",
            "description",
            "requester",
            "customer",
            "contact_account",
            "department",
            "invoice",
            "team",
            "category",
            "priority",
            "status",
            "assigned_agent",
            "sla_deadline",
            "resolution_notes",
            "customer_satisfaction_score",
        ]
        read_only_fields = ["id"]

    def _org(self):
        return self.context["request"].user.profile.organization

    def validate_requester(self, value):
        if value and getattr(value, "profile", None) and value.profile.organization_id != self._org().id:
            raise serializers.ValidationError("Requester must belong to your organization.")
        return value

    def validate_customer(self, value):
        if value and value.organization_id != self._org().id:
            raise serializers.ValidationError("Customer must belong to your organization.")
        return value

    def validate_contact_account(self, value):
        if value and value.organization_id != self._org().id:
            raise serializers.ValidationError("Contact account must belong to your organization.")
        return value

    def validate_invoice(self, value):
        if value and value.organization_id != self._org().id:
            raise serializers.ValidationError("Invoice must belong to your organization.")
        return value

    def validate_assigned_agent(self, value):
        if value and getattr(value, "profile", None) and value.profile.organization_id != self._org().id:
            raise serializers.ValidationError("Assigned agent must belong to your organization.")
        return value

    def validate_department(self, value):
        if value and value.division.organization_id != self._org().id:
            raise serializers.ValidationError("Department must belong to your organization.")
        return value

    def _requester_phones(self, requester) -> list[str]:
        phones: list[str] = []
        profile = getattr(requester, "profile", None)
        for value in [
            getattr(profile, "phone", ""),
            getattr(profile, "secondary_phone", ""),
        ]:
            normalized = str(value or "").strip()
            if normalized:
                phones.append(normalized)
        return phones

    def _resolve_customer_from_requester(self, requester):
        if requester is None:
            return None

        from apps.finance.models import Customer

        org = self._org()
        email = str(getattr(requester, "email", "") or "").strip()
        if email:
            customer = Customer.objects.filter(
                organization=org,
                email__iexact=email,
            ).first()
            if customer:
                return customer

        for phone in self._requester_phones(requester):
            customer = Customer.objects.filter(
                organization=org,
                phone=phone,
            ).first()
            if customer:
                return customer
        return None

    def _resolve_contact_account_from_requester(self, requester, *, customer=None):
        from apps.crm.models import ContactAccount

        queryset = ContactAccount.objects.filter(
            organization=self._org(),
            is_active=True,
        )
        if customer is not None:
            contact = queryset.filter(finance_customer=customer).order_by("-updated_at", "-id").first()
            if contact:
                return contact

        if requester is None:
            return None

        email = str(getattr(requester, "email", "") or "").strip()
        if email:
            contact = queryset.filter(email__iexact=email).order_by("-updated_at", "-id").first()
            if contact:
                return contact

        for phone in self._requester_phones(requester):
            contact = queryset.filter(phone=phone).order_by("-updated_at", "-id").first()
            if contact:
                return contact
        return None

    def validate(self, attrs):
        if not attrs.get("requester") and self.instance is None:
            attrs["requester"] = self.context["request"].user

        requester = attrs.get("requester") or getattr(self.instance, "requester", None)
        if not attrs.get("department") and requester and getattr(requester, "profile", None):
            attrs["department"] = requester.profile.department

        category = attrs.get("category") or getattr(self.instance, "category", SupportTicket.Category.OTHER)
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        contact_account = attrs.get("contact_account", getattr(self.instance, "contact_account", None))
        invoice = attrs.get("invoice", getattr(self.instance, "invoice", None))

        if invoice is not None:
            if customer is None:
                customer = invoice.customer
                attrs["customer"] = customer
            elif invoice.customer_id and customer.id != invoice.customer_id:
                raise serializers.ValidationError(
                    {"customer": "Selected customer does not match the selected invoice."}
                )

        if contact_account and customer and contact_account.finance_customer_id and contact_account.finance_customer_id != customer.id:
            raise serializers.ValidationError(
                {"contact_account": "Selected contact account does not belong to selected customer."}
            )

        if customer is None and contact_account and contact_account.finance_customer_id:
            customer = contact_account.finance_customer
            attrs["customer"] = customer

        if category == SupportTicket.Category.COMPLAINT:
            if customer is None:
                customer = self._resolve_customer_from_requester(requester)
                if customer is not None:
                    attrs["customer"] = customer

            if contact_account is None:
                contact_account = self._resolve_contact_account_from_requester(
                    requester,
                    customer=customer,
                )
                if contact_account is not None:
                    attrs["contact_account"] = contact_account

            if customer is None:
                raise serializers.ValidationError(
                    {"customer": "Complaint tickets must be linked to a customer profile."}
                )
            if not customer.support_ticketing_enabled:
                raise serializers.ValidationError(
                    {
                        "customer": (
                            "Support ticketing is not enabled for this customer profile. "
                            "Complete customer onboarding first."
                        )
                    }
                )

        if category == SupportTicket.Category.BILLING and invoice is None:
            raise serializers.ValidationError(
                {"invoice": "Billing tickets must be linked to an invoice."}
            )

        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self._org()
        ticket = super().create(validated_data)
        return ticket

    def update(self, instance, validated_data):
        previous_priority = instance.priority
        ticket = super().update(instance, validated_data)
        if "priority" in validated_data and ticket.priority != previous_priority:
            ticket.sla_deadline = ticket.computed_sla_deadline()
            ticket.save(update_fields=["sla_deadline", "updated_at"])
        return ticket


class SupportRequestWriteSerializer(SupportTicketWriteSerializer):
    """
    Support request write contract.

    Requests are persisted as SupportTicket rows with category fixed to "request".
    """

    def validate_category(self, value):
        if value != SupportTicket.Category.REQUEST:
            raise serializers.ValidationError("Support requests must use the Request category.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs["category"] = SupportTicket.Category.REQUEST
        return attrs


class SupportTicketAssignSerializer(serializers.Serializer):
    assigned_agent_id = serializers.IntegerField()


class SupportTicketPrioritySerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=SupportTicket.Priority.choices)


class SupportTicketInternalNoteSerializer(serializers.Serializer):
    body = serializers.CharField()


class SupportTicketReplySerializer(serializers.Serializer):
    body = serializers.CharField()


class SupportTicketLinkSerializer(serializers.Serializer):
    related_ticket_id = serializers.IntegerField(required=False)
    related_ticket_ref = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        if not attrs.get("related_ticket_id") and not attrs.get("related_ticket_ref"):
            raise serializers.ValidationError("Provide either related_ticket_id or related_ticket_ref.")
        return attrs


class SupportTicketEscalateSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, required=False, default="")


class SupportTicketCloseSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(allow_blank=True, required=False, default="")
    customer_satisfaction_score = serializers.IntegerField(required=False, min_value=1, max_value=5)


class SupportTicketAttachmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicketAttachment
        fields = [
            "id",
            "label",
            "file",
        ]
        read_only_fields = ["id"]

    def validate_file(self, value):
        from config.upload_validators import validate_upload
        return validate_upload(value, kind="any")


class SupportDeskBreakdownSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()


class SupportDeskAgentWorkloadSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField()
    active_tickets = serializers.IntegerField()
    sla_breaches = serializers.IntegerField()


class SupportDeskOverviewSerializer(serializers.Serializer):
    open_tickets = serializers.IntegerField()
    tickets_by_priority = SupportDeskBreakdownSerializer(many=True)
    tickets_by_status = SupportDeskBreakdownSerializer(many=True)
    sla_breaches = serializers.IntegerField()
    average_resolution_time_hours = serializers.FloatField(allow_null=True)
    average_resolution_time_display = serializers.CharField()
    agent_workload = SupportDeskAgentWorkloadSerializer(many=True)
    recent_requests = SupportTicketListSerializer(many=True)
    first_response_time_hours = serializers.FloatField(allow_null=True)
    first_response_time_display = serializers.CharField()
    ticket_backlog = serializers.IntegerField()
    escalated_tickets = serializers.IntegerField()
    customer_satisfaction_score = serializers.FloatField(allow_null=True)
    customer_satisfaction_display = serializers.CharField()


class SupportDeskLookupUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)


class SupportDeskLookupDepartmentSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class SupportDeskLookupCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    support_ticketing_enabled = serializers.BooleanField()


class SupportDeskLookupContactAccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    email = serializers.EmailField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    finance_customer = serializers.IntegerField(allow_null=True)
    support_ticketing_enabled = serializers.BooleanField()


class SupportDeskTicketLookupsSerializer(serializers.Serializer):
    requesters = SupportDeskLookupUserSerializer(many=True)
    agents = SupportDeskLookupUserSerializer(many=True)
    departments = SupportDeskLookupDepartmentSerializer(many=True)
    customers = SupportDeskLookupCustomerSerializer(many=True)
    contact_accounts = SupportDeskLookupContactAccountSerializer(many=True)
    categories = SupportDeskBreakdownSerializer(many=True)
    priorities = SupportDeskBreakdownSerializer(many=True)
    statuses = SupportDeskBreakdownSerializer(many=True)


class SupportKnowledgeArticleListSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    visibility_display = serializers.CharField(source="get_visibility_display", read_only=True)

    class Meta:
        model = SupportKnowledgeArticle
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "category",
            "status",
            "status_display",
            "visibility",
            "visibility_display",
            "owner",
            "owner_name",
            "reviewer",
            "reviewer_name",
            "published_at",
            "last_reviewed_at",
            "next_review_due_at",
            "view_count",
            "helpful_votes",
            "not_helpful_votes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_name(self, obj):
        return _user_display(obj.owner)

    def get_reviewer_name(self, obj):
        return _user_display(obj.reviewer)


class SupportKnowledgeArticleDetailSerializer(SupportKnowledgeArticleListSerializer):
    class Meta(SupportKnowledgeArticleListSerializer.Meta):
        fields = SupportKnowledgeArticleListSerializer.Meta.fields + [
            "organization",
            "body",
        ]


class SupportKnowledgeArticleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportKnowledgeArticle
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "body",
            "category",
            "status",
            "visibility",
            "owner",
            "reviewer",
            "next_review_due_at",
        ]
        read_only_fields = ["id"]

    def _org(self):
        return self.context["request"].user.profile.organization

    def _validate_user_org(self, value, field_label: str):
        if value and getattr(value, "profile", None) and value.profile.organization_id != self._org().id:
            raise serializers.ValidationError(f"{field_label} must belong to your organization.")
        return value

    def validate_owner(self, value):
        return self._validate_user_org(value, "Owner")

    def validate_reviewer(self, value):
        return self._validate_user_org(value, "Reviewer")

    def create(self, validated_data):
        if not validated_data.get("owner"):
            validated_data["owner"] = self.context["request"].user
        validated_data["organization"] = self._org()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        previous_status = instance.status
        article = super().update(instance, validated_data)
        if article.status == SupportKnowledgeArticle.Status.PUBLISHED and previous_status != SupportKnowledgeArticle.Status.PUBLISHED:
            article.published_at = article.published_at or timezone.now()
            article.save(update_fields=["published_at", "updated_at"])
        return article


class SupportKnowledgeArticleFeedbackSerializer(serializers.Serializer):
    helpful = serializers.BooleanField()


class SupportKnowledgeBaseOverviewSerializer(serializers.Serializer):
    total_articles = serializers.IntegerField()
    published_articles = serializers.IntegerField()
    in_review_articles = serializers.IntegerField()
    draft_articles = serializers.IntegerField()
    archived_articles = serializers.IntegerField()
    due_for_review_count = serializers.IntegerField()
    total_views = serializers.IntegerField()
    helpful_feedback_ratio = serializers.FloatField(allow_null=True)
    top_articles = SupportKnowledgeArticleListSerializer(many=True)


class SupportSlaPolicySerializer(serializers.ModelSerializer):
    category_display = serializers.SerializerMethodField()
    priority_display = serializers.SerializerMethodField()
    response_target_display = serializers.SerializerMethodField()
    resolution_target_display = serializers.SerializerMethodField()

    class Meta:
        model = SupportSlaPolicy
        fields = [
            "id",
            "name",
            "description",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "response_target_hours",
            "response_target_display",
            "resolution_target_hours",
            "resolution_target_display",
            "escalate_after_hours",
            "escalation_path",
            "agent_notify_threshold_percent",
            "manager_notify_threshold_percent",
            "breach_escalation_role",
            "notify_assigned_agent",
            "notify_manager",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_category_display(self, obj):
        return dict(SupportTicket.Category.choices).get(obj.category, "All")

    def get_priority_display(self, obj):
        return dict(SupportTicket.Priority.choices).get(obj.priority, "All")

    def get_response_target_display(self, obj):
        return format_sla_target_hours(obj.response_target_hours)

    def get_resolution_target_display(self, obj):
        return format_sla_target_hours(obj.resolution_target_hours)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        instance = getattr(self, "instance", None)
        agent_threshold = attrs.get(
            "agent_notify_threshold_percent",
            getattr(instance, "agent_notify_threshold_percent", 50),
        )
        manager_threshold = attrs.get(
            "manager_notify_threshold_percent",
            getattr(instance, "manager_notify_threshold_percent", 80),
        )

        if manager_threshold <= agent_threshold:
            raise serializers.ValidationError(
                {
                    "manager_notify_threshold_percent": (
                        "Manager threshold must be greater than agent threshold."
                    )
                }
            )

        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.profile.organization
        return super().create(validated_data)


class SupportSlaEscalationTicketSerializer(SupportTicketListSerializer):
    overdue_hours = serializers.SerializerMethodField()
    policy_name = serializers.SerializerMethodField()
    first_response_deadline = serializers.SerializerMethodField()
    resolution_deadline = serializers.SerializerMethodField()
    first_response_progress_percent = serializers.SerializerMethodField()
    resolution_progress_percent = serializers.SerializerMethodField()
    first_response_breached = serializers.SerializerMethodField()
    resolution_breached = serializers.SerializerMethodField()
    first_response_target_display = serializers.SerializerMethodField()
    resolution_target_display = serializers.SerializerMethodField()
    escalation_stage = serializers.SerializerMethodField()

    class Meta(SupportTicketListSerializer.Meta):
        fields = SupportTicketListSerializer.Meta.fields + [
            "overdue_hours",
            "policy_name",
            "first_response_deadline",
            "resolution_deadline",
            "first_response_progress_percent",
            "resolution_progress_percent",
            "first_response_breached",
            "resolution_breached",
            "first_response_target_display",
            "resolution_target_display",
            "escalation_stage",
        ]

    def _sla_cache(self):
        return self.context.setdefault("_support_sla_cache", {})

    def _sla_payload(self, obj):
        cache = self._sla_cache()
        if obj.pk in cache:
            return cache[obj.pk]

        now = self.context.get("now")
        targets = get_ticket_sla_targets(obj)
        timeline = get_ticket_sla_timeline(obj, now=now, targets=targets)
        payload = {"targets": targets, "timeline": timeline}
        cache[obj.pk] = payload
        return payload

    def get_overdue_hours(self, obj):
        timeline = self._sla_payload(obj)["timeline"]
        deadline = timeline["resolution_deadline_at"]
        if not deadline:
            return None
        delta = self.context.get("now") - deadline if self.context.get("now") else None
        if delta is None:
            return None
        hours = delta.total_seconds() / 3600
        return round(hours, 2) if hours > 0 else 0.0

    def get_policy_name(self, obj):
        policy = self._sla_payload(obj)["targets"]["policy"]
        return policy.name if policy else ""

    def get_first_response_deadline(self, obj):
        return self._sla_payload(obj)["timeline"]["response_deadline_at"]

    def get_resolution_deadline(self, obj):
        return self._sla_payload(obj)["timeline"]["resolution_deadline_at"]

    def get_first_response_progress_percent(self, obj):
        return self._sla_payload(obj)["timeline"]["response_progress_percent"]

    def get_resolution_progress_percent(self, obj):
        return self._sla_payload(obj)["timeline"]["resolution_progress_percent"]

    def get_first_response_breached(self, obj):
        return self._sla_payload(obj)["timeline"]["first_response_breached"]

    def get_resolution_breached(self, obj):
        return self._sla_payload(obj)["timeline"]["resolution_breached"]

    def get_first_response_target_display(self, obj):
        return format_sla_target_hours(self._sla_payload(obj)["targets"]["response_hours"])

    def get_resolution_target_display(self, obj):
        return format_sla_target_hours(self._sla_payload(obj)["targets"]["resolution_hours"])

    def get_escalation_stage(self, obj):
        payload = self._sla_payload(obj)
        timeline = payload["timeline"]
        policy = payload["targets"]["policy"]

        if timeline["resolution_breached"]:
            return "breached"
        if obj.status == SupportTicket.Status.ESCALATED:
            return "escalated"

        agent_threshold = (
            policy.agent_notify_threshold_percent if policy else 50
        )
        manager_threshold = (
            policy.manager_notify_threshold_percent if policy else 80
        )
        progress = timeline["resolution_progress_percent"]

        if progress >= manager_threshold:
            return "manager_warning"
        if progress >= agent_threshold:
            return "agent_warning"
        return "on_track"


class SupportSlaPolicyMatrixItemSerializer(serializers.Serializer):
    priority = serializers.CharField()
    priority_label = serializers.CharField()
    policy_name = serializers.CharField()
    first_response_target_display = serializers.CharField()
    resolution_target_display = serializers.CharField()
    agent_notify_threshold_percent = serializers.IntegerField()
    manager_notify_threshold_percent = serializers.IntegerField()
    breach_escalation_role = serializers.CharField()


class SupportSlaEscalationsOverviewSerializer(serializers.Serializer):
    active_policy_count = serializers.IntegerField()
    active_ticket_count = serializers.IntegerField()
    breached_ticket_count = serializers.IntegerField()
    escalated_ticket_count = serializers.IntegerField()
    upcoming_deadline_count = serializers.IntegerField()
    warning_50_count = serializers.IntegerField()
    warning_80_count = serializers.IntegerField()
    average_overdue_hours = serializers.FloatField(allow_null=True)
    max_overdue_hours = serializers.FloatField(allow_null=True)
    breaches_by_priority = SupportDeskBreakdownSerializer(many=True)
    policy_matrix = SupportSlaPolicyMatrixItemSerializer(many=True)
    top_breached_tickets = SupportSlaEscalationTicketSerializer(many=True)
    recent_escalations = SupportTicketListSerializer(many=True)


class SupportCommunicationLogListSerializer(serializers.ModelSerializer):
    ticket_ref = serializers.CharField(source="ticket.ticket_id", read_only=True, default="")
    ticket_subject = serializers.CharField(source="ticket.subject", read_only=True, default="")
    author_name = serializers.SerializerMethodField()
    interaction_type_display = serializers.CharField(source="get_interaction_type_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    message_preview = serializers.SerializerMethodField()

    class Meta:
        model = SupportCommunicationLog
        fields = [
            "id",
            "ticket",
            "ticket_ref",
            "ticket_subject",
            "author",
            "author_name",
            "interaction_type",
            "interaction_type_display",
            "direction",
            "direction_display",
            "channel",
            "channel_display",
            "subject",
            "message_preview",
            "participants",
            "call_duration_seconds",
            "external_message_id",
            "happened_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        return _user_display(obj.author)

    def get_message_preview(self, obj):
        source = (obj.message or "").strip() or (obj.transcript or "").strip() or obj.subject
        if len(source) <= 160:
            return source
        return f"{source[:157]}..."


class SupportCommunicationLogDetailSerializer(SupportCommunicationLogListSerializer):
    class Meta(SupportCommunicationLogListSerializer.Meta):
        fields = SupportCommunicationLogListSerializer.Meta.fields + [
            "message",
            "transcript",
            "metadata",
            "updated_at",
        ]


class SupportCommunicationLogWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportCommunicationLog
        fields = [
            "id",
            "ticket",
            "interaction_type",
            "direction",
            "channel",
            "subject",
            "message",
            "transcript",
            "participants",
            "call_duration_seconds",
            "external_message_id",
            "metadata",
            "happened_at",
        ]
        read_only_fields = ["id"]

    def _org(self):
        return self.context["request"].user.profile.organization

    def _default_channel(self, interaction_type: str) -> str:
        defaults = {
            SupportCommunicationLog.InteractionType.INTERNAL_NOTE: SupportCommunicationLog.Channel.PORTAL,
            SupportCommunicationLog.InteractionType.TICKET_CONVERSATION: SupportCommunicationLog.Channel.PORTAL,
            SupportCommunicationLog.InteractionType.EMAIL_REPLY: SupportCommunicationLog.Channel.EMAIL,
            SupportCommunicationLog.InteractionType.CHAT_TRANSCRIPT: SupportCommunicationLog.Channel.CHAT,
            SupportCommunicationLog.InteractionType.CALL_LOG: SupportCommunicationLog.Channel.PHONE,
            SupportCommunicationLog.InteractionType.WHATSAPP: SupportCommunicationLog.Channel.WHATSAPP,
        }
        return defaults.get(interaction_type, SupportCommunicationLog.Channel.OTHER)

    def _default_direction(self, interaction_type: str) -> str:
        if interaction_type == SupportCommunicationLog.InteractionType.INTERNAL_NOTE:
            return SupportCommunicationLog.Direction.INTERNAL
        return SupportCommunicationLog.Direction.OUTBOUND

    def validate_ticket(self, value):
        if value and value.organization_id != self._org().id:
            raise serializers.ValidationError("Ticket must belong to your organization.")
        return value

    def validate_participants(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Participants must be a list.")

        normalized: list[str] = []
        for participant in value:
            text = str(participant).strip()
            if text:
                normalized.append(text)
        return normalized[:40]

    def validate_metadata(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be an object.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        interaction_type = attrs.get(
            "interaction_type",
            getattr(self.instance, "interaction_type", SupportCommunicationLog.InteractionType.TICKET_CONVERSATION),
        )
        attrs.setdefault("channel", self._default_channel(interaction_type))
        attrs.setdefault("direction", self._default_direction(interaction_type))
        attrs.setdefault("metadata", {})

        message = attrs.get("message", getattr(self.instance, "message", "")).strip()
        transcript = attrs.get("transcript", getattr(self.instance, "transcript", "")).strip()
        if not message and not transcript:
            raise serializers.ValidationError(
                {"message": "Provide message or transcript content."}
            )

        call_duration = attrs.get(
            "call_duration_seconds",
            getattr(self.instance, "call_duration_seconds", None),
        )
        if interaction_type == SupportCommunicationLog.InteractionType.CALL_LOG and not call_duration:
            raise serializers.ValidationError(
                {"call_duration_seconds": "Call logs require call duration in seconds."}
            )

        if (
            interaction_type == SupportCommunicationLog.InteractionType.INTERNAL_NOTE
            and attrs.get("direction") != SupportCommunicationLog.Direction.INTERNAL
        ):
            raise serializers.ValidationError(
                {"direction": "Internal notes must use internal direction."}
            )

        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self._org()
        validated_data.setdefault("author", self.context["request"].user)
        validated_data.setdefault("participants", [])
        validated_data.setdefault("metadata", {})
        return super().create(validated_data)


class SupportCommunicationWhatsAppSendSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, default="")
    ticket_id = serializers.IntegerField(required=False)
    recipient_phone = serializers.CharField(max_length=40)
    message = serializers.CharField()
    external_message_id = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.JSONField(required=False)

    def _org(self):
        return self.context["request"].user.profile.organization

    def validate_ticket_id(self, value):
        if not SupportTicket.objects.filter(
            id=value,
            organization=self._org(),
        ).exists():
            raise serializers.ValidationError("Ticket was not found in your organization.")
        return value

    def validate_recipient_phone(self, value):
        phone = value.strip()
        if not phone:
            raise serializers.ValidationError("Recipient phone is required.")
        return phone

    def validate_provider(self, value):
        return value.strip().lower()

    def validate_metadata(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be an object.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        ticket_id = attrs.get("ticket_id")
        if ticket_id:
            attrs["ticket"] = SupportTicket.objects.filter(
                id=ticket_id,
                organization=self._org(),
            ).first()
        else:
            attrs["ticket"] = None
        attrs.setdefault("metadata", {})
        return attrs


class SupportCommunicationOverviewSerializer(serializers.Serializer):
    total_interactions = serializers.IntegerField()
    ticket_conversations_count = serializers.IntegerField()
    internal_notes_count = serializers.IntegerField()
    email_replies_count = serializers.IntegerField()
    chat_transcripts_count = serializers.IntegerField()
    call_logs_count = serializers.IntegerField()
    whatsapp_messages_count = serializers.IntegerField()
    inbound_count = serializers.IntegerField()
    outbound_count = serializers.IntegerField()
    internal_count = serializers.IntegerField()
    interactions_by_channel = SupportDeskBreakdownSerializer(many=True)
    recent_logs = SupportCommunicationLogListSerializer(many=True)


class SupportAutomationRuleSerializer(serializers.ModelSerializer):
    trigger_type_display = serializers.CharField(source="get_trigger_type_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportAutomationRule
        fields = [
            "id",
            "name",
            "description",
            "trigger_type",
            "trigger_type_display",
            "conditions",
            "actions",
            "priority",
            "run_once_per_ticket",
            "is_active",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at", "updated_at"]

    def get_created_by_name(self, obj):
        return _user_display(obj.created_by)

    def validate_conditions(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Conditions must be an object.")
        return value

    def validate_actions(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Actions must be an object.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        conditions = attrs.get("conditions", getattr(self.instance, "conditions", {})) or {}
        actions = attrs.get("actions", getattr(self.instance, "actions", {})) or {}
        trigger_type = attrs.get("trigger_type", getattr(self.instance, "trigger_type", ""))

        if trigger_type == SupportAutomationRule.TriggerType.STATUS_CHANGED and not conditions.get("status_changed_to"):
            raise serializers.ValidationError(
                {"conditions": "status_changed_to is required for status change trigger rules."}
            )

        if not actions:
            raise serializers.ValidationError({"actions": "At least one automation action is required."})

        org = self.context["request"].user.profile.organization
        assign_department_id = actions.get("assign_department_id")
        if assign_department_id:
            from apps.settings.models import Department

            if not Department.objects.filter(
                id=assign_department_id,
                division__organization=org,
                is_active=True,
            ).exists():
                raise serializers.ValidationError(
                    {"actions": "assign_department_id must reference an active department in your organization."}
                )

        assign_agent_id = actions.get("assign_agent_id")
        if assign_agent_id:
            User = self.context["request"].user.__class__
            if not User.objects.filter(
                id=assign_agent_id,
                profile__organization=org,
                profile__user_status="active",
            ).exists():
                raise serializers.ValidationError(
                    {"actions": "assign_agent_id must reference an active user in your organization."}
                )

        set_priority = actions.get("set_priority")
        if set_priority and set_priority not in dict(SupportTicket.Priority.choices):
            raise serializers.ValidationError(
                {"actions": "set_priority must be one of support ticket priorities."}
            )

        set_status = actions.get("set_status")
        if set_status and set_status not in dict(SupportTicket.Status.choices):
            raise serializers.ValidationError(
                {"actions": "set_status must be one of support ticket statuses."}
            )

        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.profile.organization
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class SupportAutomationRunSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True, default="")
    ticket_ref = serializers.CharField(source="ticket.ticket_id", read_only=True, default="")
    ticket_subject = serializers.CharField(source="ticket.subject", read_only=True, default="")
    trigger_type_display = serializers.CharField(source="get_trigger_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SupportAutomationRun
        fields = [
            "id",
            "rule",
            "rule_name",
            "ticket",
            "ticket_ref",
            "ticket_subject",
            "trigger_type",
            "trigger_type_display",
            "status",
            "status_display",
            "summary",
            "details",
            "created_at",
        ]
        read_only_fields = fields


class SupportAutomationOverviewSerializer(serializers.Serializer):
    active_rule_count = serializers.IntegerField()
    total_rule_count = serializers.IntegerField()
    recent_run_count = serializers.IntegerField()
    last_run_at = serializers.DateTimeField(allow_null=True)
    runs_by_status = SupportDeskBreakdownSerializer(many=True)
    runs_by_trigger = SupportDeskBreakdownSerializer(many=True)
    recent_runs = SupportAutomationRunSerializer(many=True)


class SupportDeskStandardReportSerializer(serializers.Serializer):
    key = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()


class SupportDeskTicketTrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    created_count = serializers.IntegerField()
    resolved_count = serializers.IntegerField()


class SupportDeskResolutionTrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    resolved_count = serializers.IntegerField()
    average_resolution_hours = serializers.FloatField(allow_null=True)
    average_resolution_display = serializers.CharField()


class SupportDeskSlaTrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    compliant_count = serializers.IntegerField()
    breached_count = serializers.IntegerField()
    compliance_rate = serializers.FloatField()


class SupportDeskAgentPerformanceSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField()
    agent_name = serializers.CharField()
    total_tickets = serializers.IntegerField()
    resolved_tickets = serializers.IntegerField()
    sla_breaches = serializers.IntegerField()
    average_resolution_hours = serializers.FloatField(allow_null=True)
    average_resolution_display = serializers.CharField()
    customer_satisfaction_score = serializers.FloatField(allow_null=True)
    customer_satisfaction_display = serializers.CharField()


class SupportDeskSlaComplianceSerializer(serializers.Serializer):
    compliant_count = serializers.IntegerField()
    breached_count = serializers.IntegerField()
    compliance_rate = serializers.FloatField()


class SupportDeskEscalationRateSerializer(serializers.Serializer):
    escalated_count = serializers.IntegerField()
    total_tickets = serializers.IntegerField()
    escalation_rate = serializers.FloatField()


class SupportDeskCustomerSatisfactionSerializer(serializers.Serializer):
    average_score = serializers.FloatField(allow_null=True)
    response_count = serializers.IntegerField()
    display = serializers.CharField()


class SupportDeskReportsOverviewSerializer(serializers.Serializer):
    window_start = serializers.DateField()
    window_end = serializers.DateField()
    total_tickets = serializers.IntegerField()
    standard_reports = SupportDeskStandardReportSerializer(many=True)
    tickets_by_department = SupportDeskBreakdownSerializer(many=True)
    tickets_by_category = SupportDeskBreakdownSerializer(many=True)
    resolution_time_average_hours = serializers.FloatField(allow_null=True)
    resolution_time_average_display = serializers.CharField()
    agent_performance = SupportDeskAgentPerformanceSerializer(many=True)
    sla_compliance = SupportDeskSlaComplianceSerializer()
    escalation_rate = SupportDeskEscalationRateSerializer()
    customer_satisfaction = SupportDeskCustomerSatisfactionSerializer()
    ticket_trend = SupportDeskTicketTrendPointSerializer(many=True)
    resolution_trend = SupportDeskResolutionTrendPointSerializer(many=True)
    sla_performance_trend = SupportDeskSlaTrendPointSerializer(many=True)


class SupportDeskConfigurationTeamSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    head_name = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()


class SupportDeskConfigurationRoleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    user_count = serializers.IntegerField()


class SupportDeskConfigurationRequestTypeSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    approval_required = serializers.BooleanField()
    sla_target_hours = serializers.IntegerField()
    is_active = serializers.BooleanField()


class SupportDeskConfigurationEmailTemplateSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    event_key = serializers.CharField()
    severity_tier = serializers.CharField()
    is_active = serializers.BooleanField()
    updated_at = serializers.DateTimeField()


class SupportDeskConfigurationNotificationRuleSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    default_channels = serializers.ListField(child=serializers.CharField(), default=list)
    configured_channels = serializers.ListField(child=serializers.CharField(), default=list)
    active_channels = serializers.ListField(child=serializers.CharField(), default=list)
    total_templates = serializers.IntegerField()
    active_templates = serializers.IntegerField()
    is_enabled = serializers.BooleanField()


class SupportDeskConfigurationChannelSettingsSerializer(serializers.Serializer):
    email_enabled = serializers.BooleanField()
    in_app_enabled = serializers.BooleanField()
    sms_enabled = serializers.BooleanField()
    push_enabled = serializers.BooleanField()


class SupportDeskConfigurationOverviewSerializer(serializers.Serializer):
    ticket_categories = SupportDeskBreakdownSerializer(many=True)
    priority_levels = SupportDeskBreakdownSerializer(many=True)
    ticket_statuses = SupportDeskBreakdownSerializer(many=True)
    support_teams = SupportDeskConfigurationTeamSerializer(many=True)
    agent_roles = SupportDeskConfigurationRoleSerializer(many=True)
    sla_policies = SupportSlaPolicySerializer(many=True)
    automation_rules = SupportAutomationRuleSerializer(many=True)
    request_types = SupportDeskConfigurationRequestTypeSerializer(many=True)
    email_templates = SupportDeskConfigurationEmailTemplateSerializer(many=True)
    notification_rules = SupportDeskConfigurationNotificationRuleSerializer(many=True)
    channel_settings = SupportDeskConfigurationChannelSettingsSerializer()

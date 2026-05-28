from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.finance.models import Invoice, PaymentMethod
from apps.properties.models import ServiceRequest
from apps.support_desk.models import SupportTicket

from .service_request_workflows import (
    ACTIVE_SERVICE_REQUEST_STATUSES,
    service_request_sla_hours_for,
    service_request_sla_status_for,
)


def _resolve_request_org(request):
    org = getattr(request, "organization", None)
    if org is not None:
        return org
    profile = getattr(getattr(request, "user", None), "profile", None)
    return getattr(profile, "organization", None)


def _user_display(user) -> str:
    if not user:
        return ""
    full_name = user.get_full_name().strip()
    return full_name or user.email or user.username


class FacilityServiceRequestListSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    facility_code = serializers.CharField(source="facility.facility_code", read_only=True, default="")
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default="")
    requester_name = serializers.SerializerMethodField()
    assigned_agent_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_channel_display = serializers.CharField(source="get_source_channel_display", read_only=True)
    location_label = serializers.SerializerMethodField()
    sla_status = serializers.SerializerMethodField()
    work_order_status = serializers.CharField(source="work_order.status", read_only=True, default="")

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "property",
            "property_name",
            "facility",
            "facility_code",
            "facility_space",
            "unit",
            "unit_number",
            "title",
            "description",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "source_channel",
            "source_channel_display",
            "requester",
            "requester_name",
            "requested_by",
            "assigned_agent",
            "assigned_agent_name",
            "assigned_to",
            "requested_date",
            "first_response_at",
            "sla_target_hours",
            "sla_due_at",
            "sla_status",
            "escalated_at",
            "resolved_date",
            "feedback_rating",
            "location_label",
            "work_order",
            "work_order_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_requester_name(self, obj):
        return _user_display(obj.requester)

    def get_assigned_agent_name(self, obj):
        return _user_display(obj.assigned_agent)

    def get_location_label(self, obj):
        if obj.facility_space_id:
            return obj.facility_space.space_label or obj.facility_space.unit.unit_number
        if obj.unit_id:
            return obj.unit.unit_number
        return ""

    def get_sla_status(self, obj):
        return service_request_sla_status_for(obj)


class FacilityServiceRequestDetailSerializer(FacilityServiceRequestListSerializer):
    class Meta(FacilityServiceRequestListSerializer.Meta):
        fields = FacilityServiceRequestListSerializer.Meta.fields + [
            "resolution_notes",
            "feedback_comment",
            "feedback_submitted_at",
            "notes",
        ]


class FacilityServiceRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "property",
            "facility",
            "facility_space",
            "unit",
            "title",
            "description",
            "category",
            "priority",
            "status",
            "requester",
            "requested_by",
            "source_channel",
            "assigned_agent",
            "assigned_to",
            "sla_target_hours",
            "sla_due_at",
            "resolved_date",
            "resolution_notes",
            "work_order",
            "notes",
        ]
        read_only_fields = ["id", "work_order"]
        extra_kwargs = {
            "property": {"required": False, "allow_null": True},
            "facility": {"required": False, "allow_null": True},
            "facility_space": {"required": False, "allow_null": True},
            "unit": {"required": False, "allow_null": True},
            "requester": {"required": False, "allow_null": True},
            "requested_by": {"required": False, "allow_blank": True},
            "assigned_agent": {"required": False, "allow_null": True},
            "assigned_to": {"required": False, "allow_blank": True},
            "sla_target_hours": {"required": False, "allow_null": True},
            "sla_due_at": {"required": False, "allow_null": True},
            "resolved_date": {"required": False, "allow_null": True},
            "resolution_notes": {"required": False, "allow_blank": True},
            "notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_org_owned(self, value, label: str):
        org = self._org()
        if value is None or org is None:
            return value
        if getattr(value, "organization_id", None) != org.id:
            raise serializers.ValidationError(f"Selected {label} is not in your organization.")
        return value

    def validate_property(self, value):
        return self._validate_org_owned(value, "property")

    def validate_facility(self, value):
        return self._validate_org_owned(value, "facility")

    def validate_facility_space(self, value):
        return self._validate_org_owned(value, "facility space")

    def validate_unit(self, value):
        return self._validate_org_owned(value, "unit")

    def validate_requester(self, value):
        org = self._org()
        if value and org and getattr(value, "profile", None) and value.profile.organization_id != org.id:
            raise serializers.ValidationError("Requester must belong to your organization.")
        return value

    def validate_assigned_agent(self, value):
        org = self._org()
        if value and org and getattr(value, "profile", None) and value.profile.organization_id != org.id:
            raise serializers.ValidationError("Assigned agent must belong to your organization.")
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        now = timezone.now()

        facility_space = attrs.get("facility_space", getattr(instance, "facility_space", None))
        facility = attrs.get("facility", getattr(instance, "facility", None))
        property_obj = attrs.get("property", getattr(instance, "property", None))
        unit = attrs.get("unit", getattr(instance, "unit", None))

        if facility_space is not None:
            attrs["facility"] = facility_space.facility
            attrs["unit"] = facility_space.unit
            attrs["property"] = facility_space.facility.property
            facility = facility_space.facility
            property_obj = facility_space.facility.property
            unit = facility_space.unit
        elif facility is not None:
            attrs["property"] = facility.property
            property_obj = facility.property
        elif property_obj is None and unit is not None:
            attrs["property"] = unit.property
            property_obj = unit.property

        if facility is None:
            raise serializers.ValidationError(
                {"facility": "Facility or mapped room / space is required for internal service requests."}
            )
        if property_obj is None:
            raise serializers.ValidationError({"property": "Property is required when no facility or facility space is selected."})
        if unit is not None and unit.property_id != property_obj.id:
            raise serializers.ValidationError({"unit": "Selected unit does not belong to the selected property."})
        if facility is not None and facility.property_id != property_obj.id:
            raise serializers.ValidationError({"facility": "Selected facility does not belong to the selected property."})
        if facility_space is not None and facility is not None and facility_space.facility_id != facility.id:
            raise serializers.ValidationError({"facility_space": "Selected space does not belong to the selected facility."})

        requester = attrs.get("requester", getattr(instance, "requester", None))
        if requester is None and instance is None:
            requester = self.context["request"].user
            attrs["requester"] = requester
        if requester and not attrs.get("requested_by"):
            attrs["requested_by"] = _user_display(requester)

        assigned_agent = attrs.get("assigned_agent", getattr(instance, "assigned_agent", None))
        if assigned_agent:
            attrs["assigned_to"] = _user_display(assigned_agent)

        priority_value = attrs.get("priority", getattr(instance, "priority", ServiceRequest.Priority.MEDIUM))
        if "priority" in attrs or attrs.get("sla_target_hours") is None and getattr(instance, "sla_target_hours", None) is None:
            attrs["sla_target_hours"] = attrs.get("sla_target_hours") or service_request_sla_hours_for(priority_value)

        status_value = attrs.get("status", getattr(instance, "status", ServiceRequest.Status.OPEN))
        if assigned_agent and status_value == ServiceRequest.Status.OPEN:
            status_value = ServiceRequest.Status.ACKNOWLEDGED
            attrs["status"] = status_value

        if (
            status_value in ACTIVE_SERVICE_REQUEST_STATUSES
            and attrs.get("sla_due_at") is None
            and getattr(instance, "sla_due_at", None) is None
        ):
            base_time = getattr(instance, "created_at", None) or now
            attrs["sla_due_at"] = base_time + timedelta(hours=attrs["sla_target_hours"])

        if (
            status_value in {
                ServiceRequest.Status.ACKNOWLEDGED,
                ServiceRequest.Status.IN_PROGRESS,
                ServiceRequest.Status.ESCALATED,
            }
            and attrs.get("first_response_at") is None
            and getattr(instance, "first_response_at", None) is None
        ):
            attrs["first_response_at"] = now

        if (
            status_value == ServiceRequest.Status.ESCALATED
            and attrs.get("escalated_at") is None
            and getattr(instance, "escalated_at", None) is None
        ):
            attrs["escalated_at"] = now

        if (
            status_value in {ServiceRequest.Status.RESOLVED, ServiceRequest.Status.CLOSED}
            and attrs.get("resolved_date") is None
            and getattr(instance, "resolved_date", None) is None
        ):
            attrs["resolved_date"] = timezone.localdate()

        return attrs


class FacilityServiceRequestFeedbackSerializer(serializers.Serializer):
    feedback_rating = serializers.IntegerField(min_value=1, max_value=5)
    feedback_comment = serializers.CharField(required=False, allow_blank=True, default="")


class FacilityServiceRequestEscalateSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class FacilityBillingTicketListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    invoice_number = serializers.CharField(source="invoice.invoice_number", read_only=True, default="")
    property_name = serializers.CharField(source="invoice.property.name", read_only=True, default="")
    assigned_agent_name = serializers.SerializerMethodField()
    requester_name = serializers.SerializerMethodField()
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    sla_breached = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id",
            "ticket_id",
            "subject",
            "description",
            "customer",
            "customer_name",
            "invoice",
            "invoice_number",
            "property_name",
            "requester",
            "requester_name",
            "assigned_agent",
            "assigned_agent_name",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "sla_deadline",
            "escalated_at",
            "resolved_at",
            "closed_at",
            "sla_breached",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assigned_agent_name(self, obj):
        return _user_display(obj.assigned_agent)

    def get_requester_name(self, obj):
        return _user_display(obj.requester)

    def get_sla_breached(self, obj):
        return obj.is_sla_breached()


class FacilityBillingTicketDetailSerializer(FacilityBillingTicketListSerializer):
    class Meta(FacilityBillingTicketListSerializer.Meta):
        fields = FacilityBillingTicketListSerializer.Meta.fields + [
            "resolution_notes",
            "customer_satisfaction_score",
        ]


class FacilityBillingTicketWriteSerializer(serializers.ModelSerializer):
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
            "priority",
            "status",
            "assigned_agent",
            "resolution_notes",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "requester": {"required": False, "allow_null": True},
            "customer": {"required": False, "allow_null": True},
            "contact_account": {"required": False, "allow_null": True},
            "department": {"required": False, "allow_null": True},
            "status": {"required": False},
            "assigned_agent": {"required": False, "allow_null": True},
            "resolution_notes": {"required": False, "allow_blank": True},
        }

    def _org(self):
        return _resolve_request_org(self.context.get("request"))

    def _validate_user_org(self, value, label: str):
        org = self._org()
        if value and org and getattr(value, "profile", None) and value.profile.organization_id != org.id:
            raise serializers.ValidationError(f"{label} must belong to your organization.")
        return value

    def validate_requester(self, value):
        return self._validate_user_org(value, "Requester")

    def validate_assigned_agent(self, value):
        return self._validate_user_org(value, "Assigned agent")

    def validate_invoice(self, value):
        org = self._org()
        if org and value.organization_id != org.id:
            raise serializers.ValidationError("Invoice must belong to your organization.")
        if value and not hasattr(value.property, "facility_registry"):
            raise serializers.ValidationError("Invoice must belong to a facility-managed property.")
        return value

    def validate_customer(self, value):
        org = self._org()
        if value and org and value.organization_id != org.id:
            raise serializers.ValidationError("Customer must belong to your organization.")
        return value

    def validate_contact_account(self, value):
        org = self._org()
        if value and org and value.organization_id != org.id:
            raise serializers.ValidationError("Contact account must belong to your organization.")
        return value

    def validate_department(self, value):
        org = self._org()
        if value and org and value.division.organization_id != org.id:
            raise serializers.ValidationError("Department must belong to your organization.")
        return value

    def validate(self, attrs):
        invoice = attrs.get("invoice", getattr(self.instance, "invoice", None))
        if invoice is None:
            raise serializers.ValidationError({"invoice": "Invoice is required for billing helpdesk tickets."})

        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if customer is None:
            attrs["customer"] = invoice.customer
            customer = invoice.customer
        elif invoice.customer_id and customer.id != invoice.customer_id:
            raise serializers.ValidationError({"customer": "Selected customer does not match the selected invoice."})

        contact_account = attrs.get("contact_account", getattr(self.instance, "contact_account", None))
        if contact_account and contact_account.finance_customer_id and customer and contact_account.finance_customer_id != customer.id:
            raise serializers.ValidationError({"contact_account": "Selected contact account does not belong to the selected customer."})

        attrs["category"] = SupportTicket.Category.BILLING
        if not attrs.get("requester") and self.instance is None:
            attrs["requester"] = self.context["request"].user
        return attrs


class FacilityInvoiceListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True, default="")
    paid_amount = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    open_billing_ticket_count = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "invoice_number",
            "customer",
            "customer_name",
            "property",
            "property_name",
            "status",
            "issue_date",
            "due_date",
            "total_amount",
            "paid_amount",
            "balance_due",
            "created_at",
            "updated_at",
            "open_billing_ticket_count",
        ]
        read_only_fields = fields

    def get_paid_amount(self, obj):
        return f"{obj.paid_amount:.2f}"

    def get_balance_due(self, obj):
        return f"{obj.balance_due:.2f}"

    def get_open_billing_ticket_count(self, obj):
        return SupportTicket.objects.filter(
            organization=obj.organization,
            invoice=obj,
            category=SupportTicket.Category.BILLING,
        ).exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]).count()


class FacilityInvoicePaymentWriteSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_date = serializers.DateField()
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices)
    reference_number = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value

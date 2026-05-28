import hashlib
import re
from decimal import ROUND_HALF_UP, Decimal

from rest_framework import serializers

from .models import (
    Broker,
    BrokerCommissionEarning,
    BrokerCommissionStructure,
    BrokerTier,
    CallRecording,
    Campaign,
    CampaignRecipient,
    CommunicationLog,
    ContactAccount,
    ContactComplianceReview,
    ContactDealLink,
    ContactDocument,
    ContactInteraction,
    ContactPropertyLink,
    FollowUpRule,
    FollowUpTask,
    Lead,
    LeadActivity,
    LeadDocumentEvent,
    LeadFinancialAssessment,
    LeadPaymentScenario,
    LeadProjectInterest,
    LeadPropertyMatch,
    LeadSource,
    LeadStageTransition,
    LeadUnitPreference,
    MeetingRecord,
    ReservationEvent,
    UnitReservation,
)

# ---------------------------------------------------------------------------
# Lead Source
# ---------------------------------------------------------------------------


class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# Broker
# ---------------------------------------------------------------------------


class BrokerListSerializer(serializers.ModelSerializer):
    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = Broker
        fields = [
            "id", "name", "company", "license_number", "email", "phone",
            "commission_rate", "status", "lead_count", "created_at", "updated_at",
        ]

    def get_lead_count(self, obj):
        return obj.leads.count()


class BrokerDetailSerializer(serializers.ModelSerializer):
    lead_count = serializers.SerializerMethodField()

    class Meta:
        model = Broker
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def get_lead_count(self, obj):
        return obj.leads.count()


class BrokerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Broker
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# Lead ↔ Project Interest
# ---------------------------------------------------------------------------


class LeadProjectInterestSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = LeadProjectInterest
        fields = [
            "id", "lead", "project", "project_name", "interest_level",
            "notes", "created_at",
        ]
        read_only_fields = ("id", "lead", "created_at")


# ---------------------------------------------------------------------------
# Lead Unit Preference
# ---------------------------------------------------------------------------


class LeadUnitPreferenceSerializer(serializers.ModelSerializer):
    unit_type_display = serializers.CharField(source="get_unit_type_display", read_only=True)

    class Meta:
        model = LeadUnitPreference
        fields = [
            "id", "lead", "unit_type", "unit_type_display",
            "min_bedrooms", "max_bedrooms",
            "min_area_sqft", "max_area_sqft",
            "floor_preference", "view_preference",
            "notes", "created_at",
        ]
        read_only_fields = ("id", "lead", "created_at")


# ---------------------------------------------------------------------------
# Lead Activity
# ---------------------------------------------------------------------------


class LeadActivitySerializer(serializers.ModelSerializer):
    activity_type_display = serializers.CharField(
        source="get_activity_type_display", read_only=True
    )
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = LeadActivity
        fields = [
            "id", "lead", "lead_name", "activity_type", "activity_type_display",
            "subject", "description", "scheduled_at", "completed_at",
            "is_completed", "performed_by", "performed_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "lead", "created_at", "updated_at")


class LeadActivityWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadActivity
        fields = [
            "activity_type", "subject", "description",
            "scheduled_at", "completed_at", "is_completed",
        ]


class LeadActivityGlobalWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadActivity
        fields = [
            "lead", "activity_type", "subject", "description",
            "scheduled_at", "completed_at", "is_completed",
        ]

    def validate_lead(self, value):
        request = self.context.get("request")
        if request is None or request.user.is_superuser:
            return value

        profile = getattr(request.user, "profile", None)
        user_org_id = getattr(getattr(profile, "organization", None), "id", None)
        if not user_org_id or value.organization_id != user_org_id:
            raise serializers.ValidationError("Selected lead is outside your organization scope.")
        return value

    def validate(self, attrs):
        activity_type = attrs.get("activity_type")
        scheduled_at = attrs.get("scheduled_at")
        is_completed = attrs.get("is_completed")
        completed_at = attrs.get("completed_at")

        if activity_type == LeadActivity.ActivityType.SITE_VISIT and not scheduled_at:
            raise serializers.ValidationError(
                {"scheduled_at": "Site visits must include a scheduled date/time."}
            )

        if completed_at and not is_completed:
            attrs["is_completed"] = True

        return attrs


# ---------------------------------------------------------------------------
# Lead Stage Transition
# ---------------------------------------------------------------------------


class LeadStageTransitionSerializer(serializers.ModelSerializer):
    transitioned_by_name = serializers.CharField(
        source="transitioned_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = LeadStageTransition
        fields = [
            "id", "lead", "from_stage", "to_stage",
            "transitioned_by", "transitioned_by_name",
            "notes", "transitioned_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Lead serializers
# ---------------------------------------------------------------------------


class LeadListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True, default=None)
    broker_name = serializers.CharField(source="broker.name", read_only=True, default=None)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )
    days_in_pipeline = serializers.IntegerField(read_only=True)
    pipeline_stage_display = serializers.CharField(
        source="get_pipeline_stage_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    activity_count = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            "id", "first_name", "last_name", "full_name", "email", "phone",
            "company", "lead_type",
            "pipeline_stage", "pipeline_stage_display",
            "status", "status_display", "priority", "score", "tags",
            "source", "source_name", "broker", "broker_name",
            "budget_min", "budget_max", "payment_capability",
            "preferred_locations",
            "assigned_to", "assigned_to_name",
            "inquiry_date", "days_in_pipeline",
            "activity_count",
            "is_archived",
            "created_at", "updated_at",
        ]

    def get_activity_count(self, obj):
        return obj.activities.count()


class LeadDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    source_name = serializers.CharField(source="source.name", read_only=True, default=None)
    broker_name = serializers.CharField(source="broker.name", read_only=True, default=None)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )
    converted_customer_name = serializers.CharField(
        source="converted_customer.name", read_only=True, default=None
    )
    days_in_pipeline = serializers.IntegerField(read_only=True)
    pipeline_stage_display = serializers.CharField(
        source="get_pipeline_stage_display", read_only=True
    )

    project_interests = LeadProjectInterestSerializer(many=True, read_only=True)
    unit_preferences = LeadUnitPreferenceSerializer(many=True, read_only=True)
    activities = LeadActivitySerializer(many=True, read_only=True)
    stage_transitions = LeadStageTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class LeadWriteSerializer(serializers.ModelSerializer):
    _phone_sanitizer = re.compile(r"\D+")

    class Meta:
        model = Lead
        fields = "__all__"
        read_only_fields = (
            "id", "organization", "converted_customer",
            "created_at", "updated_at",
        )

    @classmethod
    def _normalize_phone(cls, value):
        if value in (None, ""):
            return ""
        return cls._phone_sanitizer.sub("", str(value))

    def validate_tags(self, value):
        if value in (None, "", []):
            return []

        if isinstance(value, str):
            raw_tags = value.split(",")
        elif isinstance(value, list):
            raw_tags = value
        else:
            raise serializers.ValidationError("Tags must be a list of strings or a comma-separated string.")

        normalized = []
        seen = set()
        for raw in raw_tags:
            tag = " ".join(str(raw).strip().split())
            if not tag:
                continue
            lowered = tag.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(tag)

        return normalized[:15]

    def validate_preferred_locations(self, value):
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            items = value.split(",")
        elif isinstance(value, list):
            items = value
        else:
            raise serializers.ValidationError("Preferred locations must be a list of strings.")

        normalized = []
        seen = set()
        for raw in items:
            item = " ".join(str(raw).strip().split())
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(item)
        return normalized[:20]

    def validate(self, data):
        budget_min = data.get("budget_min")
        budget_max = data.get("budget_max")
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            raise serializers.ValidationError({
                "budget_max": "Maximum budget must be greater than or equal to minimum budget."
            })

        if "tags" not in data and self.instance is not None:
            data["tags"] = self.instance.tags or []

        request = self.context.get("request")
        organization = None
        if self.instance is not None:
            organization = self.instance.organization
        elif request is not None:
            profile = getattr(request.user, "profile", None)
            organization = getattr(profile, "organization", None)

        if organization is None:
            return data

        should_check_duplicates = (
            self.instance is None
            or "email" in data
            or "phone" in data
        )
        if not should_check_duplicates:
            return data

        email = (data.get("email") if "email" in data else getattr(self.instance, "email", "")) or ""
        phone = (data.get("phone") if "phone" in data else getattr(self.instance, "phone", "")) or ""
        email = str(email).strip()
        phone = str(phone).strip()
        normalized_phone = self._normalize_phone(phone)

        duplicates = Lead.objects.filter(organization=organization)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        existing = None
        if email:
            existing = duplicates.filter(email__iexact=email).only(
                "id", "first_name", "last_name"
            ).first()

        if existing is None and phone:
            existing = duplicates.filter(phone=phone).only(
                "id", "first_name", "last_name", "phone"
            ).first()

        if existing is None and normalized_phone:
            for candidate in duplicates.exclude(phone="").only(
                "id", "first_name", "last_name", "phone"
            ):
                if self._normalize_phone(candidate.phone) == normalized_phone:
                    existing = candidate
                    break

        if existing is not None:
            error_field = "email" if email else ("phone" if phone else "non_field_errors")
            raise serializers.ValidationError(
                {
                    error_field: [
                        (
                            f"Potential duplicate detected: lead #{existing.id} "
                            f"({existing.full_name}). Open that record instead of creating a duplicate."
                        )
                    ]
                }
            )
        return data


class LeadStageChangeSerializer(serializers.Serializer):
    """Used for the advance_stage / change_stage action."""
    stage = serializers.ChoiceField(choices=Lead.PipelineStage.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class LeadConvertSerializer(serializers.Serializer):
    """Used for converting a lead to a Finance Customer."""
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Property Matching
# ---------------------------------------------------------------------------


class LeadPropertyMatchListSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    candidate_type_display = serializers.CharField(source="get_candidate_type_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = LeadPropertyMatch
        fields = [
            "id",
            "organization",
            "lead",
            "lead_name",
            "candidate_type",
            "candidate_type_display",
            "property",
            "property_name",
            "unit",
            "unit_number",
            "project",
            "project_name",
            "match_score",
            "score_breakdown",
            "reason_summary",
            "budget_fit",
            "location_fit",
            "unit_type_fit",
            "payment_eligibility_fit",
            "status",
            "status_display",
            "source",
            "source_display",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeadPropertyMatchWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadPropertyMatch
        fields = ["status", "is_active"]

    def validate_status(self, value):
        if value not in LeadPropertyMatch.MatchStatus.values:
            raise serializers.ValidationError("Invalid match status.")
        return value


# ---------------------------------------------------------------------------
# Financial Pre-Assessment
# ---------------------------------------------------------------------------


class LeadPaymentScenarioSerializer(serializers.ModelSerializer):
    plan_type_display = serializers.CharField(
        source="get_plan_type_display", read_only=True
    )
    down_payment_amount = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = LeadPaymentScenario
        fields = [
            "id", "assessment", "label", "plan_type", "plan_type_display",
            "property_price", "down_payment_pct", "down_payment_amount",
            "financed_amount", "interest_rate", "tenure_months",
            "monthly_payment", "total_cost",
            "is_recommended", "is_affordable", "notes", "created_at",
        ]
        read_only_fields = (
            "id", "assessment", "financed_amount", "monthly_payment",
            "total_cost", "is_affordable", "created_at",
        )


class LeadPaymentScenarioWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadPaymentScenario
        fields = [
            "label", "plan_type", "property_price", "down_payment_pct",
            "interest_rate", "tenure_months", "is_recommended", "notes",
        ]


class FinancialAssessmentListSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_id = serializers.IntegerField(source="lead.id", read_only=True)
    lead_email = serializers.CharField(source="lead.email", read_only=True, default="")
    lead_pipeline_stage = serializers.CharField(
        source="lead.pipeline_stage", read_only=True
    )
    lead_budget_min = serializers.DecimalField(
        source="lead.budget_min", max_digits=15, decimal_places=2,
        read_only=True, default=None,
    )
    lead_budget_max = serializers.DecimalField(
        source="lead.budget_max", max_digits=15, decimal_places=2,
        read_only=True, default=None,
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    risk_level_display = serializers.CharField(
        source="get_risk_level_display", read_only=True, default=""
    )
    employment_status_display = serializers.CharField(
        source="get_employment_status_display", read_only=True, default=""
    )
    assessed_by_name = serializers.CharField(
        source="assessed_by.get_full_name", read_only=True, default=None
    )
    scenario_count = serializers.SerializerMethodField()

    class Meta:
        model = LeadFinancialAssessment
        fields = [
            "id", "lead_id", "lead_name", "lead_email",
            "lead_pipeline_stage", "lead_budget_min", "lead_budget_max",
            "status", "status_display",
            "affordability_score", "risk_score", "risk_level", "risk_level_display",
            "mortgage_prequalified", "mortgage_prequalification_amount",
            "employment_status", "employment_status_display",
            "recommended_plan", "max_affordable_price",
            "assessed_by", "assessed_by_name", "assessment_date",
            "scenario_count",
            "created_at", "updated_at",
        ]

    def get_scenario_count(self, obj):
        return obj.scenarios.count()


class FinancialAssessmentDetailSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_id = serializers.IntegerField(source="lead.id", read_only=True)
    lead_email = serializers.CharField(source="lead.email", read_only=True, default="")
    lead_phone = serializers.CharField(source="lead.phone", read_only=True, default="")
    lead_company = serializers.CharField(source="lead.company", read_only=True, default="")
    lead_pipeline_stage = serializers.CharField(
        source="lead.pipeline_stage", read_only=True
    )
    lead_pipeline_stage_display = serializers.CharField(
        source="lead.get_pipeline_stage_display", read_only=True
    )
    lead_budget_min = serializers.DecimalField(
        source="lead.budget_min", max_digits=15, decimal_places=2,
        read_only=True, default=None,
    )
    lead_budget_max = serializers.DecimalField(
        source="lead.budget_max", max_digits=15, decimal_places=2,
        read_only=True, default=None,
    )
    lead_payment_capability = serializers.CharField(
        source="lead.payment_capability", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    risk_level_display = serializers.CharField(
        source="get_risk_level_display", read_only=True, default=""
    )
    employment_status_display = serializers.CharField(
        source="get_employment_status_display", read_only=True, default=""
    )
    recommended_plan_display = serializers.CharField(
        source="get_recommended_plan_display", read_only=True, default=""
    )
    assessed_by_name = serializers.CharField(
        source="assessed_by.get_full_name", read_only=True, default=None
    )
    disposable_income = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    scenarios = LeadPaymentScenarioSerializer(many=True, read_only=True)

    class Meta:
        model = LeadFinancialAssessment
        fields = "__all__"
        read_only_fields = (
            "id", "affordability_score", "debt_to_income_ratio",
            "max_affordable_price", "risk_score", "risk_level", "risk_factors",
            "created_at", "updated_at",
        )


class FinancialAssessmentWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadFinancialAssessment
        fields = "__all__"
        read_only_fields = (
            "id", "affordability_score", "debt_to_income_ratio",
            "max_affordable_price", "risk_score", "risk_level", "risk_factors",
            "created_at", "updated_at",
        )


# ---------------------------------------------------------------------------
# Broker Tier
# ---------------------------------------------------------------------------


class BrokerTierSerializer(serializers.ModelSerializer):
    broker_count = serializers.SerializerMethodField()

    class Meta:
        model = BrokerTier
        fields = [
            "id", "name", "code", "min_deals", "min_revenue",
            "commission_multiplier", "bonus_pct", "evaluation_period_months",
            "benefits", "color", "sort_order", "is_active",
            "broker_count", "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_broker_count(self, obj):
        return obj.brokers.count()


class BrokerTierWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerTier
        fields = [
            "name", "code", "min_deals", "min_revenue",
            "commission_multiplier", "bonus_pct", "evaluation_period_months",
            "benefits", "color", "sort_order", "is_active",
        ]


# ---------------------------------------------------------------------------
# Broker (enhanced with tier info)
# ---------------------------------------------------------------------------


class BrokerListEnhancedSerializer(serializers.ModelSerializer):
    lead_count = serializers.SerializerMethodField()
    tier_name = serializers.CharField(source="tier.name", read_only=True, default=None)
    tier_color = serializers.CharField(source="tier.color", read_only=True, default="")
    commission_multiplier = serializers.DecimalField(
        source="tier.commission_multiplier", max_digits=4, decimal_places=2,
        read_only=True, default=None,
    )
    total_earnings = serializers.SerializerMethodField()
    deals_closed = serializers.SerializerMethodField()

    class Meta:
        model = Broker
        fields = [
            "id", "name", "company", "license_number", "email", "phone",
            "commission_rate", "tier", "tier_name", "tier_color",
            "commission_multiplier", "status",
            "lead_count", "deals_closed", "total_earnings",
            "notes", "created_at", "updated_at",
        ]

    def get_lead_count(self, obj):
        return obj.leads.count()

    def get_deals_closed(self, obj):
        return obj.leads.filter(status="won").count()

    def get_total_earnings(self, obj):
        from django.db.models import Sum
        result = obj.commission_earnings.filter(
            status__in=["approved", "processing", "paid"]
        ).aggregate(total=Sum("total_commission"))
        return result["total"] or 0


class BrokerDetailEnhancedSerializer(serializers.ModelSerializer):
    lead_count = serializers.SerializerMethodField()
    tier_name = serializers.CharField(source="tier.name", read_only=True, default=None)
    tier_color = serializers.CharField(source="tier.color", read_only=True, default="")
    tier_data = BrokerTierSerializer(source="tier", read_only=True)
    total_earnings = serializers.SerializerMethodField()
    pending_earnings = serializers.SerializerMethodField()
    deals_closed = serializers.SerializerMethodField()
    active_leads = serializers.SerializerMethodField()
    conversion_rate = serializers.SerializerMethodField()

    class Meta:
        model = Broker
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def get_lead_count(self, obj):
        return obj.leads.count()

    def get_deals_closed(self, obj):
        return obj.leads.filter(status="won").count()

    def get_active_leads(self, obj):
        return obj.leads.filter(status="active").count()

    def get_total_earnings(self, obj):
        from django.db.models import Sum
        result = obj.commission_earnings.filter(
            status__in=["approved", "processing", "paid"]
        ).aggregate(total=Sum("total_commission"))
        return result["total"] or 0

    def get_pending_earnings(self, obj):
        from django.db.models import Sum
        result = obj.commission_earnings.filter(
            status="pending"
        ).aggregate(total=Sum("total_commission"))
        return result["total"] or 0

    def get_conversion_rate(self, obj):
        total = obj.leads.count()
        won = obj.leads.filter(status="won").count()
        return round(won / total * 100, 1) if total > 0 else 0


# ---------------------------------------------------------------------------
# Commission Structure
# ---------------------------------------------------------------------------


class CommissionStructureListSerializer(serializers.ModelSerializer):
    commission_type_display = serializers.CharField(
        source="get_commission_type_display", read_only=True
    )
    trigger_stage_display = serializers.CharField(
        source="get_trigger_stage_display", read_only=True
    )
    payment_split_display = serializers.CharField(
        source="get_payment_split_display", read_only=True
    )
    broker_name = serializers.CharField(
        source="broker.name", read_only=True, default=None
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    earning_count = serializers.SerializerMethodField()

    class Meta:
        model = BrokerCommissionStructure
        fields = [
            "id", "name", "description",
            "commission_type", "commission_type_display",
            "base_rate", "fixed_amount", "tiered_brackets",
            "trigger_stage", "trigger_stage_display",
            "payment_split", "payment_split_display",
            "broker", "broker_name", "project", "project_name",
            "is_default", "is_active",
            "effective_from", "effective_to",
            "earning_count", "created_at", "updated_at",
        ]

    def get_earning_count(self, obj):
        return obj.earnings.count()


class CommissionStructureDetailSerializer(CommissionStructureListSerializer):
    class Meta(CommissionStructureListSerializer.Meta):
        fields = "__all__"
        read_only_fields = ("id", "organization", "created_at", "updated_at")


class CommissionStructureWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerCommissionStructure
        fields = [
            "name", "description", "commission_type",
            "base_rate", "fixed_amount", "tiered_brackets",
            "trigger_stage", "payment_split",
            "broker", "project",
            "is_default", "is_active",
            "effective_from", "effective_to",
        ]


# ---------------------------------------------------------------------------
# Commission Earning
# ---------------------------------------------------------------------------


class CommissionEarningListSerializer(serializers.ModelSerializer):
    broker_name = serializers.CharField(source="broker.name", read_only=True)
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    trigger_stage_display = serializers.CharField(
        source="get_trigger_stage_display", read_only=True
    )
    structure_name = serializers.CharField(
        source="commission_structure.name", read_only=True, default=None
    )

    class Meta:
        model = BrokerCommissionEarning
        fields = [
            "id", "broker", "broker_name", "lead", "lead_name",
            "project", "project_name",
            "commission_structure", "structure_name",
            "deal_value", "commission_rate",
            "base_commission", "tier_multiplier", "bonus_amount",
            "total_commission",
            "trigger_stage", "trigger_stage_display", "triggered_at",
            "status", "status_display",
            "approved_by", "approved_at", "paid_at",
            "payment_reference", "notes",
            "created_at", "updated_at",
        ]


class CommissionEarningDetailSerializer(CommissionEarningListSerializer):
    approved_by_name = serializers.CharField(
        source="approved_by.get_full_name", read_only=True, default=None,
    )

    class Meta(CommissionEarningListSerializer.Meta):
        fields = "__all__"
        read_only_fields = (
            "id", "base_commission", "tier_multiplier", "bonus_amount",
            "total_commission", "approved_at", "paid_at",
            "created_at", "updated_at",
        )


class CommissionEarningWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrokerCommissionEarning
        fields = [
            "broker", "lead", "commission_structure", "project",
            "deal_value", "commission_rate", "trigger_stage", "notes",
        ]


# ---------------------------------------------------------------------------
# Communication Log
# ---------------------------------------------------------------------------


class CallRecordingSerializer(serializers.ModelSerializer):
    disposition_display = serializers.CharField(
        source="get_disposition_display", read_only=True
    )
    duration_display = serializers.CharField(read_only=True)

    class Meta:
        model = CallRecording
        fields = [
            "id", "duration_seconds", "duration_display",
            "recording_url", "recording_storage_path",
            "disposition", "disposition_display",
            "caller_number", "callee_number",
            "transcription", "call_started_at", "call_ended_at",
            "notes", "created_at",
        ]
        read_only_fields = ("id", "created_at")


class CommunicationLogListSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True, default=None
    )
    campaign_name = serializers.CharField(
        source="campaign.name", read_only=True, default=None
    )
    has_recording = serializers.SerializerMethodField()
    thread_key = serializers.SerializerMethodField()

    class Meta:
        model = CommunicationLog
        fields = [
            "id", "lead", "lead_name",
            "channel", "channel_display",
            "direction", "direction_display",
            "status", "status_display",
            "subject", "summary",
            "from_address", "to_address",
            "campaign", "campaign_name",
            "performed_by", "performed_by_name",
            "has_recording",
            "thread_key",
            "communicated_at", "created_at",
        ]

    def get_has_recording(self, obj):
        return hasattr(obj, "call_recording") and obj.call_recording is not None

    @staticmethod
    def _normalize_contact_point(value: str | None) -> str:
        if not value:
            return ""
        return " ".join(str(value).strip().lower().split())

    def get_thread_key(self, obj):
        parties = sorted(
            {
                point
                for point in (
                    self._normalize_contact_point(getattr(obj, "from_address", "")),
                    self._normalize_contact_point(getattr(obj, "to_address", "")),
                )
                if point
            }
        )
        parties_key = "|".join(parties) if parties else "no-party"
        token = f"{obj.organization_id}|{obj.lead_id}|{obj.channel}|{parties_key}"
        return hashlib.sha1(token.encode("utf-8")).hexdigest()


class CommunicationLogDetailSerializer(CommunicationLogListSerializer):
    call_recording = CallRecordingSerializer(read_only=True)

    class Meta(CommunicationLogListSerializer.Meta):
        fields = "__all__"
        read_only_fields = ("id", "organization", "activity", "created_at", "updated_at")


class CommunicationLogWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationLog
        fields = [
            "lead", "channel", "direction", "status",
            "subject", "body", "summary",
            "external_message_id", "from_address", "to_address", "cc",
            "attachments", "campaign", "communicated_at",
        ]


class CallRecordingWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallRecording
        fields = [
            "duration_seconds", "recording_url", "recording_storage_path",
            "disposition", "caller_number", "callee_number",
            "transcription", "call_started_at", "call_ended_at", "notes",
        ]


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class CampaignRecipientSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_email = serializers.CharField(source="lead.email", read_only=True, default="")
    lead_phone = serializers.CharField(source="lead.phone", read_only=True, default="")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CampaignRecipient
        fields = [
            "id", "lead", "lead_name", "lead_email", "lead_phone",
            "status", "status_display",
            "sent_at", "delivered_at", "opened_at", "clicked_at",
            "failed_reason", "communication_log",
            "created_at",
        ]
        read_only_fields = ("id", "campaign", "created_at")


class CampaignListSerializer(serializers.ModelSerializer):
    campaign_type_display = serializers.CharField(
        source="get_campaign_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )
    open_rate = serializers.FloatField(read_only=True)
    click_rate = serializers.FloatField(read_only=True)
    delivery_rate = serializers.FloatField(read_only=True)
    roi_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "description",
            "campaign_type", "campaign_type_display",
            "status", "status_display",
            "channel", "channel_display",
            "target_pipeline_stages", "target_lead_sources", "target_projects", "target_lead_types",
            "auto_create_leads_on_launch", "auto_create_leads_count", "auto_create_lead_type",
            "auto_created_leads_count",
            "total_recipients", "sent_count", "delivered_count",
            "opened_count", "clicked_count", "failed_count",
            "spend_amount", "revenue_attributed",
            "open_rate", "click_rate", "delivery_rate",
            "roi_percent",
            "scheduled_at", "started_at", "completed_at",
            "created_by", "created_by_name",
            "created_at", "updated_at",
        ]


class CampaignDetailSerializer(CampaignListSerializer):
    recipients = CampaignRecipientSerializer(many=True, read_only=True)
    template_name = serializers.CharField(
        source="notification_template.name", read_only=True, default=None
    )

    class Meta(CampaignListSerializer.Meta):
        fields = "__all__"
        read_only_fields = (
            "id", "organization",
            "total_recipients", "sent_count", "delivered_count",
            "opened_count", "clicked_count", "failed_count",
            "auto_created_leads_count",
            "started_at", "completed_at",
            "created_at", "updated_at",
        )


class CampaignWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = [
            "name", "description", "campaign_type", "status",
            "channel", "notification_template",
            "subject", "body",
            "target_pipeline_stages", "target_lead_sources", "target_projects", "target_lead_types",
            "auto_create_leads_on_launch", "auto_create_leads_count", "auto_create_lead_type",
            "spend_amount", "revenue_attributed",
            "scheduled_at",
        ]

    @staticmethod
    def _normalize_str_list(value) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            raw_items = value.split(",")
        elif isinstance(value, list):
            raw_items = value
        else:
            raise serializers.ValidationError("Must be a list of strings.")

        normalized: list[str] = []
        seen: set[str] = set()
        for raw in raw_items:
            item = " ".join(str(raw).strip().split())
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(lowered)
        return normalized

    @staticmethod
    def _normalize_int_list(value) -> list[int]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            raw_items = value.split(",")
        elif isinstance(value, list):
            raw_items = value
        else:
            raise serializers.ValidationError("Must be a list of integers.")

        normalized: list[int] = []
        seen: set[int] = set()
        for raw in raw_items:
            if raw in (None, ""):
                continue
            try:
                item = int(raw)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Must contain valid integer IDs.") from None
            if item <= 0 or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized

    def validate_target_pipeline_stages(self, value):
        normalized = self._normalize_str_list(value)
        valid_stages = set(Lead.PipelineStage.values)
        invalid = [item for item in normalized if item not in valid_stages]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid stage(s): {', '.join(invalid)}."
            )
        return normalized

    def validate_target_lead_types(self, value):
        normalized = self._normalize_str_list(value)
        valid_types = set(Lead.LeadType.values)
        invalid = [item for item in normalized if item not in valid_types]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid lead type(s): {', '.join(invalid)}."
            )
        return normalized

    def validate_target_lead_sources(self, value):
        return self._normalize_int_list(value)

    def validate_target_projects(self, value):
        return self._normalize_int_list(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        auto_create = attrs.get(
            "auto_create_leads_on_launch",
            getattr(self.instance, "auto_create_leads_on_launch", False),
        )
        auto_count = attrs.get(
            "auto_create_leads_count",
            getattr(self.instance, "auto_create_leads_count", 0),
        )
        if auto_create and int(auto_count or 0) <= 0:
            raise serializers.ValidationError(
                {"auto_create_leads_count": "Set a value greater than zero when launch auto-create is enabled."}
            )

        spend_amount = attrs.get("spend_amount", getattr(self.instance, "spend_amount", Decimal("0.00")))
        revenue_attributed = attrs.get(
            "revenue_attributed",
            getattr(self.instance, "revenue_attributed", Decimal("0.00")),
        )
        if spend_amount is not None and spend_amount < 0:
            raise serializers.ValidationError({"spend_amount": "Spend amount cannot be negative."})
        if revenue_attributed is not None and revenue_attributed < 0:
            raise serializers.ValidationError({"revenue_attributed": "Attributed revenue cannot be negative."})
        return attrs


class CampaignAddRecipientsSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.IntegerField())


# ---------------------------------------------------------------------------
# Follow-Up Rules & Tasks
# ---------------------------------------------------------------------------


class FollowUpRuleSerializer(serializers.ModelSerializer):
    trigger_stage_display = serializers.CharField(
        source="get_trigger_stage_display", read_only=True
    )
    required_activity_type_display = serializers.CharField(
        source="get_required_activity_type_display", read_only=True
    )
    sla_severity_level = serializers.CharField(
        source="sla_severity.level", read_only=True, default=None
    )
    sla_response_hours = serializers.IntegerField(
        source="sla_severity.response_time_hours", read_only=True, default=None
    )
    active_task_count = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpRule
        fields = [
            "id", "name", "description",
            "trigger_stage", "trigger_stage_display",
            "follow_up_within_hours",
            "sla_severity", "sla_severity_level", "sla_response_hours",
            "required_activity_type", "required_activity_type_display",
            "auto_assign_to_owner", "is_active",
            "active_task_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at")

    def get_active_task_count(self, obj):
        return obj.tasks.filter(status__in=["pending", "in_progress"]).count()


class FollowUpRuleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpRule
        fields = [
            "name", "description", "trigger_stage",
            "follow_up_within_hours", "sla_severity",
            "required_activity_type", "auto_assign_to_owner", "is_active",
        ]


class FollowUpTaskListSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_id = serializers.IntegerField(source="lead.id", read_only=True)
    assigned_to_name = serializers.CharField(
        source="assigned_to.get_full_name", read_only=True, default=None
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = FollowUpTask
        fields = [
            "id", "rule", "rule_name",
            "lead", "lead_id", "lead_name",
            "assigned_to", "assigned_to_name",
            "status", "status_display",
            "due_at", "is_overdue",
            "completed_at", "breached_at", "escalated_at",
            "completed_activity", "notes",
            "created_at", "updated_at",
        ]


class FollowUpTaskDetailSerializer(FollowUpTaskListSerializer):
    class Meta(FollowUpTaskListSerializer.Meta):
        fields = "__all__"
        read_only_fields = (
            "id", "rule", "lead",
            "breached_at", "escalated_at",
            "created_at", "updated_at",
        )


class FollowUpTaskCompleteSerializer(serializers.Serializer):
    activity_id = serializers.IntegerField(
        required=False, help_text="ID of the LeadActivity that satisfies this follow-up"
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class FollowUpTaskManualCreateSerializer(serializers.Serializer):
    lead = serializers.IntegerField()
    due_at = serializers.DateTimeField()
    assigned_to = serializers.IntegerField(required=False, allow_null=True)
    rule = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Lead Document Event
# ---------------------------------------------------------------------------


class LeadDocumentEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(
        source="get_event_type_display", read_only=True
    )
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    delivered_via_display = serializers.CharField(
        source="get_delivered_via_display", read_only=True, default=""
    )
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = LeadDocumentEvent
        fields = [
            "id", "lead", "lead_name",
            "event_type", "event_type_display",
            "document_name", "document", "audit_event",
            "delivered_via", "delivered_via_display", "delivered_to",
            "viewed_at", "downloaded_at",
            "performed_by", "performed_by_name",
            "notes", "created_at",
        ]
        read_only_fields = ("id", "created_at")


class LeadDocumentEventWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadDocumentEvent
        fields = [
            "lead", "event_type", "document_name",
            "document", "audit_event",
            "delivered_via", "delivered_to",
            "viewed_at", "downloaded_at", "notes",
        ]


# ---------------------------------------------------------------------------
# Meeting Record
# ---------------------------------------------------------------------------


class MeetingRecordListSerializer(serializers.ModelSerializer):
    meeting_type_display = serializers.CharField(
        source="get_meeting_type_display", read_only=True
    )
    outcome_display = serializers.CharField(
        source="get_outcome_display", read_only=True, default=""
    )
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    organized_by_name = serializers.CharField(
        source="organized_by.get_full_name", read_only=True, default=None
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = MeetingRecord
        fields = [
            "id", "lead", "lead_name",
            "title", "meeting_type", "meeting_type_display",
            "outcome", "outcome_display",
            "scheduled_start", "scheduled_end",
            "actual_start", "actual_end",
            "location", "meeting_link",
            "organized_by", "organized_by_name",
            "project", "project_name",
            "duration_minutes",
            "created_at", "updated_at",
        ]


class MeetingRecordDetailSerializer(MeetingRecordListSerializer):
    class Meta(MeetingRecordListSerializer.Meta):
        fields = "__all__"
        read_only_fields = ("id", "activity", "created_at", "updated_at")


class MeetingRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeetingRecord
        fields = [
            "lead", "title", "meeting_type", "outcome",
            "scheduled_start", "scheduled_end",
            "actual_start", "actual_end",
            "location", "meeting_link",
            "attendees", "agenda", "minutes", "action_items",
            "project", "property_unit", "notes",
        ]


# ---------------------------------------------------------------------------
# Unit Reservation
# ---------------------------------------------------------------------------


class ReservationEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(
        source="get_event_type_display", read_only=True
    )
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = ReservationEvent
        fields = [
            "id", "reservation", "event_type", "event_type_display",
            "performed_by", "performed_by_name",
            "notes", "metadata", "created_at",
        ]
        read_only_fields = ("id", "reservation", "created_at")


class UnitReservationListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_id = serializers.IntegerField(source="lead.id", read_only=True)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True)
    unit_id = serializers.IntegerField(source="unit.id", read_only=True)
    property_name = serializers.CharField(
        source="unit.property.name", read_only=True
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = UnitReservation
        fields = [
            "id", "reservation_number", "status", "status_display",
            "lead", "lead_id", "lead_name",
            "unit", "unit_id", "unit_number", "property_name",
            "project", "project_name",
            "total_price", "deposit_amount", "reservation_fee",
            "hold_expires_at", "payment_deadline",
            "reservation_date", "confirmation_date",
            "performed_by", "performed_by_name",
            "created_at", "updated_at",
        ]


class UnitReservationDetailSerializer(UnitReservationListSerializer):
    events = ReservationEventSerializer(many=True, read_only=True)
    converted_customer_name = serializers.CharField(
        source="converted_customer.name", read_only=True, default=None
    )
    payment_plan_number = serializers.CharField(
        source="payment_plan.plan_number", read_only=True, default=None
    )
    lead_email = serializers.CharField(
        source="lead.email", read_only=True, default=""
    )
    lead_phone = serializers.CharField(
        source="lead.phone", read_only=True, default=""
    )
    lead_type = serializers.CharField(source="lead.lead_type", read_only=True)
    lead_payment_capability = serializers.CharField(
        source="lead.payment_capability", read_only=True
    )
    unit_floor = serializers.IntegerField(
        source="unit.floor", read_only=True, default=None
    )
    unit_area_sqft = serializers.DecimalField(
        source="unit.area_sqft", max_digits=10, decimal_places=2, read_only=True
    )
    unit_bedrooms = serializers.IntegerField(
        source="unit.bedrooms", read_only=True, default=None
    )
    unit_bathrooms = serializers.IntegerField(
        source="unit.bathrooms", read_only=True, default=None
    )
    unit_asking_price = serializers.DecimalField(
        source="unit.asking_price", max_digits=15, decimal_places=2,
        read_only=True, default=None
    )
    unit_status = serializers.CharField(source="unit.status", read_only=True)

    class Meta(UnitReservationListSerializer.Meta):
        fields = "__all__"
        read_only_fields = (
            "id", "organization", "reservation_number",
            "converted_customer", "payment_plan",
            "reservation_agreement", "allocation_letter", "confirmation_date",
            "created_at", "updated_at",
        )


class UnitReservationWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitReservation
        fields = [
            "lead", "unit", "project",
            "total_price", "deposit_amount", "reservation_fee",
            "hold_expires_at", "payment_deadline",
            "notes",
        ]

    def validate_unit(self, unit):
        if unit.status != "available":
            raise serializers.ValidationError(
                f"Unit {unit.unit_number} is not available "
                f"(current status: {unit.get_status_display()})."
            )
        return unit

    def validate_lead(self, lead):
        if lead.status != "active":
            raise serializers.ValidationError(
                "Lead must be in active status to create a reservation."
            )
        if lead.converted_customer is not None:
            raise serializers.ValidationError(
                "Lead has already been converted to a customer."
            )
        return lead


class ReservationConfirmSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReservationPaymentSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    payment_method = serializers.ChoiceField(
        choices=["bank_transfer", "check", "cash", "credit_card", "other"],
        default="bank_transfer",
    )
    reference_number = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ReservationCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class ReservationExtendHoldSerializer(serializers.Serializer):
    extend_hours = serializers.IntegerField(
        min_value=1, max_value=168,
        help_text="Number of hours to extend the hold",
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# ---------------------------------------------------------------------------
# Contact & Account Management
# ---------------------------------------------------------------------------


class ContactInteractionSerializer(serializers.ModelSerializer):
    interaction_type_display = serializers.CharField(
        source="get_interaction_type_display", read_only=True
    )
    performed_by_name = serializers.CharField(
        source="performed_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = ContactInteraction
        fields = [
            "id", "contact",
            "interaction_type", "interaction_type_display",
            "subject", "details", "happened_at",
            "follow_up_required", "follow_up_due_at",
            "performed_by", "performed_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = (
            "id", "contact", "performed_by", "created_at", "updated_at",
        )


class ContactDealLinkSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True, default=None)
    reservation_number = serializers.CharField(
        source="reservation.reservation_number", read_only=True, default=None
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ContactDealLink
        fields = [
            "id", "contact",
            "lead", "lead_name",
            "reservation", "reservation_number",
            "deal_name", "stage", "status", "status_display",
            "deal_value", "close_probability", "notes", "linked_at",
        ]
        read_only_fields = ("id", "contact", "linked_at")


class OpportunityDealListSerializer(serializers.ModelSerializer):
    """Global deal feed used by Opportunity / Deal Management."""

    contact_name = serializers.CharField(source="contact.display_name", read_only=True)
    lead_name = serializers.CharField(source="lead.full_name", read_only=True, default=None)
    broker_id = serializers.IntegerField(source="lead.broker.id", read_only=True, default=None)
    broker_name = serializers.CharField(source="lead.broker.name", read_only=True, default=None)
    reservation_number = serializers.CharField(
        source="reservation.reservation_number", read_only=True, default=None
    )
    reservation_status = serializers.CharField(
        source="reservation.status", read_only=True, default=None
    )
    unit_id = serializers.IntegerField(source="reservation.unit.id", read_only=True, default=None)
    unit_number = serializers.CharField(
        source="reservation.unit.unit_number", read_only=True, default=None
    )
    property_id = serializers.IntegerField(
        source="reservation.unit.property.id", read_only=True, default=None
    )
    property_name = serializers.CharField(
        source="reservation.unit.property.name", read_only=True, default=None
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    weighted_value = serializers.SerializerMethodField()
    expected_commission = serializers.SerializerMethodField()

    class Meta:
        model = ContactDealLink
        fields = [
            "id",
            "contact",
            "contact_name",
            "lead",
            "lead_name",
            "broker_id",
            "broker_name",
            "reservation",
            "reservation_number",
            "reservation_status",
            "unit_id",
            "unit_number",
            "property_id",
            "property_name",
            "deal_name",
            "stage",
            "status",
            "status_display",
            "deal_value",
            "close_probability",
            "weighted_value",
            "expected_commission",
            "notes",
            "linked_at",
        ]
        read_only_fields = (
            "id",
            "contact_name",
            "lead_name",
            "broker_id",
            "broker_name",
            "reservation_number",
            "reservation_status",
            "unit_id",
            "unit_number",
            "property_id",
            "property_name",
            "status_display",
            "weighted_value",
            "expected_commission",
            "linked_at",
        )

    @staticmethod
    def _as_decimal(value):
        if value in (None, ""):
            return Decimal("0.00")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0.00")

    def get_weighted_value(self, obj):
        deal_value = self._as_decimal(obj.deal_value)
        probability = self._as_decimal(obj.close_probability)
        weighted = (deal_value * probability) / Decimal("100")
        return weighted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def get_expected_commission(self, obj):
        if not obj.lead_id or not obj.lead.broker_id:
            return Decimal("0.00")
        rate = self._as_decimal(obj.lead.broker.commission_rate)
        if rate <= 0:
            return Decimal("0.00")
        deal_value = self._as_decimal(obj.deal_value)
        commission = (deal_value * rate) / Decimal("100")
        return commission.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class OpportunityDealWriteSerializer(serializers.ModelSerializer):
    """Write serializer for top-level opportunity management endpoints."""

    class Meta:
        model = ContactDealLink
        fields = [
            "contact",
            "lead",
            "reservation",
            "deal_name",
            "stage",
            "status",
            "deal_value",
            "close_probability",
            "notes",
        ]

    def validate_close_probability(self, value):
        if value is None:
            return value
        if value < 0 or value > 100:
            raise serializers.ValidationError("Close probability must be between 0 and 100.")
        return value

    def validate(self, attrs):
        contact = attrs.get("contact") or getattr(self.instance, "contact", None)
        lead = attrs.get("lead") if "lead" in attrs else getattr(self.instance, "lead", None)
        reservation = (
            attrs.get("reservation")
            if "reservation" in attrs
            else getattr(self.instance, "reservation", None)
        )

        if contact is None:
            raise serializers.ValidationError({"contact": "Contact is required."})

        if reservation is not None and reservation.organization_id != contact.organization_id:
            raise serializers.ValidationError(
                {"reservation": "Reservation does not belong to the same organization as contact."}
            )

        if lead is not None and lead.organization_id != contact.organization_id:
            raise serializers.ValidationError(
                {"lead": "Lead does not belong to the same organization as contact."}
            )

        if reservation is not None and lead is not None and reservation.lead_id != lead.id:
            raise serializers.ValidationError(
                {"lead": "Selected lead does not match the linked reservation lead."}
            )

        if not (lead or reservation or attrs.get("deal_name") or getattr(self.instance, "deal_name", "")):
            raise serializers.ValidationError(
                "Provide at least a lead, reservation, or deal name."
            )

        return attrs


class ContactPropertyLinkSerializer(serializers.ModelSerializer):
    relationship_type_display = serializers.CharField(
        source="get_relationship_type_display", read_only=True
    )
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    property_name = serializers.CharField(source="property.name", read_only=True, default=None)
    unit_number = serializers.CharField(source="unit.unit_number", read_only=True, default=None)

    class Meta:
        model = ContactPropertyLink
        fields = [
            "id", "contact",
            "project", "project_name",
            "property", "property_name",
            "unit", "unit_number",
            "relationship_type", "relationship_type_display",
            "budget_estimate", "notes", "linked_at",
        ]
        read_only_fields = ("id", "contact", "linked_at")


class ContactDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(
        source="get_document_type_display", read_only=True
    )
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.get_full_name", read_only=True, default=None
    )
    latest_review_status = serializers.SerializerMethodField()

    class Meta:
        model = ContactDocument
        fields = [
            "id", "contact",
            "document_type", "document_type_display",
            "file_name", "file_url", "reference_number",
            "issued_at", "expires_at",
            "is_kyc_document", "latest_review_status",
            "uploaded_by", "uploaded_by_name",
            "notes", "uploaded_at",
        ]
        read_only_fields = ("id", "contact", "uploaded_by", "uploaded_at")

    def get_latest_review_status(self, obj):
        latest = obj.compliance_reviews.order_by("-requested_at").first()
        return latest.status if latest else None


class ContactComplianceReviewSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    requested_by_name = serializers.CharField(
        source="requested_by.get_full_name", read_only=True, default=None
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.get_full_name", read_only=True, default=None
    )
    document_name = serializers.CharField(source="document.file_name", read_only=True, default=None)

    class Meta:
        model = ContactComplianceReview
        fields = [
            "id", "contact", "document", "document_name",
            "status", "status_display",
            "requested_by", "requested_by_name",
            "reviewed_by", "reviewed_by_name",
            "notes", "requested_at", "reviewed_at", "updated_at",
        ]
        read_only_fields = (
            "id", "contact", "requested_by", "requested_at", "updated_at",
        )


class ContactAccountListSerializer(serializers.ModelSerializer):
    entity_type_display = serializers.CharField(source="get_entity_type_display", read_only=True)
    kyc_status_display = serializers.CharField(source="get_kyc_status_display", read_only=True)
    risk_profile_display = serializers.CharField(source="get_risk_profile_display", read_only=True)
    display_name = serializers.CharField(read_only=True)
    finance_customer_name = serializers.CharField(source="finance_customer.name", read_only=True, default=None)
    interaction_count = serializers.SerializerMethodField()
    active_deal_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = ContactAccount
        fields = [
            "id", "entity_type", "entity_type_display",
            "display_name", "first_name", "last_name", "legal_name", "trade_name",
            "email", "phone", "city", "country",
            "kyc_status", "kyc_status_display",
            "budget_min", "budget_max", "risk_profile", "risk_profile_display",
            "preferred_locations", "preferred_property_types",
            "finance_customer", "finance_customer_name", "finance_synced_at",
            "is_active",
            "interaction_count", "active_deal_count", "document_count",
            "created_at", "updated_at",
        ]

    def get_interaction_count(self, obj):
        return getattr(obj, "interaction_count", obj.interactions.count())

    def get_active_deal_count(self, obj):
        return getattr(
            obj,
            "active_deal_count",
            obj.deal_links.filter(status=ContactDealLink.Status.ACTIVE).count(),
        )

    def get_document_count(self, obj):
        return getattr(obj, "document_count", obj.documents.count())


class ContactAccountDetailSerializer(ContactAccountListSerializer):
    interactions = ContactInteractionSerializer(many=True, read_only=True)
    deal_links = ContactDealLinkSerializer(many=True, read_only=True)
    property_links = ContactPropertyLinkSerializer(many=True, read_only=True)
    documents = ContactDocumentSerializer(many=True, read_only=True)
    compliance_reviews = ContactComplianceReviewSerializer(many=True, read_only=True)

    class Meta(ContactAccountListSerializer.Meta):
        model = ContactAccount
        fields = [
            *ContactAccountListSerializer.Meta.fields,
            "middle_name", "title", "date_of_birth", "nationality",
            "registration_number", "tax_identification_number", "primary_contact_name",
            "address", "secondary_phone",
            "kyc_reference_number", "kyc_last_uploaded_at",
            "annual_income", "net_worth", "liquidity_estimate",
            "preference_notes", "interaction_summary", "notes",
            "created_by", "updated_by",
            "interactions", "deal_links", "property_links", "documents", "compliance_reviews",
        ]


class ContactAccountWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactAccount
        fields = "__all__"
        read_only_fields = (
            "id", "organization", "finance_customer", "finance_synced_at",
            "created_by", "updated_by", "created_at", "updated_at",
        )

    @staticmethod
    def _normalize_list(value, field_name):
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            raw_items = value.split(",")
        elif isinstance(value, list):
            raw_items = value
        else:
            raise serializers.ValidationError({field_name: "Must be a list or comma-separated string."})

        normalized = []
        seen = set()
        for raw in raw_items:
            item = " ".join(str(raw).strip().split())
            if not item:
                continue
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(item)
        return normalized[:20]

    def validate(self, attrs):
        budget_min = attrs.get("budget_min")
        budget_max = attrs.get("budget_max")
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            raise serializers.ValidationError(
                {"budget_max": "Maximum budget must be greater than or equal to minimum budget."}
            )

        if "preferred_locations" in attrs:
            attrs["preferred_locations"] = self._normalize_list(
                attrs.get("preferred_locations"),
                "preferred_locations",
            )
        if "preferred_property_types" in attrs:
            attrs["preferred_property_types"] = self._normalize_list(
                attrs.get("preferred_property_types"),
                "preferred_property_types",
            )
        return attrs

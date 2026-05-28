from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from apps.admin_mixins import OrgScopedAdminMixin

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
    LeadSource,
    LeadStageTransition,
    LeadUnitPreference,
    MeetingRecord,
    ReservationEvent,
    UnitReservation,
)


@admin.register(LeadSource)
class LeadSourceAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "organization", "is_active", "sort_order"]
    list_filter = ["is_active", "organization"]
    search_fields = ["name", "code"]


@admin.register(Broker)
class BrokerAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "company", "license_number", "email", "status", "commission_rate", "created_at"]
    list_filter = ["status", "organization"]
    search_fields = ["name", "company", "license_number", "email"]
    readonly_fields = ["created_at", "updated_at"]


class LeadProjectInterestInline(TabularInline):
    model = LeadProjectInterest
    extra = 0
    fields = ["project", "interest_level", "notes"]


class LeadUnitPreferenceInline(TabularInline):
    model = LeadUnitPreference
    extra = 0
    fields = ["unit_type", "min_bedrooms", "max_bedrooms", "min_area_sqft", "max_area_sqft", "floor_preference", "view_preference"]


class LeadActivityInline(TabularInline):
    model = LeadActivity
    extra = 0
    fields = ["activity_type", "subject", "scheduled_at", "is_completed", "performed_by"]
    readonly_fields = ["created_at"]


class LeadStageTransitionInline(TabularInline):
    model = LeadStageTransition
    extra = 0
    fields = ["from_stage", "to_stage", "transitioned_by", "notes", "transitioned_at"]
    readonly_fields = ["from_stage", "to_stage", "transitioned_by", "transitioned_at"]


@admin.register(Lead)
class LeadAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "first_name", "last_name", "organization", "pipeline_stage",
        "status", "priority", "source", "broker", "assigned_to",
        "inquiry_date", "is_archived", "created_at",
    ]
    list_filter = ["pipeline_stage", "status", "priority", "lead_type", "payment_capability", "is_archived", "organization"]
    search_fields = ["first_name", "last_name", "email", "phone", "company"]
    readonly_fields = ["created_at", "updated_at", "archived_at", "archived_reason"]
    inlines = [
        LeadProjectInterestInline,
        LeadUnitPreferenceInline,
        LeadActivityInline,
        LeadStageTransitionInline,
    ]


# --- Contact & Account Management ---


class ContactInteractionInline(TabularInline):
    model = ContactInteraction
    extra = 0
    fields = ["interaction_type", "subject", "follow_up_required", "follow_up_due_at", "performed_by", "happened_at"]
    readonly_fields = ["created_at", "updated_at"]


class ContactDealLinkInline(TabularInline):
    model = ContactDealLink
    extra = 0
    fields = ["lead", "reservation", "deal_name", "stage", "status", "deal_value", "close_probability", "linked_at"]
    readonly_fields = ["linked_at"]


class ContactPropertyLinkInline(TabularInline):
    model = ContactPropertyLink
    extra = 0
    fields = ["project", "property", "unit", "relationship_type", "budget_estimate", "linked_at"]
    readonly_fields = ["linked_at"]


class ContactDocumentInline(TabularInline):
    model = ContactDocument
    extra = 0
    fields = ["document_type", "file_name", "is_kyc_document", "reference_number", "expires_at", "uploaded_by", "uploaded_at"]
    readonly_fields = ["uploaded_at"]


class ContactComplianceReviewInline(TabularInline):
    model = ContactComplianceReview
    extra = 0
    fields = ["document", "status", "requested_by", "reviewed_by", "requested_at", "reviewed_at"]
    readonly_fields = ["requested_at", "reviewed_at", "updated_at"]


@admin.register(ContactAccount)
class ContactAccountAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "display_name", "entity_type", "organization",
        "kyc_status", "email", "phone", "finance_customer",
        "is_active", "created_at",
    ]
    list_filter = ["entity_type", "kyc_status", "risk_profile", "is_active", "organization"]
    search_fields = [
        "first_name", "last_name", "legal_name", "trade_name",
        "primary_contact_name", "email", "phone", "registration_number",
    ]
    readonly_fields = ["finance_synced_at", "kyc_last_uploaded_at", "created_at", "updated_at"]
    inlines = [
        ContactInteractionInline,
        ContactDealLinkInline,
        ContactPropertyLinkInline,
        ContactDocumentInline,
        ContactComplianceReviewInline,
    ]


@admin.register(ContactDocument)
class ContactDocumentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["contact", "document_type", "file_name", "is_kyc_document", "expires_at", "uploaded_by", "uploaded_at"]
    list_filter = ["document_type", "is_kyc_document"]
    search_fields = ["contact__first_name", "contact__last_name", "contact__legal_name", "file_name", "reference_number"]
    readonly_fields = ["uploaded_at"]


@admin.register(ContactComplianceReview)
class ContactComplianceReviewAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["contact", "document", "status", "requested_by", "reviewed_by", "requested_at", "reviewed_at"]
    list_filter = ["status"]
    search_fields = ["contact__first_name", "contact__last_name", "contact__legal_name", "document__file_name"]
    readonly_fields = ["requested_at", "reviewed_at", "updated_at"]


# --- Financial Pre-Assessment ---

class LeadPaymentScenarioInline(TabularInline):
    model = LeadPaymentScenario
    extra = 0
    fields = ["label", "plan_type", "property_price", "down_payment_pct", "financed_amount", "monthly_payment", "is_recommended", "is_affordable"]
    readonly_fields = ["financed_amount", "monthly_payment"]


@admin.register(LeadFinancialAssessment)
class LeadFinancialAssessmentAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "lead", "status", "affordability_score", "risk_score", "risk_level",
        "mortgage_prequalified", "assessment_date", "assessed_by", "created_at",
    ]
    list_filter = ["status", "risk_level", "mortgage_prequalified", "employment_status"]
    search_fields = ["lead__first_name", "lead__last_name", "lead__email"]
    readonly_fields = [
        "affordability_score", "debt_to_income_ratio", "max_affordable_price",
        "risk_score", "risk_level", "risk_factors",
        "created_at", "updated_at",
    ]
    inlines = [LeadPaymentScenarioInline]


# --- Broker Tiers & Commissions ---

@admin.register(BrokerTier)
class BrokerTierAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "code", "organization", "min_deals", "min_revenue", "commission_multiplier", "bonus_pct", "sort_order", "is_active"]
    list_filter = ["is_active", "organization"]
    search_fields = ["name", "code"]
    readonly_fields = ["created_at", "updated_at"]


class BrokerCommissionEarningInline(TabularInline):
    model = BrokerCommissionEarning
    extra = 0
    fields = ["lead", "deal_value", "commission_rate", "total_commission", "trigger_stage", "status", "triggered_at"]
    readonly_fields = ["total_commission", "triggered_at"]


@admin.register(BrokerCommissionStructure)
class BrokerCommissionStructureAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "organization", "commission_type", "base_rate", "trigger_stage", "broker", "project", "is_default", "is_active"]
    list_filter = ["commission_type", "trigger_stage", "is_default", "is_active", "organization"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(BrokerCommissionEarning)
class BrokerCommissionEarningAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["broker", "lead", "deal_value", "commission_rate", "total_commission", "trigger_stage", "status", "triggered_at"]
    list_filter = ["status", "trigger_stage"]
    search_fields = ["broker__name", "lead__first_name", "lead__last_name"]
    readonly_fields = ["base_commission", "tier_multiplier", "bonus_amount", "total_commission", "approved_at", "paid_at", "created_at", "updated_at"]


# --- Communication Engine ---


class CallRecordingInline(StackedInline):
    model = CallRecording
    extra = 0
    fields = ["duration_seconds", "disposition", "recording_url", "caller_number", "callee_number", "transcription", "call_started_at", "call_ended_at"]


@admin.register(CommunicationLog)
class CommunicationLogAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["lead", "channel", "direction", "status", "subject", "performed_by", "communicated_at"]
    list_filter = ["channel", "direction", "status", "organization"]
    search_fields = ["subject", "summary", "lead__first_name", "lead__last_name", "to_address"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [CallRecordingInline]


class CampaignRecipientInline(TabularInline):
    model = CampaignRecipient
    extra = 0
    fields = ["lead", "status", "sent_at", "delivered_at", "opened_at", "clicked_at"]
    readonly_fields = ["sent_at", "delivered_at", "opened_at", "clicked_at"]


@admin.register(Campaign)
class CampaignAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "campaign_type", "status", "channel", "total_recipients", "sent_count", "delivered_count", "opened_count", "created_at"]
    list_filter = ["campaign_type", "status", "channel", "organization"]
    search_fields = ["name", "description"]
    readonly_fields = ["total_recipients", "sent_count", "delivered_count", "opened_count", "clicked_count", "failed_count", "started_at", "completed_at", "created_at", "updated_at"]
    inlines = [CampaignRecipientInline]


class FollowUpTaskInline(TabularInline):
    model = FollowUpTask
    extra = 0
    fields = ["lead", "assigned_to", "status", "due_at", "completed_at"]
    readonly_fields = ["created_at"]


@admin.register(FollowUpRule)
class FollowUpRuleAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["name", "trigger_stage", "follow_up_within_hours", "required_activity_type", "sla_severity", "is_active"]
    list_filter = ["trigger_stage", "is_active", "organization"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [FollowUpTaskInline]


@admin.register(FollowUpTask)
class FollowUpTaskAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["rule", "lead", "assigned_to", "status", "due_at", "completed_at", "breached_at"]
    list_filter = ["status", "rule__trigger_stage"]
    search_fields = ["lead__first_name", "lead__last_name", "rule__name"]
    readonly_fields = ["breached_at", "escalated_at", "created_at", "updated_at"]


@admin.register(LeadDocumentEvent)
class LeadDocumentEventAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["lead", "event_type", "document_name", "delivered_via", "performed_by", "created_at"]
    list_filter = ["event_type", "delivered_via"]
    search_fields = ["document_name", "lead__first_name", "lead__last_name"]
    readonly_fields = ["created_at"]


@admin.register(MeetingRecord)
class MeetingRecordAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["title", "lead", "meeting_type", "outcome", "scheduled_start", "organized_by"]
    list_filter = ["meeting_type", "outcome"]
    search_fields = ["title", "lead__first_name", "lead__last_name", "location"]
    readonly_fields = ["created_at", "updated_at"]


# --- Reservation & Conversion ---


class ReservationEventInline(TabularInline):
    model = ReservationEvent
    extra = 0
    fields = ["event_type", "performed_by", "notes", "created_at"]
    readonly_fields = ["event_type", "performed_by", "notes", "created_at"]


@admin.register(UnitReservation)
class UnitReservationAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = [
        "reservation_number", "lead", "unit", "project",
        "status", "total_price", "deposit_amount",
        "hold_expires_at", "created_at",
    ]
    list_filter = ["status", "organization"]
    search_fields = [
        "reservation_number",
        "lead__first_name", "lead__last_name",
        "unit__unit_number",
    ]
    readonly_fields = [
        "reservation_number", "confirmation_date",
        "created_at", "updated_at",
    ]
    inlines = [ReservationEventInline]


@admin.register(ReservationEvent)
class ReservationEventAdmin(OrgScopedAdminMixin, ModelAdmin):
    list_display = ["reservation", "event_type", "performed_by", "created_at"]
    list_filter = ["event_type"]
    search_fields = ["reservation__reservation_number"]
    readonly_fields = ["created_at"]

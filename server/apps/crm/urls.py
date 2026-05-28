from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    ActivityTaskManagementOverviewView,
                    BrokerPerformanceOverviewView,
                    BrokerTierViewSet,
                    BrokerViewSet,
                    CampaignViewSet,
                    CommissionEarningViewSet,
                    CommissionStructureViewSet,
                    CommunicationLogViewSet,
                    CommunicationOverviewView,
                    ContactAccountOverviewView,
                    ContactAccountViewSet,
                    ContactComplianceReviewViewSet,
                    ContactDealLinkViewSet,
                    ContactDocumentViewSet,
                    ContactInteractionViewSet,
                    ContactPropertyLinkViewSet,
                    CRMActivityViewSet,
                    CRMAnalyticsPipelineDropCheckView,
                    CRMAnalyticsProcurementDemandSyncView,
                    CRMAnalyticsProjectDemandSyncView,
                    CRMAnalyticsReportingOverviewView,
                    CRMAnalyticsWeeklyReportRunView,
                    FinancialAssessmentViewSet,
                    FollowUpRuleViewSet,
                    FollowUpTaskViewSet,
                    LeadActivityViewSet,
                    LeadDocumentEventViewSet,
                    LeadPaymentScenarioViewSet,
                    LeadProjectInterestViewSet,
                    LeadPropertyMatchViewSet,
                    LeadSourceViewSet,
                    LeadUnitPreferenceViewSet,
                    LeadViewSet,
                    MeetingRecordViewSet,
                    OpportunityDealViewSet,
                    OpportunityOverviewView,
                    PipelineOverviewView,
                    PropertyMatchOverviewView,
                    PropertyMatchRefreshView,
                    ReservationOverviewView,
                    UnitReservationViewSet,
)

router = DefaultRouter()
router.register(r"leads", LeadViewSet, basename="lead")
router.register(r"sources", LeadSourceViewSet, basename="lead-source")
router.register(r"brokers", BrokerViewSet, basename="broker")
router.register(r"assessments", FinancialAssessmentViewSet, basename="financial-assessment")
router.register(r"tiers", BrokerTierViewSet, basename="broker-tier")
router.register(r"commission-structures", CommissionStructureViewSet, basename="commission-structure")
router.register(r"commission-earnings", CommissionEarningViewSet, basename="commission-earning")

# Communication Engine
router.register(r"communications", CommunicationLogViewSet, basename="communication-log")
router.register(r"campaigns", CampaignViewSet, basename="campaign")
router.register(r"follow-up-rules", FollowUpRuleViewSet, basename="follow-up-rule")
router.register(r"follow-up-tasks", FollowUpTaskViewSet, basename="follow-up-task")
router.register(r"document-events", LeadDocumentEventViewSet, basename="lead-document-event")
router.register(r"meetings", MeetingRecordViewSet, basename="meeting-record")
router.register(r"contacts", ContactAccountViewSet, basename="contact-account")
router.register(r"opportunities", OpportunityDealViewSet, basename="opportunity-deal")
router.register(r"property-matches", LeadPropertyMatchViewSet, basename="lead-property-match")
router.register(r"activities", CRMActivityViewSet, basename="crm-activity")

# Reservation & Conversion
router.register(r"reservations", UnitReservationViewSet, basename="reservation")

# Nested routers for lead sub-resources
interest_router = DefaultRouter()
interest_router.register(r"", LeadProjectInterestViewSet, basename="lead-project-interest")

preference_router = DefaultRouter()
preference_router.register(r"", LeadUnitPreferenceViewSet, basename="lead-unit-preference")

activity_router = DefaultRouter()
activity_router.register(r"", LeadActivityViewSet, basename="lead-activity")

scenario_router = DefaultRouter()
scenario_router.register(r"", LeadPaymentScenarioViewSet, basename="payment-scenario")

contact_interaction_router = DefaultRouter()
contact_interaction_router.register(r"", ContactInteractionViewSet, basename="contact-interaction")

contact_deal_link_router = DefaultRouter()
contact_deal_link_router.register(r"", ContactDealLinkViewSet, basename="contact-deal-link")

contact_property_link_router = DefaultRouter()
contact_property_link_router.register(r"", ContactPropertyLinkViewSet, basename="contact-property-link")

contact_document_router = DefaultRouter()
contact_document_router.register(r"", ContactDocumentViewSet, basename="contact-document")

contact_compliance_router = DefaultRouter()
contact_compliance_router.register(r"", ContactComplianceReviewViewSet, basename="contact-compliance-review")

urlpatterns = [
    path("activities-tasks/overview/", ActivityTaskManagementOverviewView.as_view(), name="activities-task-overview"),
    path("analytics-reporting/overview/", CRMAnalyticsReportingOverviewView.as_view(), name="crm-analytics-reporting-overview"),
    path("analytics-reporting/run-weekly-report/", CRMAnalyticsWeeklyReportRunView.as_view(), name="crm-analytics-weekly-report-run"),
    path("analytics-reporting/check-pipeline-drop/", CRMAnalyticsPipelineDropCheckView.as_view(), name="crm-analytics-pipeline-drop-check"),
    path("analytics-reporting/sync-project-demand-insights/", CRMAnalyticsProjectDemandSyncView.as_view(), name="crm-analytics-project-demand-sync"),
    path("analytics-reporting/sync-procurement-demand-insights/", CRMAnalyticsProcurementDemandSyncView.as_view(), name="crm-analytics-procurement-demand-sync"),
    path("pipeline/overview/", PipelineOverviewView.as_view(), name="pipeline-overview"),
    path("contacts/overview/", ContactAccountOverviewView.as_view(), name="contact-account-overview"),
    path("brokers/performance/", BrokerPerformanceOverviewView.as_view(), name="broker-performance-overview"),
    path("communications/overview/", CommunicationOverviewView.as_view(), name="communication-overview"),
    path("reservations/overview/", ReservationOverviewView.as_view(), name="reservation-overview"),
    path("opportunities/overview/", OpportunityOverviewView.as_view(), name="opportunity-overview"),
    path("property-matches/overview/", PropertyMatchOverviewView.as_view(), name="property-match-overview"),
    path("property-matches/refresh/", PropertyMatchRefreshView.as_view(), name="property-match-refresh"),
    path("leads/<int:lead_pk>/interests/", include(interest_router.urls)),
    path("leads/<int:lead_pk>/preferences/", include(preference_router.urls)),
    path("leads/<int:lead_pk>/activities/", include(activity_router.urls)),
    path("assessments/<int:assessment_pk>/scenarios/", include(scenario_router.urls)),
    path("contacts/<int:contact_pk>/interactions/", include(contact_interaction_router.urls)),
    path("contacts/<int:contact_pk>/deal-links/", include(contact_deal_link_router.urls)),
    path("contacts/<int:contact_pk>/property-links/", include(contact_property_link_router.urls)),
    path("contacts/<int:contact_pk>/documents/", include(contact_document_router.urls)),
    path("contacts/<int:contact_pk>/compliance-reviews/", include(contact_compliance_router.urls)),
] + router.urls

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    SupportAutomationOverviewView,
                    SupportAutomationRuleViewSet,
                    SupportAutomationRunViewSet,
                    SupportCommunicationLogViewSet,
                    SupportCommunicationOverviewView,
                    SupportDeskConfigurationOverviewView,
                    SupportDeskOverviewView,
                    SupportDeskReportsOverviewView,
                    SupportKnowledgeArticleViewSet,
                    SupportKnowledgeBaseOverviewView,
                    SupportRequestViewSet,
                    SupportSlaEscalationsOverviewView,
                    SupportSlaEscalationTicketViewSet,
                    SupportSlaPolicyViewSet,
                    SupportTicketViewSet,
)

router = DefaultRouter()
router.register(r"tickets", SupportTicketViewSet, basename="support-ticket")
router.register(r"requests", SupportRequestViewSet, basename="support-request")
router.register(r"communication/logs", SupportCommunicationLogViewSet, basename="support-communication-log")
router.register(r"automation/rules", SupportAutomationRuleViewSet, basename="support-automation-rule")
router.register(r"automation/runs", SupportAutomationRunViewSet, basename="support-automation-run")
router.register(r"knowledge-base/articles", SupportKnowledgeArticleViewSet, basename="support-knowledge-article")
router.register(r"sla-escalations/policies", SupportSlaPolicyViewSet, basename="support-sla-policy")
router.register(r"sla-escalations/tickets", SupportSlaEscalationTicketViewSet, basename="support-sla-ticket")

urlpatterns = [
    path("overview/", SupportDeskOverviewView.as_view(), name="support-desk-overview"),
    path("communication/overview/", SupportCommunicationOverviewView.as_view(), name="support-communication-overview"),
    path("automation/overview/", SupportAutomationOverviewView.as_view(), name="support-automation-overview"),
    path("reports/overview/", SupportDeskReportsOverviewView.as_view(), name="support-desk-reports-overview"),
    path("configuration/overview/", SupportDeskConfigurationOverviewView.as_view(), name="support-desk-configuration-overview"),
    path("knowledge-base/overview/", SupportKnowledgeBaseOverviewView.as_view(), name="support-knowledge-base-overview"),
    path("sla-escalations/overview/", SupportSlaEscalationsOverviewView.as_view(), name="support-sla-escalations-overview"),
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .portal_views import (
    PartnerPortalApprovalsView,
    PartnerPortalCommunicationView,
    PartnerPortalComplianceView,
    PartnerPortalContextView,
    PartnerPortalDashboardView,
    PartnerPortalDocumentVaultView,
    PartnerPortalFinancialView,
    PartnerPortalLegalAcceptView,
    PartnerPortalLegalStatusView,
    PartnerPortalNotificationsView,
    PartnerPortalProfilePhotoView,
    PartnerPortalProfileView,
)
from .views import (
    OnboardingTemplateDocumentRequirementViewSet,
    OnboardingTemplateStageViewSet,
    OnboardingTemplateViewSet,
    PartnerEntitlementViewSet,
    PartnerOnboardingAuditLogViewSet,
    PartnerOnboardingCaseViewSet,
    PartnerOnboardingIntakeDocumentViewSet,
    PartnerOnboardingOverviewView,
)

router = DefaultRouter()
router.register(r"templates", OnboardingTemplateViewSet, basename="partner-onboarding-template")
router.register(r"cases", PartnerOnboardingCaseViewSet, basename="partner-onboarding-case")
router.register(r"entitlements", PartnerEntitlementViewSet, basename="partner-entitlement")
router.register(r"audit-events", PartnerOnboardingAuditLogViewSet, basename="partner-onboarding-audit-event")
router.register(r"intake-documents", PartnerOnboardingIntakeDocumentViewSet, basename="partner-onboarding-intake-document")

template_stage_router = DefaultRouter()
template_stage_router.register(r"", OnboardingTemplateStageViewSet, basename="partner-onboarding-template-stage")
template_requirement_router = DefaultRouter()
template_requirement_router.register(
    r"",
    OnboardingTemplateDocumentRequirementViewSet,
    basename="partner-onboarding-template-document-requirement",
)
case_intake_router = DefaultRouter()
case_intake_router.register(r"", PartnerOnboardingIntakeDocumentViewSet, basename="partner-onboarding-case-intake-document")

urlpatterns = [
    path("templates/<int:template_pk>/stages/", include(template_stage_router.urls)),
    path("templates/<int:template_pk>/document-requirements/", include(template_requirement_router.urls)),
    path("cases/<int:case_pk>/intake-documents/", include(case_intake_router.urls)),
    path("portal/context/", PartnerPortalContextView.as_view(), name="partner-portal-context"),
    path("portal/legal/", PartnerPortalLegalStatusView.as_view(), name="partner-portal-legal-status"),
    path("portal/legal/accept/", PartnerPortalLegalAcceptView.as_view(), name="partner-portal-legal-accept"),
    path("portal/dashboard/", PartnerPortalDashboardView.as_view(), name="partner-portal-dashboard"),
    path("portal/documents/", PartnerPortalDocumentVaultView.as_view(), name="partner-portal-documents"),
    path("portal/communications/", PartnerPortalCommunicationView.as_view(), name="partner-portal-communications"),
    path("portal/approvals/", PartnerPortalApprovalsView.as_view(), name="partner-portal-approvals"),
    path("portal/financial/", PartnerPortalFinancialView.as_view(), name="partner-portal-financial"),
    path("portal/compliance/", PartnerPortalComplianceView.as_view(), name="partner-portal-compliance"),
    path("portal/notifications/", PartnerPortalNotificationsView.as_view(), name="partner-portal-notifications"),
    path("portal/profile/", PartnerPortalProfileView.as_view(), name="partner-portal-profile"),
    path("portal/profile/photo/", PartnerPortalProfilePhotoView.as_view(), name="partner-portal-profile-photo"),
    path("overview/", PartnerOnboardingOverviewView.as_view(), name="partner-onboarding-overview"),
    path("", include(router.urls)),
]

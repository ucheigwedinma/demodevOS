from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    ComplianceAuditViewSet,
                    ComplianceRequirementViewSet,
                    ComplianceViolationViewSet,
                    PropertyComplianceViewSet,
)

requirements_router = DefaultRouter()
requirements_router.register("", ComplianceRequirementViewSet, basename="compliance-requirement")

tracker_router = DefaultRouter()
tracker_router.register("", PropertyComplianceViewSet, basename="property-compliance")

violations_router = DefaultRouter()
violations_router.register("", ComplianceViolationViewSet, basename="compliance-violation")

audits_router = DefaultRouter()
audits_router.register("", ComplianceAuditViewSet, basename="compliance-audit")

urlpatterns = [
    path("requirements/", include(requirements_router.urls)),
    path("tracker/", include(tracker_router.urls)),
    path("violations/", include(violations_router.urls)),
    path("audits/", include(audits_router.urls)),
]

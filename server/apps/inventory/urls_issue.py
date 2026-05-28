from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConsumptionTrackingDashboardView, MaterialIssueDashboardView, MaterialIssueLineViewSet, MaterialIssueViewSet, VarianceInvestigationViewSet

router = DefaultRouter()
router.register(r"", MaterialIssueViewSet, basename="material-issue")

line_router = DefaultRouter()
line_router.register(r"", MaterialIssueLineViewSet, basename="material-issue-line")

variance_router = DefaultRouter()
variance_router.register(r"", VarianceInvestigationViewSet, basename="variance-investigation")

urlpatterns = [
    path("dashboard/", MaterialIssueDashboardView.as_view(), name="material-issue-dashboard"),
    path("consumption-tracking/", ConsumptionTrackingDashboardView.as_view(), name="consumption-tracking"),
    path("variance-investigations/", include(variance_router.urls)),
] + router.urls + [
    path("<int:issue_pk>/lines/", include(line_router.urls)),
]

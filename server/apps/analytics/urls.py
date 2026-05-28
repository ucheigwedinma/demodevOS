from django.urls import path

from .views import (
    ApprovalTimeDrilldownView,
    BoardKpiView,
    BudgetOverrunDrilldownView,
    CostVarianceDrilldownView,
    CustomDashboardViewSet,
    EmergencyPurchasesDrilldownView,
    PortfolioAnalyticsView,
    ProcurementCycleDrilldownView,
    RiskAlertAckView,
    RiskAlertsView,
    SnapshotHealthView,
    VendorReliabilityDrilldownView,
)

urlpatterns = [
    path("portfolio/", PortfolioAnalyticsView.as_view(), name="portfolio-analytics"),
    path("board-kpis/", BoardKpiView.as_view(), name="board-kpis"),
    path("risk-alerts/", RiskAlertsView.as_view(), name="risk-alerts"),
    path("risk-alerts/<str:alert_id>/ack/", RiskAlertAckView.as_view(), name="risk-alert-ack"),
    path("health/", SnapshotHealthView.as_view(), name="analytics-health"),
    # Drilldowns
    path("drilldowns/procurement-cycle/", ProcurementCycleDrilldownView.as_view(), name="drilldown-procurement-cycle"),
    path("drilldowns/cost-variance/", CostVarianceDrilldownView.as_view(), name="drilldown-cost-variance"),
    path("drilldowns/vendor-reliability/", VendorReliabilityDrilldownView.as_view(), name="drilldown-vendor-reliability"),
    path("drilldowns/emergency-purchases/", EmergencyPurchasesDrilldownView.as_view(), name="drilldown-emergency-purchases"),
    path("drilldowns/budget-overrun/", BudgetOverrunDrilldownView.as_view(), name="drilldown-budget-overrun"),
    path("drilldowns/approval-time/", ApprovalTimeDrilldownView.as_view(), name="drilldown-approval-time"),
    # Custom dashboards
    path("dashboards/", CustomDashboardViewSet.as_view({"get": "list", "post": "create"}), name="custom-dashboard-list"),
    path("dashboards/<int:pk>/", CustomDashboardViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="custom-dashboard-detail"),
]

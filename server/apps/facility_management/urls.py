from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .asset_views import FacilityAssetOverviewView, FacilityAssetViewSet
from .document_drawings_views import (
                                      FacilityDocumentsLookupsView,
                                      FacilityDocumentsOverviewView,
                                      FacilityDocumentsWorkflowView,
                                      FacilityDocumentViewSet,
)
from .health_safety_views import (
                                      FacilityComplianceChecklistViewSet,
                                      FacilityHealthSafetyInspectionViewSet,
                                      FacilityHealthSafetyLookupsView,
                                      FacilityHealthSafetyOverviewView,
                                      FacilityHealthSafetyWorkflowView,
                                      FacilityIncidentViewSet,
                                      FacilityRegulatoryDocumentViewSet,
                                      FacilitySafetyAuditLogViewSet,
)
from .maintenance_views import (
                                      FacilityMaintenanceOverviewView,
                                      FacilityMaintenancePredictiveAlertViewSet,
                                      FacilityMaintenancePredictiveRuleViewSet,
                                      FacilityMaintenancePreventiveViewSet,
                                      FacilityMaintenanceWorkflowView,
                                      FacilityMaintenanceWorkOrderViewSet,
)
from .registry_views import (
                                      FacilityAvailableUnitViewSet,
                                      FacilityFloorViewSet,
                                      FacilityRegistryOverviewView,
                                      FacilityUnitSpaceViewSet,
                                      FacilityViewSet,
                                      FacilityZoneViewSet,
)
from .service_request_views import (
                                      FacilityBillingTicketViewSet,
                                      FacilityInvoiceViewSet,
                                      FacilityServiceRequestsLookupsView,
                                      FacilityServiceRequestsOverviewView,
                                      FacilityServiceRequestViewSet,
                                      FacilityServiceRequestWorkflowView,
)
from .space_occupancy_views import (
                                      FacilitySpaceAllocationViewSet,
                                      FacilitySpaceBookingViewSet,
                                      FacilitySpaceOccupancyLookupsView,
                                      FacilitySpaceOccupancyOverviewView,
                                      FacilitySpaceOccupancyWorkflowView,
                                      FacilitySpaceProfileViewSet,
)
from .utility_views import (
                                      FacilityUtilitiesLookupsView,
                                      FacilityUtilitiesOverviewView,
                                      FacilityUtilitiesWorkflowView,
                                      FacilityUtilityBillViewSet,
                                      FacilityUtilityMeterReadingViewSet,
                                      FacilityUtilityMeterViewSet,
)
from .views import FacilityDashboardOverviewView

registry_router = DefaultRouter()
registry_router.register(r"registry/facilities", FacilityViewSet, basename="facility-registry-facility")
registry_router.register(r"registry/floors", FacilityFloorViewSet, basename="facility-registry-floor")
registry_router.register(r"registry/zones", FacilityZoneViewSet, basename="facility-registry-zone")
registry_router.register(r"registry/unit-spaces", FacilityUnitSpaceViewSet, basename="facility-registry-unit-space")
registry_router.register(r"registry/units", FacilityAvailableUnitViewSet, basename="facility-registry-unit")
registry_router.register(r"assets/register", FacilityAssetViewSet, basename="facility-asset-register")
registry_router.register(r"maintenance/work-orders", FacilityMaintenanceWorkOrderViewSet, basename="facility-maintenance-work-order")
registry_router.register(r"maintenance/preventive", FacilityMaintenancePreventiveViewSet, basename="facility-maintenance-preventive")
registry_router.register(r"maintenance/predictive-rules", FacilityMaintenancePredictiveRuleViewSet, basename="facility-maintenance-predictive-rule")
registry_router.register(r"maintenance/predictive-alerts", FacilityMaintenancePredictiveAlertViewSet, basename="facility-maintenance-predictive-alert")
registry_router.register(r"service-requests/requests", FacilityServiceRequestViewSet, basename="facility-service-request")
registry_router.register(r"service-requests/billing-tickets", FacilityBillingTicketViewSet, basename="facility-billing-ticket")
registry_router.register(r"service-requests/invoices", FacilityInvoiceViewSet, basename="facility-service-request-invoice")
registry_router.register(r"space-occupancy/profiles", FacilitySpaceProfileViewSet, basename="facility-space-profile")
registry_router.register(r"space-occupancy/allocations", FacilitySpaceAllocationViewSet, basename="facility-space-allocation")
registry_router.register(r"space-occupancy/bookings", FacilitySpaceBookingViewSet, basename="facility-space-booking")
registry_router.register(r"utilities/meters", FacilityUtilityMeterViewSet, basename="facility-utility-meter")
registry_router.register(r"utilities/readings", FacilityUtilityMeterReadingViewSet, basename="facility-utility-reading")
registry_router.register(r"utilities/bills", FacilityUtilityBillViewSet, basename="facility-utility-bill")
registry_router.register(r"documents/records", FacilityDocumentViewSet, basename="facility-document")
registry_router.register(r"health-safety/incidents", FacilityIncidentViewSet, basename="facility-health-safety-incident")
registry_router.register(
    r"health-safety/inspections",
    FacilityHealthSafetyInspectionViewSet,
    basename="facility-health-safety-inspection",
)
registry_router.register(
    r"health-safety/checklists",
    FacilityComplianceChecklistViewSet,
    basename="facility-health-safety-checklist",
)
registry_router.register(
    r"health-safety/regulatory-documents",
    FacilityRegulatoryDocumentViewSet,
    basename="facility-health-safety-regulatory-document",
)
registry_router.register(
    r"health-safety/audit-logs",
    FacilitySafetyAuditLogViewSet,
    basename="facility-health-safety-audit-log",
)

urlpatterns = [
    path(
        "dashboard/overview/",
        FacilityDashboardOverviewView.as_view(),
        name="facility_dashboard_overview",
    ),
    path(
        "registry/overview/",
        FacilityRegistryOverviewView.as_view(),
        name="facility_registry_overview",
    ),
    path(
        "assets/overview/",
        FacilityAssetOverviewView.as_view(),
        name="facility_asset_overview",
    ),
    path(
        "maintenance/overview/",
        FacilityMaintenanceOverviewView.as_view(),
        name="facility_maintenance_overview",
    ),
    path(
        "maintenance/sync/",
        FacilityMaintenanceWorkflowView.as_view(),
        name="facility_maintenance_sync",
    ),
    path(
        "service-requests/overview/",
        FacilityServiceRequestsOverviewView.as_view(),
        name="facility_service_requests_overview",
    ),
    path(
        "service-requests/lookups/",
        FacilityServiceRequestsLookupsView.as_view(),
        name="facility_service_requests_lookups",
    ),
    path(
        "service-requests/sync/",
        FacilityServiceRequestWorkflowView.as_view(),
        name="facility_service_requests_sync",
    ),
    path(
        "space-occupancy/overview/",
        FacilitySpaceOccupancyOverviewView.as_view(),
        name="facility_space_occupancy_overview",
    ),
    path(
        "space-occupancy/lookups/",
        FacilitySpaceOccupancyLookupsView.as_view(),
        name="facility_space_occupancy_lookups",
    ),
    path(
        "space-occupancy/sync/",
        FacilitySpaceOccupancyWorkflowView.as_view(),
        name="facility_space_occupancy_sync",
    ),
    path(
        "utilities/overview/",
        FacilityUtilitiesOverviewView.as_view(),
        name="facility_utilities_overview",
    ),
    path(
        "utilities/lookups/",
        FacilityUtilitiesLookupsView.as_view(),
        name="facility_utilities_lookups",
    ),
    path(
        "utilities/sync/",
        FacilityUtilitiesWorkflowView.as_view(),
        name="facility_utilities_sync",
    ),
    path(
        "documents/overview/",
        FacilityDocumentsOverviewView.as_view(),
        name="facility_documents_overview",
    ),
    path(
        "documents/lookups/",
        FacilityDocumentsLookupsView.as_view(),
        name="facility_documents_lookups",
    ),
    path(
        "documents/sync/",
        FacilityDocumentsWorkflowView.as_view(),
        name="facility_documents_sync",
    ),
    path(
        "health-safety/overview/",
        FacilityHealthSafetyOverviewView.as_view(),
        name="facility_health_safety_overview",
    ),
    path(
        "health-safety/lookups/",
        FacilityHealthSafetyLookupsView.as_view(),
        name="facility_health_safety_lookups",
    ),
    path(
        "health-safety/sync/",
        FacilityHealthSafetyWorkflowView.as_view(),
        name="facility_health_safety_sync",
    ),
    path("", include(registry_router.urls)),
]

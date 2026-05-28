from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .operations_views import (
                               BillingSyncView,
                               CommunicationsSyncView,
                               ComplaintsSyncView,
                               DocumentsSyncView,
                               InspectionsSyncView,
                               LeaseAgreementViewSet,
                               LeaseOccupancySyncView,
                               LeaseRenewalRequestViewSet,
                               LeaseTerminationRequestViewSet,
                               OccupancyRecordViewSet,
                               PaymentsSyncView,
                               RecurringChargeRuleViewSet,
                               ServiceRequestsSyncView,
                               TenantBillingInvoiceListView,
                               TenantBillingOverviewView,
                               TenantBroadcastViewSet,
                               TenantCommunicationLogListView,
                               TenantCommunicationsOverviewView,
                               TenantComplaintsOverviewView,
                               TenantComplaintViewSet,
                               TenantDocumentRecordViewSet,
                               TenantDocumentsOverviewView,
                               TenantInspectionsOverviewView,
                               TenantInspectionViewSet,
                               TenantLeaseOccupancyOverviewView,
                               TenantOperationsLookupsView,
                               TenantPaymentsOverviewView,
                               TenantPaymentsRecordView,
                               TenantReportsOverviewView,
                               TenantServiceRequestFeedbackView,
                               TenantServiceRequestListCreateView,
                               TenantServiceRequestsOverviewView,
)
from .views import (
                               TenantDashboardLayoutView,
                               TenantDashboardOverviewView,
                               TenantDashboardRevenueAnalyticsView,
                               TenantProfileViewSet,
                               TenantRegistryExportView,
                               TenantRegistryLookupView,
                               TenantRegistryOverviewView,
)

router = DefaultRouter()
router.register(r"profiles", TenantProfileViewSet, basename="tenant-profile")
router.register(r"lease-occupancy/leases", LeaseAgreementViewSet, basename="tenant-lease-agreement")
router.register(r"lease-occupancy/occupancies", OccupancyRecordViewSet, basename="tenant-occupancy-record")
router.register(r"lease-occupancy/renewals", LeaseRenewalRequestViewSet, basename="tenant-lease-renewal")
router.register(r"lease-occupancy/terminations", LeaseTerminationRequestViewSet, basename="tenant-lease-termination")
router.register(r"billing/charge-rules", RecurringChargeRuleViewSet, basename="tenant-recurring-charge-rule")
router.register(r"communications/broadcasts", TenantBroadcastViewSet, basename="tenant-broadcast")
router.register(r"documents/records", TenantDocumentRecordViewSet, basename="tenant-document-record")
router.register(r"inspections/records", TenantInspectionViewSet, basename="tenant-inspection")
router.register(r"complaints/records", TenantComplaintViewSet, basename="tenant-complaint")

urlpatterns = [
    path("dashboard/layout/", TenantDashboardLayoutView.as_view(), name="tenant-dashboard-layout"),
    path("dashboard/overview/", TenantDashboardOverviewView.as_view(), name="tenant-dashboard-overview"),
    path("dashboard/revenue-analytics/", TenantDashboardRevenueAnalyticsView.as_view(), name="tenant-dashboard-revenue-analytics"),
    path("registry/overview/", TenantRegistryOverviewView.as_view(), name="tenant-registry-overview"),
    path("registry/lookups/", TenantRegistryLookupView.as_view(), name="tenant-registry-lookups"),
    path("profiles/export/", TenantRegistryExportView.as_view(), name="tenant-registry-export"),
    path("operations/lookups/", TenantOperationsLookupsView.as_view(), name="tenant-operations-lookups"),
    path("lease-occupancy/overview/", TenantLeaseOccupancyOverviewView.as_view(), name="tenant-lease-occupancy-overview"),
    path("lease-occupancy/sync/", LeaseOccupancySyncView.as_view(), name="tenant-lease-occupancy-sync"),
    path("billing/overview/", TenantBillingOverviewView.as_view(), name="tenant-billing-overview"),
    path("billing/invoices/", TenantBillingInvoiceListView.as_view(), name="tenant-billing-invoices"),
    path("billing/sync/", BillingSyncView.as_view(), name="tenant-billing-sync"),
    path("payments/overview/", TenantPaymentsOverviewView.as_view(), name="tenant-payments-overview"),
    path("payments/records/", TenantPaymentsRecordView.as_view(), name="tenant-payments-records"),
    path("payments/sync/", PaymentsSyncView.as_view(), name="tenant-payments-sync"),
    path("service-requests/overview/", TenantServiceRequestsOverviewView.as_view(), name="tenant-service-requests-overview"),
    path("service-requests/requests/", TenantServiceRequestListCreateView.as_view(), name="tenant-service-requests"),
    path("service-requests/requests/<int:request_id>/feedback/", TenantServiceRequestFeedbackView.as_view(), name="tenant-service-request-feedback"),
    path("service-requests/sync/", ServiceRequestsSyncView.as_view(), name="tenant-service-requests-sync"),
    path("communications/overview/", TenantCommunicationsOverviewView.as_view(), name="tenant-communications-overview"),
    path("communications/logs/", TenantCommunicationLogListView.as_view(), name="tenant-communications-logs"),
    path("communications/sync/", CommunicationsSyncView.as_view(), name="tenant-communications-sync"),
    path("documents/overview/", TenantDocumentsOverviewView.as_view(), name="tenant-documents-overview"),
    path("documents/sync/", DocumentsSyncView.as_view(), name="tenant-documents-sync"),
    path("inspections/overview/", TenantInspectionsOverviewView.as_view(), name="tenant-inspections-overview"),
    path("inspections/sync/", InspectionsSyncView.as_view(), name="tenant-inspections-sync"),
    path("complaints/overview/", TenantComplaintsOverviewView.as_view(), name="tenant-complaints-overview"),
    path("complaints/sync/", ComplaintsSyncView.as_view(), name="tenant-complaints-sync"),
    path("reports/overview/", TenantReportsOverviewView.as_view(), name="tenant-reports-overview"),
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    AssetComponentViewSet,
                    InspectionViewSet,
                    MaintenanceVendorViewSet,
                    PreventiveScheduleViewSet,
                    PropertyDocumentViewSet,
                    PropertyEncumbranceViewSet,
                    PropertyImageViewSet,
                    PropertyInventoryEventViewSet,
                    PropertyInventoryViewSet,
                    PropertyOwnershipViewSet,
                    PropertyUnitViewSet,
                    PropertyValuationViewSet,
                    PropertyViewSet,
                    ServiceRequestViewSet,
                    UnitViewSet,
                    WorkOrderViewSet,
)

router = DefaultRouter()
router.register(r"", PropertyViewSet, basename="property")
router.register(r"units", UnitViewSet, basename="unit")

unit_router = DefaultRouter()
unit_router.register(r"", PropertyUnitViewSet, basename="property-unit")

image_router = DefaultRouter()
image_router.register(r"", PropertyImageViewSet, basename="property-image")

document_router = DefaultRouter()
document_router.register(r"", PropertyDocumentViewSet, basename="property-document")

valuation_router = DefaultRouter()
valuation_router.register(r"", PropertyValuationViewSet, basename="property-valuation")

ownership_router = DefaultRouter()
ownership_router.register(r"", PropertyOwnershipViewSet, basename="property-ownership")

encumbrance_router = DefaultRouter()
encumbrance_router.register(r"", PropertyEncumbranceViewSet, basename="property-encumbrance")

# --- Maintenance module routers ---
maintenance_vendor_router = DefaultRouter()
maintenance_vendor_router.register(r"", MaintenanceVendorViewSet, basename="maintenance-vendor")

asset_component_router = DefaultRouter()
asset_component_router.register(r"", AssetComponentViewSet, basename="asset-component")

work_order_router = DefaultRouter()
work_order_router.register(r"", WorkOrderViewSet, basename="work-order")

preventive_router = DefaultRouter()
preventive_router.register(r"", PreventiveScheduleViewSet, basename="preventive-schedule")

inspection_router = DefaultRouter()
inspection_router.register(r"", InspectionViewSet, basename="inspection")

service_request_router = DefaultRouter()
service_request_router.register(r"", ServiceRequestViewSet, basename="service-request")

inventory_router = DefaultRouter()
inventory_router.register(r"", PropertyInventoryViewSet, basename="property-inventory")

inventory_event_router = DefaultRouter()
inventory_event_router.register(r"", PropertyInventoryEventViewSet, basename="property-inventory-event")

urlpatterns = [
    path("", include(router.urls)),
    path("<int:property_pk>/units/", include(unit_router.urls)),
    path("<int:property_pk>/images/", include(image_router.urls)),
    path("<int:property_pk>/documents/", include(document_router.urls)),
    path("<int:property_pk>/valuations/", include(valuation_router.urls)),
    path("<int:property_pk>/ownerships/", include(ownership_router.urls)),
    path("<int:property_pk>/encumbrances/", include(encumbrance_router.urls)),
    # Maintenance module
    path("maintenance/vendors/", include(maintenance_vendor_router.urls)),
    path("maintenance/assets/", include(asset_component_router.urls)),
    path("maintenance/work-orders/", include(work_order_router.urls)),
    path("maintenance/preventive/", include(preventive_router.urls)),
    path("maintenance/inspections/", include(inspection_router.urls)),
    path("maintenance/service-requests/", include(service_request_router.urls)),
    # Property Inventory
    path("inventory/", include(inventory_router.urls)),
    path("inventory/<int:inventory_pk>/events/", include(inventory_event_router.urls)),
]

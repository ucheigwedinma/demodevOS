from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InventoryItemViewSet,
    InventoryOverviewView,
    InventoryStockViewSet,
    InventoryTransactionViewSet,
    WarehouseDashboardView,
    WarehouseViewSet,
)

warehouse_router = DefaultRouter()
warehouse_router.register(r"", WarehouseViewSet, basename="inventory-warehouse")

item_router = DefaultRouter()
item_router.register(r"", InventoryItemViewSet, basename="inventory-item")

stock_router = DefaultRouter()
stock_router.register(r"", InventoryStockViewSet, basename="inventory-stock")

transaction_router = DefaultRouter()
transaction_router.register(r"", InventoryTransactionViewSet, basename="inventory-transaction")

urlpatterns = [
    path("overview/", InventoryOverviewView.as_view(), name="inventory-overview"),
    path("warehouse-dashboard/", WarehouseDashboardView.as_view(), name="warehouse-dashboard"),
    path("warehouses/", include(warehouse_router.urls)),
    path("items/", include(item_router.urls)),
    path("stocks/", include(stock_router.urls)),
    path("transactions/", include(transaction_router.urls)),
]


from django.urls import path

from .views import (
    GoodsReceiptDashboardView,
    GoodsReceiptDocumentView,
    GoodsReceiptInspectView,
    GoodsReceiptLogArrivalView,
    GoodsReceiptPhotoUploadView,
    GoodsReceiptPOLookupView,
    ProcurementBridgeView,
    ProcurementIntegrationView,
)

urlpatterns = [
    path("", ProcurementIntegrationView.as_view(), name="procurement-integration"),
    path("bridge/", ProcurementBridgeView.as_view(), name="procurement-bridge"),
    path("goods-receipt-dashboard/", GoodsReceiptDashboardView.as_view(), name="goods-receipt-dashboard"),
    path("po-lookup/", GoodsReceiptPOLookupView.as_view(), name="goods-receipt-po-lookup"),
    path("log-arrival/", GoodsReceiptLogArrivalView.as_view(), name="goods-receipt-log-arrival"),
    path("inspect/", GoodsReceiptInspectView.as_view(), name="goods-receipt-inspect"),
    path("grn-document/", GoodsReceiptDocumentView.as_view(), name="goods-receipt-document"),
    path("grn-photos/", GoodsReceiptPhotoUploadView.as_view(), name="goods-receipt-photos"),
]

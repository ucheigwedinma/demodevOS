from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MaterialTransferDashboardView, MaterialTransferLineViewSet, MaterialTransferViewSet, MaterialTransferWaybillView

router = DefaultRouter()
router.register(r"", MaterialTransferViewSet, basename="material-transfer")

line_router = DefaultRouter()
line_router.register(r"", MaterialTransferLineViewSet, basename="material-transfer-line")

urlpatterns = [
    path("dashboard/", MaterialTransferDashboardView.as_view(), name="material-transfer-dashboard"),
    path("waybill/", MaterialTransferWaybillView.as_view(), name="material-transfer-waybill"),
] + router.urls + [
    path("<int:transfer_pk>/lines/", include(line_router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ComparableSaleViewSet, ValuationAppealViewSet, ValuationRecordViewSet

records_router = DefaultRouter()
records_router.register("", ValuationRecordViewSet, basename="valuation-record")

comparables_router = DefaultRouter()
comparables_router.register("", ComparableSaleViewSet, basename="comparable-sale")

appeals_router = DefaultRouter()
appeals_router.register("", ValuationAppealViewSet, basename="valuation-appeal")

urlpatterns = [
    path("records/", include(records_router.urls)),
    path("comparables/", include(comparables_router.urls)),
    path("appeals/", include(appeals_router.urls)),
]

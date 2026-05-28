from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RateBookViewSet, RateItemViewSet, RateCompositeComponentViewSet

router = DefaultRouter()
router.register(r"", RateBookViewSet, basename="rate-book")

item_router = DefaultRouter()
item_router.register(r"", RateItemViewSet, basename="rate-item")

component_router = DefaultRouter()
component_router.register(r"", RateCompositeComponentViewSet, basename="rate-component")

urlpatterns = router.urls + [
    path("<int:book_pk>/items/", include(item_router.urls)),
    path("<int:book_pk>/items/<int:rate_pk>/components/", include(component_router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BOMViewSet

router = DefaultRouter()
router.register(r"", BOMViewSet, basename="bom")

urlpatterns = [
    path("", include(router.urls)),
]

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MaterialMasterViewSet

router = DefaultRouter()
router.register(r"", MaterialMasterViewSet, basename="material-master")

urlpatterns = [
    path("", include(router.urls)),
]

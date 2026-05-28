from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MaterialReturnDashboardView, MaterialReturnLineViewSet, MaterialReturnViewSet

router = DefaultRouter()
router.register(r"", MaterialReturnViewSet, basename="material-return")

line_router = DefaultRouter()
line_router.register(r"", MaterialReturnLineViewSet, basename="material-return-line")

urlpatterns = [
    path("dashboard/", MaterialReturnDashboardView.as_view(), name="material-return-dashboard"),
] + router.urls + [
    path("<int:return_pk>/lines/", include(line_router.urls)),
]

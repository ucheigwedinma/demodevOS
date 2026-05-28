from rest_framework.routers import DefaultRouter
from .views import BoqTaskMappingViewSet

router = DefaultRouter()
router.register(r"", BoqTaskMappingViewSet, basename="boq-mapping")

urlpatterns = router.urls

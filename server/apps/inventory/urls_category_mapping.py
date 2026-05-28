from rest_framework.routers import DefaultRouter

from .views import BoqCategoryMappingViewSet

router = DefaultRouter()
router.register(r"", BoqCategoryMappingViewSet, basename="boq-category-mapping")

urlpatterns = router.urls

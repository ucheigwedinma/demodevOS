from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MaterialRequisitionViewSet, MaterialRequisitionLineViewSet, MaterialRequisitionCommentViewSet

router = DefaultRouter()
router.register(r"", MaterialRequisitionViewSet, basename="material-requisition")

line_router = DefaultRouter()
line_router.register(r"", MaterialRequisitionLineViewSet, basename="material-requisition-line")

comment_router = DefaultRouter()
comment_router.register(r"", MaterialRequisitionCommentViewSet, basename="material-requisition-comment")

urlpatterns = router.urls + [
    path("<int:requisition_pk>/lines/", include(line_router.urls)),
    path("<int:requisition_pk>/comments/", include(comment_router.urls)),
]

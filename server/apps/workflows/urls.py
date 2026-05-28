from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
                    ApplicableContentTypesView,
                    ApprovalPolicyViewSet,
                    MyApprovalsView,
                    UserDelegationViewSet,
                    WorkflowAuditEventViewSet,
                    WorkflowInstanceViewSet,
                    WorkflowTemplateStepViewSet,
                    WorkflowTemplateViewSet,
)

template_router = DefaultRouter()
template_router.register(r"", WorkflowTemplateViewSet, basename="workflow-template")

step_router = DefaultRouter()
step_router.register(r"", WorkflowTemplateStepViewSet, basename="workflow-template-step")

policy_router = DefaultRouter()
policy_router.register(r"", ApprovalPolicyViewSet, basename="approval-policy")

delegation_router = DefaultRouter()
delegation_router.register(r"", UserDelegationViewSet, basename="user-delegation")

instance_router = DefaultRouter()
instance_router.register(r"", WorkflowInstanceViewSet, basename="workflow-instance")

audit_router = DefaultRouter()
audit_router.register(r"", WorkflowAuditEventViewSet, basename="workflow-audit-event")

urlpatterns = [
    # Configuration
    path("templates/", include(template_router.urls)),
    path("templates/<int:template_pk>/steps/", include(step_router.urls)),
    path("policies/", include(policy_router.urls)),
    path("delegations/", include(delegation_router.urls)),
    # Runtime
    path("instances/", include(instance_router.urls)),
    path("my-approvals/", MyApprovalsView.as_view(), name="my-approvals"),
    path("audit-events/", include(audit_router.urls)),
    # Helpers
    path("content-types/", ApplicableContentTypesView.as_view(), name="workflow-content-types"),
]

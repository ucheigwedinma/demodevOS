"""
Generic workflow engine — resolve policies, submit objects for approval,
record decisions, handle delegation, evaluate conditions, and manage SLA.
"""

from __future__ import annotations

import json
import operator as op
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import (
    ApprovalPolicy,
    UserDelegation,
    WorkflowAuditEvent,
    WorkflowInstance,
    WorkflowStep,
    WorkflowTemplate,
    WorkflowTemplateStep,
)

# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------

@dataclass
class PolicyResolution:
    template: WorkflowTemplate
    policy: ApprovalPolicy | None


def resolve_policy_for_object(obj) -> PolicyResolution:
    """Find the first matching ApprovalPolicy for *obj*, falling back to
    the is_default template for the object's content type."""

    ct = ContentType.objects.get_for_model(obj)
    org = _get_org(obj)

    policies = (
        ApprovalPolicy.objects
        .filter(is_active=True, content_type=ct, organization=org)
        .select_related("template")
        .order_by("priority", "id")
    )

    for policy in policies:
        if not policy.template.is_active:
            continue
        amount = _resolve_field(obj, policy.amount_field)
        if amount is None:
            continue
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            continue
        if policy.min_amount is not None and amount < policy.min_amount:
            continue
        if policy.max_amount is not None and amount > policy.max_amount:
            continue
        return PolicyResolution(template=policy.template, policy=policy)

    # Fallback: default template for this content type
    fallback = (
        WorkflowTemplate.objects
        .filter(
            is_active=True,
            is_default=True,
            organization=org,
            applicable_content_types=ct,
        )
        .order_by("id")
        .first()
    )
    if not fallback:
        raise ValueError(
            f"No active workflow template or approval policy found for "
            f"{ct.app_label}.{ct.model}."
        )
    return PolicyResolution(template=fallback, policy=None)


# ---------------------------------------------------------------------------
# Submit for approval
# ---------------------------------------------------------------------------

def submit_for_approval(
    obj,
    user,
    *,
    template: WorkflowTemplate | None = None,
) -> WorkflowInstance:
    """Create a WorkflowInstance for *obj* and instantiate runtime steps.

    If *template* is not supplied the engine resolves one via
    `resolve_policy_for_object`.
    """

    ct = ContentType.objects.get_for_model(obj)

    # Prevent duplicate active workflows
    active = WorkflowInstance.objects.filter(
        content_type=ct,
        object_id=obj.pk,
        state__in=[
            WorkflowInstance.State.PENDING,
            WorkflowInstance.State.IN_PROGRESS,
        ],
    ).exists()
    if active:
        raise ValueError("An active workflow already exists for this object.")

    resolution = None
    if template is None:
        resolution = resolve_policy_for_object(obj)
        template = resolution.template

    with transaction.atomic():
        instance = WorkflowInstance.objects.create(
            content_type=ct,
            object_id=obj.pk,
            template=template,
            matched_policy=resolution.policy if resolution else None,
            state=WorkflowInstance.State.PENDING,
            submitted_by=user,
            submitted_at=timezone.now(),
        )

        _create_runtime_steps(instance, obj)

        # Advance to in_progress if first step(s) are ready
        instance.state = WorkflowInstance.State.IN_PROGRESS
        instance.save(update_fields=["state", "updated_at"])

        _log_event(
            instance,
            WorkflowAuditEvent.EventType.WORKFLOW_SUBMITTED,
            actor=user,
            payload={"template_id": template.pk, "template_name": template.name},
        )

    return instance


# ---------------------------------------------------------------------------
# Record step decision
# ---------------------------------------------------------------------------

def record_step_decision(
    *,
    step: WorkflowStep,
    decision: str,
    user,
    comments: str = "",
    request=None,
) -> WorkflowStep:
    """Record an approval/rejection on a step and advance the workflow."""

    if decision not in {
        WorkflowStep.Decision.APPROVED,
        WorkflowStep.Decision.REJECTED,
    }:
        raise ValueError("Decision must be 'approved' or 'rejected'.")

    instance = step.workflow_instance

    if instance.state not in {
        WorkflowInstance.State.PENDING,
        WorkflowInstance.State.IN_PROGRESS,
    }:
        raise ValueError("Workflow is not in a reviewable state.")

    if step.decision != WorkflowStep.Decision.PENDING:
        raise ValueError("This step has already been decided.")

    acting_on_behalf_of = None
    profile = getattr(user, "profile", None)
    assigned_role = getattr(profile, "assigned_role", None)
    user_role_slug = getattr(assigned_role, "slug", "") if assigned_role else ""
    is_org_admin = bool(profile and profile.role == "admin")

    from .process_authority import user_has_process_authority_for_step

    # Step actor authorization:
    # 1) direct user assignment (or delegated assignment)
    # 2) role assignment on step
    # 3) process authority registry
    # 4) org-admin override
    if step.approver_user_id:
        if step.approver_user_id != user.pk:
            delegation = resolve_delegate(
                user=step.approver_user,
                delegate=user,
                role_slug=step.approver_role_slug,
                content_type=instance.content_type,
            )
            if delegation is None and not is_org_admin:
                raise PermissionError(
                    "You are not authorised to decide on this step."
                )
            acting_on_behalf_of = step.approver_user if delegation else None
    elif step.approver_role_slug:
        if (
            user_role_slug != step.approver_role_slug
            and not user_has_process_authority_for_step(step, user)
            and not is_org_admin
        ):
            raise PermissionError(
                "You are not authorised to decide on this step."
            )
    elif not user_has_process_authority_for_step(step, user) and not is_org_admin:
        raise PermissionError(
            "You are not authorised to decide on this step."
        )

    # Contextual access evaluation for approval decisions.
    if request is not None:
        sub_module = _infer_sub_module_for_workflow_instance(instance)
        if sub_module:
            from apps.settings.contextual_access import evaluate_contextual_access

            contextual_decision = evaluate_contextual_access(
                user=user,
                request=request,
                module=sub_module.split(".", 1)[0],
                sub_module=sub_module,
                action="approve",
            )
            if not contextual_decision.allowed:
                raise PermissionError(
                    contextual_decision.reason
                    or "Access denied by contextual policy."
                )

    with transaction.atomic():
        now = timezone.now()
        step.decision = decision
        step.decided_by = user
        step.acting_on_behalf_of = acting_on_behalf_of
        step.comments = comments
        step.decided_at = now
        step.save(update_fields=[
            "decision", "decided_by", "acting_on_behalf_of",
            "comments", "decided_at", "updated_at",
        ])

        _log_event(
            instance,
            WorkflowAuditEvent.EventType.STEP_DECISION,
            actor=user,
            payload={
                "step_sequence": step.sequence,
                "step_name": step.name,
                "decision": decision,
                "comments": comments,
                "on_behalf_of": (
                    acting_on_behalf_of.pk if acting_on_behalf_of else None
                ),
            },
        )

        if decision == WorkflowStep.Decision.REJECTED:
            _complete_workflow(instance, WorkflowInstance.State.REJECTED, user)
            return step

        # Advance workflow
        _advance_workflow(instance, user)

    return step


# ---------------------------------------------------------------------------
# Cancel workflow
# ---------------------------------------------------------------------------

def cancel_workflow(instance: WorkflowInstance, user) -> WorkflowInstance:
    """Cancel a workflow instance, skipping remaining steps."""

    if instance.state in {
        WorkflowInstance.State.APPROVED,
        WorkflowInstance.State.REJECTED,
        WorkflowInstance.State.CANCELLED,
    }:
        raise ValueError("Workflow is already in a terminal state.")

    with transaction.atomic():
        instance.steps.filter(
            decision=WorkflowStep.Decision.PENDING,
        ).update(decision=WorkflowStep.Decision.SKIPPED)

        _complete_workflow(instance, WorkflowInstance.State.CANCELLED, user)

    return instance


# ---------------------------------------------------------------------------
# Delegation
# ---------------------------------------------------------------------------

def resolve_delegate(
    *,
    user,
    delegate,
    role_slug: str = "",
    content_type=None,
) -> UserDelegation | None:
    """Find an active delegation from *user* to *delegate*."""

    now = timezone.now()
    qs = UserDelegation.objects.filter(
        delegator=user,
        delegate=delegate,
        status=UserDelegation.Status.ACTIVE,
        starts_at__lte=now,
        ends_at__gte=now,
    )

    for delegation in qs:
        if delegation.role_scope_id:
            if delegation.role_scope.slug != role_slug:
                continue
        if delegation.content_type_scope_id:
            if content_type and delegation.content_type_scope_id != content_type.pk:
                continue
        return delegation

    return None


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------

_OPERATORS = {
    "gt": op.gt,
    "gte": op.ge,
    "lt": op.lt,
    "lte": op.le,
    "eq": op.eq,
}


def evaluate_condition(template_step: WorkflowTemplateStep, obj) -> bool:
    """Evaluate a condition step against *obj*."""

    field_value = _resolve_field(obj, template_step.condition_field)
    if field_value is None:
        return False

    compare_value = template_step.condition_value

    if template_step.condition_operator == "in":
        try:
            in_list = json.loads(compare_value)
        except (json.JSONDecodeError, TypeError):
            return False
        return str(field_value) in [str(v) for v in in_list]

    # Numeric comparison
    try:
        field_num = Decimal(str(field_value))
        compare_num = Decimal(str(compare_value))
    except (InvalidOperation, TypeError, ValueError):
        # Fallback to string comparison
        fn = _OPERATORS.get(template_step.condition_operator, op.eq)
        return fn(str(field_value), str(compare_value))

    fn = _OPERATORS.get(template_step.condition_operator, op.eq)
    return fn(field_num, compare_num)


# ---------------------------------------------------------------------------
# SLA checking (called by Celery task)
# ---------------------------------------------------------------------------

def check_sla_breaches(*, organization_id: int | None = None) -> int:
    """Detect overdue steps and mark them as breached / escalated.
    Returns the count of newly breached steps."""

    now = timezone.now()
    overdue_steps = WorkflowStep.objects.filter(
        decision=WorkflowStep.Decision.PENDING,
        sla_deadline__lt=now,
        sla_breached=False,
    ).select_related("workflow_instance")
    if organization_id is not None:
        overdue_steps = overdue_steps.filter(
            workflow_instance__template__organization_id=organization_id
        )

    breached_count = 0
    for step in overdue_steps:
        with transaction.atomic():
            step.sla_breached = True
            step.escalated_at = now
            step.decision = WorkflowStep.Decision.ESCALATED
            step.save(update_fields=[
                "sla_breached", "escalated_at", "decision", "updated_at",
            ])

            instance = step.workflow_instance
            _log_event(
                instance,
                WorkflowAuditEvent.EventType.SLA_BREACHED,
                payload={
                    "step_sequence": step.sequence,
                    "step_name": step.name,
                    "sla_deadline": step.sla_deadline.isoformat(),
                },
            )

            # Try to advance (escalation may allow next step)
            _advance_workflow(instance, actor=None)

            breached_count += 1

    return breached_count


# ---------------------------------------------------------------------------
# Delegation expiry (called by Celery task)
# ---------------------------------------------------------------------------

def expire_delegations(*, organization_id: int | None = None) -> int:
    """Mark expired delegations. Returns count of newly expired."""

    now = timezone.now()
    delegations = UserDelegation.objects.filter(
        status=UserDelegation.Status.ACTIVE,
        ends_at__lt=now,
    )
    if organization_id is not None:
        delegations = delegations.filter(organization_id=organization_id)
    return delegations.update(status=UserDelegation.Status.EXPIRED)


_WORKFLOW_CONTENT_TYPE_TO_SUB_MODULE = {
    ("finance", "bill"): "finance.bills",
    ("finance", "invoice"): "finance.invoices",
    ("finance", "budget"): "finance.budgets",
    ("finance", "billpayment"): "finance.payments",
    ("finance", "invoicepayment"): "finance.payments",
    ("finance", "paymentinstallment"): "finance.payments",
    ("procurement", "requisition"): "procurement.requisitions",
    ("procurement", "purchaseorder"): "procurement.orders",
    ("procurement", "requestforquotation"): "procurement.rfqs",
    ("procurement", "tendercomparison"): "procurement.tenders",
    ("documents", "document"): "documents.all",
    ("projects", "projectcost"): "projects.costs",
}


def _infer_sub_module_for_workflow_instance(instance: WorkflowInstance) -> str:
    key = (instance.content_type.app_label, instance.content_type.model)
    return _WORKFLOW_CONTENT_TYPE_TO_SUB_MODULE.get(key, "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_org(obj):
    """Extract organization from an object (tries common FK names)."""
    for attr in ("organization", "org", "company"):
        org = getattr(obj, attr, None)
        if org is not None:
            return org
    # Try through vendor → organization or property → organization
    if hasattr(obj, "vendor") and hasattr(obj.vendor, "organization"):
        return obj.vendor.organization
    if hasattr(obj, "property") and obj.property and hasattr(obj.property, "organization"):
        return obj.property.organization
    raise ValueError(
        f"Cannot determine organization for {obj.__class__.__name__}."
    )


def _resolve_field(obj, field_path: str) -> Any:
    """Traverse a dotted field path (e.g. 'total_amount') on *obj*."""
    if not field_path:
        return None
    current = obj
    for part in field_path.split("."):
        current = getattr(current, part, None)
        if current is None:
            return None
        if callable(current):
            current = current()
    return current


def _create_runtime_steps(instance: WorkflowInstance, obj) -> None:
    """Instantiate WorkflowStep rows from the template, evaluating
    condition steps to determine which branches to include."""

    template_steps = list(
        WorkflowTemplateStep.objects
        .filter(template=instance.template, is_active=True)
        .order_by("sequence", "id")
    )

    if not template_steps:
        raise ValueError("Workflow template has no active steps.")

    steps_by_seq = {s.sequence: s for s in template_steps}
    visited = set()
    runtime_steps = []
    seq = template_steps[0].sequence

    while seq is not None and seq not in visited:
        visited.add(seq)
        ts = steps_by_seq.get(seq)
        if ts is None:
            break

        if ts.step_type == WorkflowTemplateStep.StepType.CONDITION:
            # Evaluate and branch
            result = evaluate_condition(ts, obj)
            seq = ts.condition_true_step if result else ts.condition_false_step
            continue

        # Calculate SLA deadline
        sla_deadline = None
        if ts.sla_hours:
            sla_deadline = timezone.now() + timezone.timedelta(
                hours=ts.sla_hours
            )

        runtime_steps.append(
            WorkflowStep(
                workflow_instance=instance,
                sequence=len(runtime_steps) + 1,
                name=ts.name,
                execution_mode=ts.execution_mode,
                approver_role_slug=ts.approver_role_slug,
                approver_user=ts.approver_user,
                sla_deadline=sla_deadline,
            )
        )

        # Move to next sequential step
        remaining = [
            s.sequence for s in template_steps
            if s.sequence > seq and s.sequence not in visited
        ]
        seq = min(remaining) if remaining else None

    if not runtime_steps:
        raise ValueError("No approval steps resolved from the template.")

    WorkflowStep.objects.bulk_create(runtime_steps)


def _advance_workflow(instance: WorkflowInstance, actor) -> None:
    """Check if the workflow can advance or is complete."""

    pending = instance.steps.filter(
        decision=WorkflowStep.Decision.PENDING,
    ).order_by("sequence")

    if not pending.exists():
        _complete_workflow(instance, WorkflowInstance.State.APPROVED, actor)
        return

    # If current step group is parallel, check if all parallel steps decided
    first_pending = pending.first()
    if first_pending.execution_mode == WorkflowStep.ExecutionMode.PARALLEL:
        parallel_group = instance.steps.filter(
            sequence=first_pending.sequence,
        )
        if parallel_group.filter(
            decision=WorkflowStep.Decision.PENDING,
        ).exists():
            return  # Still waiting for parallel votes

    # Workflow remains in progress
    instance.state = WorkflowInstance.State.IN_PROGRESS
    instance.save(update_fields=["state", "updated_at"])


def _complete_workflow(
    instance: WorkflowInstance,
    final_state: str,
    actor,
) -> None:
    """Transition workflow to a terminal state."""

    instance.state = final_state
    instance.completed_at = timezone.now()
    instance.save(update_fields=["state", "completed_at", "updated_at"])

    event_map = {
        WorkflowInstance.State.APPROVED: WorkflowAuditEvent.EventType.WORKFLOW_APPROVED,
        WorkflowInstance.State.REJECTED: WorkflowAuditEvent.EventType.WORKFLOW_REJECTED,
        WorkflowInstance.State.CANCELLED: WorkflowAuditEvent.EventType.WORKFLOW_CANCELLED,
    }
    event_type = event_map.get(final_state)
    if event_type:
        _log_event(instance, event_type, actor=actor)


def _log_event(
    instance: WorkflowInstance,
    event_type: str,
    actor=None,
    payload: dict | None = None,
) -> WorkflowAuditEvent:
    """Create an immutable audit event."""
    return WorkflowAuditEvent.objects.create(
        workflow_instance=instance,
        event_type=event_type,
        actor=actor,
        payload=payload or {},
    )

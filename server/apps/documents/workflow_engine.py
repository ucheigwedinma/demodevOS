from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    Document,
    DocumentApproval,
    DocumentVersion,
    DocumentWorkflowInstance,
    DocumentWorkflowRule,
    DocumentWorkflowStep,
    DocumentWorkflowTemplate,
    DocumentWorkflowTemplateStep,
)


@dataclass
class WorkflowResolution:
    template: DocumentWorkflowTemplate
    rule: DocumentWorkflowRule | None


def _normalize_risk_rating(document: Document) -> str:
    if document.project and document.project.risk_rating:
        return document.project.risk_rating
    return DocumentWorkflowRule.ProjectRiskRating.MEDIUM


def resolve_workflow_template_for_document(document: Document) -> WorkflowResolution:
    """Select the first matching active workflow rule for a document."""

    rules = (
        DocumentWorkflowRule.objects
        .filter(is_active=True)
        .select_related("template", "document_type")
        .order_by("priority", "id")
    )

    contract_value = document.contract_value or Decimal("0")
    project_risk_rating = _normalize_risk_rating(document)

    for rule in rules:
        if not rule.template.is_active:
            continue
        if rule.document_type_id and rule.document_type_id != document.document_type_id:
            continue
        if rule.min_contract_value is not None and contract_value < rule.min_contract_value:
            continue
        if rule.max_contract_value is not None and contract_value > rule.max_contract_value:
            continue

        allowed_confidentiality = rule.normalized_confidentiality_levels()
        if allowed_confidentiality and document.confidentiality_level not in allowed_confidentiality:
            continue

        allowed_risk = rule.normalized_project_risk_ratings()
        if allowed_risk and project_risk_rating not in allowed_risk:
            continue

        return WorkflowResolution(template=rule.template, rule=rule)

    fallback = (
        DocumentWorkflowTemplate.objects
        .filter(is_active=True, is_default=True)
        .order_by("id")
        .first()
    )
    if not fallback:
        raise ValueError("No active workflow template found for this document.")

    return WorkflowResolution(template=fallback, rule=None)


def _create_instance_steps(instance: DocumentWorkflowInstance) -> None:
    templates = list(
        DocumentWorkflowTemplateStep.objects
        .filter(template=instance.template, is_active=True)
        .order_by("sequence", "id")
    )

    if not templates:
        raise ValueError("Selected workflow template has no active steps.")

    steps = [
        DocumentWorkflowStep(
            organization=instance.organization,
            workflow_instance=instance,
            sequence=template_step.sequence,
            approver_label=template_step.approver_label,
            approver_role_slug=template_step.approver_role_slug,
        )
        for template_step in templates
    ]
    DocumentWorkflowStep.objects.bulk_create(steps)


def _ensure_instance(document: Document, resolution: WorkflowResolution) -> DocumentWorkflowInstance:
    active_instance = (
        DocumentWorkflowInstance.objects
        .filter(
            document=document,
            state__in=[
                DocumentWorkflowInstance.State.SUBMITTED,
                DocumentWorkflowInstance.State.UNDER_REVIEW,
            ],
        )
        .order_by("-created_at")
        .first()
    )
    if active_instance:
        return active_instance

    with transaction.atomic():
        instance = DocumentWorkflowInstance.objects.create(
            organization=document.organization,
            document=document,
            template=resolution.template,
            matched_rule=resolution.rule,
            state=DocumentWorkflowInstance.State.SUBMITTED,
            submitted_at=timezone.now(),
        )
        _create_instance_steps(instance)

    document.status = Document.Status.SUBMITTED
    document.save(update_fields=["status"])
    return instance


def _current_pending_step(instance: DocumentWorkflowInstance) -> DocumentWorkflowStep | None:
    return (
        instance.steps
        .filter(decision=DocumentWorkflowStep.Decision.PENDING)
        .order_by("sequence", "id")
        .first()
    )


def submit_document_for_workflow(document: Document) -> DocumentWorkflowInstance:
    """Create or reuse workflow instance for document and move to review state."""
    if document.status in {Document.Status.ARCHIVED, Document.Status.SUPERSEDED}:
        raise ValueError("Archived or superseded documents cannot be submitted for approval.")
    if not document.current_version_id:
        raise ValueError("Document must have a current version before workflow submission.")

    resolution = resolve_workflow_template_for_document(document)
    instance = _ensure_instance(document=document, resolution=resolution)

    if instance.state == DocumentWorkflowInstance.State.SUBMITTED:
        instance.state = DocumentWorkflowInstance.State.UNDER_REVIEW
        instance.save(update_fields=["state", "updated_at"])
        document.status = Document.Status.UNDER_REVIEW
        document.save(update_fields=["status"])

    return instance


def record_workflow_step_decision(
    *,
    instance: DocumentWorkflowInstance,
    step: DocumentWorkflowStep,
    decision: str,
    decided_by,
    comments: str = "",
) -> DocumentWorkflowStep:
    """Apply an approval decision and update workflow/document state."""

    if decision not in {DocumentWorkflowStep.Decision.APPROVED, DocumentWorkflowStep.Decision.REJECTED}:
        raise ValueError("decision must be approved or rejected")

    if instance.state not in {
        DocumentWorkflowInstance.State.SUBMITTED,
        DocumentWorkflowInstance.State.UNDER_REVIEW,
    }:
        raise ValueError("Workflow instance is not in a reviewable state.")

    with transaction.atomic():
        step.decision = decision
        step.decided_by = decided_by
        step.comments = comments
        step.decided_at = timezone.now()
        step.save(update_fields=["decision", "decided_by", "comments", "decided_at", "updated_at"])

        if decision == DocumentWorkflowStep.Decision.REJECTED:
            instance.state = DocumentWorkflowInstance.State.REJECTED
            instance.completed_at = timezone.now()
            instance.save(update_fields=["state", "completed_at", "updated_at"])

            document = instance.document
            document.status = Document.Status.REJECTED
            document.save(update_fields=["status"])
            if document.current_version_id:
                document.current_version.approval_status = DocumentVersion.ApprovalStatus.REJECTED
                document.current_version.save(update_fields=["approval_status"])
            return step

        pending = _current_pending_step(instance)
        document = instance.document

        if pending:
            instance.state = DocumentWorkflowInstance.State.UNDER_REVIEW
            instance.save(update_fields=["state", "updated_at"])
            document.status = Document.Status.UNDER_REVIEW
            document.save(update_fields=["status"])
            if document.current_version_id:
                document.current_version.approval_status = DocumentVersion.ApprovalStatus.PENDING
                document.current_version.save(update_fields=["approval_status"])
        else:
            instance.state = DocumentWorkflowInstance.State.APPROVED
            instance.completed_at = timezone.now()
            instance.save(update_fields=["state", "completed_at", "updated_at"])
            document.status = Document.Status.APPROVED
            document.save(update_fields=["status"])
            if document.current_version_id:
                document.current_version.approval_status = DocumentVersion.ApprovalStatus.APPROVED
                document.current_version.save(update_fields=["approval_status"])

    if document.current_version_id:
        owner_role = document.owner_role
        DocumentApproval.objects.get_or_create(
            organization=document.organization,
            document_version_id=document.current_version_id,
            user=decided_by,
            role=owner_role,
            decision=(
                DocumentApproval.Decision.APPROVED
                if decision == DocumentWorkflowStep.Decision.APPROVED
                else DocumentApproval.Decision.REJECTED
            ),
            comments=comments,
        )

    return step

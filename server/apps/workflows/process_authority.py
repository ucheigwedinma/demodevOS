from __future__ import annotations

from django.db.models import Q

from .models import ProcessAuthority, ProcessWorkflowStep

APPROVAL_AUTHORITY_TYPES = {
    ProcessAuthority.AuthorityType.RESPONSIBLE,
    ProcessAuthority.AuthorityType.ACCOUNTABLE,
}


def user_has_process_authority_for_step(step, user) -> bool:
    """
    Resolve process-level workflow authority for a runtime workflow step.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    profile = getattr(user, "profile", None)
    template = step.workflow_instance.template
    organization = getattr(profile, "organization", None) or template.organization
    if organization is None:
        return False

    role_id = getattr(profile, "assigned_role_id", None)

    step_definition_ids = list(
        ProcessWorkflowStep.objects.filter(
            organization=organization,
            is_active=True,
        )
        .filter(
            Q(template=template, sequence=step.sequence)
            | Q(process_key=template.code, sequence=step.sequence)
            | Q(process_key=template.code, name__iexact=step.name)
        )
        .values_list("id", flat=True)
    )
    if not step_definition_ids:
        return False

    authorities = (
        ProcessAuthority.objects.filter(
            organization=organization,
            workflow_step_id__in=step_definition_ids,
            authority_type__in=APPROVAL_AUTHORITY_TYPES,
            is_active=True,
            approver__is_active=True,
        )
        .select_related("approver")
        .order_by("sort_order", "id")
    )

    for authority in authorities:
        approver = authority.approver
        if approver.user_id == user.id:
            return True
        if role_id and approver.role_id == role_id:
            return True

    return False

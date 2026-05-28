"""
Default seed logic for process authority (workflow authority/RACI layer).
"""

from __future__ import annotations

from apps.settings.models import Role

from .models import Approver, ProcessAuthority, ProcessWorkflowStep, WorkflowRole

WORKFLOW_ROLE_CATALOG = [
    {
        "code": "requester",
        "name": "Requester",
        "responsibility": WorkflowRole.Responsibility.RESPONSIBLE,
        "description": "Initiates the process request.",
    },
    {
        "code": "manager",
        "name": "Manager",
        "responsibility": WorkflowRole.Responsibility.ACCOUNTABLE,
        "description": "Owns first-level approval accountability.",
    },
    {
        "code": "procurement",
        "name": "Procurement",
        "responsibility": WorkflowRole.Responsibility.RESPONSIBLE,
        "description": "Performs procurement governance review.",
    },
    {
        "code": "finance",
        "name": "Finance",
        "responsibility": WorkflowRole.Responsibility.ACCOUNTABLE,
        "description": "Owns financial approval accountability.",
    },
    {
        "code": "ceo",
        "name": "CEO",
        "responsibility": WorkflowRole.Responsibility.ACCOUNTABLE,
        "description": "Final executive authority for high-value approvals.",
    },
]


DEFAULT_PROCUREMENT_STEPS = [
    {"process_key": "procurement", "code": "requester-submit", "name": "Requester", "sequence": 1},
    {"process_key": "procurement", "code": "manager-review", "name": "Manager Review", "sequence": 2},
    {"process_key": "procurement", "code": "procurement-review", "name": "Procurement Review", "sequence": 3},
    {"process_key": "procurement", "code": "finance-review", "name": "Finance Review", "sequence": 4},
    {"process_key": "procurement", "code": "ceo-approval", "name": "CEO Approval", "sequence": 5},
]


DEFAULT_PROCESS_AUTHORITY_MATRIX = [
    {
        "step_code": "manager-review",
        "workflow_role_code": "manager",
        "authority_type": ProcessAuthority.AuthorityType.ACCOUNTABLE,
        "role_slugs": ["manager", "department-admin"],
    },
    {
        "step_code": "procurement-review",
        "workflow_role_code": "procurement",
        "authority_type": ProcessAuthority.AuthorityType.RESPONSIBLE,
        "role_slugs": ["procurement-officer"],
    },
    {
        "step_code": "finance-review",
        "workflow_role_code": "finance",
        "authority_type": ProcessAuthority.AuthorityType.ACCOUNTABLE,
        "role_slugs": ["finance-controller"],
    },
    {
        "step_code": "ceo-approval",
        "workflow_role_code": "ceo",
        "authority_type": ProcessAuthority.AuthorityType.ACCOUNTABLE,
        "role_slugs": ["developer-executive", "super-admin"],
    },
]


def seed_process_authority_for_org(org, *, reset: bool = False) -> dict[str, int]:
    created = {
        "workflow_roles": 0,
        "workflow_steps": 0,
        "approvers": 0,
        "process_authority": 0,
        "reset_deleted": 0,
    }

    workflow_roles_by_code: dict[str, WorkflowRole] = {}
    for row in WORKFLOW_ROLE_CATALOG:
        workflow_role, is_created = WorkflowRole.objects.get_or_create(
            organization=org,
            code=row["code"],
            defaults={
                "name": row["name"],
                "responsibility": row["responsibility"],
                "description": row["description"],
                "is_active": True,
            },
        )
        if is_created:
            created["workflow_roles"] += 1
        elif reset:
            workflow_role.name = row["name"]
            workflow_role.responsibility = row["responsibility"]
            workflow_role.description = row["description"]
            workflow_role.is_active = True
            workflow_role.save(
                update_fields=[
                    "name",
                    "responsibility",
                    "description",
                    "is_active",
                    "updated_at",
                ]
            )
        workflow_roles_by_code[row["code"]] = workflow_role

    process_steps_by_code: dict[str, ProcessWorkflowStep] = {}
    for row in DEFAULT_PROCUREMENT_STEPS:
        process_step, is_created = ProcessWorkflowStep.objects.get_or_create(
            organization=org,
            process_key=row["process_key"],
            code=row["code"],
            defaults={
                "name": row["name"],
                "sequence": row["sequence"],
                "is_active": True,
            },
        )
        if is_created:
            created["workflow_steps"] += 1
        elif reset:
            process_step.name = row["name"]
            process_step.sequence = row["sequence"]
            process_step.is_active = True
            process_step.save(
                update_fields=["name", "sequence", "is_active", "updated_at"]
            )
        process_steps_by_code[row["code"]] = process_step

    if reset:
        matrix_step_codes = [m["step_code"] for m in DEFAULT_PROCESS_AUTHORITY_MATRIX]
        deleted_count, _ = ProcessAuthority.objects.filter(
            organization=org,
            workflow_step__process_key="procurement",
        ).exclude(workflow_step__code__in=matrix_step_codes).delete()
        created["reset_deleted"] += deleted_count

    for row in DEFAULT_PROCESS_AUTHORITY_MATRIX:
        process_step = process_steps_by_code.get(row["step_code"])
        workflow_role = workflow_roles_by_code.get(row["workflow_role_code"])
        if process_step is None or workflow_role is None:
            continue

        for role_slug in row["role_slugs"]:
            role = Role.objects.filter(organization=org, slug=role_slug).first()
            if role is None:
                continue

            approver = (
                Approver.objects.filter(
                    organization=org,
                    role=role,
                    user__isnull=True,
                    workflow_role=workflow_role,
                )
                .order_by("id")
                .first()
            )
            if approver is None:
                approver = Approver.objects.create(
                    organization=org,
                    role=role,
                    workflow_role=workflow_role,
                    title=workflow_role.name,
                    is_active=True,
                )
                created["approvers"] += 1
            elif reset and not approver.is_active:
                approver.is_active = True
                approver.save(update_fields=["is_active", "updated_at"])

            process_authority, is_created = ProcessAuthority.objects.get_or_create(
                organization=org,
                workflow_step=process_step,
                workflow_role=workflow_role,
                approver=approver,
                authority_type=row["authority_type"],
                defaults={"sort_order": process_step.sequence, "is_active": True},
            )
            if is_created:
                created["process_authority"] += 1
            elif reset and not process_authority.is_active:
                process_authority.is_active = True
                process_authority.sort_order = process_step.sequence
                process_authority.save(
                    update_fields=["is_active", "sort_order", "updated_at"]
                )

    return created

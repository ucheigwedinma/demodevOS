"""
Default contextual access policy seed logic.
"""

from __future__ import annotations

from .models import AccessPolicy, PolicyAction, PolicyCondition


def seed_contextual_access_policies_for_org(org, *, reset: bool = False) -> dict[str, int]:
    created = {
        "access_policies": 0,
        "policy_conditions": 0,
        "policy_actions": 0,
        "reset_deleted": 0,
    }

    policy, is_created = AccessPolicy.objects.get_or_create(
        organization=org,
        key="finance-manager-approve-requires-mfa",
        defaults={
            "name": "Finance approvals require MFA",
            "description": (
                "Enforces MFA for finance approval actions when executed "
                "by finance managerial roles."
            ),
            "module": "finance",
            "sub_module": "",
            "action": "approve",
            "priority": 10,
            "is_active": True,
        },
    )
    if is_created:
        created["access_policies"] += 1
    elif reset:
        policy.name = "Finance approvals require MFA"
        policy.description = (
            "Enforces MFA for finance approval actions when executed "
            "by finance managerial roles."
        )
        policy.module = "finance"
        policy.sub_module = ""
        policy.action = "approve"
        policy.priority = 10
        policy.is_active = True
        policy.save(
            update_fields=[
                "name",
                "description",
                "module",
                "sub_module",
                "action",
                "priority",
                "is_active",
                "updated_at",
            ]
        )

    condition_defaults = {
        "value": ["finance-manager", "finance-controller"],
        "sort_order": 10,
        "is_active": True,
    }
    condition, condition_created = PolicyCondition.objects.get_or_create(
        access_policy=policy,
        condition_type=PolicyCondition.ConditionType.USER_ROLE,
        operator=PolicyCondition.Operator.IN,
        defaults=condition_defaults,
    )
    if condition_created:
        created["policy_conditions"] += 1
    elif reset:
        condition.value = condition_defaults["value"]
        condition.sort_order = condition_defaults["sort_order"]
        condition.is_active = True
        condition.save(update_fields=["value", "sort_order", "is_active"])

    action_defaults = {
        "parameters": {},
        "message": "MFA is required to approve finance actions.",
        "sort_order": 10,
        "is_active": True,
    }
    policy_action, action_created = PolicyAction.objects.get_or_create(
        access_policy=policy,
        action_type=PolicyAction.ActionType.REQUIRE_MFA,
        defaults=action_defaults,
    )
    if action_created:
        created["policy_actions"] += 1
    elif reset:
        policy_action.parameters = action_defaults["parameters"]
        policy_action.message = action_defaults["message"]
        policy_action.sort_order = action_defaults["sort_order"]
        policy_action.is_active = True
        policy_action.save(
            update_fields=["parameters", "message", "sort_order", "is_active"]
        )

    if reset:
        deleted_conditions, _ = policy.conditions.exclude(id=condition.id).delete()
        deleted_actions, _ = policy.policy_actions.exclude(id=policy_action.id).delete()
        created["reset_deleted"] += deleted_conditions + deleted_actions

    return created

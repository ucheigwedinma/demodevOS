"""Add finance.budgets permissions to existing system roles.

developer-executive & finance-controller → full access
project-director, sales-manager, procurement-officer, governance-officer,
board-viewer → view only
legal, auditor → view + approve (review access)
"""
from django.db import migrations

BUDGET_SUB_MODULE = "finance.budgets"
MODULE = "finance"

# role_slug → actions
ROLE_BUDGET_PERMS = {
    "developer-executive": ["view", "create", "edit", "delete", "approve"],
    "finance-controller": ["view", "create", "edit", "delete", "approve"],
    "project-director": ["view"],
    "sales-manager": ["view"],
    "procurement-officer": ["view"],
    "governance-officer": ["view"],
    "legal": ["view", "approve"],
    "auditor": ["view", "approve"],
    "board-viewer": ["view"],
}


def add_budget_permissions(apps, schema_editor):
    Role = apps.get_model("settings", "Role")
    RolePermission = apps.get_model("settings", "RolePermission")

    for role in Role.objects.filter(is_system=True, slug__in=ROLE_BUDGET_PERMS):
        actions = ROLE_BUDGET_PERMS[role.slug]
        for action in actions:
            RolePermission.objects.get_or_create(
                role=role,
                module=MODULE,
                sub_module=BUDGET_SUB_MODULE,
                action=action,
            )


def remove_budget_permissions(apps, schema_editor):
    RolePermission = apps.get_model("settings", "RolePermission")
    RolePermission.objects.filter(sub_module=BUDGET_SUB_MODULE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0006_alter_rolepermission_sub_module"),
    ]

    operations = [
        migrations.RunPython(add_budget_permissions, remove_budget_permissions),
    ]

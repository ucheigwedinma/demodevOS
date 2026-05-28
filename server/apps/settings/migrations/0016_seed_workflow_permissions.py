"""Seed workflow-related RBAC permissions for existing system roles."""

from django.db import migrations

WORKFLOW_PERMS = {
    "developer-executive": [
        ("settings.workflow_templates", ["view", "create", "edit", "delete"]),
        ("settings.approval_policies", ["view", "create", "edit", "delete"]),
        ("settings.delegations", ["view", "create", "edit", "delete"]),
    ],
    "governance-officer": [
        ("settings.workflow_templates", ["view", "create", "edit", "delete"]),
        ("settings.approval_policies", ["view", "create", "edit", "delete"]),
        ("settings.delegations", ["view", "create", "edit"]),
    ],
    "finance-controller": [
        ("settings.workflow_templates", ["view"]),
        ("settings.approval_policies", ["view"]),
        ("settings.delegations", ["view", "create"]),
    ],
    "project-director": [
        ("settings.workflow_templates", ["view"]),
        ("settings.approval_policies", ["view"]),
        ("settings.delegations", ["view", "create"]),
    ],
    "auditor": [
        ("settings.workflow_templates", ["view", "export"]),
        ("settings.approval_policies", ["view", "export"]),
        ("settings.delegations", ["view", "export"]),
    ],
}

# All other roles get view-only
_VIEW_ONLY_ROLES = [
    "sales-manager", "procurement-officer", "legal",
    "external-consultant", "board-viewer",
]
for _slug in _VIEW_ONLY_ROLES:
    WORKFLOW_PERMS[_slug] = [
        ("settings.workflow_templates", ["view"]),
        ("settings.approval_policies", ["view"]),
        ("settings.delegations", ["view"]),
    ]


def seed_workflow_permissions(apps, schema_editor):
    Role = apps.get_model("settings", "Role")
    RolePermission = apps.get_model("settings", "RolePermission")

    for slug, sub_modules in WORKFLOW_PERMS.items():
        for role in Role.objects.filter(slug=slug, is_system=True):
            perms = []
            for sub_module, actions in sub_modules:
                module = sub_module.split(".")[0]
                for action in actions:
                    if not RolePermission.objects.filter(
                        role=role, sub_module=sub_module, action=action,
                    ).exists():
                        perms.append(RolePermission(
                            role=role, module=module,
                            sub_module=sub_module, action=action,
                        ))
            if perms:
                RolePermission.objects.bulk_create(perms)


def unseed_workflow_permissions(apps, schema_editor):
    RolePermission = apps.get_model("settings", "RolePermission")
    RolePermission.objects.filter(
        sub_module__in=[
            "settings.workflow_templates",
            "settings.approval_policies",
            "settings.delegations",
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0015_alter_rolepermission_sub_module_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_workflow_permissions, unseed_workflow_permissions),
    ]

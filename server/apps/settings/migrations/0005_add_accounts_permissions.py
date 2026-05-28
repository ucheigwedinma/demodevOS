from django.db import migrations

# Permissions to add for finance.accounts per system role
ACCOUNTS_PERMS_BY_ROLE = {
    "developer-executive": ["view", "create", "edit", "delete"],
    "project-director": ["view"],
    "sales-manager": ["view"],
    "finance-controller": ["view", "create", "edit", "delete"],
    "procurement-officer": ["view"],
    "governance-officer": ["view"],
    "legal": ["view"],
    "external-consultant": [],
    "auditor": ["view"],
    "board-viewer": ["view"],
}


def add_accounts_permissions(apps, schema_editor):
    Role = apps.get_model("settings", "Role")
    RolePermission = apps.get_model("settings", "RolePermission")

    for role in Role.objects.filter(is_system=True):
        actions = ACCOUNTS_PERMS_BY_ROLE.get(role.slug, [])
        if not actions:
            continue

        perms = []
        for action in actions:
            if not RolePermission.objects.filter(
                role=role, sub_module="finance.accounts", action=action
            ).exists():
                perms.append(
                    RolePermission(
                        role=role,
                        module="finance",
                        sub_module="finance.accounts",
                        action=action,
                    )
                )
        if perms:
            RolePermission.objects.bulk_create(perms)


def remove_accounts_permissions(apps, schema_editor):
    RolePermission = apps.get_model("settings", "RolePermission")
    RolePermission.objects.filter(sub_module="finance.accounts").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0004_phase4_documents_access_levels"),
    ]

    operations = [
        migrations.RunPython(add_accounts_permissions, remove_accounts_permissions),
    ]

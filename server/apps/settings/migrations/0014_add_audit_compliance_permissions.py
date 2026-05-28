"""Grant settings.audit_compliance permissions to existing system roles."""

from django.db import migrations

# (role_slug, [actions])
ROLE_GRANTS = [
    ("developer-executive", ["view", "edit"]),
    ("governance-officer", ["view", "edit"]),
    ("auditor", ["view", "edit"]),
    ("project-director", ["view"]),
    ("finance-controller", ["view"]),
    ("legal", ["view"]),
]


def forwards(apps, schema_editor):
    Role = apps.get_model("settings", "Role")
    RolePermission = apps.get_model("settings", "RolePermission")

    for role_slug, actions in ROLE_GRANTS:
        for role in Role.objects.filter(slug=role_slug, is_system=True):
            for action in actions:
                RolePermission.objects.get_or_create(
                    role=role,
                    module="settings",
                    sub_module="settings.audit_compliance",
                    action=action,
                )


def backwards(apps, schema_editor):
    RolePermission = apps.get_model("settings", "RolePermission")
    RolePermission.objects.filter(sub_module="settings.audit_compliance").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0013_auditcompliancesettings"),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]

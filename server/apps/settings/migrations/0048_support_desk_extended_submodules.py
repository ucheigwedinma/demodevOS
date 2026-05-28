from django.db import migrations

SUPPORT_DESK_SUBMODULE_ACTIONS = {
    "support_desk.requests": ["view", "create", "edit", "delete", "assign", "comment"],
    "support_desk.knowledge_base": ["view", "create", "edit", "delete", "approve", "archive"],
    "support_desk.sla_escalations": ["view", "edit", "configure"],
    "support_desk.communication": ["view", "create", "edit", "delete", "comment"],
    "support_desk.automation": ["view", "create", "edit", "delete", "configure"],
    "support_desk.reports": ["view", "export"],
    "support_desk.configuration": ["view", "edit", "configure"],
}

SUPPORT_DESK_ROLE_GRANTS = {
    "governance-officer": {
        "support_desk.requests": ["view"],
        "support_desk.knowledge_base": ["view"],
        "support_desk.sla_escalations": ["view"],
        "support_desk.communication": ["view"],
        "support_desk.automation": ["view"],
        "support_desk.reports": ["view"],
        "support_desk.configuration": ["view"],
    },
    "auditor": {
        "support_desk.requests": ["view"],
        "support_desk.knowledge_base": ["view"],
        "support_desk.sla_escalations": ["view"],
        "support_desk.communication": ["view"],
        "support_desk.automation": ["view"],
        "support_desk.reports": ["view"],
        "support_desk.configuration": ["view"],
    },
    "system-admin": {
        "support_desk.requests": ["view", "create", "edit", "delete", "assign", "comment"],
        "support_desk.knowledge_base": ["view", "create", "edit", "delete", "approve", "archive"],
        "support_desk.sla_escalations": ["view", "edit", "configure"],
        "support_desk.communication": ["view", "create", "edit", "delete", "comment"],
        "support_desk.automation": ["view", "create", "edit", "delete", "configure"],
        "support_desk.reports": ["view", "export"],
        "support_desk.configuration": ["view", "edit", "configure"],
    },
    "department-admin": {
        "support_desk.requests": ["view", "create", "edit", "delete", "assign", "comment"],
        "support_desk.knowledge_base": ["view", "create", "edit", "delete", "approve", "archive"],
        "support_desk.sla_escalations": ["view", "edit", "configure"],
        "support_desk.communication": ["view", "create", "edit", "delete", "comment"],
        "support_desk.automation": ["view", "create", "edit", "delete", "configure"],
        "support_desk.reports": ["view", "export"],
        "support_desk.configuration": ["view", "edit", "configure"],
    },
    "manager": {
        "support_desk.requests": ["view", "create", "edit", "assign", "comment"],
        "support_desk.knowledge_base": ["view"],
        "support_desk.sla_escalations": ["view"],
        "support_desk.communication": ["view"],
        "support_desk.automation": ["view"],
        "support_desk.reports": ["view"],
        "support_desk.configuration": ["view"],
    },
    "staff": {
        "support_desk.requests": ["view", "create", "edit", "comment"],
        "support_desk.knowledge_base": ["view"],
        "support_desk.sla_escalations": ["view"],
        "support_desk.communication": ["view"],
        "support_desk.automation": ["view"],
        "support_desk.reports": ["view"],
        "support_desk.configuration": ["view"],
    },
    "external-auditor": {
        "support_desk.requests": ["view"],
        "support_desk.knowledge_base": ["view"],
        "support_desk.sla_escalations": ["view"],
        "support_desk.communication": ["view"],
        "support_desk.automation": ["view"],
        "support_desk.reports": ["view"],
        "support_desk.configuration": ["view"],
    },
}


def seed_support_desk_extended_permissions(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    ModuleActivationSettings = apps.get_model("settings", "ModuleActivationSettings")
    Permission = apps.get_model("settings", "Permission")
    Role = apps.get_model("settings", "Role")
    RolePermission = apps.get_model("settings", "RolePermission")

    permission_map = {}
    for sub_module, actions in SUPPORT_DESK_SUBMODULE_ACTIONS.items():
        for action in actions:
            permission_map[(sub_module, action)] = Permission.objects.get_or_create(
                sub_module=sub_module,
                action=action,
                defaults={
                    "module": "support_desk",
                    "key": f"{sub_module}.{action}",
                },
            )[0]

    for org in Organization.objects.all():
        activation, _ = ModuleActivationSettings.objects.get_or_create(
            organization=org,
            defaults={"enabled_modules": ["support_desk"]},
        )
        enabled_modules = list(activation.enabled_modules or [])
        if "support_desk" not in enabled_modules:
            enabled_modules.append("support_desk")
            activation.enabled_modules = enabled_modules
            activation.save(update_fields=["enabled_modules", "updated_at"])

        roles = {
            role.slug: role
            for role in Role.objects.filter(organization=org, slug__in=SUPPORT_DESK_ROLE_GRANTS.keys())
        }

        for slug, grants in SUPPORT_DESK_ROLE_GRANTS.items():
            role = roles.get(slug)
            if role is None:
                continue
            for sub_module, actions in grants.items():
                for action in actions:
                    permission = permission_map[(sub_module, action)]
                    RolePermission.objects.get_or_create(
                        role=role,
                        sub_module=sub_module,
                        action=action,
                        defaults={
                            "permission": permission,
                            "module": "support_desk",
                        },
                    )


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0047_support_desk_module_and_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_support_desk_extended_permissions, migrations.RunPython.noop),
    ]

"""Seed default platform roles and permissions."""
from django.db import migrations

PERMISSIONS = [
    # IAM
    ("iam.view_users", "View all users", "iam", "view"),
    ("iam.create_users", "Create users", "iam", "create"),
    ("iam.edit_users", "Edit users", "iam", "edit"),
    ("iam.delete_users", "Delete users", "iam", "delete"),
    ("iam.impersonate", "Impersonate tenant users", "iam", "impersonate"),
    # Tenants
    ("tenants.view", "View all tenants", "tenants", "view"),
    ("tenants.create", "Create tenants", "tenants", "create"),
    ("tenants.edit", "Edit tenants", "tenants", "edit"),
    ("tenants.delete", "Delete tenants", "tenants", "delete"),
    # Telemetry
    ("telemetry.view_metrics", "View platform metrics", "telemetry", "view"),
    ("telemetry.view_activity", "View activity feed", "telemetry", "view"),
    ("telemetry.view_workflows", "View workflow monitor", "telemetry", "view"),
    # Billing
    ("billing.view", "View billing & subscriptions", "billing", "view"),
    ("billing.manage", "Manage subscriptions & plans", "billing", "edit"),
    ("billing.refund", "Process refunds", "billing", "execute"),
    # Operations
    ("operations.view", "View platform operations", "operations", "view"),
    ("operations.execute", "Execute platform operations", "operations", "execute"),
    ("operations.deploy", "Trigger deployments", "operations", "execute"),
    # Settings
    ("settings.view", "View system settings", "settings", "view"),
    ("settings.edit", "Edit system settings", "settings", "edit"),
    ("settings.feature_flags", "Manage feature flags", "settings", "edit"),
    # Audit
    ("audit.view", "View audit logs", "audit", "view"),
    ("audit.export", "Export audit data", "audit", "execute"),
]

ROLES = {
    "platform-owner": {
        "name": "Platform Owner",
        "tier": "owner",
        "description": "Full unrestricted access to all platform features.",
        "is_system": True,
        "permissions": "*",  # all permissions
    },
    "platform-admin": {
        "name": "Platform Admin",
        "tier": "admin",
        "description": "Full access except impersonation and destructive operations.",
        "is_system": True,
        "permissions": [
            "iam.view_users", "iam.create_users", "iam.edit_users",
            "tenants.view", "tenants.create", "tenants.edit",
            "telemetry.view_metrics", "telemetry.view_activity", "telemetry.view_workflows",
            "billing.view", "billing.manage",
            "operations.view", "operations.execute",
            "settings.view", "settings.edit", "settings.feature_flags",
            "audit.view", "audit.export",
        ],
    },
    "support-agent": {
        "name": "Support Agent",
        "tier": "support",
        "description": "View tenants and users, handle support escalations.",
        "is_system": True,
        "permissions": [
            "iam.view_users", "iam.edit_users", "iam.impersonate",
            "tenants.view",
            "telemetry.view_activity",
            "audit.view",
        ],
    },
    "billing-manager": {
        "name": "Billing Manager",
        "tier": "billing",
        "description": "Manage subscriptions, plans, and billing inquiries.",
        "is_system": True,
        "permissions": [
            "tenants.view",
            "billing.view", "billing.manage", "billing.refund",
            "audit.view",
        ],
    },
    "devops": {
        "name": "DevOps Engineer",
        "tier": "devops",
        "description": "Infrastructure, telemetry, deployments, and operations.",
        "is_system": True,
        "permissions": [
            "telemetry.view_metrics", "telemetry.view_activity", "telemetry.view_workflows",
            "operations.view", "operations.execute", "operations.deploy",
            "settings.view",
            "audit.view",
        ],
    },
    "viewer": {
        "name": "Read-Only Viewer",
        "tier": "viewer",
        "description": "Read-only access to the console dashboard and metrics.",
        "is_system": True,
        "permissions": [
            "tenants.view",
            "telemetry.view_metrics", "telemetry.view_activity", "telemetry.view_workflows",
            "billing.view",
            "audit.view",
        ],
    },
}


def seed_platform_roles(apps, schema_editor):
    PlatformPermission = apps.get_model("accounts", "PlatformPermission")
    PlatformRole = apps.get_model("accounts", "PlatformRole")
    PlatformRolePermission = apps.get_model("accounts", "PlatformRolePermission")

    # Create permissions
    perm_map = {}
    for slug, name, module, action in PERMISSIONS:
        perm, _ = PlatformPermission.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "module": module, "action": action},
        )
        perm_map[slug] = perm

    # Create roles and assign permissions
    for slug, config in ROLES.items():
        role, _ = PlatformRole.objects.get_or_create(
            slug=slug,
            defaults={
                "name": config["name"],
                "tier": config["tier"],
                "description": config["description"],
                "is_system": config["is_system"],
            },
        )
        if config["permissions"] == "*":
            perms = perm_map.values()
        else:
            perms = [perm_map[p] for p in config["permissions"] if p in perm_map]

        for perm in perms:
            PlatformRolePermission.objects.get_or_create(
                role=role, permission=perm,
            )

    # Assign Platform Owner role to all existing superusers
    UserProfile = apps.get_model("accounts", "UserProfile")
    User = apps.get_model("auth", "User")
    owner_role = PlatformRole.objects.filter(slug="platform-owner").first()
    if owner_role:
        superuser_ids = User.objects.filter(is_superuser=True).values_list("id", flat=True)
        UserProfile.objects.filter(user_id__in=superuser_ids).update(platform_role=owner_role)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0040_platform_roles"),
    ]

    operations = [
        migrations.RunPython(seed_platform_roles, migrations.RunPython.noop),
    ]

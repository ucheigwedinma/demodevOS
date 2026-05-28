"""
Management command to synchronize the custom RBAC system with Django's
built-in auth.Group and auth.Permission framework.

For each Organization:
  - Creates a Django Group named "{org.name} | {role.name}" for each Role.
  - Assigns the matching Django auth.Permissions to each Group based on
    the role's RolePermission entries.
  - Assigns users with that assigned_role to the corresponding Group.

This enables Django admin to respect RBAC — non-superuser staff members
see only the models their role grants access to.

Run after seeding roles or updating the permission matrix:
    python manage.py sync_rbac_to_django_groups
"""

from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission as DjangoPermission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.accounts.models import Organization, UserProfile
from apps.settings.models import Role, RolePermission

# Map RBAC module to Django app_labels that belong to it.
_RBAC_MODULE_TO_APP_LABELS = {
    "properties": ["properties", "valuations"],
    "projects": ["projects"],
    "finance": ["finance"],
    "procurement": ["procurement"],
    "documents": ["documents"],
    "analytics": ["analytics"],
    "crm": ["crm"],
    "compliance": ["compliance"],
    "hr": ["hr"],
    "iam": ["accounts"],
    "settings": ["settings"],
    "support_desk": ["support_desk"],
    "tenants": ["crm"],
    "contracts": ["compliance"],
}

# Map RBAC action to Django permission codename prefixes.
_RBAC_ACTION_TO_DJANGO_PREFIX = {
    "view": "view",
    "create": "add",
    "edit": "change",
    "delete": "delete",
    "approve": "change",  # Map approve → change for admin purposes
    "export": "view",     # Map export → view for admin purposes
    "assign": "change",
    "comment": "view",
    "upload_version": "change",
    "archive": "change",
    "admin_override": "change",
    "configure": "change",
    "manage": "change",
}


def _django_group_name(org, role):
    """Generate a unique Django Group name for an org+role pair."""
    return f"{org.name} | {role.name}"


def _get_django_permissions_for_rbac_perms(role_permissions):
    """
    Given a queryset of RolePermission objects, return a set of
    Django auth.Permission IDs that correspond to them.
    """
    django_perm_ids = set()

    for rp in role_permissions:
        module = rp.module
        action = rp.action

        django_prefix = _RBAC_ACTION_TO_DJANGO_PREFIX.get(action)
        if not django_prefix:
            continue

        app_labels = _RBAC_MODULE_TO_APP_LABELS.get(module, [])
        if not app_labels:
            continue

        # Find all Django permissions matching this prefix in these apps
        content_types = ContentType.objects.filter(app_label__in=app_labels)
        matching = DjangoPermission.objects.filter(
            content_type__in=content_types,
            codename__startswith=f"{django_prefix}_",
        )
        django_perm_ids.update(matching.values_list("id", flat=True))

    return django_perm_ids


class Command(BaseCommand):
    help = "Sync custom RBAC roles to Django Groups and Permissions for admin access control."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org-id",
            type=int,
            help="Sync only a specific organization (by ID).",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Remove stale groups for deleted roles/orgs.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org_id")
        clean = options.get("clean", False)

        if org_id:
            orgs = Organization.objects.filter(pk=org_id)
        else:
            orgs = Organization.objects.all()

        total_groups_created = 0
        total_groups_updated = 0
        total_users_assigned = 0

        for org in orgs:
            roles = Role.objects.filter(organization=org)

            for role in roles:
                group_name = _django_group_name(org, role)
                group, created = Group.objects.get_or_create(name=group_name)

                if created:
                    total_groups_created += 1
                else:
                    total_groups_updated += 1

                # Get RBAC permissions for this role
                role_perms = RolePermission.objects.filter(role=role)
                django_perm_ids = _get_django_permissions_for_rbac_perms(role_perms)

                # Set group permissions (replace, not append)
                group.permissions.set(django_perm_ids)

                # Assign users with this role to the group
                user_ids = UserProfile.objects.filter(
                    organization=org,
                    assigned_role=role,
                ).values_list("user_id", flat=True)

                # Also assign org admins to this group if it's a full-access role
                admin_user_ids = UserProfile.objects.filter(
                    organization=org,
                    role="admin",
                ).values_list("user_id", flat=True)

                from django.contrib.auth import get_user_model
                User = get_user_model()

                role_users = User.objects.filter(pk__in=user_ids)
                group.user_set.set(role_users)
                total_users_assigned += role_users.count()

                # Ensure admin users are staff so they can access admin
                admin_users = User.objects.filter(pk__in=admin_user_ids)
                for admin_user in admin_users:
                    if not admin_user.is_staff:
                        admin_user.is_staff = True
                        admin_user.save(update_fields=["is_staff"])

        if clean:
            self._clean_stale_groups()

        self.stdout.write(self.style.SUCCESS(
            f"Sync complete: {total_groups_created} groups created, "
            f"{total_groups_updated} groups updated, "
            f"{total_users_assigned} user assignments."
        ))

    def _clean_stale_groups(self):
        """Remove Django Groups that no longer match any org+role pair."""
        valid_names = set()
        for org in Organization.objects.all():
            for role in Role.objects.filter(organization=org):
                valid_names.add(_django_group_name(org, role))

        stale = Group.objects.filter(name__contains=" | ").exclude(name__in=valid_names)
        count = stale.count()
        if count:
            stale.delete()
            self.stdout.write(self.style.WARNING(f"Removed {count} stale groups."))

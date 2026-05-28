import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import Organization

from .models import ModuleActivationSettings, Role, RolePermission
from .permissions import bump_org_module_activation_cache_version, bump_role_permission_cache_version

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Organization)
def create_default_roles(sender, instance, created, **kwargs):
    """Seed default RBAC roles and data-scope defaults for a new organization."""
    bump_org_module_activation_cache_version(instance.id)

    if created:
        from .org_bootstrap import bootstrap_new_organization
        from .rbac_defaults import seed_roles_for_org
        from .scope_defaults import seed_role_scopes_for_org

        seed_roles_for_org(instance)
        seed_role_scopes_for_org(instance)
        bootstrap_new_organization(instance)


@receiver(post_save, sender=ModuleActivationSettings)
@receiver(post_delete, sender=ModuleActivationSettings)
def invalidate_module_activation_cache(sender, instance, **kwargs):
    bump_org_module_activation_cache_version(instance.organization_id)


@receiver(post_save, sender=RolePermission)
@receiver(post_delete, sender=RolePermission)
def invalidate_role_permission_cache(sender, instance, **kwargs):
    bump_role_permission_cache_version(instance.role_id)


@receiver(post_save, sender=Role)
@receiver(post_delete, sender=Role)
def invalidate_role_cache_on_role_change(sender, instance, **kwargs):
    bump_role_permission_cache_version(instance.id)


# ---------------------------------------------------------------------------
# Django Group ↔ RBAC Role sync
# ---------------------------------------------------------------------------


def _sync_role_to_django_group(role):
    """Sync a single Role's permissions to its corresponding Django Group."""
    try:
        from django.contrib.auth.models import Group

        from .management.commands.sync_rbac_to_django_groups import (
            _django_group_name,
            _get_django_permissions_for_rbac_perms,
        )

        org = role.organization
        group_name = _django_group_name(org, role)
        group, _ = Group.objects.get_or_create(name=group_name)

        role_perms = RolePermission.objects.filter(role=role)
        django_perm_ids = _get_django_permissions_for_rbac_perms(role_perms)
        group.permissions.set(django_perm_ids)
    except Exception:
        logger.exception("Failed to sync Role %s to Django Group", role.pk)


@receiver(post_save, sender=RolePermission)
def sync_django_group_on_permission_change(sender, instance, **kwargs):
    """Keep the Django Group in sync when RolePermission rows change."""
    _sync_role_to_django_group(instance.role)


@receiver(post_delete, sender=RolePermission)
def sync_django_group_on_permission_delete(sender, instance, **kwargs):
    """Keep the Django Group in sync when RolePermission rows are removed."""
    _sync_role_to_django_group(instance.role)

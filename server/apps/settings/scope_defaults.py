"""
Default data-scope seed logic for layered access control.

This module seeds:
1. Data scope catalog (self/department/project/organization)
2. Role-level default scopes (role_scopes)
3. Optional user-level override scopes (user_scope_assignments)
"""

from __future__ import annotations

from collections.abc import Mapping

from .models import DataScope, Role, RoleScope, UserScopeAssignment

DATA_SCOPE_CATALOG = {
    DataScope.ScopeKey.SELF: {
        "label": "Self",
        "description": "Only records owned or directly managed by the current user.",
    },
    DataScope.ScopeKey.DEPARTMENT: {
        "label": "Department",
        "description": "Records tied to users in the same department.",
    },
    DataScope.ScopeKey.PROJECT: {
        "label": "Project",
        "description": "Records for projects assigned to the current user.",
    },
    DataScope.ScopeKey.ORGANIZATION: {
        "label": "Organization",
        "description": "All records available within the organization boundary.",
    },
}


# Module-level scope defaults per role slug.
# Keys are Module values (e.g. "iam", "projects").
DEFAULT_ROLE_SCOPE_MATRIX: dict[str, dict[str, str]] = {
    "developer-executive": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "project-director": {
        "iam": DataScope.ScopeKey.DEPARTMENT,
        "projects": DataScope.ScopeKey.PROJECT,
    },
    "sales-manager": {
        "iam": DataScope.ScopeKey.DEPARTMENT,
        "projects": DataScope.ScopeKey.PROJECT,
    },
    "finance-controller": {
        "iam": DataScope.ScopeKey.DEPARTMENT,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "procurement-officer": {
        "iam": DataScope.ScopeKey.DEPARTMENT,
        "projects": DataScope.ScopeKey.PROJECT,
    },
    "governance-officer": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "legal": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "external-consultant": {
        "iam": DataScope.ScopeKey.SELF,
        "projects": DataScope.ScopeKey.PROJECT,
    },
    "auditor": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "board-viewer": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "super-admin": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "system-admin": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "department-admin": {
        "iam": DataScope.ScopeKey.DEPARTMENT,
        "projects": DataScope.ScopeKey.DEPARTMENT,
    },
    "manager": {
        "iam": DataScope.ScopeKey.DEPARTMENT,
        "projects": DataScope.ScopeKey.PROJECT,
    },
    "staff": {
        "iam": DataScope.ScopeKey.SELF,
        "projects": DataScope.ScopeKey.PROJECT,
    },
    "external-auditor": {
        "iam": DataScope.ScopeKey.ORGANIZATION,
        "projects": DataScope.ScopeKey.ORGANIZATION,
    },
    "guest": {
        "iam": DataScope.ScopeKey.SELF,
        "projects": DataScope.ScopeKey.SELF,
    },
}


def seed_data_scope_catalog() -> dict[str, DataScope]:
    catalog: dict[str, DataScope] = {}
    for key, meta in DATA_SCOPE_CATALOG.items():
        scope, _ = DataScope.objects.get_or_create(
            key=key,
            defaults={
                "label": meta["label"],
                "description": meta["description"],
                "is_system": True,
            },
        )
        # Keep labels/descriptions aligned when defaults evolve.
        updates = []
        if scope.label != meta["label"]:
            scope.label = meta["label"]
            updates.append("label")
        if scope.description != meta["description"]:
            scope.description = meta["description"]
            updates.append("description")
        if not scope.is_system:
            scope.is_system = True
            updates.append("is_system")
        if updates:
            scope.save(update_fields=[*updates, "updated_at"])
        catalog[key] = scope
    return catalog


def _upsert_role_scope(
    *,
    role: Role,
    module: str,
    data_scope: DataScope,
    reset: bool,
) -> tuple[int, int]:
    created = 0
    updated = 0
    existing_qs = RoleScope.objects.filter(
        role=role,
        module=module,
        sub_module="",
    ).order_by("id")

    if not existing_qs.exists():
        RoleScope.objects.create(
            role=role,
            module=module,
            sub_module="",
            data_scope=data_scope,
        )
        return 1, 0

    matching_qs = existing_qs.filter(data_scope=data_scope)
    if matching_qs.exists():
        if reset:
            # Keep the first matching row and remove divergent rows for this module.
            keep_id = matching_qs.values_list("id", flat=True).first()
            deleted_count, _ = existing_qs.exclude(id=keep_id).delete()
            updated += deleted_count
        return created, updated

    if not reset:
        RoleScope.objects.create(
            role=role,
            module=module,
            sub_module="",
            data_scope=data_scope,
        )
        return 1, 0

    # Reset mode: converge all module-level rows to a single default scope.
    scope = existing_qs.first()
    scope.data_scope = data_scope
    scope.save(update_fields=["data_scope"])
    updated += 1
    deleted_count, _ = existing_qs.exclude(id=scope.id).delete()
    updated += deleted_count
    return created, updated


def seed_role_scopes_for_org(org, *, reset: bool = False) -> tuple[int, int]:
    """
    Seed module-level role scopes for one organization.

    Returns: (created_count, updated_count)
    """
    catalog = seed_data_scope_catalog()
    created_count = 0
    updated_count = 0

    roles = Role.objects.filter(organization=org)
    for role in roles:
        module_scope_map = DEFAULT_ROLE_SCOPE_MATRIX.get(role.slug)
        if not module_scope_map:
            continue
        for module_key, scope_key in module_scope_map.items():
            data_scope = catalog.get(scope_key)
            if not data_scope:
                continue
            created, updated = _upsert_role_scope(
                role=role,
                module=module_key,
                data_scope=data_scope,
                reset=reset,
            )
            created_count += created
            updated_count += updated

    return created_count, updated_count


def _default_scope_map_for_profile(profile) -> Mapping[str, str] | None:
    if profile.role == "admin":
        return {
            "iam": DataScope.ScopeKey.ORGANIZATION,
            "projects": DataScope.ScopeKey.ORGANIZATION,
        }

    role = getattr(profile, "assigned_role", None)
    role_slug = getattr(role, "slug", "") if role else ""
    if not role_slug:
        return None
    return DEFAULT_ROLE_SCOPE_MATRIX.get(role_slug)


def seed_user_scope_assignments_for_org(org, *, reset: bool = False) -> tuple[int, int]:
    """
    Seed user-level scope assignments as explicit overrides.

    Returns: (created_count, updated_count)
    """
    from apps.accounts.models import UserProfile

    catalog = seed_data_scope_catalog()
    created_count = 0
    updated_count = 0

    profiles = (
        UserProfile.objects.filter(organization=org)
        .select_related("assigned_role", "user")
    )

    for profile in profiles:
        user_scope_map = _default_scope_map_for_profile(profile)
        if not user_scope_map:
            continue

        for module_key, scope_key in user_scope_map.items():
            data_scope = catalog.get(scope_key)
            if not data_scope:
                continue

            existing_qs = UserScopeAssignment.objects.filter(
                user_id=profile.user_id,
                module=module_key,
                sub_module="",
            ).order_by("id")

            if not existing_qs.exists():
                UserScopeAssignment.objects.create(
                    user_id=profile.user_id,
                    module=module_key,
                    sub_module="",
                    data_scope=data_scope,
                )
                created_count += 1
                continue

            matching_qs = existing_qs.filter(data_scope=data_scope)
            if matching_qs.exists():
                if reset:
                    keep_id = matching_qs.values_list("id", flat=True).first()
                    deleted_count, _ = existing_qs.exclude(id=keep_id).delete()
                    updated_count += deleted_count
                continue

            if not reset:
                UserScopeAssignment.objects.create(
                    user_id=profile.user_id,
                    module=module_key,
                    sub_module="",
                    data_scope=data_scope,
                )
                created_count += 1
                continue

            assignment = existing_qs.first()
            assignment.data_scope = data_scope
            assignment.save(update_fields=["data_scope"])
            updated_count += 1
            deleted_count, _ = existing_qs.exclude(id=assignment.id).delete()
            updated_count += deleted_count

    return created_count, updated_count

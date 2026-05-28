from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Q, QuerySet

from .models import DataScope, RoleScope, UserScopeAssignment


def _scope_target_filter(module: str, sub_module: str = "") -> Q:
    module = (module or "").strip()
    sub_module = (sub_module or "").strip()

    target_filter = Q(module="", sub_module="")
    if module:
        target_filter |= Q(module=module, sub_module="")
    if sub_module:
        target_filter |= Q(sub_module=sub_module)
    return target_filter


def _project_manager_identifiers(user) -> list[str]:
    values = []
    full_name = user.get_full_name().strip()
    if full_name:
        values.append(full_name)
    email = getattr(user, "email", "") or ""
    if email:
        values.append(email.strip())
    username = getattr(user, "username", "") or ""
    if username:
        values.append(username.strip())

    seen = set()
    deduped = []
    for value in values:
        key = value.lower()
        if key not in seen:
            deduped.append(value)
            seen.add(key)
    return deduped


def _combine_or(filters: Iterable[Q]) -> Q | None:
    combined = None
    for q_filter in filters:
        combined = q_filter if combined is None else (combined | q_filter)
    return combined


def effective_scope_keys_for_user(
    user,
    *,
    module: str,
    sub_module: str = "",
) -> set[str]:
    if not user or not user.is_authenticated:
        return set()

    if user.is_superuser:
        return {DataScope.ScopeKey.ORGANIZATION}

    profile = getattr(user, "profile", None)
    if profile is None:
        return set()

    if profile.role == "admin":
        return {DataScope.ScopeKey.ORGANIZATION}

    target_filter = _scope_target_filter(module=module, sub_module=sub_module)

    user_scopes = set(
        UserScopeAssignment.objects.filter(user_id=user.id)
        .filter(target_filter)
        .values_list("data_scope__key", flat=True)
    )
    if user_scopes:
        return user_scopes

    role_id = getattr(profile, "assigned_role_id", None)
    if role_id:
        role_scopes = set(
            RoleScope.objects.filter(role_id=role_id)
            .filter(target_filter)
            .values_list("data_scope__key", flat=True)
        )
        if role_scopes:
            return role_scopes

    # Backward-compatible default until explicit scopes are assigned.
    return {DataScope.ScopeKey.ORGANIZATION}


def scoped_user_profile_queryset_for_user(
    queryset: QuerySet,
    user,
    *,
    sub_module: str = "iam.users",
) -> QuerySet:
    scope_keys = effective_scope_keys_for_user(
        user,
        module="iam",
        sub_module=sub_module,
    )
    if not scope_keys:
        return queryset.none()

    if DataScope.ScopeKey.ORGANIZATION in scope_keys:
        if user.is_superuser:
            return queryset
        org = _user_organization(user)
        if org is None:
            return queryset.none()
        return queryset.filter(organization=org)

    profile = getattr(user, "profile", None)
    filters = []

    if DataScope.ScopeKey.SELF in scope_keys:
        filters.append(Q(user_id=user.id))

    if DataScope.ScopeKey.DEPARTMENT in scope_keys and profile and profile.department_id:
        filters.append(Q(department_id=profile.department_id))

    combined = _combine_or(filters)
    if combined is None:
        return queryset.none()
    return queryset.filter(combined).distinct()


def _user_organization(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "organization", None)


def scoped_project_queryset_for_user(
    queryset: QuerySet,
    user,
    *,
    sub_module: str = "projects.projects",
) -> QuerySet:
    scope_keys = effective_scope_keys_for_user(
        user,
        module="projects",
        sub_module=sub_module,
    )
    if not scope_keys:
        return queryset.none()

    if DataScope.ScopeKey.ORGANIZATION in scope_keys:
        if user.is_superuser:
            return queryset
        org = _user_organization(user)
        if org is None:
            return queryset.none()
        return queryset.filter(organization=org)

    from apps.projects.models import ProjectTask

    manager_identifiers = _project_manager_identifiers(user)
    manager_filter = _combine_or(
        [Q(project_manager__iexact=value) for value in manager_identifiers]
    )

    filters = []

    if DataScope.ScopeKey.SELF in scope_keys and manager_filter is not None:
        filters.append(manager_filter)

    if DataScope.ScopeKey.PROJECT in scope_keys:
        assigned_project_ids = ProjectTask.objects.filter(
            assigned_user_id=user.id
        ).values_list("phase__project_id", flat=True)
        filters.append(Q(pk__in=assigned_project_ids))
        if manager_filter is not None:
            filters.append(manager_filter)

    if DataScope.ScopeKey.DEPARTMENT in scope_keys:
        profile = getattr(user, "profile", None)
        department_id = getattr(profile, "department_id", None)
        if department_id:
            department_project_ids = ProjectTask.objects.filter(
                assigned_user__profile__department_id=department_id
            ).values_list("phase__project_id", flat=True)
            filters.append(Q(pk__in=department_project_ids))
        if manager_filter is not None:
            filters.append(manager_filter)

    combined = _combine_or(filters)
    if combined is None:
        return queryset.none()
    return queryset.filter(combined).distinct()


def scope_queryset_by_projects_for_user(
    queryset: QuerySet,
    user,
    *,
    project_lookup: str,
    sub_module: str = "projects.projects",
) -> QuerySet:
    from apps.projects.models import Project

    visible_project_ids = scoped_project_queryset_for_user(
        Project.objects.all(),
        user,
        sub_module=sub_module,
    ).values_list("id", flat=True)
    return queryset.filter(**{f"{project_lookup}__in": visible_project_ids})

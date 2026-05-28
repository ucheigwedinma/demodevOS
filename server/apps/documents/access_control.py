from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from .models import (
    Document,
    DocumentBusinessUnitMembership,
    DocumentProjectMembership,
    DocumentRoleScope,
)

REPOSITORY_CREATOR_ROLE_SLUGS = {
    "governance-officer",
    "developer-executive",
}


def _is_org_admin(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "admin")


def can_create_repository_document(user) -> bool:
    """Limit document master creation to governance admins + executive tier."""
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    if not profile:
        return False
    if profile.role == "admin":
        return True
    assigned_role = getattr(profile, "assigned_role", None)
    return bool(assigned_role and assigned_role.slug in REPOSITORY_CREATOR_ROLE_SLUGS)


def ensure_can_create_repository_document(user) -> None:
    if can_create_repository_document(user):
        return
    raise PermissionDenied(
        "Only governance admins, superusers, and developer executives can add documents."
    )


def _require_profile_and_role(user):
    profile = getattr(user, "profile", None)
    if not profile or not profile.assigned_role_id:
        raise PermissionDenied("No assigned role found for this user.")
    return profile


def _get_or_create_role_scope(user) -> DocumentRoleScope:
    profile = _require_profile_and_role(user)
    scope, _ = DocumentRoleScope.objects.get_or_create(role_id=profile.assigned_role_id)
    return scope


def _membership_sets(user) -> tuple[set[int], set[int]]:
    memberships = (
        DocumentBusinessUnitMembership.objects
        .filter(user=user)
        .select_related("department__division")
    )

    division_ids: set[int] = set()
    department_ids: set[int] = set()

    for membership in memberships:
        if membership.division_id:
            division_ids.add(membership.division_id)
        if membership.department_id:
            department_ids.add(membership.department_id)
            if membership.department and membership.department.division_id:
                division_ids.add(membership.department.division_id)

    return division_ids, department_ids


def _normalize_confidentiality_levels(levels: Iterable[str]) -> list[str]:
    allowed = {
        Document.ConfidentialityLevel.PUBLIC,
        Document.ConfidentialityLevel.INTERNAL,
        Document.ConfidentialityLevel.CONFIDENTIAL,
        Document.ConfidentialityLevel.RESTRICTED,
    }
    result: list[str] = []
    seen: set[str] = set()
    for level in levels:
        if level in seen or level not in allowed:
            continue
        seen.add(level)
        result.append(level)
    return result


def scoped_document_queryset_for_user(user, queryset=None):
    """Return the document queryset constrained by role scope + memberships."""
    queryset = queryset or Document.objects.all()

    if _is_org_admin(user):
        return queryset

    scope = _get_or_create_role_scope(user)

    allowed_levels = _normalize_confidentiality_levels(scope.allowed_confidentiality_levels or [])
    if not allowed_levels:
        return queryset.none()

    scoped_queryset = queryset.filter(confidentiality_level__in=allowed_levels)

    if scope.project_scope == DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS:
        project_ids = list(
            DocumentProjectMembership.objects
            .filter(user=user)
            .values_list("project_id", flat=True)
        )
        if not project_ids:
            return scoped_queryset.none()
        scoped_queryset = scoped_queryset.filter(project_id__in=project_ids)

    if scope.business_unit_scope == DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS:
        division_ids, department_ids = _membership_sets(user)
        if not division_ids and not department_ids:
            return scoped_queryset.none()

        business_unit_filter = Q()
        if department_ids:
            business_unit_filter |= Q(business_unit_department_id__in=department_ids)
        if division_ids:
            business_unit_filter |= Q(business_unit_division_id__in=division_ids)
            business_unit_filter |= Q(business_unit_department__division_id__in=division_ids)

        scoped_queryset = scoped_queryset.filter(business_unit_filter)

    return scoped_queryset


def filter_queryset_by_scoped_documents(user, queryset, document_lookup: str = "document"):
    """Filter any queryset via a related document foreign key path."""
    scoped_documents = scoped_document_queryset_for_user(user).values("id")
    return queryset.filter(**{f"{document_lookup}_id__in": scoped_documents})


def ensure_payload_within_scope(
    user,
    *,
    project_id: int | None,
    business_unit_division_id: int | None,
    business_unit_department_id: int | None,
    confidentiality_level: str,
) -> None:
    """Validate write payload against project/business-unit/confidentiality scope."""
    if _is_org_admin(user):
        return

    scope = _get_or_create_role_scope(user)

    allowed_levels = _normalize_confidentiality_levels(scope.allowed_confidentiality_levels or [])
    if confidentiality_level not in allowed_levels:
        raise PermissionDenied("Confidentiality level is outside your role scope.")

    if scope.project_scope == DocumentRoleScope.ProjectScope.ASSIGNED_PROJECTS:
        if project_id is None:
            raise PermissionDenied("This role can only create or edit project-scoped documents.")

        is_member = DocumentProjectMembership.objects.filter(
            user=user,
            project_id=project_id,
        ).exists()
        if not is_member:
            raise PermissionDenied("Project is outside your membership scope.")

    if scope.business_unit_scope == DocumentRoleScope.BusinessUnitScope.ASSIGNED_BUSINESS_UNITS:
        division_ids, department_ids = _membership_sets(user)
        if not division_ids and not department_ids:
            raise PermissionDenied("No business unit memberships are assigned for this user.")

        if business_unit_department_id and business_unit_department_id in department_ids:
            return

        if business_unit_division_id and business_unit_division_id in division_ids:
            return

        if business_unit_division_id is None and business_unit_department_id is None:
            raise PermissionDenied("A business unit is required for this role scope.")

        if business_unit_department_id:
            from apps.settings.models import Department

            department = Department.objects.filter(id=business_unit_department_id).first()
            if department and department.division_id in division_ids:
                return

        raise PermissionDenied("Business unit is outside your membership scope.")


def ensure_document_in_scope(user, document: Document) -> None:
    if _is_org_admin(user):
        return

    allowed = scoped_document_queryset_for_user(user, queryset=Document.objects.filter(pk=document.pk)).exists()
    if not allowed:
        raise PermissionDenied("Document is outside your role scope.")

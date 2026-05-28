from django.db.models import Q
from rest_framework.exceptions import PermissionDenied


def check_resource_quota(organization, resource_model, quota_field, label):
    """
    Raise PermissionDenied if the organization has reached its edition quota.

    Args:
        organization: The Organization instance.
        resource_model: The Django model class to count (e.g. Project, Property).
        quota_field: The PlatformEdition field name holding the limit (e.g. "max_projects").
        label: Human-readable resource name for the error message (e.g. "projects").
    """
    subscription = getattr(organization, "subscription", None)
    if subscription is None:
        return

    edition = subscription.edition
    limit = getattr(edition, quota_field, None)
    if limit is None:
        return  # unlimited

    current_count = resource_model.objects.filter(organization=organization).count()
    if current_count >= limit:
        raise PermissionDenied(
            f"Your {edition.name} plan allows a maximum of {limit} {label}. "
            f"Upgrade your plan to create more."
        )


def check_seat_quota(organization):
    """
    Raise PermissionDenied if the organization has reached its user seat limit.
    Counts active users + pending invitations against the edition's max_users.
    """
    from apps.accounts.models import Invitation, UserProfile

    subscription = getattr(organization, "subscription", None)
    if subscription is None:
        return

    limit = subscription.effective_max_users
    if limit is None:
        return  # unlimited (Scale)

    active_users = UserProfile.objects.filter(
        organization=organization, user__is_active=True,
    ).count()
    pending_invites = Invitation.objects.filter(
        organization=organization, status="pending",
    ).count()

    if active_users + pending_invites >= limit:
        raise PermissionDenied(
            f"Your {subscription.edition.name} plan allows a maximum of "
            f"{limit} users. Upgrade your plan to invite more."
        )


def is_entity_map_available(organization, entity) -> bool:
    """
    Check if this entity (project or property) is within the org's
    map quota. Entities with GPS coordinates are ranked by creation date;
    only the first N (per edition limit) get maps.

    Returns True if unlimited or within quota, False otherwise.
    """
    subscription = getattr(organization, "subscription", None)
    if subscription is None:
        return True

    limit = getattr(subscription.edition, "max_entity_maps", None)
    if limit is None:
        return True  # unlimited

    from apps.projects.models import Project
    from apps.properties.models import Property

    has_gps = Q(gps_latitude__isnull=False, gps_longitude__isnull=False)
    org_filter = Q(organization=organization)

    # Collect (created_at, type, id) for all entities with GPS coords
    entries = []
    for pk, created_at in (
        Project.objects.filter(org_filter & has_gps)
        .order_by("created_at")
        .values_list("id", "created_at")
    ):
        entries.append(("project", pk, created_at))
    for pk, created_at in (
        Property.objects.filter(org_filter & has_gps)
        .order_by("created_at")
        .values_list("id", "created_at")
    ):
        entries.append(("property", pk, created_at))

    # Sort by creation date, take the first N
    entries.sort(key=lambda e: e[2])
    allowed = entries[:limit]

    if isinstance(entity, Project):
        return ("project", entity.pk) in {(t, pk) for t, pk, _ in allowed}
    if isinstance(entity, Property):
        return ("property", entity.pk) in {(t, pk) for t, pk, _ in allowed}
    return False

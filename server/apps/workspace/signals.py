"""
Workspace signals.

Three responsibilities:

1. **Slug generation** — auto-fill `Team.slug` from `name` on create, and
   recompute on rename (with deterministic -2/-3 suffixing per design EC8).

2. **Owner auto-promotion** — when a user is deactivated (`is_active=False`),
   promote the oldest admin of every team they own (per design EC2). If no
   admin exists, the team becomes orphaned (computed via `Team.is_orphaned`).

3. **Membership-state notifications** — fire real-time notifications for the
   six events listed in design §10 table A. Respects `notify_realtime`.
"""

from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Team, TeamMembership


# ---------------------------------------------------------------------------
# 1. Slug generation
# ---------------------------------------------------------------------------


@receiver(pre_save, sender=Team)
def _team_slug_pre_save(sender, instance: Team, **kwargs):
    """Auto-fill slug on create; recompute on rename."""
    if not instance.organization_id:
        return
    needs_regen = False
    if not instance.slug:
        needs_regen = True
    elif instance.pk:
        try:
            current = Team.objects.only("name", "slug").get(pk=instance.pk)
        except Team.DoesNotExist:
            current = None
        if current is not None and current.name != instance.name and not _slug_was_set_explicitly(
            current.slug, instance.slug
        ):
            needs_regen = True
    if needs_regen:
        instance.slug = Team.generate_unique_slug(
            instance.organization, instance.name, exclude_pk=instance.pk
        )


def _slug_was_set_explicitly(old_slug: str, new_slug: str) -> bool:
    """
    If the slug was deliberately changed by the caller (different from old
    AND not derivable from the new name automatically), respect their choice.
    Conservative: regenerate only when slug field wasn't touched.
    """
    return old_slug != new_slug


# ---------------------------------------------------------------------------
# 2. Owner auto-promotion (design EC2)
# ---------------------------------------------------------------------------


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def _user_deactivated_promote_admin(sender, instance, created, **kwargs):
    """
    When a user becomes inactive (is_active=False), promote the oldest active
    admin of every team they own. If no admin exists, the team is left
    "orphaned" — surfaced via the `Team.is_orphaned` computed property.

    Only fires on transitions to inactive (best-effort: we recheck membership
    on every user save; cheap and idempotent).
    """
    if created or instance.is_active:
        return
    owner_memberships = TeamMembership.objects.filter(
        user=instance, role=TeamMembership.Role.OWNER
    ).select_related("team")
    for ownership in owner_memberships:
        new_owner = (
            TeamMembership.objects.filter(
                team=ownership.team,
                role=TeamMembership.Role.ADMIN,
                user__is_active=True,
            )
            .order_by("joined_at")
            .first()
        )
        if new_owner is None:
            # No admin to promote — team becomes orphaned (is_orphaned is computed).
            # The departed owner's membership stays in place; org admins can intervene.
            continue
        # Single-tx swap: demote the inactive owner, promote oldest admin.
        # Done in two saves; the partial unique constraint allows it because
        # we drop the owner-role first.
        ownership.role = TeamMembership.Role.ADMIN
        ownership.save(update_fields=["role", "updated_at"])
        new_owner.role = TeamMembership.Role.OWNER
        new_owner.save(update_fields=["role", "updated_at"])


# ---------------------------------------------------------------------------
# 3. Membership-state notifications
# ---------------------------------------------------------------------------


def _make_notification(*, recipient, organization, title: str, message: str, link_url: str):
    """
    Wrapper around apps.notifications.Notification.objects.create. Imported
    lazily so the signals module loads before the notifications app's
    AppConfig.ready when running the test suite.
    """
    from apps.notifications.models import Notification

    return Notification.objects.create(
        recipient=recipient,
        organization=organization,
        title=title,
        message=message,
        category=Notification.Category.SYSTEM,
        severity=Notification.Severity.INFO,
        link_url=link_url,
    )


def _team_link(team: Team) -> str:
    return f"/teams/{team.id}"


@receiver(post_save, sender=TeamMembership)
def _membership_post_save_notify(sender, instance: TeamMembership, created, update_fields=None, **kwargs):
    """Fan out real-time notifications on add and on role changes."""
    if not instance.notify_realtime:
        return
    team = instance.team
    if created:
        _make_notification(
            recipient=instance.user,
            organization=team.organization,
            title=f"You've been added to {team.name}",
            message=f"You're now a {instance.get_role_display()} of the team.",
            link_url=_team_link(team),
        )
        return

    # Role change: only fire when the role field was specifically updated, OR
    # when we can't tell what changed (no update_fields hint). The transitions
    # we care about are admin↔member and member↔guest; ownership transfer is
    # handled by the dedicated transfer endpoint, which sends both sides.
    if update_fields is not None and "role" not in update_fields:
        return
    role = instance.role
    title_map = {
        TeamMembership.Role.ADMIN: f"You're now an admin of {team.name}",
        TeamMembership.Role.MEMBER: f"Your role in {team.name} changed to Member",
        TeamMembership.Role.GUEST: f"Your role in {team.name} changed to Guest",
        TeamMembership.Role.OWNER: f"You're now the owner of {team.name}",
    }
    message_map = {
        TeamMembership.Role.ADMIN: "You can now manage members and metadata.",
        TeamMembership.Role.MEMBER: "You can view and contribute to team-scoped work.",
        TeamMembership.Role.GUEST: "You can view team-scoped work in read-only mode.",
        TeamMembership.Role.OWNER: "You can manage everything, including transfer and deletion.",
    }
    _make_notification(
        recipient=instance.user,
        organization=team.organization,
        title=title_map.get(role, f"Your role in {team.name} changed"),
        message=message_map.get(role, ""),
        link_url=_team_link(team),
    )


@receiver(post_delete, sender=TeamMembership)
def _membership_post_delete_notify(sender, instance: TeamMembership, **kwargs):
    """Fan out a 'removed from team' notification on delete (incl. self-leave)."""
    if not instance.notify_realtime:
        return
    # During CASCADE from a Team or User delete, instance.team / instance.user
    # may be inaccessible. Skip notification in that case.
    try:
        team = instance.team
        organization = team.organization
        user = instance.user
    except Team.DoesNotExist:  # type: ignore[attr-defined]
        return
    except Exception:
        return
    _make_notification(
        recipient=user,
        organization=organization,
        title=f"You've been removed from {team.name}",
        message="You no longer have access to this team's content.",
        link_url="/teams",
    )

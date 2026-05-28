"""
Workspace teams.

A `Team` is a lightweight, cross-functional collaboration group — a project
pod, an initiative/task force, or an interest-based guild. Distinct from
`apps.hr.Team`, which is department-bound and HR-curated.

A `TeamMembership` is the through-table linking users to teams with a role
(owner/admin/member/guest) and per-user notification preferences.

Lifecycle, visibility, and ownership rules:
- Exactly one `owner` per team (DB-enforced via partial unique constraint).
- `visibility` controls whether non-members see the team in the directory
  and how they can join. See `Visibility` enum.
- `is_archived=True` hides from default queries but keeps data; an org
  admin can hard-delete via Django admin if truly needed (the API also
  exposes hard delete to owners).

See docs/workspace-teams-design.md §6 for the full design.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Team(models.Model):
    class Purpose(models.TextChoices):
        PROJECT = "project", "Project"
        INITIATIVE = "initiative", "Initiative"
        GUILD = "guild", "Guild"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        SECRET = "secret", "Secret"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="workspace_teams",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    purpose = models.CharField(
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.INITIATIVE,
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workspace_teams",
        help_text="Set only when purpose='project'.",
    )
    emoji = models.CharField(max_length=8, default="👥")
    color = models.CharField(
        max_length=20,
        default="sky",
        help_text="Palette token (e.g. 'sky', 'violet'). Resolved to Tailwind classes on the frontend.",
    )
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_workspace_teams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="workspace_team_org_slug_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="ws_team_org_created_idx",
            ),
            models.Index(
                fields=["organization", "is_archived", "visibility"],
                name="ws_team_org_arch_vis_idx",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    # --- Slug helpers --------------------------------------------------------

    @classmethod
    def generate_unique_slug(cls, organization, name: str, *, exclude_pk=None) -> str:
        """
        Deterministic, idempotent: turn name into a slug, then append -2/-3/...
        until it's unique within the organization. Excluding `exclude_pk` lets
        us call this on rename without colliding with our own row.
        """
        base = slugify(name) or "team"
        slug = base
        suffix = 2
        qs = cls.objects.filter(organization=organization)
        if exclude_pk is not None:
            qs = qs.exclude(pk=exclude_pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    @property
    def is_orphaned(self) -> bool:
        """True when nobody can manage this team (no active owner or admin)."""
        return not self.memberships.filter(
            role__in=[TeamMembership.Role.OWNER, TeamMembership.Role.ADMIN],
            user__is_active=True,
        ).exists()


class TeamMembership(models.Model):
    """
    User membership in a workspace team.

    The four-tier role enum (owner/admin/member/guest) is documented in
    docs/workspace-teams-design.md §8. Per-membership notification prefs
    are stored here (not on a separate table) — one row per (user, team)
    is the right granularity.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        GUEST = "guest", "Guest"

    class DigestFrequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        OFF = "off", "Off"

    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workspace_invitations_sent",
    )
    notify_realtime = models.BooleanField(default=True)
    digest_frequency = models.CharField(
        max_length=10,
        choices=DigestFrequency.choices,
        default=DigestFrequency.DAILY,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "user"],
                name="ws_membership_team_user_uniq",
            ),
            models.UniqueConstraint(
                fields=["team"],
                condition=models.Q(role="owner"),
                name="ws_membership_one_owner_per_team",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "team"],
                name="ws_membership_user_team_idx",
            ),
            models.Index(
                fields=["team", "role"],
                name="ws_membership_team_role_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.team} ({self.role})"

"""
Internal task models.

`Task` is the lightweight personal/team todo entity — distinct from
`apps.projects.ProjectTask` (project-scoped), `apps.crm.FollowUpTask`
(CRM pipeline), and `apps.hr.OnboardingTask` (HR onboarding). Those keep
their domain-specific fields; Internal Tasks captures the "loose work"
gap.

`TaskComment` carries discussion + @mention notifications.

Per design §6:
- `completed_at` auto-populated on transition to status=done (cleared on
  reopen).
- `tags` are stored lowercase via TaskQuerySet helpers and the save()
  override.
- `mentions` on a comment are computed from the body via regex on save.
- `checklist_items` schema validated in the serializer (NOT the model)
  to keep the model thin.

See docs/workspace-internal-tasks-design.md.
"""

from __future__ import annotations

import re
from typing import Iterable

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# `@username` parser. Matches the local-part of an email or a generic
# alphanumeric handle. We resolve to users in the comment's save() override.
_MENTION_RE = re.compile(r"@([A-Za-z0-9._\-]+)")


def _normalize_tags(values: Iterable[str]) -> list[str]:
    """
    Lowercase + trim + dedupe (order-preserving). Empty strings dropped.
    Per design EC7: tag "BoarD" is stored as "board".
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in values or []:
        v = (raw or "").strip().lower()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------


class Task(models.Model):
    """
    A loose personal/team todo. Distinct from operational task models.
    """

    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        TEAM = "team", "Team"
        ORG = "org", "Org-wide"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="internal_tasks",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_internal_tasks",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_internal_tasks",
        help_text="Defaults to creator at create time; can be null = unassigned (team backlog).",
    )
    team = models.ForeignKey(
        "workspace.Team",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="internal_tasks",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )

    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Auto-set by save() when status transitions to 'done'; cleared on reopen.",
    )

    tags = ArrayField(
        models.CharField(max_length=40),
        default=list,
        blank=True,
        help_text="Lowercased on save. Filter via ?tag=foo (uses GIN index for AND queries).",
    )
    checklist_items = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'List of {"label": str, "checked": bool}. Validated in the serializer; '
            "soft limit 50 (UI warning), hard limit 100 (serializer 400)."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "status", "due_date"],
                name="it_org_status_due_idx",
            ),
            models.Index(
                fields=["assignee", "status", "due_date"],
                name="it_assignee_status_due_idx",
            ),
            models.Index(
                fields=["team", "status", "due_date"],
                name="it_team_status_due_idx",
            ),
            GinIndex(fields=["tags"], name="it_tags_gin_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        """
        - Lowercase tags via the helper (defensive — the serializer also does
          this; bare ORM creates still produce normalized rows).
        - Auto-set/clear completed_at when status transitions to/from 'done'.
        """
        self.tags = _normalize_tags(self.tags or [])

        # Detect status transition via the in-memory cache of the previous
        # status. Refreshed via __init__ pre-load below.
        previous_status = getattr(self, "_previous_status", None)
        if self.status == self.Status.DONE and previous_status != self.Status.DONE:
            self.completed_at = timezone.now()
        elif self.status != self.Status.DONE and previous_status == self.Status.DONE:
            self.completed_at = None

        super().save(*args, **kwargs)
        # Refresh the in-memory cache so subsequent saves see the right value.
        self._previous_status = self.status

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cache the value loaded from the DB so save() can detect transitions.
        # New (unsaved) rows will see previous_status == default (Status.TODO).
        self._previous_status = self.status


# ---------------------------------------------------------------------------
# TaskComment
# ---------------------------------------------------------------------------


class TaskComment(models.Model):
    """
    A comment on a Task. `mentions` is auto-computed from the body via regex.
    Per design EC4: unknown @handles are silently dropped from `mentions`
    (no error). Per EC5: duplicates are deduped.
    """

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="task_comments",
        help_text=(
            "Null when the author has been deleted (the comment row survives, "
            "but the UI shows '[deactivated user]' per design EC10)."
        ),
    )
    body = models.TextField()
    mentions = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True,
        help_text="User ids parsed from @ syntax in body. Computed in save().",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["task", "created_at"],
                name="it_comment_task_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"comment {self.pk} on task {self.task_id}"

    def save(self, *args, **kwargs):
        """
        Parse mentions from body. Resolve handles → user ids by matching
        against the parent task's organization users. Unknown handles are
        silently dropped (EC4). Duplicates are deduped (EC5).
        """
        self.mentions = self._resolve_mentions(self.body)
        super().save(*args, **kwargs)

    def _resolve_mentions(self, body: str) -> list[int]:
        from django.contrib.auth import get_user_model

        if not body:
            return []
        handles = _MENTION_RE.findall(body)
        if not handles:
            return []

        # Resolve handles to user ids — case-insensitive, within the task's
        # organization, on first_name/last_name OR email local part OR username.
        User = get_user_model()
        unique_handles = []
        seen: set[str] = set()
        for h in handles:
            lh = h.lower()
            if lh not in seen:
                seen.add(lh)
                unique_handles.append(lh)

        org = getattr(self.task, "organization_id", None)
        if org is None:
            return []

        qs = User.objects.filter(profile__organization_id=org).only(
            "id", "first_name", "last_name", "email", "username"
        )

        ids_in_order: list[int] = []
        for handle in unique_handles:
            match = next(
                (
                    u
                    for u in qs
                    if _user_matches_handle(u, handle)
                ),
                None,
            )
            if match is not None and match.id not in ids_in_order:
                ids_in_order.append(match.id)
        return ids_in_order


def _user_matches_handle(user, handle: str) -> bool:
    """Match a @handle against a user's name, email local-part, or username."""
    handle_l = handle.lower()
    # username
    if (user.username or "").lower() == handle_l:
        return True
    # email local-part
    email_local = (user.email or "").split("@", 1)[0].lower()
    if email_local and email_local == handle_l:
        return True
    # first.last or first
    first = (user.first_name or "").lower()
    last = (user.last_name or "").lower()
    if first and (first == handle_l or f"{first}.{last}" == handle_l):
        return True
    return False

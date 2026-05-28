"""
Calendar models.

`CalendarEvent` is the new "loose event" model — covers project pods'
1:1s, focus blocks, OOO, and reminders. Distinct from `apps.meetings.Meeting`
which owns operational/structured business meetings.

Per design §6:
- CHECK constraint enforces ends_at >= starts_at OR ends_at IS NULL (latter
  reserved for kind=reminder).
- Occurrence overrides are sparse — null/blank means "unchanged from the
  series template" — keeping the table small even for active series.
- `recurrence_rule` is an RFC 5545 RRULE string (no leading `RRULE:` prefix
  to match what python-dateutil emits and consumes).
- iCal feed tokens stored hashed (SHA-256); the raw token is only shown once
  at allocation and must be rotated to recover.

See docs/workspace-calendar-design.md.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class CalendarEvent(models.Model):
    class Kind(models.TextChoices):
        MEETING = "meeting", "Meeting"
        FOCUS = "focus", "Focus block"
        OUT_OF_OFFICE = "out_of_office", "Out of office"
        REMINDER = "reminder", "Reminder"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        TEAM = "team", "Team"
        ORG = "org", "Org-wide"

    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="calendar_events",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_calendar_events",
    )
    team = models.ForeignKey(
        "workspace.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_events",
        help_text="Optional. Required when visibility=team.",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    meeting_link = models.URLField(max_length=500, blank=True)
    external_attendee_emails = models.JSONField(
        default=list,
        blank=True,
        help_text="Free-form list of external (non-org) attendee emails. Used for .ics email invites.",
    )

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.MEETING,
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text="IANA name (e.g. America/New_York). Used for RRULE expansion + render.",
    )

    recurrence_rule = models.CharField(
        max_length=400,
        blank=True,
        help_text="RFC 5545 RRULE without the 'RRULE:' prefix. Empty = single occurrence.",
    )
    recurrence_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Denormalised cap derived from RRULE UNTIL/COUNT, or null for open-ended.",
    )

    reminder_minutes_before = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "null → use UserProfile.default_reminder_minutes; "
            "0 → no reminder; >0 → override in minutes."
        ),
    )

    is_cancelled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [
            models.Index(
                fields=["organization", "starts_at"],
                name="calendar_event_org_start_idx",
            ),
            models.Index(
                fields=["creator", "starts_at"],
                name="cal_event_creator_start_idx",
            ),
            models.Index(
                fields=["team", "starts_at"],
                name="calendar_event_team_start_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                # ends_at must be >= starts_at when present; null is allowed (kind=reminder).
                check=models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=F("starts_at")),
                name="calendar_event_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.kind})"

    @property
    def is_recurring(self) -> bool:
        return bool(self.recurrence_rule)


class CalendarEventOccurrence(models.Model):
    """
    Override of a single occurrence of a recurring CalendarEvent.

    Sparse semantics:
    - `original_start` is mandatory and identifies the occurrence (matches
      what the RRULE would have produced).
    - `is_cancelled=True` skips this occurrence entirely.
    - `starts_at`/`ends_at` null means "unchanged from the RRULE-expanded time."
    - `title`/`location`/`description` blank means "unchanged from the series."

    An override becomes "orphaned" (per EC4) when `original_start` no longer
    matches the parent event's RRULE — caller shortened the rule, or COUNT
    was reduced below the override's index. Orphans are detected at
    expansion time and surfaced in the list response so the UI can offer
    cleanup.
    """

    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name="occurrences",
    )
    original_start = models.DateTimeField(
        help_text="The UTC start the RRULE would have produced. Identifies the occurrence."
    )
    is_cancelled = models.BooleanField(default=False)

    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "original_start"],
                name="calendar_occurrence_event_original_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["event", "original_start"], name="calendar_occ_event_orig_idx"),
        ]

    def __str__(self) -> str:
        return f"Override of {self.event_id} at {self.original_start}"


class CalendarEventAttendee(models.Model):
    """User attendee on a CalendarEvent (no RSVP in v1; just presence)."""

    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name="attendees",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_event_attendances",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_event_invitations_sent",
    )
    invited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="calendar_attendee_event_user_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "event"], name="cal_attendee_user_event_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.event}"


class IcalFeedToken(models.Model):
    """
    Per-user iCal subscription token. One row per active token; rotated
    tokens stay rows with `revoked_at` set so we can audit who rotated when.

    The raw token is only present on allocation — we store SHA-256 hash.
    Resolution: SELECT user FROM IcalFeedToken WHERE token_hash = sha256(req_token)
                AND revoked_at IS NULL.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ical_feed_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "revoked_at"], name="ical_token_user_revoked_idx"),
        ]

    def __str__(self) -> str:
        return f"iCalToken user={self.user_id} revoked={self.revoked_at is not None}"

    @staticmethod
    def generate_raw_token() -> str:
        """Return a fresh URL-safe random token. Caller hashes via hash_token()."""
        return secrets.token_urlsafe(24)

    @staticmethod
    def hash_token(raw: str) -> str:
        import hashlib

        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

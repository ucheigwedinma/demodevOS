"""
Unified Meeting Management System.

Provides a single meeting model that serves all modules:
  - Projects (site meetings, steering committee)
  - Construction (toolbox talks, progress reviews)
  - Design (design reviews)
  - CRM (client meetings)
  - Finance (investor updates)
  - Consultant coordination

Features:
  - Meeting templates for recurring series
  - Auto-generated minutes from agenda + action items
  - Calendar integration (iCal export)
  - Cross-module linking (project, consultant, lead, etc.)
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class MeetingTemplate(models.Model):
    """Reusable template for recurring meeting series."""

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        FORTNIGHTLY = "fortnightly", "Fortnightly"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        AD_HOC = "ad_hoc", "Ad-Hoc"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="meeting_templates",
    )
    name = models.CharField(max_length=255, help_text="e.g. Weekly Site Progress, Monthly Steering Committee")
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.WEEKLY)

    # Default agenda sections
    default_agenda = models.JSONField(
        default=list, blank=True,
        help_text='[{"title":"Health & Safety","duration_mins":10},{"title":"Progress Review","duration_mins":30}]',
    )

    # Default attendees (roles, not specific people)
    default_attendee_roles = models.JSONField(
        default=list, blank=True,
        help_text='["Project Manager","Lead Architect","QS","Site Supervisor"]',
    )

    # Auto-generation settings
    auto_generate_minutes = models.BooleanField(
        default=True, help_text="Auto-generate minutes document from completed meeting.",
    )
    minutes_template = models.TextField(
        blank=True,
        help_text="Template text for minutes. Variables: {title}, {date}, {attendees}, {agenda}, {decisions}, {action_items}",
    )

    default_duration_mins = models.PositiveIntegerField(default=60)
    default_location = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class Meeting(models.Model):
    """Unified meeting record used across all modules."""

    class MeetingType(models.TextChoices):
        SITE_PROGRESS = "site_progress", "Site Progress Meeting"
        STEERING_COMMITTEE = "steering_committee", "Steering Committee"
        DESIGN_REVIEW = "design_review", "Design Review"
        TOOLBOX_TALK = "toolbox_talk", "Toolbox Talk / Safety Briefing"
        INVESTOR_UPDATE = "investor_update", "Investor Update"
        CLIENT_MEETING = "client_meeting", "Client Meeting"
        CONSULTANT_COORDINATION = "consultant_coordination", "Consultant Coordination"
        PROCUREMENT_REVIEW = "procurement_review", "Procurement Review"
        FINANCIAL_REVIEW = "financial_review", "Financial Review"
        HANDOVER = "handover", "Handover Meeting"
        KICK_OFF = "kick_off", "Kick-Off Meeting"
        CLOSE_OUT = "close_out", "Close-Out Meeting"
        OTHER = "other", "Other"

    class MeetingStatus(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        POSTPONED = "postponed", "Postponed"

    class MeetingFormat(models.TextChoices):
        IN_PERSON = "in_person", "In Person"
        VIDEO_CALL = "video_call", "Video Call"
        PHONE = "phone", "Phone Conference"
        HYBRID = "hybrid", "Hybrid"

    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="meetings",
    )

    # Template & Series
    template = models.ForeignKey(
        MeetingTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="meetings", help_text="Template this meeting was created from.",
    )
    series_name = models.CharField(
        max_length=255, blank=True,
        help_text="Grouping name, e.g. 'Weekly Site Meeting'. Auto-set from template.",
    )

    # Core
    meeting_number = models.CharField(max_length=100, blank=True, unique=True)
    title = models.CharField(max_length=255)
    meeting_type = models.CharField(max_length=30, choices=MeetingType.choices, default=MeetingType.OTHER)
    status = models.CharField(max_length=20, choices=MeetingStatus.choices, default=MeetingStatus.SCHEDULED)
    meeting_format = models.CharField(max_length=20, choices=MeetingFormat.choices, default=MeetingFormat.IN_PERSON)

    # Scheduling
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    duration_mins = models.PositiveIntegerField(default=60)

    # Location
    location = models.CharField(max_length=255, blank=True)
    meeting_link = models.URLField(max_length=500, blank=True, help_text="Video call URL")

    # Cross-module links (all nullable — meeting can relate to any combination)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="meetings",
    )
    consultant = models.ForeignKey(
        "projects.ProjectConsultant", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="meetings",
    )

    # Content
    agenda = models.JSONField(
        default=list, blank=True,
        help_text='[{"title":"Item","duration_mins":10,"presenter":"Name","notes":""}]',
    )
    key_decisions = models.JSONField(
        default=list, blank=True,
        help_text='[{"decision":"Text","decided_by":"Name","rationale":"Why"}]',
    )

    # Live Notes (raw input during meeting — the source for AI generation)
    live_notes = models.TextField(
        blank=True,
        help_text="Raw notes typed during the meeting. AI processes these into structured minutes.",
    )

    # Post-Meeting Structured Capture (fallback when no live notes)
    discussion_points = models.JSONField(
        default=list, blank=True,
        help_text='[{"topic":"What was discussed","summary":"Key points","raised_by":"Name"}]',
    )
    decisions_made = models.JSONField(
        default=list, blank=True,
        help_text='[{"decision":"What was decided","decided_by":"Who","rationale":"Why","impact":"What it affects"}]',
    )
    issues_raised = models.JSONField(
        default=list, blank=True,
        help_text='[{"issue":"Problem","raised_by":"Name","resolution":"How resolved or next steps"}]',
    )

    # Minutes (AI-generated from live_notes, or from structured form, or manual)
    class MinutesSource(models.TextChoices):
        NOT_GENERATED = "not_generated", "Not Generated"
        AI_FROM_NOTES = "ai_from_notes", "AI — From Live Notes"
        AI_FROM_FORM = "ai_from_form", "AI — From Structured Form"
        MANUAL = "manual", "Manually Written"

    minutes_text = models.TextField(blank=True, help_text="Final meeting minutes.")
    minutes_source = models.CharField(
        max_length=20, choices=MinutesSource.choices, default=MinutesSource.NOT_GENERATED,
    )
    minutes_generated_at = models.DateTimeField(null=True, blank=True)
    minutes_approved = models.BooleanField(default=False)
    minutes_approved_by = models.CharField(max_length=255, blank=True)
    minutes_approved_at = models.DateTimeField(null=True, blank=True)

    # Organizer
    organized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="meeting_organized_meetings",
    )
    recorded_by = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_start"]
        indexes = [
            models.Index(fields=["organization", "status", "-scheduled_start"], name="mtg_org_sts_start_idx"),
            models.Index(fields=["organization", "meeting_type"], name="mtg_org_type_idx"),
            models.Index(fields=["project", "-scheduled_start"], name="mtg_proj_start_idx"),
        ]

    @property
    def is_overdue(self):
        if self.status in ("completed", "cancelled"):
            return False
        if self.scheduled_start and self.scheduled_start < timezone.now():
            return self.status == "scheduled"
        return False

    def save(self, *args, **kwargs):
        if not self.meeting_number:
            last = (
                Meeting.objects.filter(meeting_number__startswith="MTG-")
                .order_by("-meeting_number")
                .values_list("meeting_number", flat=True)
                .first()
            )
            seq = 1
            if last:
                try:
                    seq = int(last.split("-")[1]) + 1
                except (IndexError, ValueError):
                    pass
            self.meeting_number = f"MTG-{seq:05d}"
        if self.template and not self.series_name:
            self.series_name = self.template.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.meeting_number} — {self.title}"


class MeetingAttendee(models.Model):
    """Individual attendee record for a meeting."""

    class AttendanceStatus(models.TextChoices):
        INVITED = "invited", "Invited"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        ATTENDED = "attended", "Attended"
        NO_SHOW = "no_show", "No Show"

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="attendees")
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=255, blank=True, help_text="e.g. Project Manager, Lead Architect")
    company = models.CharField(max_length=255, blank=True)
    attendance_status = models.CharField(
        max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.INVITED,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="meeting_attendances",
    )
    is_required = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("meeting", "email")]

    def __str__(self):
        return f"{self.name} — {self.get_attendance_status_display()}"


class MeetingActionItem(models.Model):
    """Action item arising from a meeting — can link to project tasks."""

    class ActionStatus(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        OVERDUE = "overdue", "Overdue"

    meeting = models.ForeignKey(Meeting, on_delete=models.CASCADE, related_name="action_items")
    description = models.TextField()
    assigned_to = models.CharField(max_length=255)
    assigned_to_email = models.EmailField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ActionStatus.choices, default=ActionStatus.OPEN)
    completed_date = models.DateField(null=True, blank=True)
    priority = models.CharField(
        max_length=10,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
        default="medium",
    )

    # Link to project task (optional — for "extract to task" feature)
    linked_task = models.ForeignKey(
        "projects.ProjectTask", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="source_meeting_actions",
    )

    sort_order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "due_date"]

    @property
    def is_overdue(self):
        from datetime import date
        if self.status in ("completed", "cancelled"):
            return False
        if self.due_date and self.due_date < date.today():
            return True
        return False

    def __str__(self):
        return f"{self.description[:60]} → {self.assigned_to}"

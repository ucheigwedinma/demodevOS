from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import Organization


def support_ticket_attachment_upload_to(instance: SupportTicketAttachment, filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    ticket_ref = instance.ticket.ticket_id or f"ticket-{instance.ticket_id}"
    return f"support-desk/{instance.ticket.organization_id}/{ticket_ref}/{uuid.uuid4()}.{extension}"


def default_sla_hours_for_priority(priority: str) -> int:
    mapping = {
        SupportTicket.Priority.CRITICAL: 4,
        SupportTicket.Priority.HIGH: 24,
        SupportTicket.Priority.MEDIUM: 48,
        SupportTicket.Priority.LOW: 72,
    }
    return mapping.get(priority, 24)


def default_first_response_hours_for_priority(priority: str) -> float:
    mapping = {
        SupportTicket.Priority.CRITICAL: 0.5,
        SupportTicket.Priority.HIGH: 2,
        SupportTicket.Priority.MEDIUM: 8,
        SupportTicket.Priority.LOW: 24,
    }
    return mapping.get(priority, 8)


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        ACCESS = "access", "Access"
        BILLING = "billing", "Billing"
        TECHNICAL = "technical", "Technical"
        WORKFLOW = "workflow", "Workflow"
        ACCOUNT = "account", "Account"
        COMPLAINT = "complaint", "Complaint"
        REQUEST = "request", "Request"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        PENDING_REQUESTER = "pending_requester", "Pending Customer"
        ESCALATED = "escalated", "Escalated"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    ticket_id = models.CharField(max_length=24, unique=True, blank=True, db_index=True)
    subject = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets_requested",
    )
    customer = models.ForeignKey(
        "finance.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    contact_account = models.ForeignKey(
        "crm.ContactAccount",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    department = models.ForeignKey(
        "settings.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    invoice = models.ForeignKey(
        "finance.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
    )
    team = models.ForeignKey(
        "workspace.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets",
        help_text=(
            "Optional workspace team scope. When set, ticket visibility is "
            "additionally constrained by the team's visibility (see "
            "docs/workspace-teams-design.md §12)."
        ),
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_tickets_assigned",
    )
    sla_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    customer_satisfaction_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    linked_tickets = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
            models.Index(fields=["organization", "priority", "-created_at"]),
            models.Index(fields=["organization", "assigned_agent", "status"]),
            models.Index(fields=["organization", "customer", "-created_at"]),
            models.Index(fields=["organization", "contact_account", "-created_at"]),
            models.Index(fields=["organization", "invoice", "-created_at"]),
            models.Index(fields=["organization", "sla_deadline"]),
            models.Index(
                fields=["team", "-created_at"],
                name="supportticket_team_created_idx",
            ),
        ]

    def __str__(self) -> str:
        return self.ticket_id or f"Support Ticket {self.pk}"

    def is_sla_breached(self) -> bool:
        return (
            self.sla_deadline is not None
            and self.status not in {self.Status.RESOLVED, self.Status.CLOSED}
            and self.sla_deadline < timezone.now()
        )

    def computed_sla_deadline(self) -> timezone.datetime:
        base_time = self.created_at or timezone.now()
        from .sla import get_ticket_sla_targets

        targets = get_ticket_sla_targets(self)
        return base_time + timedelta(hours=targets["resolution_hours"])

    def _apply_status_timestamps(self) -> None:
        now = timezone.now()
        if self.status == self.Status.ESCALATED and self.escalated_at is None:
            self.escalated_at = now
        if self.status == self.Status.RESOLVED and self.resolved_at is None:
            self.resolved_at = now
        if self.status == self.Status.CLOSED:
            if self.resolved_at is None:
                self.resolved_at = now
            if self.closed_at is None:
                self.closed_at = now

    def save(self, *args, **kwargs):
        if self.sla_deadline is None:
            self.sla_deadline = self.computed_sla_deadline()

        self._apply_status_timestamps()

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.ticket_id:
            generated_ticket_id = f"SD-{self.pk:06d}"
            self.ticket_id = generated_ticket_id
            type(self).objects.filter(pk=self.pk).update(ticket_id=generated_ticket_id)


class SupportTicketComment(models.Model):
    class CommentType(models.TextChoices):
        INTERNAL_NOTE = "internal_note", "Internal Note"
        REQUESTER_REPLY = "requester_reply", "Reply to Requester"

    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_ticket_comments",
    )
    comment_type = models.CharField(
        max_length=20,
        choices=CommentType.choices,
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["ticket", "comment_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.ticket.ticket_id} {self.comment_type}"


class SupportTicketAttachment(models.Model):
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_ticket_attachments",
    )
    label = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=support_ticket_attachment_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.ticket.ticket_id} attachment {self.pk}"


class SupportCommunicationLog(models.Model):
    class InteractionType(models.TextChoices):
        TICKET_CONVERSATION = "ticket_conversation", "Ticket Conversation"
        INTERNAL_NOTE = "internal_note", "Internal Note"
        EMAIL_REPLY = "email_reply", "Email Reply"
        CHAT_TRANSCRIPT = "chat_transcript", "Chat Transcript"
        CALL_LOG = "call_log", "Call Log"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"
        INTERNAL = "internal", "Internal"

    class Channel(models.TextChoices):
        PORTAL = "portal", "Support Portal"
        EMAIL = "email", "Email"
        CHAT = "chat", "Chat"
        PHONE = "phone", "Phone"
        WHATSAPP = "whatsapp", "WhatsApp"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="support_communication_logs",
    )
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communication_logs",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_communication_logs",
    )
    interaction_type = models.CharField(
        max_length=30,
        choices=InteractionType.choices,
        default=InteractionType.TICKET_CONVERSATION,
    )
    direction = models.CharField(
        max_length=12,
        choices=Direction.choices,
        default=Direction.INTERNAL,
    )
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.PORTAL,
    )
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    transcript = models.TextField(blank=True)
    participants = models.JSONField(default=list, blank=True)
    call_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    external_message_id = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    happened_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-happened_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "ticket", "-happened_at"]),
            models.Index(fields=["organization", "interaction_type", "-happened_at"]),
            models.Index(fields=["organization", "channel", "-happened_at"]),
            models.Index(fields=["organization", "direction", "-happened_at"]),
        ]

    def __str__(self) -> str:
        ticket_ref = self.ticket.ticket_id if self.ticket_id and self.ticket else "No Ticket"
        return f"{ticket_ref} {self.interaction_type} ({self.channel})"


class SupportAutomationRule(models.Model):
    class TriggerType(models.TextChoices):
        TICKET_CREATED = "ticket_created", "Ticket Creation"
        TICKET_UPDATED = "ticket_updated", "Ticket Update"
        SLA_THRESHOLD = "sla_threshold", "SLA Threshold"
        STATUS_CHANGED = "status_changed", "Status Change"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="support_automation_rules",
    )
    name = models.CharField(max_length=140)
    description = models.TextField(blank=True)
    trigger_type = models.CharField(
        max_length=24,
        choices=TriggerType.choices,
        default=TriggerType.TICKET_CREATED,
    )
    conditions = models.JSONField(default=dict, blank=True)
    actions = models.JSONField(default=dict, blank=True)
    priority = models.PositiveIntegerField(default=100)
    run_once_per_ticket = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_automation_rules_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["trigger_type", "priority", "id"]
        indexes = [
            models.Index(fields=["organization", "is_active", "trigger_type", "priority"]),
            models.Index(fields=["organization", "name"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_trigger_type_display()})"


class SupportAutomationRun(models.Model):
    class Status(models.TextChoices):
        MATCHED = "matched", "Matched"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="support_automation_runs",
    )
    rule = models.ForeignKey(
        SupportAutomationRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="runs",
    )
    ticket = models.ForeignKey(
        SupportTicket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="automation_runs",
    )
    trigger_type = models.CharField(
        max_length=24,
        choices=SupportAutomationRule.TriggerType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.MATCHED,
    )
    summary = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "ticket", "-created_at"]),
            models.Index(fields=["organization", "rule", "-created_at"]),
            models.Index(fields=["organization", "trigger_type", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_status_display()} {self.trigger_type} run #{self.id}"


class SupportKnowledgeArticle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In Review"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    class Visibility(models.TextChoices):
        INTERNAL = "internal", "Internal"
        PORTAL = "portal", "Partner Portal"
        PUBLIC = "public", "Public"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="support_knowledge_articles",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280)
    summary = models.TextField(blank=True)
    body = models.TextField()
    category = models.CharField(max_length=40, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.INTERNAL,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_knowledge_articles_owned",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="support_knowledge_articles_reviewed",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    next_review_due_at = models.DateField(null=True, blank=True)
    view_count = models.PositiveIntegerField(default=0)
    helpful_votes = models.PositiveIntegerField(default=0)
    not_helpful_votes = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        unique_together = [("organization", "slug")]
        indexes = [
            models.Index(fields=["organization", "status", "-updated_at"]),
            models.Index(fields=["organization", "visibility", "-updated_at"]),
            models.Index(fields=["organization", "category"]),
            models.Index(fields=["organization", "next_review_due_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def _generate_unique_slug(self) -> str:
        base = slugify(self.title)[:240] or "article"
        slug = base
        suffix = 2
        while type(self).objects.filter(organization=self.organization, slug=slug).exclude(pk=self.pk).exists():
            suffix_str = f"-{suffix}"
            slug = f"{base[: max(1, 240 - len(suffix_str))]}{suffix_str}"
            suffix += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()

        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)


class SupportSlaPolicy(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="support_sla_policies",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20,
        choices=SupportTicket.Category.choices,
        blank=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=SupportTicket.Priority.choices,
        blank=True,
    )
    response_target_hours = models.DecimalField(max_digits=6, decimal_places=2, default=8)
    resolution_target_hours = models.DecimalField(max_digits=6, decimal_places=2, default=48)
    escalate_after_hours = models.PositiveIntegerField(default=2)
    escalation_path = models.JSONField(default=list, blank=True)
    agent_notify_threshold_percent = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    manager_notify_threshold_percent = models.PositiveSmallIntegerField(
        default=80,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    breach_escalation_role = models.CharField(max_length=80, default="director")
    notify_assigned_agent = models.BooleanField(default=True)
    notify_manager = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        unique_together = [("organization", "name")]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "category", "priority"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization.name})"

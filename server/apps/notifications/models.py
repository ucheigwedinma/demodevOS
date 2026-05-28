from django.conf import settings
from django.db import models

USER_NOTIFICATION_CHANNELS = (
    ("in_app", "In-app notifications"),
    ("email", "Email notifications"),
    ("push", "Push notifications"),
    ("sms", "SMS"),
)

USER_NOTIFICATION_FREQUENCIES = (
    ("instant", "Instant"),
    ("hourly_digest", "Hourly digest"),
    ("daily_digest", "Daily digest"),
    ("weekly_summary", "Weekly summary"),
)

USER_NOTIFICATION_CATEGORIES = (
    ("tasks_assigned", "Tasks assigned"),
    ("approvals_required", "Approvals required"),
    ("mentions_comments", "Mentions / comments"),
    ("workflow_updates", "Workflow updates"),
    ("sla_warnings", "SLA warnings"),
    ("escalations", "Escalations"),
    ("system_announcements", "System announcements"),
    ("reports_ready", "Reports ready"),
    ("project_updates", "Project updates"),
    ("financial_approvals", "Financial approvals"),
    ("property_updates", "Property updates"),
    ("procurement_updates", "Procurement updates"),
    ("hr_updates", "HR & people"),
    ("partner_updates", "Partner updates"),
    ("crm_updates", "CRM & sales"),
)


def default_user_notification_category_preferences():
    return {
        key: {
            "enabled": True,
            "channels": ["in_app", "email"],
            "frequency": "instant",
        }
        for key, _label in USER_NOTIFICATION_CATEGORIES
    }


class Notification(models.Model):
    """Generic in-app notification for any user."""

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class Category(models.TextChoices):
        BUDGET_WARNING = "budget_warning", "Budget Warning"
        BUDGET_EXCEEDED = "budget_exceeded", "Budget Exceeded"
        BUDGET_DIGEST = "budget_digest", "Budget Digest"
        REPORTS_READY = "reports_ready", "Reports Ready"
        SYSTEM = "system", "System"
        WORKFLOW_PENDING = "workflow_pending", "Workflow Pending"
        WORKFLOW_APPROVED = "workflow_approved", "Workflow Approved"
        WORKFLOW_REJECTED = "workflow_rejected", "Workflow Rejected"
        WORKFLOW_ESCALATED = "workflow_escalated", "Workflow Escalated"
        WORKFLOW_SLA_WARNING = "workflow_sla_warning", "Workflow SLA Warning"
        DELEGATION_ASSIGNED = "delegation_assigned", "Delegation Assigned"
        DELEGATION_EXPIRED = "delegation_expired", "Delegation Expired"
        # Projects
        PROJECT_UPDATE = "project_update", "Project Update"
        PROJECT_RISK = "project_risk", "Project Risk"
        # Properties
        PROPERTY_STATUS = "property_status", "Property Status"
        PROPERTY_MAINT = "property_maint", "Property Maintenance"
        # Procurement
        PROCUREMENT_ORDER = "procurement_order", "Procurement Order"
        PROCUREMENT_GRN = "procurement_grn", "Goods Receipt"
        # HR
        HR_LEAVE = "hr_leave", "Leave Request"
        HR_LIFECYCLE = "hr_lifecycle", "HR Lifecycle"
        # Partners
        PARTNER_ONBOARDING = "partner_onboarding", "Partner Onboarding"
        # CRM
        CRM_LEAD = "crm_lead", "CRM Lead"
        CRM_RESERVATION = "crm_reservation", "CRM Reservation"
        # Calendar
        CALENDAR_REMINDER = "calendar_reminder", "Calendar Reminder"
        # Internal Tasks
        TASK_REMINDER = "task_reminder", "Task Reminder"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_notifications",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(
        max_length=20, choices=Severity.choices, default=Severity.INFO
    )
    category = models.CharField(
        max_length=30, choices=Category.choices, default=Category.SYSTEM
    )
    is_read = models.BooleanField(default=False)
    link_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="Frontend URL for click-through",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "-created_at"]),
            models.Index(
                fields=["organization", "-created_at"],
                name="notif_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.recipient} — {self.title}"


class UserNotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    organization = models.ForeignKey(
        "accounts.Organization",
        on_delete=models.CASCADE,
        related_name="org_notification_preferences",
        null=True,
        blank=True,
    )
    channel_in_app_enabled = models.BooleanField(default=True)
    channel_email_enabled = models.BooleanField(default=True)
    channel_push_enabled = models.BooleanField(default=False)
    channel_sms_enabled = models.BooleanField(default=False)
    category_preferences = models.JSONField(
        default=default_user_notification_category_preferences,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="notif_pref_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"Notification Preferences — {self.user.email}"

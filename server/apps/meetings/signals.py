"""Signals for the unified meeting system."""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


@receiver(pre_save, sender="meetings.Meeting")
def auto_generate_minutes_on_completion(sender, instance, **kwargs):
    """When a meeting transitions to 'completed', auto-generate minutes if configured."""
    if not instance.pk:
        return  # New meeting, skip

    try:
        from apps.meetings.models import Meeting
        old = Meeting.objects.get(pk=instance.pk)
    except Meeting.DoesNotExist:
        return

    # Only trigger when status changes TO completed
    if old.status != "completed" and instance.status == "completed":
        should_generate = True
        if instance.template and not instance.template.auto_generate_minutes:
            should_generate = False

        if should_generate and not instance.minutes_text:
            try:
                from apps.meetings.minutes_generator import auto_generate_minutes
                text, source = auto_generate_minutes(instance)
                instance.minutes_text = text
                instance.minutes_source = source
                instance.minutes_generated_at = timezone.now()
                logger.info(f"Auto-generated minutes for {instance.meeting_number} (source: {source})")
            except ValueError as e:
                logger.info(f"Minutes not generated for {instance.meeting_number}: {e}")
            except Exception:
                logger.debug("Failed to auto-generate minutes", exc_info=True)


@receiver(post_save, sender="meetings.Meeting")
def broadcast_meeting_change(sender, instance, created, **kwargs):
    """Broadcast meeting changes via WebSocket."""
    try:
        from apps.notifications.broadcast import broadcast_data_change
        org_id = instance.organization_id
        if org_id:
            broadcast_data_change(
                org_id=org_id,
                model="Meeting",
                action="created" if created else "updated",
                id=instance.pk,
                summary=f"{instance.meeting_number} — {instance.title}",
            )
    except Exception:
        pass


@receiver(post_save, sender="meetings.MeetingActionItem")
def check_action_item_overdue(sender, instance, **kwargs):
    """Update action item status to overdue if past due date."""
    from datetime import date
    if instance.status == "open" and instance.due_date and instance.due_date < date.today():
        from apps.meetings.models import MeetingActionItem
        MeetingActionItem.objects.filter(pk=instance.pk).update(status="overdue")


# ── Meeting Cancelled ─────────────────────────────────────────────────


@receiver(pre_save, sender="meetings.Meeting")
def capture_meeting_previous_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            from apps.meetings.models import Meeting
            instance._prev_meeting_status = Meeting.objects.get(pk=instance.pk).status
        except Exception:
            instance._prev_meeting_status = None
    else:
        instance._prev_meeting_status = None


@receiver(post_save, sender="meetings.Meeting")
def on_meeting_cancelled(sender, instance, created, **kwargs):
    if created:
        return
    prev = getattr(instance, "_prev_meeting_status", None)
    if prev == instance.status or instance.status != "cancelled":
        return
    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization
        project_name = instance.project.name if instance.project else ""

        def _org_admin_users(o):
            from apps.accounts.models import UserProfile
            return [p.user for p in UserProfile.objects.filter(organization=o, role="admin", user__is_active=True).select_related("user")]

        # Notify attendees + admins
        from django.contrib.auth import get_user_model
        User = get_user_model()
        attendee_ids = list(instance.attendees.filter(user__isnull=False).values_list("user_id", flat=True))
        recipients = list(User.objects.filter(pk__in=set(attendee_ids), is_active=True))
        if not recipients:
            recipients = _org_admin_users(org)

        dispatch_workflow_notification(
            organization=org, event_key="meeting_cancelled", recipients=recipients,
            link_url="/calendar", fallback_channels=["in_app"],
            fallback_title=f"Meeting Cancelled — {instance.title}",
            fallback_message=(
                f"'{instance.title}' scheduled for {instance.scheduled_start.strftime('%d %B at %H:%M') if instance.scheduled_start else 'N/A'}"
                + (f" ({project_name})" if project_name else "")
                + " has been cancelled."
            ),
            fallback_category=Notification.Category.SYSTEM,
            fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Meeting cancelled notification skipped", exc_info=True)

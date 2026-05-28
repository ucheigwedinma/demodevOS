"""
Internal Tasks signals — notification fan-out.

All deliveries flow through apps.notifications.services.dispatch_workflow_notification
(per design A1). Imported at module level so tests can patch it (same pattern
as Calendar).

Events:
- Task post_save: notify assignee on assignment, previous assignee on
  re-assignment, creator on status moves to blocked/done (when actor != creator).
- TaskComment post_save: notify task.creator + task.assignee + prior
  commenters (deduped, excluding the actor) + mentioned users.
"""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# Module-level import so unittest.mock.patch can intercept it cleanly.
from apps.notifications.services import dispatch_workflow_notification

from .models import Task, TaskComment

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------------------------------------------------------------------------
# Task notifications
# ---------------------------------------------------------------------------


@receiver(pre_save, sender=Task)
def _task_pre_save_snapshot(sender, instance: Task, **kwargs):
    """
    Snapshot the previous assignee + status so the post_save handler can
    detect transitions.
    """
    if instance.pk is None:
        instance._previous_assignee_id = None
        instance._previous_status_for_signal = None
        return
    try:
        prev = Task.objects.only("assignee_id", "status").get(pk=instance.pk)
    except Task.DoesNotExist:
        instance._previous_assignee_id = None
        instance._previous_status_for_signal = None
        return
    instance._previous_assignee_id = prev.assignee_id
    instance._previous_status_for_signal = prev.status


@receiver(post_save, sender=Task)
def _task_post_save_notify(sender, instance: Task, created, **kwargs):
    """Fan out assignment + status notifications via the notifications service."""
    from apps.notifications.models import Notification

    prev_assignee_id = getattr(instance, "_previous_assignee_id", None)
    prev_status = getattr(instance, "_previous_status_for_signal", None)

    # ----- Assignment -----
    if created and instance.assignee_id and instance.assignee_id != instance.creator_id:
        _safe_dispatch(
            organization=instance.organization,
            event_key="internal_tasks.assigned",
            recipients=[instance.assignee],
            link_url=_task_link(instance),
            fallback_title=f"You've been assigned: {instance.title}",
            fallback_message=instance.description or "",
        )
    elif not created and instance.assignee_id != prev_assignee_id:
        # Reassignment — notify the new assignee + the previous one.
        if instance.assignee_id:
            _safe_dispatch(
                organization=instance.organization,
                event_key="internal_tasks.assigned",
                recipients=[instance.assignee],
                link_url=_task_link(instance),
                fallback_title=f"You've been assigned: {instance.title}",
                fallback_message=instance.description or "",
            )
        if prev_assignee_id:
            try:
                prev_user = User.objects.get(pk=prev_assignee_id)
            except User.DoesNotExist:
                prev_user = None
            if prev_user:
                _safe_dispatch(
                    organization=instance.organization,
                    event_key="internal_tasks.unassigned",
                    recipients=[prev_user],
                    link_url=_task_link(instance),
                    fallback_title=f"You've been removed from: {instance.title}",
                    fallback_message="",
                )

    # ----- Status moves to blocked / done -----
    if not created and prev_status != instance.status:
        if instance.status == Task.Status.BLOCKED:
            _notify_creator_about_status(instance, "blocked")
        elif instance.status == Task.Status.DONE:
            _notify_creator_about_status(instance, "done")


def _notify_creator_about_status(task: Task, new_status: str):
    """Notify the creator when status moves to blocked/done (if creator != actor)."""
    # We can't know the "actor" from a signal in general; the simpler heuristic
    # is "notify the creator unless the creator IS the assignee (likely the
    # actor)." This avoids self-pings in the common solo case.
    if task.creator_id == task.assignee_id:
        return
    try:
        creator = task.creator
    except User.DoesNotExist:
        return
    headline = (
        f"Task blocked: {task.title}"
        if new_status == "blocked"
        else f"Task done: {task.title}"
    )
    _safe_dispatch(
        organization=task.organization,
        event_key=f"internal_tasks.{new_status}",
        recipients=[creator],
        link_url=_task_link(task),
        fallback_title=headline,
        fallback_message="",
    )


# ---------------------------------------------------------------------------
# Comment notifications
# ---------------------------------------------------------------------------


@receiver(post_save, sender=TaskComment)
def _comment_post_save_notify(sender, instance: TaskComment, created, **kwargs):
    if not created:
        return  # edits don't fan out

    task = instance.task
    actor_id = instance.author_id

    # Recipients = task creator + assignee + previous commenters + mentioned
    # (deduped, exclude actor).
    recipient_ids: set[int] = set()
    if task.creator_id and task.creator_id != actor_id:
        recipient_ids.add(task.creator_id)
    if task.assignee_id and task.assignee_id != actor_id:
        recipient_ids.add(task.assignee_id)
    prior_commenter_ids = (
        TaskComment.objects.filter(task=task)
        .exclude(pk=instance.pk)
        .exclude(author_id=actor_id)
        .exclude(author__isnull=True)
        .values_list("author_id", flat=True)
        .distinct()
    )
    recipient_ids.update(prior_commenter_ids)

    mentioned_ids = set(instance.mentions or []) - {actor_id}
    recipient_ids.update(mentioned_ids)

    if not recipient_ids:
        return

    recipients = list(User.objects.filter(pk__in=recipient_ids, is_active=True))
    if not recipients:
        return

    # Mentioned users get a different headline.
    other_recipients = [u for u in recipients if u.id not in mentioned_ids]
    mention_recipients = [u for u in recipients if u.id in mentioned_ids]

    if other_recipients:
        _safe_dispatch(
            organization=task.organization,
            event_key="internal_tasks.commented",
            recipients=other_recipients,
            link_url=_task_link(task),
            fallback_title=f"New comment on: {task.title}",
            fallback_message=instance.body[:200],
        )
    if mention_recipients:
        _safe_dispatch(
            organization=task.organization,
            event_key="internal_tasks.mentioned",
            recipients=mention_recipients,
            link_url=_task_link(task),
            fallback_title=f"You were mentioned: {task.title}",
            fallback_message=instance.body[:200],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task_link(task: Task) -> str:
    return f"/internal-tasks/{task.pk}"


def _safe_dispatch(*, organization, event_key, recipients, link_url, fallback_title, fallback_message):
    """Single wrapper so tests can patch one symbol + future logging in one place."""
    from apps.notifications.models import Notification

    if not recipients:
        return
    try:
        dispatch_workflow_notification(
            organization=organization,
            event_key=event_key,
            recipients=recipients,
            context={},
            link_url=link_url,
            channels=("in_app", "email"),
            fallback_channels=("in_app", "email"),
            fallback_title=fallback_title,
            fallback_message=fallback_message,
            fallback_category=Notification.Category.TASK_REMINDER,
            fallback_severity=Notification.Severity.INFO,
        )
    except Exception:
        logger.exception(
            "Internal Tasks signal dispatch failed (event=%s recipients=%s)",
            event_key,
            [getattr(r, "id", None) for r in recipients],
        )

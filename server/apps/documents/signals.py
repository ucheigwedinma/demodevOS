import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DocumentVersion
from .search_engine import schedule_document_reindex

logger = logging.getLogger(__name__)


def _org_admin_users(org):
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org, role="admin", user__is_active=True
        ).select_related("user")
    ]


@receiver(post_save, sender=DocumentVersion)
def reindex_document_on_version_save(sender, instance: DocumentVersion, **kwargs):
    schedule_document_reindex(document_id=instance.document_id, force=True)


# ---------------------------------------------------------------------------
# Document notifications
# ---------------------------------------------------------------------------

@receiver(post_save, sender="documents.Document")
def on_document_status_changed(sender, instance, created, **kwargs):
    """Notify when a document status changes (submitted, approved, rejected)."""
    if created:
        return
    update_fields = kwargs.get("update_fields")
    if update_fields and "status" not in update_fields:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    status_label = instance.get_status_display()
    title_text = getattr(instance, "title", "") or str(instance)

    dispatch_workflow_notification(
        organization=org,
        event_key="document_status_changed",
        recipients=_org_admin_users(org),
        context={
            "document_title": title_text[:100],
            "document_number": getattr(instance, "document_number", ""),
            "new_status": status_label,
            "action_url": f"/documents/{instance.id}",
        },
        link_url=f"/documents/{instance.id}",
        fallback_channels=["in_app"],
        fallback_title=f"Document Status Updated — {status_label}",
        fallback_message=(
            f"Document '{title_text[:80]}' has been updated to {status_label}. "
            f"Please review if further action is required."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="documents.DocumentApproval")
def on_document_approval_created(sender, instance, created, **kwargs):
    """Notify when a document approval decision is recorded."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    decision = instance.get_decision_display()
    version = instance.document_version
    doc = version.document if version else None
    doc_title = doc.title if doc else "Unknown document"

    dispatch_workflow_notification(
        organization=org,
        event_key="document_approval_decision",
        recipients=_org_admin_users(org),
        context={
            "document_title": doc_title[:100],
            "decision": decision,
            "action_url": f"/documents/{doc.id}" if doc else "/documents",
        },
        link_url=f"/documents/{doc.id}" if doc else "/documents",
        fallback_channels=["in_app"],
        fallback_title=f"Document Approval — {decision}",
        fallback_message=(
            f"Document '{doc_title[:80]}' has been {decision.lower()} "
            f"during the review process."
            f"{' It is now cleared for distribution.' if decision.lower() == 'approved' else ' Please review the feedback and resubmit if necessary.'}"
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


@receiver(post_save, sender="documents.DocumentVersion")
def on_new_document_version(sender, instance, created, **kwargs):
    """Notify when a new document version is uploaded."""
    if not created:
        return

    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    org = instance.organization
    doc = instance.document if instance.document_id else None
    doc_title = doc.title if doc else "Unknown document"
    version_label = f"v{instance.version_major}.{instance.version_minor}"

    dispatch_workflow_notification(
        organization=org,
        event_key="document_version_uploaded",
        recipients=_org_admin_users(org),
        context={
            "document_title": doc_title[:100],
            "version": version_label,
            "action_url": f"/documents/{doc.id}" if doc else "/documents",
        },
        link_url=f"/documents/{doc.id}" if doc else "/documents",
        fallback_channels=["in_app"],
        fallback_title=f"New Document Version Uploaded — {version_label}",
        fallback_message=(
            f"Version {version_label} of '{doc_title[:80]}' has been uploaded "
            f"and is now available for review. Previous versions remain accessible in the document history."
        ),
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=Notification.Severity.INFO,
    )


# ── Document Signature Request Created ────────────────────────────────


@receiver(post_save, sender="documents.DocumentSignatureRequest")
def on_signature_request_created(sender, instance, created, **kwargs):
    """Notify the signee when a document signature is requested."""
    if not created:
        return

    try:
        from apps.notifications.models import Notification
        from apps.notifications.services import dispatch_workflow_notification

        org = instance.organization if hasattr(instance, "organization") else None
        if not org and hasattr(instance, "document") and hasattr(instance.document, "organization"):
            org = instance.document.organization
        if not org:
            return

        doc_title = getattr(instance.document, "title", "Unknown Document") if hasattr(instance, "document") else "Unknown Document"
        signee_name = getattr(instance, "signee_name", "") or getattr(instance, "requested_from", "") or "Unknown"
        requested_by = getattr(instance, "requested_by_name", "") or getattr(instance, "created_by", "")

        # Notify the signee if they're a user
        recipients = _org_admin_users(org)
        signee_user = getattr(instance, "signee", None) or getattr(instance, "requested_from_user", None)
        if signee_user and signee_user not in recipients:
            recipients.append(signee_user)

        dispatch_workflow_notification(
            organization=org,
            event_key="signature_request_created",
            recipients=recipients,
            link_url="/documents/signatures",
            fallback_channels=["in_app"],
            fallback_title=f"Signature Requested — {doc_title[:60]}",
            fallback_message=(
                f"Your signature is requested on '{doc_title}'. "
                f"Requested by: {requested_by or 'N/A'}. "
                f"Signee: {signee_name}. "
                f"Please review and sign at your earliest convenience."
            ),
            fallback_category=Notification.Category.SYSTEM,
            fallback_severity=Notification.Severity.WARNING,
        )
    except Exception:
        logger.debug("Signature request notification skipped", exc_info=True)

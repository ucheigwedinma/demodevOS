from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import UserProfile
from apps.notifications.models import Notification
from apps.notifications.services import dispatch_workflow_notification
from apps.projects.models import Project

from .models import (
    Document,
    DocumentApproval,
    DocumentBusinessUnitMembership,
    DocumentExpiry,
    DocumentProjectMembership,
)

ESCALATION_ROLE_SLUGS = (
    "governance-officer",
    "legal",
    "developer-executive",
)


@dataclass
class ComplianceMonitorSummary:
    monitor_date: str
    processed: int = 0
    alerts_90_day: int = 0
    alerts_30_day: int = 0
    expired_alerts: int = 0
    escalations: int = 0
    expired_documents: int = 0
    notifications_sent: int = 0
    emails_sent: int = 0
    project_scores_updated: int = 0

    def as_dict(self) -> dict[str, int | str]:
        return {
            "monitor_date": self.monitor_date,
            "processed": self.processed,
            "alerts_90_day": self.alerts_90_day,
            "alerts_30_day": self.alerts_30_day,
            "expired_alerts": self.expired_alerts,
            "escalations": self.escalations,
            "expired_documents": self.expired_documents,
            "notifications_sent": self.notifications_sent,
            "emails_sent": self.emails_sent,
            "project_scores_updated": self.project_scores_updated,
        }


def _document_link(document_id: int) -> str:
    frontend_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    if frontend_url:
        return f"{frontend_url}/documents?document={document_id}"
    return f"/documents?document={document_id}"


def _build_alert_payload(*, expiry: DocumentExpiry, alert_type: str, days_to_expiry: int) -> tuple[str, str, str]:
    document = expiry.document
    category_label = expiry.get_trigger_category_display()

    if alert_type == "90_day":
        title = f"Document expiry in 90 days: {document.document_number}"
        message = (
            f"{category_label} for {document.document_number} ({document.title}) expires on "
            f"{expiry.expiry_date.isoformat()} ({days_to_expiry} days remaining)."
        )
        severity = Notification.Severity.WARNING
    elif alert_type == "30_day":
        title = f"Document expiry in 30 days: {document.document_number}"
        message = (
            f"{category_label} for {document.document_number} ({document.title}) expires on "
            f"{expiry.expiry_date.isoformat()} ({days_to_expiry} days remaining)."
        )
        severity = Notification.Severity.WARNING
    elif alert_type == "expired":
        days_overdue = abs(days_to_expiry)
        title = f"Document expired: {document.document_number}"
        message = (
            f"{category_label} for {document.document_number} ({document.title}) expired on "
            f"{expiry.expiry_date.isoformat()} ({days_overdue} days overdue)."
        )
        severity = Notification.Severity.CRITICAL
    else:  # escalated
        days_overdue = abs(days_to_expiry)
        title = f"Escalation required: expired document {document.document_number}"
        message = (
            f"Escalation triggered for {category_label} on {document.document_number} ({document.title}). "
            f"Expired on {expiry.expiry_date.isoformat()} and is {days_overdue} days overdue."
        )
        severity = Notification.Severity.CRITICAL

    return title, message, severity


def _recipient_ids_for_document(document: Document, *, escalation: bool) -> set[int]:
    user_model = get_user_model()
    recipient_ids: set[int] = set()

    if document.project_id:
        project_user_ids = DocumentProjectMembership.objects.filter(
            project_id=document.project_id,
        ).values_list("user_id", flat=True)
        recipient_ids.update(project_user_ids)

    if document.business_unit_department_id:
        department_ids = DocumentBusinessUnitMembership.objects.filter(
            department_id=document.business_unit_department_id,
        ).values_list("user_id", flat=True)
        recipient_ids.update(department_ids)
    elif document.business_unit_division_id:
        division_ids = DocumentBusinessUnitMembership.objects.filter(
            division_id=document.business_unit_division_id,
        ).values_list("user_id", flat=True)
        recipient_ids.update(division_ids)

    if document.current_version_id and document.current_version and document.current_version.uploaded_by_id:
        recipient_ids.add(document.current_version.uploaded_by_id)

    if document.current_version_id:
        decision_user_ids = DocumentApproval.objects.filter(
            document_version_id=document.current_version_id,
        ).values_list("user_id", flat=True)
        recipient_ids.update(decision_user_ids)

    superuser_ids = user_model.objects.filter(is_superuser=True, is_active=True).values_list("id", flat=True)
    recipient_ids.update(superuser_ids)

    if escalation and recipient_ids:
        org_ids = UserProfile.objects.filter(
            user_id__in=recipient_ids,
            organization_id__isnull=False,
        ).values_list("organization_id", flat=True)
        escalation_user_ids = UserProfile.objects.filter(
            organization_id__in=org_ids,
            user__is_active=True,
            assigned_role__slug__in=ESCALATION_ROLE_SLUGS,
        ).values_list("user_id", flat=True)
        recipient_ids.update(escalation_user_ids)

    return recipient_ids


def _dispatch_alert(
    *,
    expiry: DocumentExpiry,
    alert_type: str,
    days_to_expiry: int,
    escalation: bool,
) -> tuple[int, int]:
    user_model = get_user_model()
    recipient_ids = _recipient_ids_for_document(expiry.document, escalation=escalation)
    recipients = user_model.objects.filter(id__in=recipient_ids, is_active=True).distinct()

    if not recipients.exists():
        return 0, 0

    title, message, severity = _build_alert_payload(
        expiry=expiry,
        alert_type=alert_type,
        days_to_expiry=days_to_expiry,
    )

    link_url = _document_link(expiry.document_id)
    document = expiry.document
    days_overdue = abs(days_to_expiry)

    event_key_map = {
        "90_day": "documents_expiry_90_day",
        "30_day": "documents_expiry_30_day",
        "expired": "documents_expired",
        "escalated": "documents_expiry_escalated",
    }
    event_key = event_key_map.get(alert_type, "documents_expired")

    dispatch_result = dispatch_workflow_notification(
        organization=document.organization,
        event_key=event_key,
        recipients=recipients,
        context={
            "document_number": document.document_number,
            "document_title": document.title,
            "category_label": expiry.get_trigger_category_display(),
            "expiry_date": expiry.expiry_date.isoformat(),
            "days_to_expiry": str(days_to_expiry),
            "days_overdue": str(days_overdue),
            "action_url": link_url,
        },
        link_url=link_url,
        fallback_channels=["in_app", "email"],
        fallback_title=title,
        fallback_message=message,
        fallback_category=Notification.Category.SYSTEM,
        fallback_severity=severity,
    )

    return dispatch_result["notifications_sent"], dispatch_result["emails_sent"]


def _score_for_project(*, total: int, expired: int, due_30: int, due_90: int) -> tuple[Decimal, str]:
    if total <= 0:
        return Decimal("100.00"), Project.ComplianceStatus.COMPLIANT

    total_decimal = Decimal(total)
    penalty = (
        Decimal(expired)
        + (Decimal(due_30) * Decimal("0.60"))
        + (Decimal(due_90) * Decimal("0.25"))
    )
    ratio = Decimal("1.00") - (penalty / total_decimal)
    if ratio < Decimal("0"):
        ratio = Decimal("0")

    score = (ratio * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if expired > 0 or score < Decimal("60.00"):
        status = Project.ComplianceStatus.NON_COMPLIANT
    elif due_30 > 0 or score < Decimal("85.00"):
        status = Project.ComplianceStatus.WARNING
    else:
        status = Project.ComplianceStatus.COMPLIANT

    return score, status


def update_project_compliance_scores(*, reference_date: date | None = None) -> int:
    monitor_date = reference_date or timezone.now().date()
    evaluated_at = timezone.now()

    counters: dict[int, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "expired": 0,
            "due_30": 0,
            "due_90": 0,
        }
    )

    expiry_queryset = (
        DocumentExpiry.objects
        .filter(document__project_id__isnull=False)
        .exclude(
            document__status__in=[
                Document.Status.ARCHIVED,
                Document.Status.SUPERSEDED,
            ]
        )
        .select_related("document")
    )

    for expiry in expiry_queryset.iterator():
        project_id = expiry.document.project_id
        bucket = counters[project_id]
        bucket["total"] += 1

        days_to_expiry = (expiry.expiry_date - monitor_date).days
        if days_to_expiry < 0:
            bucket["expired"] += 1
        elif days_to_expiry <= 30:
            bucket["due_30"] += 1
        elif days_to_expiry <= 90:
            bucket["due_90"] += 1

    projects = list(Project.objects.all())
    if not projects:
        return 0

    for project in projects:
        project_counts = counters.get(
            project.id,
            {
                "total": 0,
                "expired": 0,
                "due_30": 0,
                "due_90": 0,
            },
        )
        score, status = _score_for_project(
            total=project_counts["total"],
            expired=project_counts["expired"],
            due_30=project_counts["due_30"],
            due_90=project_counts["due_90"],
        )

        project.compliance_score = score
        project.compliance_status = status
        project.compliance_last_evaluated_at = evaluated_at

    Project.objects.bulk_update(
        projects,
        fields=["compliance_score", "compliance_status", "compliance_last_evaluated_at"],
    )
    return len(projects)


def run_expiry_compliance_monitor(*, reference_date: date | None = None) -> dict[str, int | str]:
    monitor_date = reference_date or timezone.now().date()
    now = timezone.now()
    summary = ComplianceMonitorSummary(monitor_date=monitor_date.isoformat())

    expiry_queryset = (
        DocumentExpiry.objects
        .select_related(
            "document",
            "document__project",
            "document__current_version",
        )
        .exclude(
            document__status__in=[
                Document.Status.ARCHIVED,
                Document.Status.SUPERSEDED,
            ]
        )
        .order_by("expiry_date", "id")
    )

    for expiry in expiry_queryset.iterator():
        summary.processed += 1
        days_to_expiry = (expiry.expiry_date - monitor_date).days

        update_fields = ["last_checked_at"]
        expiry.last_checked_at = now

        if expiry.alert_90_days and expiry.alert_90_days_sent_at is None and 31 <= days_to_expiry <= 90:
            sent_notifications, sent_emails = _dispatch_alert(
                expiry=expiry,
                alert_type="90_day",
                days_to_expiry=days_to_expiry,
                escalation=False,
            )
            expiry.alert_90_days_sent_at = now
            update_fields.append("alert_90_days_sent_at")
            summary.alerts_90_day += 1
            summary.notifications_sent += sent_notifications
            summary.emails_sent += sent_emails

        if expiry.alert_30_days and expiry.alert_30_days_sent_at is None and 0 <= days_to_expiry <= 30:
            sent_notifications, sent_emails = _dispatch_alert(
                expiry=expiry,
                alert_type="30_day",
                days_to_expiry=days_to_expiry,
                escalation=False,
            )
            expiry.alert_30_days_sent_at = now
            update_fields.append("alert_30_days_sent_at")
            summary.alerts_30_day += 1
            summary.notifications_sent += sent_notifications
            summary.emails_sent += sent_emails

        if days_to_expiry < 0:
            summary.expired_documents += 1

            if expiry.alert_expired and expiry.expired_alert_sent_at is None:
                sent_notifications, sent_emails = _dispatch_alert(
                    expiry=expiry,
                    alert_type="expired",
                    days_to_expiry=days_to_expiry,
                    escalation=False,
                )
                expiry.expired_alert_sent_at = now
                update_fields.append("expired_alert_sent_at")
                summary.expired_alerts += 1
                summary.notifications_sent += sent_notifications
                summary.emails_sent += sent_emails

            if expiry.escalated_at is None:
                sent_notifications, sent_emails = _dispatch_alert(
                    expiry=expiry,
                    alert_type="escalated",
                    days_to_expiry=days_to_expiry,
                    escalation=True,
                )
                expiry.escalated_at = now
                update_fields.append("escalated_at")
                summary.escalations += 1
                summary.notifications_sent += sent_notifications
                summary.emails_sent += sent_emails

        if update_fields:
            expiry.save(update_fields=update_fields)

    summary.project_scores_updated = update_project_compliance_scores(reference_date=monitor_date)
    return summary.as_dict()

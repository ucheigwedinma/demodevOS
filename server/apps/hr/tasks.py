import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context

logger = logging.getLogger(__name__)


@shared_task
def check_certification_expiry():
    """
    Daily task: find certifications and licenses expiring within 30 days
    and notify employees + their reporting managers.
    """
    from apps.hr.models import Certification, ProfessionalLicense
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    now = timezone.now().date()
    threshold = now + timedelta(days=30)
    recent_cutoff = now - timedelta(days=1)  # dedup: skip if notified today

    for organization_id in iter_organization_ids():
        with rls_context(organization_id, bypass=False):
            from apps.accounts.models import Organization
            org = Organization.objects.get(pk=organization_id)

            # Certifications expiring within 30 days
            expiring_certs = Certification.objects.filter(
                organization_id=organization_id,
                expiry_date__gte=now,
                expiry_date__lte=threshold,
                status="active",
            ).select_related("employee", "employee__user")

            for cert in expiring_certs:
                employee_user = getattr(cert.employee, "user", None) if cert.employee_id else None
                if not employee_user or not employee_user.is_active:
                    continue

                # Dedup: skip if same-title notification exists from today
                if Notification.objects.filter(
                    recipient=employee_user,
                    category=Notification.Category.HR_LIFECYCLE,
                    title__icontains=cert.name if hasattr(cert, "name") else "certification",
                    created_at__date__gte=recent_cutoff,
                ).exists():
                    continue

                days_remaining = (cert.expiry_date - now).days
                recipients = [employee_user]

                profile = getattr(employee_user, "profile", None)
                if profile and profile.reporting_manager_id:
                    recipients.append(profile.reporting_manager)

                cert_name = getattr(cert, "name", "") or getattr(cert, "certification_name", str(cert))

                dispatch_workflow_notification(
                    organization=org,
                    event_key="hr_certification_expiring",
                    recipients=recipients,
                    context={
                        "employee_name": employee_user.get_full_name() or employee_user.email,
                        "certification_name": cert_name,
                        "expiry_date": str(cert.expiry_date),
                        "days_remaining": str(days_remaining),
                        "action_url": "/hr/certifications",
                    },
                    link_url="/hr/certifications",
                    fallback_channels=["in_app", "email"],
                    fallback_title=f"Certification expiring: {cert_name}",
                    fallback_message=(
                        f'Certification "{cert_name}" expires in {days_remaining} days'
                        f"({cert.expiry_date})."
                    ),
                    fallback_category=Notification.Category.HR_LIFECYCLE,
                    fallback_severity=Notification.Severity.WARNING,
                )

            # Professional licenses expiring within 30 days
            expiring_licenses = ProfessionalLicense.objects.filter(
                organization_id=organization_id,
                expiry_date__gte=now,
                expiry_date__lte=threshold,
                status="active",
            ).select_related("employee", "employee__user")

            for lic in expiring_licenses:
                employee_user = getattr(lic.employee, "user", None) if lic.employee_id else None
                if not employee_user or not employee_user.is_active:
                    continue

                if Notification.objects.filter(
                    recipient=employee_user,
                    category=Notification.Category.HR_LIFECYCLE,
                    title__icontains=lic.name if hasattr(lic, "name") else "license",
                    created_at__date__gte=recent_cutoff,
                ).exists():
                    continue

                days_remaining = (lic.expiry_date - now).days
                recipients = [employee_user]

                profile = getattr(employee_user, "profile", None)
                if profile and profile.reporting_manager_id:
                    recipients.append(profile.reporting_manager)

                lic_name = getattr(lic, "name", "") or getattr(lic, "license_name", str(lic))

                dispatch_workflow_notification(
                    organization=org,
                    event_key="hr_certification_expiring",
                    recipients=recipients,
                    context={
                        "employee_name": employee_user.get_full_name() or employee_user.email,
                        "certification_name": lic_name,
                        "expiry_date": str(lic.expiry_date),
                        "days_remaining": str(days_remaining),
                        "action_url": "/hr/licenses",
                    },
                    link_url="/hr/licenses",
                    fallback_channels=["in_app", "email"],
                    fallback_title=f"License expiring: {lic_name}",
                    fallback_message=(
                        f'Professional license "{lic_name}" expires in {days_remaining} days '
                        f"({lic.expiry_date})."
                    ),
                    fallback_category=Notification.Category.HR_LIFECYCLE,
                    fallback_severity=Notification.Severity.WARNING,
                )


@shared_task
def check_critical_position_vacancy_alerts():
    """
    Daily task: find critical positions vacant for >30 days and notify BU heads.
    """
    from apps.hr.automation import check_overdue_critical_position_vacancies

    total_alerts = 0
    for organization_id in iter_organization_ids():
        with rls_context(organization_id, bypass=False):
            total_alerts += check_overdue_critical_position_vacancies(
                organization_id=organization_id,
            )

    logger.info(
        "Critical vacancy sweep completed. Alerts sent: %s",
        total_alerts,
    )
    return total_alerts

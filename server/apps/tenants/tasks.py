import logging

from celery import shared_task

from apps.accounts.models import Organization
from apps.accounts.rls import iter_organization_ids, rls_context

from .workflows import run_tenant_operations_automation

logger = logging.getLogger(__name__)


@shared_task(name="tenants.run_scheduled_tenant_operations_workflows")
def run_scheduled_tenant_operations_workflows(organization_ids: list[int] | None = None):
    """Run lease, billing, collections, communication, inspection, and complaint automation."""

    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "leases_synced": 0,
        "occupancies_synced": 0,
        "renewals_created": 0,
        "terminations_created": 0,
        "access_records_synced": 0,
        "utility_tracking_records_synced": 0,
        "utility_tracking_activated": 0,
        "billing_rules_stopped": 0,
        "vacancy_risks_created": 0,
        "vacancy_risks_updated": 0,
        "vacancy_risks_resolved": 0,
        "vacancy_risks_open": 0,
        "invoices_created": 0,
        "payments_reconciled": 0,
        "late_payment_penalties_applied": 0,
        "payment_journals_posted": 0,
        "overdue_invoices_flagged": 0,
        "billing_tickets_synced": 0,
        "billing_tickets_escalated": 0,
        "rent_reminders_sent": 0,
        "admin_expiry_alerts_sent": 0,
        "broadcasts_processed": 0,
        "documents_created": 0,
        "inspections_created": 0,
        "facility_inspection_alerts_sent": 0,
        "deposit_settlements_created": 0,
        "deposit_settlements_updated": 0,
        "deposit_settlements_ready": 0,
        "deposit_collection_invoices_created": 0,
        "complaints_escalated": 0,
        "service_requests_created": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())
    for organization_id in org_ids:
        logger.info("tenants.operations_workflows.start organization_id=%s", organization_id)
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_tenant_operations_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception("tenants.operations_workflows.failed organization_id=%s", organization_id)
            continue

        summary["organizations_processed"] += 1
        for key in (
            "leases_synced",
            "occupancies_synced",
            "renewals_created",
            "terminations_created",
            "access_records_synced",
            "utility_tracking_records_synced",
            "utility_tracking_activated",
            "billing_rules_stopped",
            "vacancy_risks_created",
            "vacancy_risks_updated",
            "vacancy_risks_resolved",
            "vacancy_risks_open",
            "invoices_created",
            "payments_reconciled",
            "late_payment_penalties_applied",
            "payment_journals_posted",
            "overdue_invoices_flagged",
            "billing_tickets_synced",
            "billing_tickets_escalated",
            "rent_reminders_sent",
            "admin_expiry_alerts_sent",
            "broadcasts_processed",
            "documents_created",
            "inspections_created",
            "facility_inspection_alerts_sent",
            "deposit_settlements_created",
            "deposit_settlements_updated",
            "deposit_settlements_ready",
            "deposit_collection_invoices_created",
            "complaints_escalated",
            "service_requests_created",
        ):
            summary[key] += result.get(key, 0)

        logger.info(
            "tenants.operations_workflows.success organization_id=%s leases_synced=%s invoices_created=%s reminders_sent=%s complaints_escalated=%s",
            organization_id,
            result.get("leases_synced", 0),
            result.get("invoices_created", 0),
            result.get("rent_reminders_sent", 0),
            result.get("complaints_escalated", 0),
        )

    logger.info(
        "tenants.operations_workflows.complete organizations_processed=%s errors=%s leases_synced=%s invoices_created=%s reminders_sent=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["leases_synced"],
        summary["invoices_created"],
        summary["rent_reminders_sent"],
    )
    return summary

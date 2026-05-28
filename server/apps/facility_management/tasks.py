import logging

from celery import shared_task

from apps.accounts.models import Organization
from apps.accounts.rls import iter_organization_ids, rls_context
from apps.facility_management.document_drawings_workflows import run_documents_drawings_automation
from apps.facility_management.health_safety_workflows import run_health_safety_compliance_automation
from apps.facility_management.service_request_workflows import run_service_request_helpdesk_automation
from apps.facility_management.space_occupancy_workflows import run_space_occupancy_automation
from apps.facility_management.utility_workflows import run_utility_energy_automation
from apps.properties.maintenance_workflows import run_maintenance_automation

logger = logging.getLogger(__name__)


@shared_task(name="facility_management.run_scheduled_maintenance_workflows")
def run_scheduled_maintenance_workflows(organization_ids: list[int] | None = None):
    """Run preventive and predictive maintenance automation across organizations."""
    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "preventive_work_orders_created": 0,
        "preventive_work_orders_skipped": 0,
        "predictive_alerts_created": 0,
        "predictive_work_orders_created": 0,
        "predictive_rules_skipped": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())

    for organization_id in org_ids:
        logger.info(
            "facility_management.maintenance_workflows.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_maintenance_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception(
                "facility_management.maintenance_workflows.failed organization_id=%s",
                organization_id,
            )
            continue

        summary["organizations_processed"] += 1
        summary["preventive_work_orders_created"] += result["preventive_work_orders_created"]
        summary["preventive_work_orders_skipped"] += result["preventive_work_orders_skipped"]
        summary["predictive_alerts_created"] += result["predictive_alerts_created"]
        summary["predictive_work_orders_created"] += result["predictive_work_orders_created"]
        summary["predictive_rules_skipped"] += result["predictive_rules_skipped"]

        logger.info(
            "facility_management.maintenance_workflows.success organization_id=%s preventive_created=%s predictive_alerts=%s predictive_work_orders=%s",
            organization_id,
            result["preventive_work_orders_created"],
            result["predictive_alerts_created"],
            result["predictive_work_orders_created"],
        )

    logger.info(
        "facility_management.maintenance_workflows.complete organizations_processed=%s errors=%s preventive_created=%s predictive_alerts=%s predictive_work_orders=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["preventive_work_orders_created"],
        summary["predictive_alerts_created"],
        summary["predictive_work_orders_created"],
    )
    return summary


@shared_task(name="facility_management.run_scheduled_service_request_helpdesk_workflows")
def run_scheduled_service_request_helpdesk_workflows(organization_ids: list[int] | None = None):
    """Run internal service-request and billing/helpdesk automation across organizations."""

    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "service_requests_synced": 0,
        "service_requests_escalated": 0,
        "work_orders_created": 0,
        "overdue_invoices_flagged": 0,
        "billing_tickets_synced": 0,
        "billing_tickets_escalated": 0,
        "billing_tickets_resolved": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())

    for organization_id in org_ids:
        logger.info(
            "facility_management.service_request_helpdesk_workflows.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_service_request_helpdesk_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception(
                "facility_management.service_request_helpdesk_workflows.failed organization_id=%s",
                organization_id,
            )
            continue

        summary["organizations_processed"] += 1
        for key in (
            "service_requests_synced",
            "service_requests_escalated",
            "work_orders_created",
            "overdue_invoices_flagged",
            "billing_tickets_synced",
            "billing_tickets_escalated",
            "billing_tickets_resolved",
        ):
            summary[key] += result[key]

        logger.info(
            "facility_management.service_request_helpdesk_workflows.success organization_id=%s service_requests_synced=%s escalated=%s work_orders_created=%s billing_resolved=%s",
            organization_id,
            result["service_requests_synced"],
            result["service_requests_escalated"],
            result["work_orders_created"],
            result["billing_tickets_resolved"],
        )

    logger.info(
        "facility_management.service_request_helpdesk_workflows.complete organizations_processed=%s errors=%s service_requests_synced=%s escalated=%s work_orders_created=%s billing_resolved=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["service_requests_synced"],
        summary["service_requests_escalated"],
        summary["work_orders_created"],
        summary["billing_tickets_resolved"],
    )
    return summary


@shared_task(name="facility_management.run_scheduled_space_occupancy_workflows")
def run_scheduled_space_occupancy_workflows(organization_ids: list[int] | None = None):
    """Run occupancy, vacancy, booking, and tenant-allocation automation across organizations."""

    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "space_profiles_synced": 0,
        "allocations_synced": 0,
        "allocations_ended": 0,
        "tenant_profiles_synced": 0,
        "inventory_updates": 0,
        "bookings_synced": 0,
        "bookings_completed": 0,
        "bookings_no_show": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())

    for organization_id in org_ids:
        logger.info(
            "facility_management.space_occupancy_workflows.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_space_occupancy_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception(
                "facility_management.space_occupancy_workflows.failed organization_id=%s",
                organization_id,
            )
            continue

        summary["organizations_processed"] += 1
        for key in (
            "space_profiles_synced",
            "allocations_synced",
            "allocations_ended",
            "tenant_profiles_synced",
            "inventory_updates",
            "bookings_synced",
            "bookings_completed",
            "bookings_no_show",
        ):
            summary[key] += result[key]

        logger.info(
            "facility_management.space_occupancy_workflows.success organization_id=%s space_profiles_synced=%s allocations_synced=%s tenant_profiles_synced=%s bookings_synced=%s",
            organization_id,
            result["space_profiles_synced"],
            result["allocations_synced"],
            result["tenant_profiles_synced"],
            result["bookings_synced"],
        )

    logger.info(
        "facility_management.space_occupancy_workflows.complete organizations_processed=%s errors=%s allocations_synced=%s tenant_profiles_synced=%s bookings_synced=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["allocations_synced"],
        summary["tenant_profiles_synced"],
        summary["bookings_synced"],
    )
    return summary


@shared_task(name="facility_management.run_scheduled_utility_energy_workflows")
def run_scheduled_utility_energy_workflows(organization_ids: list[int] | None = None):
    """Run utilities, utility billing, and sustainability automation across organizations."""

    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "meters_synced": 0,
        "readings_synced": 0,
        "anomalies_flagged": 0,
        "consumption_days_synced": 0,
        "bills_synced": 0,
        "finance_bills_synced": 0,
        "overdue_bills": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())

    for organization_id in org_ids:
        logger.info(
            "facility_management.utility_energy_workflows.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_utility_energy_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception(
                "facility_management.utility_energy_workflows.failed organization_id=%s",
                organization_id,
            )
            continue

        summary["organizations_processed"] += 1
        for key in (
            "meters_synced",
            "readings_synced",
            "anomalies_flagged",
            "consumption_days_synced",
            "bills_synced",
            "finance_bills_synced",
            "overdue_bills",
        ):
            summary[key] += result[key]

        logger.info(
            "facility_management.utility_energy_workflows.success organization_id=%s meters_synced=%s readings_synced=%s bills_synced=%s finance_bills_synced=%s",
            organization_id,
            result["meters_synced"],
            result["readings_synced"],
            result["bills_synced"],
            result["finance_bills_synced"],
        )

    logger.info(
        "facility_management.utility_energy_workflows.complete organizations_processed=%s errors=%s readings_synced=%s bills_synced=%s finance_bills_synced=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["readings_synced"],
        summary["bills_synced"],
        summary["finance_bills_synced"],
    )
    return summary


@shared_task(name="facility_management.run_scheduled_health_safety_compliance_workflows")
def run_scheduled_health_safety_compliance_workflows(organization_ids: list[int] | None = None):
    """Run health, safety, and compliance automation across organizations."""

    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "incidents_synced": 0,
        "incidents_resolved": 0,
        "follow_up_inspections_created": 0,
        "corrective_work_orders_created": 0,
        "inspections_synced": 0,
        "checklists_synced": 0,
        "checklist_failures": 0,
        "compliance_records_synced": 0,
        "violations_created": 0,
        "regulatory_documents_synced": 0,
        "expired_documents_flagged": 0,
        "audit_logs_created": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())

    for organization_id in org_ids:
        logger.info(
            "facility_management.health_safety_compliance_workflows.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_health_safety_compliance_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception(
                "facility_management.health_safety_compliance_workflows.failed organization_id=%s",
                organization_id,
            )
            continue

        summary["organizations_processed"] += 1
        for key in (
            "incidents_synced",
            "incidents_resolved",
            "follow_up_inspections_created",
            "corrective_work_orders_created",
            "inspections_synced",
            "checklists_synced",
            "checklist_failures",
            "compliance_records_synced",
            "violations_created",
            "regulatory_documents_synced",
            "expired_documents_flagged",
            "audit_logs_created",
        ):
            summary[key] += result[key]

        logger.info(
            "facility_management.health_safety_compliance_workflows.success organization_id=%s incidents_synced=%s inspections_synced=%s checklists_synced=%s violations_created=%s",
            organization_id,
            result["incidents_synced"],
            result["inspections_synced"],
            result["checklists_synced"],
            result["violations_created"],
        )

    logger.info(
        "facility_management.health_safety_compliance_workflows.complete organizations_processed=%s errors=%s incidents_synced=%s inspections_synced=%s checklists_synced=%s violations_created=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["incidents_synced"],
        summary["inspections_synced"],
        summary["checklists_synced"],
        summary["violations_created"],
    )
    return summary


@shared_task(name="facility_management.run_scheduled_documents_drawings_workflows")
def run_scheduled_documents_drawings_workflows(organization_ids: list[int] | None = None):
    """Run facility document status refresh and maintenance-log generation across organizations."""

    summary = {
        "organizations_processed": 0,
        "errors": 0,
        "documents_synced": 0,
        "maintenance_logs_generated": 0,
        "review_due_documents": 0,
        "expired_documents": 0,
        "compliance_certificates_flagged": 0,
    }

    org_ids = organization_ids or list(iter_organization_ids())

    for organization_id in org_ids:
        logger.info(
            "facility_management.documents_drawings_workflows.start organization_id=%s",
            organization_id,
        )
        try:
            with rls_context(organization_id, bypass=False):
                organization = Organization.objects.only("id").get(pk=organization_id)
                result = run_documents_drawings_automation(organization)
        except Exception:
            summary["errors"] += 1
            logger.exception(
                "facility_management.documents_drawings_workflows.failed organization_id=%s",
                organization_id,
            )
            continue

        summary["organizations_processed"] += 1
        for key in (
            "documents_synced",
            "maintenance_logs_generated",
            "review_due_documents",
            "expired_documents",
            "compliance_certificates_flagged",
        ):
            summary[key] += result[key]

        logger.info(
            "facility_management.documents_drawings_workflows.success organization_id=%s documents_synced=%s maintenance_logs_generated=%s review_due_documents=%s expired_documents=%s",
            organization_id,
            result["documents_synced"],
            result["maintenance_logs_generated"],
            result["review_due_documents"],
            result["expired_documents"],
        )

    logger.info(
        "facility_management.documents_drawings_workflows.complete organizations_processed=%s errors=%s documents_synced=%s maintenance_logs_generated=%s review_due_documents=%s expired_documents=%s",
        summary["organizations_processed"],
        summary["errors"],
        summary["documents_synced"],
        summary["maintenance_logs_generated"],
        summary["review_due_documents"],
        summary["expired_documents"],
    )
    return summary

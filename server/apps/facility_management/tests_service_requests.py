from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone
from apps.facility_management.tasks import run_scheduled_service_request_helpdesk_workflows
from apps.finance.models import Customer, Invoice, InvoicePayment, PaymentMethod
from apps.properties.models import Property, ServiceRequest, Unit, WorkOrder
from apps.support_desk.models import SupportTicket

User = get_user_model()


class FacilityServiceRequestApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Facility Service Request Org")
        self.user = User.objects.create_superuser(
            username="facility-service-admin@example.com",
            email="facility-service-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])

        self.assigned_agent = User.objects.create_user(
            username="facility-service-agent@example.com",
            email="facility-service-agent@example.com",
            password="Pass123!",
            first_name="Ifeoma",
            last_name="Nwafor",
        )
        agent_profile = self.assigned_agent.profile
        agent_profile.organization = self.org
        agent_profile.role = "manager"
        agent_profile.user_status = "active"
        agent_profile.mfa_enabled = True
        agent_profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])

        self.client.force_authenticate(self.user)

        self.property = Property.objects.create(
            organization=self.org,
            name="Atlas Towers",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="12 Marina Road, Lagos",
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="2B-14",
            floor=2,
            area_sqft=240,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-ATL-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Operations Floor",
            floor_code="OPS-2",
            floor_number=2,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="East Services",
            zone_code="EST-SVC",
            zone_type=FacilityZone.ZoneType.COMMERCIAL,
        )
        self.space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit,
            space_label="Electrical Closet 2B",
        )
        self.customer = Customer.objects.create(
            organization=self.org,
            name="Meridian Occupiers Ltd",
            email="ops@meridian.example.com",
            phone="+2348012345678",
            support_ticketing_enabled=True,
        )
        today = timezone.localdate()
        self.invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            property=self.property,
            invoice_number="INV-FAC-1001",
            status=Invoice.Status.SENT,
            issue_date=today - timedelta(days=14),
            due_date=today - timedelta(days=2),
            subtotal=Decimal("250000.00"),
            total_amount=Decimal("250000.00"),
        )

    def test_service_request_create_derives_context_and_creates_work_order(self):
        payload = {
            "facility_space": self.space.id,
            "title": "Restore lighting in electrical closet",
            "description": "Two fittings failed after a brief power surge.",
            "category": WorkOrder.Category.ELECTRICAL,
            "priority": ServiceRequest.Priority.HIGH,
            "status": ServiceRequest.Status.OPEN,
            "source_channel": ServiceRequest.SourceChannel.MOBILE,
            "assigned_agent": self.assigned_agent.id,
        }

        response = self.client.post(
            "/api/facility-management/service-requests/requests/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        service_request = ServiceRequest.objects.get(title="Restore lighting in electrical closet")
        self.assertEqual(service_request.property_id, self.property.id)
        self.assertEqual(service_request.facility_id, self.facility.id)
        self.assertEqual(service_request.facility_space_id, self.space.id)
        self.assertEqual(service_request.unit_id, self.unit.id)
        self.assertEqual(service_request.requester_id, self.user.id)
        self.assertEqual(service_request.status, ServiceRequest.Status.ACKNOWLEDGED)
        self.assertEqual(service_request.sla_target_hours, 8)
        self.assertIsNotNone(service_request.first_response_at)
        self.assertIsNotNone(service_request.work_order_id)
        self.assertEqual(service_request.work_order.maintenance_mode, WorkOrder.MaintenanceMode.CORRECTIVE)
        self.assertEqual(service_request.work_order.status, WorkOrder.Status.ASSIGNED)

    def test_workflow_sync_escalates_overdue_request_and_updates_linked_work_order(self):
        work_order = WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            title="Reset access control panel",
            description="Controller keeps rebooting after voltage fluctuation.",
            maintenance_mode=WorkOrder.MaintenanceMode.CORRECTIVE,
            category=WorkOrder.Category.ELECTRICAL,
            priority=WorkOrder.Priority.MEDIUM,
            status=WorkOrder.Status.OPEN,
            reported_by="Security Desk",
        )
        service_request = ServiceRequest.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            title="Reset access control panel",
            description="Controller keeps rebooting after voltage fluctuation.",
            category=WorkOrder.Category.ELECTRICAL,
            priority=ServiceRequest.Priority.MEDIUM,
            status=ServiceRequest.Status.OPEN,
            requested_by="Security Desk",
            requester=self.user,
            sla_target_hours=24,
            sla_due_at=timezone.now() - timedelta(hours=2),
            work_order=work_order,
        )

        response = self.client.post(
            "/api/facility-management/service-requests/sync/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        service_request.refresh_from_db()
        work_order.refresh_from_db()

        self.assertEqual(service_request.status, ServiceRequest.Status.ESCALATED)
        self.assertIsNotNone(service_request.escalated_at)
        self.assertEqual(work_order.status, WorkOrder.Status.IN_PROGRESS)
        self.assertEqual(work_order.priority, WorkOrder.Priority.HIGH)
        self.assertEqual(response.data["service_requests_escalated"], 1)

    def test_record_payment_resolves_billing_ticket_and_marks_invoice_paid(self):
        ticket = SupportTicket.objects.create(
            organization=self.org,
            subject="Clarify outstanding utilities charge",
            description="Tenant needs confirmation before remittance.",
            requester=self.user,
            customer=self.customer,
            invoice=self.invoice,
            category=SupportTicket.Category.BILLING,
            priority=SupportTicket.Priority.HIGH,
            status=SupportTicket.Status.OPEN,
        )

        response = self.client.post(
            f"/api/facility-management/service-requests/invoices/{self.invoice.id}/record-payment/",
            {
                "amount": "250000.00",
                "payment_date": timezone.localdate().isoformat(),
                "payment_method": PaymentMethod.BANK_TRANSFER,
                "reference_number": "PAY-88301",
                "notes": "Tenant paid via transfer.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        self.invoice.refresh_from_db()
        ticket.refresh_from_db()

        self.assertEqual(self.invoice.status, Invoice.Status.PAID)
        self.assertEqual(ticket.status, SupportTicket.Status.RESOLVED)
        self.assertIsNotNone(ticket.resolved_at)
        self.assertEqual(response.data["billing_tickets_resolved"], 1)

    def test_overview_returns_combined_service_request_and_billing_snapshot(self):
        ServiceRequest.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            title="Replace door closer",
            description="Door closer is leaking oil.",
            category=WorkOrder.Category.GENERAL,
            priority=ServiceRequest.Priority.MEDIUM,
            status=ServiceRequest.Status.ESCALATED,
            requested_by="Admin Desk",
            requester=self.user,
            sla_target_hours=24,
            sla_due_at=timezone.now() - timedelta(hours=1),
            feedback_rating=4,
        )
        SupportTicket.objects.create(
            organization=self.org,
            subject="Query service charge balance",
            description="Tenant wants a breakdown.",
            requester=self.user,
            customer=self.customer,
            invoice=self.invoice,
            category=SupportTicket.Category.BILLING,
            priority=SupportTicket.Priority.MEDIUM,
            status=SupportTicket.Status.OPEN,
        )

        response = self.client.get("/api/facility-management/service-requests/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["open_requests"], 1)
        self.assertEqual(response.data["kpis"]["escalated_requests"], 1)
        self.assertEqual(response.data["kpis"]["sla_at_risk"], 1)
        self.assertEqual(response.data["kpis"]["open_billing_tickets"], 1)
        self.assertEqual(response.data["kpis"]["overdue_invoices"], 1)
        self.assertEqual(response.data["kpis"]["avg_feedback_rating"], 4.0)

    def test_scheduled_task_runs_service_request_and_billing_automation(self):
        ServiceRequest.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            title="Replace damaged smoke detector",
            description="Sensor in corridor is beeping continuously.",
            category=WorkOrder.Category.FIRE_SAFETY,
            priority=ServiceRequest.Priority.MEDIUM,
            status=ServiceRequest.Status.OPEN,
            requested_by="Safety Desk",
            requester=self.user,
            sla_target_hours=24,
            sla_due_at=timezone.now() - timedelta(hours=3),
        )
        SupportTicket.objects.create(
            organization=self.org,
            subject="Invoice follow-up",
            description="Awaiting confirmation of receipt.",
            requester=self.user,
            customer=self.customer,
            invoice=self.invoice,
            category=SupportTicket.Category.BILLING,
            priority=SupportTicket.Priority.MEDIUM,
            status=SupportTicket.Status.OPEN,
        )
        InvoicePayment.objects.create(
            invoice=self.invoice,
            amount=Decimal("250000.00"),
            payment_date=timezone.localdate(),
            payment_method=PaymentMethod.BANK_TRANSFER,
            reference_number="PAY-SYNC-01",
        )

        summary = run_scheduled_service_request_helpdesk_workflows([self.org.id])

        self.assertEqual(summary["organizations_processed"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertGreaterEqual(summary["service_requests_escalated"], 1)
        self.assertGreaterEqual(summary["work_orders_created"], 1)
        self.assertGreaterEqual(summary["billing_tickets_resolved"], 1)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.PAID)

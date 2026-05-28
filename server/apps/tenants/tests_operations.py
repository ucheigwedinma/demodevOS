from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from auditlog.context import disable_auditlog
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone, UtilityMeter
from apps.finance.models import Customer, Invoice, JournalEntry
from apps.properties.models import Property, ServiceRequest, Unit, WorkOrder
from apps.support_desk.models import SupportTicket
from apps.support_desk.whatsapp_providers import WhatsAppDispatchResult
from apps.tenants.models import (
    LeaseAccessProvisioning,
    LeaseAgreement,
    LeaseRenewalRequest,
    LeaseTerminationRequest,
    LeaseUtilityTracking,
    OccupancyRecord,
    RecurringChargeRule,
    TenantCommunicationLog,
    TenantComplaint,
    TenantDepositSettlement,
    TenantDocumentRecord,
    TenantInspection,
    TenantProfile,
    TenantVacancyRiskAlert,
)
from apps.tenants.workflows import run_tenant_operations_automation

User = get_user_model()


@override_settings(ROOT_URLCONF="apps.tenants.tests_urls")
class TenantOperationsApiTests(APITestCase):
    def setUp(self):
        today = timezone.localdate()
        with disable_auditlog():
            self.org = Organization.objects.create(name="Tenant Operations Org")

        self.user = User.objects.create_superuser(
            username="tenant-ops-admin@example.com",
            email="tenant-ops-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        self.client.force_authenticate(self.user)

        self.property = Property.objects.create(
            organization=self.org,
            name="Helios Residences",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="14 Admiralty Way, Lagos",
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="A-12",
            floor=1,
            area_sqft=500,
            unit_category=Unit.UnitCategory.APARTMENT,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="HEL-LAG-01",
            facility_classification=Facility.FacilityClassification.RESIDENTIAL,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Level 1",
            floor_code="L1",
            floor_number=1,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="East Wing",
            zone_code="EW",
            zone_type=FacilityZone.ZoneType.RESIDENTIAL,
        )
        self.space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit,
            space_label="Apartment A-12",
        )
        self.customer = Customer.objects.create(
            organization=self.org,
            name="Atlas Household",
            email="atlas@example.com",
            phone="+2348011111111",
            support_ticketing_enabled=True,
        )
        self.tenant = TenantProfile.objects.create(
            organization=self.org,
            customer=self.customer,
            primary_user=self.user,
            property=self.property,
            unit=self.unit,
            facility=self.facility,
            facility_space=self.space,
            status=TenantProfile.Status.ACTIVE,
            display_name="Atlas Household",
            lease_start_date=today - timedelta(days=120),
            lease_end_date=today + timedelta(days=30),
            move_in_date=today - timedelta(days=120),
        )
        self.lease = LeaseAgreement.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            property=self.property,
            unit=self.unit,
            facility=self.facility,
            facility_space=self.space,
            title="Atlas Household annual lease",
            status=LeaseAgreement.Status.ACTIVE,
            start_date=today - timedelta(days=120),
            end_date=today + timedelta(days=30),
            rent_amount=Decimal("250000.00"),
            service_charge_amount=Decimal("25000.00"),
            payment_frequency=LeaseAgreement.PaymentFrequency.MONTHLY,
            auto_generate_billing=True,
            next_billing_date=today,
        )

    def _create_secondary_location(self):
        property_record = Property.objects.create(
            organization=self.org,
            name="Helios Annex",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="22 Bourdillon Road, Lagos",
        )
        unit = Unit.objects.create(
            organization=self.org,
            property=property_record,
            unit_number="B-04",
            floor=2,
            area_sqft=420,
            unit_category=Unit.UnitCategory.APARTMENT,
            status=Unit.UnitStatus.AVAILABLE,
        )
        facility = Facility.objects.create(
            organization=self.org,
            property=property_record,
            facility_code="HEL-LAG-02",
            facility_classification=Facility.FacilityClassification.RESIDENTIAL,
        )
        floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=facility,
            name="Level 2",
            floor_code="L2",
            floor_number=2,
        )
        zone = FacilityZone.objects.create(
            organization=self.org,
            facility=facility,
            floor=floor,
            name="West Wing",
            zone_code="WW",
            zone_type=FacilityZone.ZoneType.RESIDENTIAL,
        )
        space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=facility,
            zone=zone,
            unit=unit,
            space_label="Apartment B-04",
        )
        return property_record, unit, facility, space

    def test_tenant_can_have_multiple_leases_and_chain_is_derived(self):
        today = timezone.localdate()
        property_record, unit, facility, space = self._create_secondary_location()

        response = self.client.post(
            "/api/tenants/lease-occupancy/leases/",
            {
                "tenant_profile": self.tenant.id,
                "unit": unit.id,
                "title": "Atlas Household annex lease",
                "start_date": (today + timedelta(days=10)).isoformat(),
                "end_date": (today + timedelta(days=375)).isoformat(),
                "rent_amount": "180000.00",
                "service_charge_amount": "18000.00",
                "payment_frequency": "monthly",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        new_lease = LeaseAgreement.objects.get(pk=response.data["id"])
        self.assertEqual(self.tenant.lease_agreements.count(), 2)
        self.assertEqual(new_lease.property_id, property_record.id)
        self.assertEqual(new_lease.facility_id, facility.id)
        self.assertEqual(new_lease.facility_space_id, space.id)
        self.assertEqual(property_record.facility.id, facility.id)

    def test_lease_creation_rejects_property_facility_mismatch(self):
        today = timezone.localdate()
        property_record, _, facility, _ = self._create_secondary_location()

        response = self.client.post(
            "/api/tenants/lease-occupancy/leases/",
            {
                "tenant_profile": self.tenant.id,
                "property": self.property.id,
                "facility": facility.id,
                "title": "Invalid linked lease",
                "start_date": (today + timedelta(days=5)).isoformat(),
                "end_date": (today + timedelta(days=370)).isoformat(),
                "rent_amount": "120000.00",
                "service_charge_amount": "12000.00",
                "payment_frequency": "monthly",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("facility", response.data)
        self.assertEqual(property_record.facility.id, facility.id)

    def test_lease_created_event_builds_billing_assignment_and_access(self):
        today = timezone.localdate()
        property_record, unit, facility, space = self._create_secondary_location()
        UtilityMeter.objects.create(
            organization=self.org,
            property=property_record,
            meter_number="UTIL-BEACON-001",
            utility_type=UtilityMeter.UtilityType.ELECTRICITY,
            location_label="Retail riser",
            is_active=True,
        )
        customer = Customer.objects.create(
            organization=self.org,
            name="Beacon Retail",
            email="beacon@example.com",
            phone="+2348090000000",
            support_ticketing_enabled=True,
        )
        tenant = TenantProfile.objects.create(
            organization=self.org,
            customer=customer,
            primary_user=self.user,
            tenant_type=TenantProfile.TenantType.CORPORATE,
            status=TenantProfile.Status.PENDING_MOVE_IN,
            display_name="Beacon Retail",
        )

        lease = LeaseAgreement.objects.create(
            organization=self.org,
            tenant_profile=tenant,
            property=property_record,
            unit=unit,
            facility=facility,
            facility_space=space,
            title="Beacon Retail flagship lease",
            status=LeaseAgreement.Status.ACTIVE,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=364),
            rent_amount=Decimal("300000.00"),
            service_charge_amount=Decimal("45000.00"),
            payment_frequency=LeaseAgreement.PaymentFrequency.MONTHLY,
            auto_generate_billing=True,
        )

        tenant.refresh_from_db()
        lease.refresh_from_db()

        self.assertEqual(tenant.property_id, property_record.id)
        self.assertEqual(tenant.facility_id, facility.id)
        self.assertEqual(tenant.unit_id, unit.id)
        self.assertEqual(tenant.facility_space_id, space.id)
        self.assertTrue(
            OccupancyRecord.objects.filter(
                organization=self.org,
                lease_agreement=lease,
                tenant_profile=tenant,
                status=OccupancyRecord.Status.ACTIVE,
            ).exists()
        )
        self.assertEqual(
            RecurringChargeRule.objects.filter(
                organization=self.org,
                lease_agreement=lease,
                charge_type__in=[
                    RecurringChargeRule.ChargeType.RENT,
                    RecurringChargeRule.ChargeType.SERVICE_CHARGE,
                ],
            ).count(),
            2,
        )
        self.assertGreaterEqual(
            Invoice.objects.filter(organization=self.org, customer=customer).count(),
            2,
        )
        access_record = LeaseAccessProvisioning.objects.get(organization=self.org, lease_agreement=lease)
        self.assertEqual(access_record.status, LeaseAccessProvisioning.Status.ACTIVE)
        self.assertTrue(access_record.facility_access_active)
        self.assertTrue(access_record.security_access_active)
        utility_tracking = LeaseUtilityTracking.objects.get(organization=self.org, lease_agreement=lease)
        self.assertEqual(utility_tracking.status, LeaseUtilityTracking.Status.ACTIVE)
        self.assertTrue(utility_tracking.utility_tracking_active)
        self.assertEqual(utility_tracking.tracked_meter_count, 1)
        self.assertEqual(utility_tracking.tracked_utility_types, [UtilityMeter.UtilityType.ELECTRICITY])

    def test_lease_sync_creates_occupancy_and_renewal(self):
        response = self.client.post("/api/tenants/lease-occupancy/sync/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            OccupancyRecord.objects.filter(organization=self.org, lease_agreement=self.lease, tenant_profile=self.tenant).exists()
        )
        self.assertTrue(
            LeaseRenewalRequest.objects.filter(organization=self.org, lease_agreement=self.lease).exists()
        )
        self.assertGreaterEqual(response.data["renewals_created"], 1)

    @patch("apps.notifications.services.dispatch_workflow_notification")
    def test_lease_sync_creates_vacancy_risk_and_admin_alert(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 1,
            "emails_sent": 0,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }

        response = self.client.post("/api/tenants/lease-occupancy/sync/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        alert = TenantVacancyRiskAlert.objects.get(organization=self.org, lease_agreement=self.lease)
        self.assertIn(
            alert.status,
            {TenantVacancyRiskAlert.Status.OPEN, TenantVacancyRiskAlert.Status.MITIGATED},
        )
        self.assertGreater(alert.risk_score, 0)
        self.assertEqual(alert.forecasted_vacancy_date, self.lease.end_date)
        self.assertIsNotNone(alert.tenant_notified_at)
        self.assertIsNotNone(alert.admin_notified_at)
        self.assertEqual(response.data["vacancy_risks_open"], 1)
        self.assertEqual(response.data["admin_expiry_alerts_sent"], 1)
        mock_dispatch.assert_called_once()

    def test_lease_overview_includes_vacancy_risk_watchlist(self):
        self.client.post("/api/tenants/lease-occupancy/sync/", {}, format="json")

        response = self.client.get("/api/tenants/lease-occupancy/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["vacancy_risks_open"], 1)
        self.assertEqual(len(response.data["vacancy_risk_watchlist"]), 1)
        self.assertEqual(response.data["vacancy_risk_watchlist"][0]["lease_code"], self.lease.lease_code)

    def test_approved_renewal_resolves_vacancy_risk(self):
        self.client.post("/api/tenants/lease-occupancy/sync/", {}, format="json")
        renewal = LeaseRenewalRequest.objects.get(organization=self.org, lease_agreement=self.lease)

        response = self.client.post(f"/api/tenants/lease-occupancy/renewals/{renewal.id}/approve/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        alert = TenantVacancyRiskAlert.objects.get(organization=self.org, lease_agreement=self.lease)
        self.assertEqual(alert.status, TenantVacancyRiskAlert.Status.RESOLVED)
        self.assertEqual(response.data["workflow"]["vacancy_risks_resolved"], 1)

    @patch("apps.notifications.services.dispatch_workflow_notification")
    def test_termination_approval_vacates_unit_stops_billing_and_notifies_facility(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 1,
            "emails_sent": 0,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }
        rule = RecurringChargeRule.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            lease_agreement=self.lease,
            property=self.property,
            unit=self.unit,
            facility=self.facility,
            facility_space=self.space,
            title="Future rent",
            charge_type=RecurringChargeRule.ChargeType.RENT,
            amount=Decimal("250000.00"),
            frequency=RecurringChargeRule.Frequency.MONTHLY,
            start_date=timezone.localdate() - timedelta(days=90),
            end_date=timezone.localdate() + timedelta(days=30),
            next_invoice_date=timezone.localdate() + timedelta(days=10),
        )
        termination = LeaseTerminationRequest.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            lease_agreement=self.lease,
            status=LeaseTerminationRequest.Status.REQUESTED,
            requested_move_out_date=timezone.localdate(),
            notice_period_days=30,
            reason="Lease terminated by management.",
        )

        response = self.client.post(
            f"/api/tenants/lease-occupancy/terminations/{termination.id}/approve/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.lease.refresh_from_db()
        self.tenant.refresh_from_db()
        self.unit.refresh_from_db()
        rule.refresh_from_db()
        occupancy = OccupancyRecord.objects.get(organization=self.org, lease_agreement=self.lease)
        inspection = TenantInspection.objects.get(
            organization=self.org,
            lease_agreement=self.lease,
            inspection_type=TenantInspection.InspectionType.MOVE_OUT,
        )
        self.assertEqual(self.lease.status, LeaseAgreement.Status.TERMINATED)
        self.assertEqual(self.tenant.status, TenantProfile.Status.MOVED_OUT)
        self.assertEqual(self.tenant.move_out_date, timezone.localdate())
        self.assertEqual(self.unit.status, Unit.UnitStatus.AVAILABLE)
        self.assertEqual(occupancy.status, OccupancyRecord.Status.VACATED)
        self.assertEqual(rule.status, RecurringChargeRule.Status.ENDED)
        self.assertIsNone(rule.next_invoice_date)
        self.assertEqual(inspection.scheduled_date, timezone.localdate())
        self.assertGreaterEqual(response.data["workflow"]["billing_rules_stopped"], 1)
        self.assertEqual(response.data["workflow"]["facility_inspection_alerts_sent"], 1)
        self.assertEqual(response.data["workflow"]["deposit_settlements_created"], 1)
        self.assertTrue(
            any(call.kwargs.get("event_key") == "tenant_move_out_inspection_required" for call in mock_dispatch.call_args_list)
        )

    @patch("apps.tenants.workflows.get_whatsapp_provider_adapter")
    @patch("apps.tenants.workflows.send_mail")
    def test_move_in_sync_activates_queued_access_utility_tracking_and_billing_cycle(
        self,
        mocked_send_mail,
        mocked_adapter_factory,
    ):
        mocked_send_mail.return_value = 1
        mocked_adapter = mocked_adapter_factory.return_value
        mocked_adapter.send_message.return_value = WhatsAppDispatchResult(
            provider_key="mock",
            provider_label="Mock Provider",
            mode="mock",
            status="queued",
            provider_message_id="mock-move-in-sync",
            payload={"status": "queued"},
        )
        future_today = timezone.localdate()
        move_in_date = future_today + timedelta(days=3)
        property_record, unit, facility, space = self._create_secondary_location()
        UtilityMeter.objects.create(
            organization=self.org,
            property=property_record,
            meter_number="UTIL-FUTURE-001",
            utility_type=UtilityMeter.UtilityType.WATER,
            location_label="Annex water meter",
            is_active=True,
        )
        customer = Customer.objects.create(
            organization=self.org,
            name="Future Tenant",
            email="future@example.com",
            phone="+2348099999999",
            support_ticketing_enabled=True,
        )
        tenant = TenantProfile.objects.create(
            organization=self.org,
            customer=customer,
            primary_user=self.user,
            tenant_type=TenantProfile.TenantType.INDIVIDUAL,
            status=TenantProfile.Status.PENDING_MOVE_IN,
            display_name="Future Tenant",
            move_in_date=move_in_date,
        )
        lease = LeaseAgreement.objects.create(
            organization=self.org,
            tenant_profile=tenant,
            property=property_record,
            unit=unit,
            facility=facility,
            facility_space=space,
            title="Future Tenant move-in lease",
            status=LeaseAgreement.Status.ACTIVE,
            start_date=move_in_date,
            end_date=move_in_date + timedelta(days=365),
            rent_amount=Decimal("180000.00"),
            service_charge_amount=Decimal("18000.00"),
            payment_frequency=LeaseAgreement.PaymentFrequency.MONTHLY,
            auto_generate_billing=True,
        )

        queued_access = LeaseAccessProvisioning.objects.get(organization=self.org, lease_agreement=lease)
        queued_utility_tracking = LeaseUtilityTracking.objects.get(organization=self.org, lease_agreement=lease)
        self.assertEqual(queued_access.status, LeaseAccessProvisioning.Status.QUEUED)
        self.assertEqual(queued_utility_tracking.status, LeaseUtilityTracking.Status.QUEUED)
        self.assertFalse(queued_utility_tracking.utility_tracking_active)
        self.assertEqual(
            Invoice.objects.filter(organization=self.org, customer=customer).count(),
            0,
        )

        with patch("apps.tenants.workflows.timezone.localdate", return_value=move_in_date):
            with self.captureOnCommitCallbacks(execute=True):
                workflow = run_tenant_operations_automation(self.org, scopes={"lease_occupancy", "billing"})

        queued_access.refresh_from_db()
        queued_utility_tracking.refresh_from_db()
        tenant.refresh_from_db()

        self.assertEqual(queued_access.status, LeaseAccessProvisioning.Status.ACTIVE)
        self.assertTrue(queued_access.facility_access_active)
        self.assertTrue(queued_access.security_access_active)
        self.assertEqual(queued_utility_tracking.status, LeaseUtilityTracking.Status.ACTIVE)
        self.assertTrue(queued_utility_tracking.utility_tracking_active)
        self.assertEqual(queued_utility_tracking.tracked_meter_count, 1)
        self.assertEqual(queued_utility_tracking.tracked_utility_types, [UtilityMeter.UtilityType.WATER])
        self.assertEqual(tenant.status, TenantProfile.Status.ACTIVE)
        self.assertGreaterEqual(
            Invoice.objects.filter(organization=self.org, customer=customer).count(),
            2,
        )
        self.assertGreaterEqual(workflow["access_records_synced"], 1)
        self.assertGreaterEqual(workflow["utility_tracking_activated"], 1)
        self.assertGreaterEqual(workflow["invoices_created"], 2)

    def test_completed_move_out_inspection_creates_deposit_settlement_balance(self):
        self.lease.security_deposit = Decimal("100000.00")
        self.lease.save(update_fields=["security_deposit", "updated_at"])
        termination = LeaseTerminationRequest.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            lease_agreement=self.lease,
            status=LeaseTerminationRequest.Status.REQUESTED,
            requested_move_out_date=timezone.localdate(),
            notice_period_days=30,
            reason="Lease terminated by management.",
        )
        self.client.post(
            f"/api/tenants/lease-occupancy/terminations/{termination.id}/approve/",
            {},
            format="json",
        )
        inspection = TenantInspection.objects.get(
            organization=self.org,
            lease_agreement=self.lease,
            inspection_type=TenantInspection.InspectionType.MOVE_OUT,
        )
        inspection.status = TenantInspection.Status.COMPLETED
        inspection.completed_date = timezone.localdate()
        inspection.security_deposit_deduction = Decimal("150000.00")
        inspection.save(update_fields=["status", "completed_date", "security_deposit_deduction", "updated_at"])

        response = self.client.post("/api/tenants/inspections/sync/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        settlement = TenantDepositSettlement.objects.get(organization=self.org, lease_agreement=self.lease)
        self.assertEqual(settlement.status, TenantDepositSettlement.Status.PENDING_COLLECTION)
        self.assertEqual(settlement.deposit_amount, Decimal("100000.00"))
        self.assertEqual(settlement.assessed_deductions, Decimal("150000.00"))
        self.assertEqual(settlement.additional_amount_due, Decimal("50000.00"))
        self.assertEqual(settlement.refundable_amount, Decimal("0.00"))
        self.assertIsNotNone(settlement.collection_invoice_id)
        self.assertEqual(settlement.collection_invoice.total_amount, Decimal("50000.00"))
        self.assertEqual(response.data["deposit_collection_invoices_created"], 1)
        self.assertEqual(response.data["deposit_settlements_ready"], 1)

    @patch("apps.tenants.workflows.get_whatsapp_provider_adapter")
    @patch("apps.tenants.workflows.send_mail")
    def test_billing_sync_creates_invoice_from_charge_rule(
        self,
        mocked_send_mail,
        mocked_adapter_factory,
    ):
        mocked_send_mail.return_value = 1
        mocked_adapter = mocked_adapter_factory.return_value
        mocked_adapter.send_message.return_value = WhatsAppDispatchResult(
            provider_key="mock",
            provider_label="Mock Provider",
            mode="mock",
            status="queued",
            provider_message_id="mock-billing-sync",
            payload={"status": "queued"},
        )
        RecurringChargeRule.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            lease_agreement=self.lease,
            property=self.property,
            unit=self.unit,
            facility=self.facility,
            facility_space=self.space,
            title="Monthly rent charge",
            charge_type=RecurringChargeRule.ChargeType.RENT,
            amount=Decimal("250000.00"),
            frequency=RecurringChargeRule.Frequency.MONTHLY,
            start_date=timezone.localdate() - timedelta(days=60),
            next_invoice_date=timezone.localdate(),
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/tenants/billing/sync/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        invoice = Invoice.objects.filter(organization=self.org, customer=self.customer).order_by("-id").first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.status, Invoice.Status.SENT)
        self.assertEqual(invoice.line_items.count(), 1)
        self.assertEqual(response.data["invoices_created"], 1)
        self.assertTrue(
            any(
                call.args
                and isinstance(call.args[0], str)
                and call.args[0].startswith("Rent invoice ")
                for call in mocked_send_mail.call_args_list
            )
        )
        mocked_adapter.send_message.assert_called_once()
        self.assertTrue(
            TenantCommunicationLog.objects.filter(
                tenant_profile=self.tenant,
                interaction_type=TenantCommunicationLog.InteractionType.INVOICE_GENERATED,
                direction=TenantCommunicationLog.Direction.OUTBOUND,
            ).exists()
        )

    @patch("apps.tenants.workflows.get_whatsapp_provider_adapter")
    @patch("apps.tenants.workflows.send_mail")
    def test_billing_sync_applies_penalty_and_escalates_sustained_overdue_invoice(
        self,
        mocked_send_mail,
        mocked_adapter_factory,
    ):
        mocked_send_mail.return_value = 1
        mocked_adapter = mocked_adapter_factory.return_value
        mocked_adapter.send_message.return_value = WhatsAppDispatchResult(
            provider_key="mock",
            provider_label="Mock Provider",
            mode="mock",
            status="queued",
            provider_message_id="mock-overdue-sync",
            payload={"status": "queued"},
        )
        overdue_invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            property=self.property,
            status=Invoice.Status.SENT,
            issue_date=timezone.localdate() - timedelta(days=40),
            due_date=timezone.localdate() - timedelta(days=31),
            subtotal=Decimal("100000.00"),
            total_amount=Decimal("100000.00"),
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/tenants/billing/sync/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        overdue_invoice.refresh_from_db()
        self.assertEqual(overdue_invoice.status, Invoice.Status.OVERDUE)
        self.assertGreaterEqual(response.data["overdue_invoices_flagged"], 1)
        self.assertEqual(response.data["late_payment_penalties_applied"], 1)
        self.assertGreaterEqual(response.data["rent_reminders_sent"], 1)

        penalty_invoice = Invoice.objects.exclude(pk=overdue_invoice.id).get(
            organization=self.org,
            customer=self.customer,
            notes__icontains=f"[overdue-penalty:invoice:{overdue_invoice.id}]",
        )
        self.assertEqual(penalty_invoice.total_amount, Decimal("5000.00"))

        ticket = SupportTicket.objects.get(
            organization=self.org,
            invoice=overdue_invoice,
            category=SupportTicket.Category.BILLING,
        )
        self.assertEqual(ticket.status, SupportTicket.Status.ESCALATED)
        self.assertEqual(ticket.priority, SupportTicket.Priority.CRITICAL)
        self.assertEqual(response.data["billing_tickets_escalated"], 1)
        self.assertTrue(
            any(
                call.args
                and isinstance(call.args[0], str)
                and call.args[0].startswith("Payment reminder - ")
                for call in mocked_send_mail.call_args_list
            )
        )

    def test_record_payment_creates_receipt_document(self):
        invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer,
            property=self.property,
            status=Invoice.Status.OVERDUE,
            issue_date=timezone.localdate() - timedelta(days=12),
            due_date=timezone.localdate() - timedelta(days=2),
            subtotal=Decimal("120000.00"),
            total_amount=Decimal("120000.00"),
        )

        response = self.client.post(
            "/api/tenants/payments/records/",
            {
                "invoice": invoice.id,
                "amount": "120000.00",
                "payment_date": timezone.localdate().isoformat(),
                "payment_method": "bank_transfer",
                "reference_number": "TEN-PAY-001",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            TenantDocumentRecord.objects.filter(
                organization=self.org,
                tenant_profile=self.tenant,
                category=TenantDocumentRecord.Category.PAYMENT_RECEIPT,
            ).exists()
        )
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        journal = JournalEntry.objects.get(
            organization=self.org,
            source_type="payment",
            source_id=response.data["payment"]["id"],
        )
        self.assertEqual(journal.status, JournalEntry.Status.POSTED)
        self.assertEqual(journal.lines.count(), 2)
        self.assertEqual(journal.ledger_entries.count(), 2)
        self.assertTrue(
            journal.lines.filter(account__code="1000", debit_amount=Decimal("120000.00")).exists()
        )
        self.assertTrue(
            journal.lines.filter(account__code="1100", credit_amount=Decimal("120000.00")).exists()
        )

    def test_tenant_service_request_auto_assigns_technician_and_starts_sla(self):
        technician = User.objects.create_user(
            username="tenant-service-tech@example.com",
            email="tenant-service-tech@example.com",
            password="Pass123!",
            first_name="Tobi",
            last_name="Adeleke",
        )
        technician_profile = technician.profile
        technician_profile.organization = self.org
        technician_profile.role = "member"
        technician_profile.user_status = "active"
        technician_profile.identity_type = technician_profile.IdentityType.EMPLOYEE
        technician_profile.job_title = "HVAC Technician"
        technician_profile.business_unit = "Facilities Operations"
        technician_profile.mfa_enabled = True
        technician_profile.save(
            update_fields=[
                "organization",
                "role",
                "user_status",
                "identity_type",
                "job_title",
                "business_unit",
                "mfa_enabled",
            ]
        )

        response = self.client.post(
            "/api/tenants/service-requests/requests/",
            {
                "facility_space": self.space.id,
                "title": "Air conditioning not cooling",
                "description": "The apartment AC has been blowing warm air since morning.",
                "category": WorkOrder.Category.HVAC,
                "priority": ServiceRequest.Priority.HIGH,
                "status": ServiceRequest.Status.OPEN,
                "source_channel": ServiceRequest.SourceChannel.MOBILE,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        service_request = ServiceRequest.objects.get(title="Air conditioning not cooling")
        self.assertEqual(service_request.assigned_agent_id, technician.id)
        self.assertEqual(service_request.assigned_to, "Tobi Adeleke")
        self.assertEqual(service_request.status, ServiceRequest.Status.ACKNOWLEDGED)
        self.assertEqual(service_request.sla_target_hours, 8)
        self.assertIsNotNone(service_request.sla_due_at)
        self.assertIsNotNone(service_request.first_response_at)
        self.assertIsNotNone(service_request.work_order_id)
        self.assertEqual(service_request.work_order.status, WorkOrder.Status.ASSIGNED)
        self.assertEqual(service_request.work_order.assigned_to, "Tobi Adeleke")

    @patch("apps.tenants.workflows.get_whatsapp_provider_adapter")
    @patch("apps.tenants.workflows.send_mail")
    def test_resolved_service_request_notifies_tenant_requests_feedback_and_updates_score(
        self,
        mocked_send_mail,
        mocked_adapter_factory,
    ):
        mocked_send_mail.return_value = 1
        mocked_adapter = mocked_adapter_factory.return_value
        mocked_adapter.send_message.return_value = WhatsAppDispatchResult(
            provider_key="mock",
            provider_label="Mock Provider",
            mode="mock",
            status="queued",
            provider_message_id="mock-resolution-sync",
            payload={"status": "queued"},
        )

        create_response = self.client.post(
            "/api/tenants/service-requests/requests/",
            {
                "facility_space": self.space.id,
                "title": "Water heater stopped working",
                "description": "No hot water since yesterday evening.",
                "category": WorkOrder.Category.MECHANICAL,
                "priority": ServiceRequest.Priority.MEDIUM,
                "status": ServiceRequest.Status.OPEN,
                "source_channel": ServiceRequest.SourceChannel.WEB,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)

        service_request = ServiceRequest.objects.get(title="Water heater stopped working")
        self.assertEqual(service_request.tenant_profile_id, self.tenant.id)

        with self.captureOnCommitCallbacks(execute=True):
            work_order = service_request.work_order
            work_order.status = WorkOrder.Status.COMPLETED
            work_order.completed_date = timezone.localdate()
            work_order.save(update_fields=["status", "completed_date", "updated_at"])

        service_request.refresh_from_db()
        self.assertEqual(service_request.status, ServiceRequest.Status.RESOLVED)
        self.assertEqual(service_request.tenant_profile_id, self.tenant.id)

        outbound_logs = TenantCommunicationLog.objects.filter(
            organization=self.org,
            tenant_profile=self.tenant,
            direction=TenantCommunicationLog.Direction.OUTBOUND,
        )
        self.assertTrue(outbound_logs.filter(subject__startswith=f"Issue resolved - SR-{service_request.id}").exists())
        self.assertTrue(outbound_logs.filter(subject__startswith=f"Feedback request - SR-{service_request.id}").exists())
        self.assertTrue(
            any(
                call.args
                and isinstance(call.args[0], str)
                and call.args[0].startswith("Issue resolved - SR-")
                for call in mocked_send_mail.call_args_list
            )
        )
        self.assertTrue(
            any(
                call.args
                and isinstance(call.args[0], str)
                and call.args[0].startswith("Feedback request - SR-")
                for call in mocked_send_mail.call_args_list
            )
        )

        with self.captureOnCommitCallbacks(execute=True):
            feedback_response = self.client.post(
                f"/api/tenants/service-requests/requests/{service_request.id}/feedback/",
                {
                    "feedback_rating": 5,
                    "feedback_comment": "Resolved quickly and professionally.",
                },
                format="json",
            )

        self.assertEqual(feedback_response.status_code, status.HTTP_200_OK, feedback_response.data)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.satisfaction_score, Decimal("5.00"))
        self.assertEqual(self.tenant.satisfaction_response_count, 1)
        self.assertIsNotNone(self.tenant.last_satisfaction_feedback_at)

    def test_complaint_sync_creates_service_request(self):
        complaint = TenantComplaint.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            property=self.property,
            unit=self.unit,
            facility=self.facility,
            facility_space=self.space,
            category=TenantComplaint.Category.MAINTENANCE,
            priority=TenantComplaint.Priority.HIGH,
            subject="Persistent water leakage",
            description="Kitchen ceiling has been leaking since yesterday.",
        )

        response = self.client.post("/api/tenants/complaints/sync/", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        complaint.refresh_from_db()
        self.assertIsNotNone(complaint.service_request_id)
        self.assertTrue(ServiceRequest.objects.filter(pk=complaint.service_request_id).exists())
        self.assertEqual(response.data["service_requests_created"], 1)

    def test_reports_overview_returns_portfolio_metrics(self):
        TenantInspection.objects.create(
            organization=self.org,
            tenant_profile=self.tenant,
            lease_agreement=self.lease,
            property=self.property,
            unit=self.unit,
            facility=self.facility,
            facility_space=self.space,
            inspection_type=TenantInspection.InspectionType.MOVE_IN,
            status=TenantInspection.Status.COMPLETED,
            title="Move-in inspection",
            scheduled_date=timezone.localdate() - timedelta(days=2),
            completed_date=timezone.localdate() - timedelta(days=1),
        )

        response = self.client.get("/api/tenants/reports/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["occupancy"]["occupied_units"], 1)
        self.assertEqual(response.data["tenant_churn"]["active_tenants"], 1)
        self.assertIn("revenue_per_tenant", response.data)

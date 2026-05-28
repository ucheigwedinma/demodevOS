from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import (
    Broker,
    BrokerCommissionEarning,
    BrokerTier,
    ContactAccount,
    ContactDealLink,
    Lead,
    ReservationEvent,
    UnitReservation,
)
from apps.documents.models import DocumentOwnerRole, DocumentRetentionPolicy, DocumentType, DocumentWorkflowPhase
from apps.finance.models import Invoice, JournalEntry, PaymentInstallment, PaymentPlan
from apps.hr.models import Bonus, EmployeeRecord
from apps.properties.models import Property, PropertyInventory, Unit
from apps.settings.models import ensure_default_document_automation_settings

User = get_user_model()


class OpportunityDealAutomationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Opportunity Deal Test Org")
        self.user = User.objects.create_superuser(
            username="opportunity-admin@example.com",
            email="opportunity-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        self.client.force_authenticate(self.user)

        self.broker_tier = BrokerTier.objects.create(
            organization=self.org,
            name="Gold",
            code="gold",
            min_deals=1,
            min_revenue=Decimal("10000000.00"),
            commission_multiplier=Decimal("1.10"),
            bonus_pct=Decimal("2.00"),
            evaluation_period_months=12,
            is_active=True,
        )
        self.broker_user = User.objects.create_user(
            username="partner@example.com",
            email="partner@example.com",
            password="Pass123!",
            first_name="Prime",
            last_name="Partner",
        )
        self.broker_employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=self.broker_user,
            hire_date=timezone.now().date(),
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        self.broker = Broker.objects.create(
            organization=self.org,
            name="Prime Channel Partner",
            email="partner@example.com",
            commission_rate=Decimal("3.00"),
            tier=self.broker_tier,
            status=Broker.Status.ACTIVE,
        )
        self.lead = Lead.objects.create(
            organization=self.org,
            first_name="Amina",
            last_name="Cole",
            email="amina.cole@example.com",
            phone="+1-555-0123",
            status=Lead.Status.ACTIVE,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
            broker=self.broker,
        )
        self.contact = ContactAccount.objects.create(
            organization=self.org,
            entity_type=ContactAccount.EntityType.INDIVIDUAL,
            first_name="Amina",
            last_name="Cole",
            email="amina.cole@example.com",
            phone="+1-555-0123",
            kyc_status=ContactAccount.KYCStatus.VERIFIED,
        )
        self.property = Property.objects.create(
            organization=self.org,
            name="Northfield Court",
            property_type=Property.PropertyType.BUILDING,
            address="12 Seaside Boulevard",
            classification=Property.Classification.OWNED,
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="A-101",
            area_sqft=Decimal("1200.00"),
            asking_price=Decimal("15000000.00"),
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.reservation = UnitReservation.objects.create(
            organization=self.org,
            lead=self.lead,
            unit=self.unit,
            total_price=Decimal("14500000.00"),
            deposit_amount=Decimal("1450000.00"),
            reservation_fee=Decimal("0.00"),
            hold_expires_at=timezone.now() + timezone.timedelta(hours=48),
            status=UnitReservation.Status.HOLD,
            performed_by=self.user,
        )

        uniq = uuid4().hex[:8]
        DocumentType.objects.create(
            organization=self.org,
            code=f"contract_{uniq}",
            name=f"Contract Type {uniq}",
            category_code="CON",
            is_active=True,
        )
        DocumentOwnerRole.objects.create(
            organization=self.org,
            code=f"owner_{uniq}",
            name=f"Owner Role {uniq}",
            is_active=True,
        )
        DocumentWorkflowPhase.objects.create(
            organization=self.org,
            code=f"phase_{uniq}",
            name=f"Phase {uniq}",
            numbering_code="PH1",
            sort_order=1,
            is_active=True,
        )
        DocumentRetentionPolicy.objects.create(
            organization=self.org,
            code=f"ret_{uniq}",
            name=f"Retention {uniq}",
            retention_years=7,
            is_indefinite=False,
            is_active=True,
        )
        ensure_default_document_automation_settings(self.org)

    def _create_opportunity(self) -> ContactDealLink:
        payload = {
            "contact": self.contact.id,
            "lead": self.lead.id,
            "reservation": self.reservation.id,
            "deal_name": "Northfield A-101 Purchase",
            "stage": "Prospecting",
            "status": "active",
            "deal_value": "14500000.00",
            "close_probability": 65,
            "notes": "New buyer opportunity",
        }
        res = self.client.post("/api/crm/opportunities/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        return ContactDealLink.objects.latest("id")

    def test_deal_created_reserves_unit_inventory(self):
        self.assertEqual(self.unit.status, Unit.UnitStatus.AVAILABLE)

        deal = self._create_opportunity()

        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, Unit.UnitStatus.RESERVED)

        inventory = PropertyInventory.objects.get(unit=self.unit)
        self.assertEqual(inventory.status, PropertyInventory.InventoryStatus.RESERVED)
        self.assertEqual(inventory.reservation_id, self.reservation.id)

        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.NOTE_ADDED,
                metadata__automation="deal_created_reserve_unit",
            ).exists()
        )
        self.assertEqual(deal.status, ContactDealLink.Status.ACTIVE)

    @patch("apps.notifications.services.dispatch_workflow_notification")
    def test_closed_won_generates_sales_agreement_allocation_letter_invoice_commission_and_marks_sold(self, mock_dispatch):
        deal = self._create_opportunity()

        patch_payload = {
            "stage": "Closed Won",
            "status": "won",
            "close_probability": 100,
        }
        res = self.client.patch(
            f"/api/crm/opportunities/{deal.id}/",
            patch_payload,
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        self.unit.refresh_from_db()
        self.reservation.refresh_from_db()
        self.assertEqual(self.unit.status, Unit.UnitStatus.SOLD)
        self.assertIsNotNone(self.reservation.reservation_agreement_id)
        self.assertIsNotNone(self.reservation.allocation_letter_id)
        self.assertTrue(
            self.reservation.reservation_agreement.title.startswith("Sales Agreement")
        )
        self.assertTrue(
            self.reservation.allocation_letter.title.startswith("Allocation Letter")
        )

        invoice = Invoice.objects.filter(
            organization=self.org,
            notes__icontains=f"[CRM_DEAL_LINK:{deal.id}]",
        ).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal("14500000.00"))

        payment_plan = PaymentPlan.objects.filter(
            organization=self.org,
            notes__icontains=f"[CRM_DEAL_PAYMENT_PLAN:{deal.id}]",
        ).first()
        self.assertIsNotNone(payment_plan)
        self.assertEqual(payment_plan.direction, PaymentPlan.Direction.RECEIVABLE)
        self.assertEqual(payment_plan.total_amount, Decimal("14500000.00"))
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.payment_plan_id, payment_plan.id)

        installment = PaymentInstallment.objects.filter(
            payment_plan=payment_plan,
            installment_number=1,
        ).first()
        self.assertIsNotNone(installment)
        self.assertEqual(installment.amount, Decimal("14500000.00"))

        journal = JournalEntry.objects.filter(
            organization=self.org,
            description__icontains=f"[CRM_DEAL_LEDGER:{deal.id}]",
        ).first()
        self.assertIsNotNone(journal)
        self.assertEqual(journal.status, JournalEntry.Status.POSTED)
        self.assertEqual(journal.ledger_entries.count(), 2)

        commission = BrokerCommissionEarning.objects.filter(
            broker=self.broker,
            lead=self.lead,
            trigger_stage="closed",
            notes__icontains=f"[CRM_DEAL_COMMISSION:{deal.id}:closed]",
        ).first()
        self.assertIsNotNone(commission)
        self.assertGreater(commission.total_commission, Decimal("0.00"))
        self.assertEqual(commission.status, BrokerCommissionEarning.Status.PENDING)
        expected_hr_commission = (
            commission.total_commission - commission.bonus_amount
        ).quantize(Decimal("0.01"))
        expected_hr_incentive = commission.bonus_amount.quantize(Decimal("0.01"))

        hr_commission = Bonus.objects.filter(
            organization=self.org,
            employee=self.broker_employee,
            reason__icontains=f"[CRM_DEAL_HR_COMMISSION:{deal.id}]",
        ).first()
        self.assertIsNotNone(hr_commission)
        self.assertEqual(hr_commission.amount, expected_hr_commission)
        self.assertEqual(hr_commission.status, Bonus.Status.PENDING)

        hr_incentive = Bonus.objects.filter(
            organization=self.org,
            employee=self.broker_employee,
            reason__icontains=f"[CRM_DEAL_HR_BONUS:{deal.id}]",
        ).first()
        self.assertIsNotNone(hr_incentive)
        self.assertEqual(hr_incentive.amount, expected_hr_incentive)
        self.assertEqual(hr_incentive.status, Bonus.Status.PENDING)

        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.FORM_GENERATED,
                metadata__automation="deal_closed_won_sales_agreement_generation",
            ).exists()
        )
        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.FORM_GENERATED,
                metadata__automation="deal_closed_won_allocation_letter_generation",
            ).exists()
        )
        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.NOTE_ADDED,
                metadata__automation="deal_closed_won_payment_schedule_creation",
            ).exists()
        )
        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.NOTE_ADDED,
                metadata__automation="deal_closed_won_customer_ledger_posted",
            ).exists()
        )
        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.UNIT_TRANSFERRED,
                metadata__automation="deal_closed_won_property_status",
            ).exists()
        )
        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.NOTE_ADDED,
                metadata__automation="deal_closed_won_hr_rewards_sync",
            ).exists()
        )

        event_keys = [kwargs.get("event_key") for _, kwargs in mock_dispatch.call_args_list]
        self.assertIn("crm_broker_commission_ready_for_finance", event_keys)
        self.assertIn("crm_broker_target_hit_incentive", event_keys)

        repeat = self.client.patch(
            f"/api/crm/opportunities/{deal.id}/",
            patch_payload,
            format="json",
        )
        self.assertEqual(repeat.status_code, status.HTTP_200_OK, repeat.data)
        self.assertEqual(
            BrokerCommissionEarning.objects.filter(
                broker=self.broker,
                lead=self.lead,
                trigger_stage="closed",
                notes__icontains=f"[CRM_DEAL_COMMISSION:{deal.id}:closed]",
            ).count(),
            1,
        )
        self.assertEqual(
            Bonus.objects.filter(
                organization=self.org,
                employee=self.broker_employee,
                reason__icontains=f"[CRM_DEAL_HR_COMMISSION:{deal.id}]",
            ).count(),
            1,
        )
        self.assertEqual(
            Bonus.objects.filter(
                organization=self.org,
                employee=self.broker_employee,
                reason__icontains=f"[CRM_DEAL_HR_BONUS:{deal.id}]",
            ).count(),
            1,
        )

    def test_closed_won_blocked_when_kyc_is_not_verified(self):
        deal = self._create_opportunity()
        self.contact.kyc_status = ContactAccount.KYCStatus.NOT_SUBMITTED
        self.contact.save(update_fields=["kyc_status", "updated_at"])

        res = self.client.patch(
            f"/api/crm/opportunities/{deal.id}/",
            {
                "stage": "Closed Won",
                "status": "won",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, res.data)
        self.assertIn("KYC verification is required", str(res.data))

        self.contact.kyc_status = ContactAccount.KYCStatus.VERIFIED
        self.contact.save(update_fields=["kyc_status", "updated_at"])
        allowed = self.client.patch(
            f"/api/crm/opportunities/{deal.id}/",
            {
                "stage": "Closed Won",
                "status": "won",
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)

    def test_closed_lost_releases_reserved_unit_inventory(self):
        deal = self._create_opportunity()

        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, Unit.UnitStatus.RESERVED)

        res = self.client.patch(
            f"/api/crm/opportunities/{deal.id}/",
            {
                "stage": "Closed Lost",
                "status": "lost",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        self.unit.refresh_from_db()
        self.assertEqual(self.unit.status, Unit.UnitStatus.AVAILABLE)

        inventory = PropertyInventory.objects.get(unit=self.unit)
        self.assertEqual(inventory.status, PropertyInventory.InventoryStatus.AVAILABLE)
        self.assertIsNone(inventory.reservation_id)

        self.assertTrue(
            ReservationEvent.objects.filter(
                reservation=self.reservation,
                event_type=ReservationEvent.EventType.NOTE_ADDED,
                metadata__automation="deal_lost_release_unit",
            ).exists()
        )

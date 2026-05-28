from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from auditlog.context import disable_auditlog
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.finance.models import Customer, Invoice, InvoicePayment
from apps.properties.models import Property, Unit, WorkOrder
from apps.support_desk.whatsapp_providers import WhatsAppDispatchResult
from apps.tenants.models import TenantCommunicationLog, TenantProfile

User = get_user_model()


class TenantDashboardOverviewApiTests(APITestCase):
    def setUp(self):
        today = timezone.localdate()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
        current_month_end = next_month_start - timedelta(days=1)
        current_month_due_date = min(today + timedelta(days=7), current_month_end)

        with disable_auditlog():
            self.org = Organization.objects.create(name="Tenant Dashboard Org")

        self.user = User.objects.create_superuser(
            username="tenant-admin@example.com",
            email="tenant-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        self.client.force_authenticate(self.user)

        self.property_lagos = Property.objects.create(
            organization=self.org,
            name="Civic Tower Lagos",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="12 Ozumba Mbadiwe, Lagos",
        )
        self.property_abuja = Property.objects.create(
            organization=self.org,
            name="Summit Plaza Abuja",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="4 Adetokunbo Ademola Crescent, Abuja",
        )

        self.unit_a101 = Unit.objects.create(
            organization=self.org,
            property=self.property_lagos,
            unit_number="A-101",
            floor=1,
            area_sqft=420,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.LEASED,
        )
        self.unit_a102 = Unit.objects.create(
            organization=self.org,
            property=self.property_lagos,
            unit_number="A-102",
            floor=1,
            area_sqft=430,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.LEASED,
        )
        self.unit_b201 = Unit.objects.create(
            organization=self.org,
            property=self.property_abuja,
            unit_number="B-201",
            floor=2,
            area_sqft=480,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.unit_b202 = Unit.objects.create(
            organization=self.org,
            property=self.property_abuja,
            unit_number="B-202",
            floor=2,
            area_sqft=500,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )

        self.customer_alpha = Customer.objects.create(
            organization=self.org,
            name="Alpha Advisory Limited",
            email="alpha@example.com",
        )
        self.customer_beta = Customer.objects.create(
            organization=self.org,
            name="Beta Logistics Limited",
            email="beta@example.com",
            phone="+2348012345678",
        )

        self.tenant_alpha = TenantProfile.objects.create(
            organization=self.org,
            customer=self.customer_alpha,
            property=self.property_lagos,
            unit=self.unit_a101,
            status=TenantProfile.Status.ACTIVE,
            display_name="Alpha Advisory Limited",
            lease_start_date=today - timedelta(days=180),
            lease_end_date=today + timedelta(days=180),
        )
        self.tenant_beta = TenantProfile.objects.create(
            organization=self.org,
            customer=self.customer_beta,
            property=self.property_lagos,
            unit=self.unit_a102,
            status=TenantProfile.Status.ACTIVE,
            display_name="Beta Logistics Limited",
            lease_start_date=today - timedelta(days=90),
            lease_end_date=today + timedelta(days=30),
            move_out_date=today + timedelta(days=21),
            notes="Tenant asked for a revised payment plan after an AC repair complaint.",
        )

        TenantCommunicationLog.objects.create(
            organization=self.org,
            tenant_profile=self.tenant_beta,
            author=self.user,
            interaction_type=TenantCommunicationLog.InteractionType.PHONE,
            channel=TenantCommunicationLog.Channel.PHONE,
            direction=TenantCommunicationLog.Direction.OUTBOUND,
            status=TenantCommunicationLog.Status.RECORDED,
            subject="AC repair follow-up",
            message="Called regarding AC repair on March 15 and discussed arrears recovery.",
        )

        Invoice.objects.create(
            organization=self.org,
            customer=self.customer_beta,
            property=self.property_lagos,
            status=Invoice.Status.OVERDUE,
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=20),
            subtotal=Decimal("450000.00"),
            total_amount=Decimal("450000.00"),
        )
        Invoice.objects.create(
            organization=self.org,
            customer=self.customer_beta,
            property=self.property_lagos,
            status=Invoice.Status.OVERDUE,
            issue_date=today - timedelta(days=70),
            due_date=today - timedelta(days=45),
            subtotal=Decimal("80000.00"),
            total_amount=Decimal("80000.00"),
        )
        Invoice.objects.create(
            organization=self.org,
            customer=self.customer_beta,
            property=self.property_lagos,
            status=Invoice.Status.OVERDUE,
            issue_date=today - timedelta(days=100),
            due_date=today - timedelta(days=75),
            subtotal=Decimal("150000.00"),
            total_amount=Decimal("150000.00"),
        )
        Invoice.objects.create(
            organization=self.org,
            customer=self.customer_beta,
            property=self.property_lagos,
            status=Invoice.Status.OVERDUE,
            issue_date=today - timedelta(days=140),
            due_date=today - timedelta(days=120),
            subtotal=Decimal("250000.00"),
            total_amount=Decimal("250000.00"),
        )
        current_month_invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer_alpha,
            property=self.property_lagos,
            status=Invoice.Status.SENT,
            issue_date=month_start,
            due_date=current_month_due_date,
            subtotal=Decimal("900000.00"),
            total_amount=Decimal("900000.00"),
        )

        InvoicePayment.objects.create(
            invoice=current_month_invoice,
            amount=Decimal("900000.00"),
            payment_date=today,
        )
        older_invoice_one = Invoice.objects.create(
            organization=self.org,
            customer=self.customer_alpha,
            property=self.property_lagos,
            status=Invoice.Status.PAID,
            issue_date=today - timedelta(days=65),
            due_date=today - timedelta(days=58),
            subtotal=Decimal("300000.00"),
            total_amount=Decimal("300000.00"),
        )
        InvoicePayment.objects.create(
            invoice=older_invoice_one,
            amount=Decimal("300000.00"),
            payment_date=today - timedelta(days=60),
        )
        older_invoice_two = Invoice.objects.create(
            organization=self.org,
            customer=self.customer_alpha,
            property=self.property_lagos,
            status=Invoice.Status.PAID,
            issue_date=today - timedelta(days=145),
            due_date=today - timedelta(days=138),
            subtotal=Decimal("200000.00"),
            total_amount=Decimal("200000.00"),
        )
        InvoicePayment.objects.create(
            invoice=older_invoice_two,
            amount=Decimal("200000.00"),
            payment_date=today - timedelta(days=140),
        )

        WorkOrder.objects.create(
            organization=self.org,
            property=self.property_abuja,
            unit=self.unit_b201,
            title="Electrical panel review",
            category=WorkOrder.Category.ELECTRICAL,
            priority=WorkOrder.Priority.HIGH,
            status=WorkOrder.Status.OPEN,
        )
        WorkOrder.objects.create(
            organization=self.org,
            property=self.property_lagos,
            unit=self.unit_a101,
            title="HVAC maintenance closeout",
            category=WorkOrder.Category.HVAC,
            priority=WorkOrder.Priority.MEDIUM,
            status=WorkOrder.Status.VERIFIED,
            completed_date=today - timedelta(days=14),
            actual_cost=Decimal("150000.00"),
        )
        WorkOrder.objects.create(
            organization=self.org,
            property=self.property_abuja,
            unit=self.unit_b201,
            title="Electrical repair closeout",
            category=WorkOrder.Category.ELECTRICAL,
            priority=WorkOrder.Priority.HIGH,
            status=WorkOrder.Status.COMPLETED,
            completed_date=today - timedelta(days=45),
            actual_cost=Decimal("40000.00"),
        )

    def test_dashboard_overview_returns_portfolio_health_metrics(self):
        response = self.client.get("/api/tenants/dashboard/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["portfolio_scope"]["properties_count"], 2)
        self.assertEqual(response.data["portfolio_scope"]["active_tenants"], 2)
        self.assertEqual(response.data["portfolio_scope"]["total_units"], 4)

        self.assertEqual(response.data["occupancy"]["occupied_units"], 2)
        self.assertEqual(response.data["occupancy"]["total_units"], 4)
        self.assertEqual(response.data["occupancy"]["rate"], 50.0)

        self.assertEqual(response.data["arrears"]["total"], "930000.00")
        self.assertEqual(response.data["arrears"]["overdue_invoices"], 4)
        self.assertEqual(response.data["arrears"]["customers_in_arrears"], 1)

        self.assertEqual(response.data["monthly_revenue"]["collections_total"], "900000.00")
        self.assertEqual(response.data["monthly_revenue"]["target_total"], "900000.00")
        self.assertEqual(response.data["monthly_revenue"]["attainment_pct"], 100.0)

        self.assertEqual(response.data["maintenance"]["open_work_orders"], 1)
        self.assertEqual(response.data["maintenance"]["urgent_open_work_orders"], 1)

        self.assertEqual(response.data["lease_expirations"]["count"], 1)
        self.assertEqual(response.data["lease_expirations"]["window_days"], 90)
        self.assertEqual(
            response.data["lease_expirations"]["soonest_date"],
            (timezone.localdate() + timedelta(days=30)).isoformat(),
        )

    def test_dashboard_layout_returns_master_list_and_occupancy_grid(self):
        response = self.client.get("/api/tenants/dashboard/layout/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["master_list"]), 2)

        overdue_row = response.data["master_list"][0]
        self.assertEqual(overdue_row["tenant_name"], "Beta Logistics Limited")
        self.assertEqual(overdue_row["unit_label"], "A-102")
        self.assertEqual(overdue_row["property_name"], "Civic Tower Lagos")
        self.assertEqual(overdue_row["balance"], "930000.00")
        self.assertEqual(overdue_row["status_key"], "overdue")
        self.assertEqual(overdue_row["status_label"], "Overdue")
        self.assertEqual(overdue_row["property_location"], "Lagos")
        self.assertEqual(overdue_row["tenancy_type_key"], "commercial")
        self.assertEqual(overdue_row["debt_status_key"], "overdue")

        active_row = response.data["master_list"][1]
        self.assertEqual(active_row["tenant_name"], "Alpha Advisory Limited")
        self.assertEqual(active_row["balance"], "0.00")
        self.assertEqual(active_row["status_key"], "active")
        self.assertEqual(active_row["property_location"], "Lagos")
        self.assertEqual(active_row["tenancy_type_key"], "commercial")
        self.assertEqual(active_row["debt_status_key"], "clear")
        self.assertEqual(response.data["filters"]["property_locations"], ["Lagos"])

        totals = response.data["occupancy_vacancy"]["totals"]
        self.assertEqual(totals["occupied"], 1)
        self.assertEqual(totals["notice_given"], 1)
        self.assertEqual(totals["under_maintenance"], 1)
        self.assertEqual(totals["vacant_ready"], 1)

        properties = {row["property_name"]: row for row in response.data["occupancy_vacancy"]["properties"]}
        self.assertEqual(properties["Civic Tower Lagos"]["totals"]["occupied"], 1)
        self.assertEqual(properties["Civic Tower Lagos"]["totals"]["notice_given"], 1)
        self.assertEqual(properties["Summit Plaza Abuja"]["totals"]["under_maintenance"], 1)
        self.assertEqual(properties["Summit Plaza Abuja"]["totals"]["vacant_ready"], 1)
        lagos_notice_unit = next(
            unit
            for unit in properties["Civic Tower Lagos"]["units"]
            if unit["unit_number"] == "A-102"
        )
        self.assertEqual(lagos_notice_unit["tenant_profile_id"], self.tenant_beta.id)

    def test_tenant_intelligence_returns_score_timeline_and_logs(self):
        response = self.client.get(f"/api/tenants/profiles/{self.tenant_beta.id}/intelligence/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["tenant"]["id"], self.tenant_beta.id)
        self.assertEqual(response.data["tenant"]["name"], "Beta Logistics Limited")
        self.assertEqual(response.data["tenant"]["property_name"], "Civic Tower Lagos")
        self.assertEqual(response.data["payment_reliability"]["score"], 2)
        self.assertEqual(response.data["payment_reliability"]["overdue_invoices"], 4)
        self.assertEqual(response.data["payment_reliability"]["overdue_balance"], "930000.00")
        self.assertEqual(response.data["lease_timeline"]["status_label"], "Active")
        self.assertGreaterEqual(len(response.data["communication_log"]), 2)
        self.assertTrue(response.data["quick_actions"]["can_generate_invoice"])
        self.assertTrue(response.data["quick_actions"]["can_send_payment_reminder"])
        self.assertTrue(response.data["quick_actions"]["can_initiate_eviction_notice"])

    def test_tenant_revenue_analytics_returns_collections_aging_and_expense_comparison(self):
        response = self.client.get("/api/tenants/dashboard/revenue-analytics/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["collection_trend"]["months"]), 6)
        self.assertEqual(response.data["collection_trend"]["total_collections"], "1400000.00")
        self.assertEqual(response.data["collection_trend"]["peak_collections"], "900000.00")

        self.assertEqual(response.data["aging_buckets"]["total_overdue"], "930000.00")
        self.assertEqual(response.data["aging_buckets"]["overdue_invoices"], 4)
        buckets = {bucket["key"]: bucket for bucket in response.data["aging_buckets"]["buckets"]}
        self.assertEqual(buckets["current"]["total"], "450000.00")
        self.assertEqual(buckets["overdue_30"]["total"], "80000.00")
        self.assertEqual(buckets["overdue_60"]["total"], "150000.00")
        self.assertEqual(buckets["overdue_90"]["total"], "250000.00")

        self.assertEqual(response.data["expense_vs_income"]["rent_collected_total"], "1400000.00")
        self.assertEqual(response.data["expense_vs_income"]["maintenance_cost_total"], "190000.00")
        self.assertEqual(response.data["expense_vs_income"]["net_operating_total"], "1210000.00")
        properties = {
            row["property_name"]: row
            for row in response.data["expense_vs_income"]["property_breakdown"]
        }
        self.assertEqual(properties["Civic Tower Lagos"]["income_collected"], "1400000.00")
        self.assertEqual(properties["Civic Tower Lagos"]["maintenance_cost"], "150000.00")
        self.assertEqual(properties["Summit Plaza Abuja"]["income_collected"], "0.00")
        self.assertEqual(properties["Summit Plaza Abuja"]["maintenance_cost"], "40000.00")

    @patch("apps.tenants.views.get_whatsapp_provider_adapter")
    @patch("apps.tenants.views.send_mail")
    def test_tenant_quick_actions_generate_invoice_reminder_and_eviction_notice(
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
            provider_message_id="mock-tenant-reminder",
            payload={"status": "queued"},
        )

        invoice_response = self.client.post(
            f"/api/tenants/profiles/{self.tenant_beta.id}/generate-invoice/",
            {},
            format="json",
        )
        self.assertEqual(invoice_response.status_code, status.HTTP_200_OK, invoice_response.data)
        self.assertEqual(invoice_response.data["invoice"]["total_amount"], "450000.00")
        self.assertTrue(
            TenantCommunicationLog.objects.filter(
                tenant_profile=self.tenant_beta,
                interaction_type=TenantCommunicationLog.InteractionType.INVOICE_GENERATED,
            ).exists()
        )

        reminder_response = self.client.post(
            f"/api/tenants/profiles/{self.tenant_beta.id}/send-payment-reminder/",
            {},
            format="json",
        )
        self.assertEqual(reminder_response.status_code, status.HTTP_200_OK, reminder_response.data)
        self.assertIn("Email", reminder_response.data["detail"])
        self.assertIn("WhatsApp", reminder_response.data["detail"])
        mocked_send_mail.assert_called()
        mocked_adapter.send_message.assert_called_once()

        eviction_response = self.client.post(
            f"/api/tenants/profiles/{self.tenant_beta.id}/initiate-eviction-notice/",
            {},
            format="json",
        )
        self.assertEqual(eviction_response.status_code, status.HTTP_200_OK, eviction_response.data)
        self.tenant_beta.refresh_from_db()
        self.assertEqual(eviction_response.data["notice_date"], self.tenant_beta.move_out_date.isoformat())
        self.assertTrue(
            TenantCommunicationLog.objects.filter(
                tenant_profile=self.tenant_beta,
                interaction_type=TenantCommunicationLog.InteractionType.EVICTION_NOTICE,
            ).exists()
        )

    @patch("apps.tenants.views.get_whatsapp_provider_adapter")
    @patch("apps.tenants.views.send_mail")
    def test_bulk_admin_actions_generate_service_charge_invoices_and_holiday_announcements(
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
            provider_message_id="mock-holiday",
            payload={"status": "queued"},
        )

        invoice_response = self.client.post(
            "/api/tenants/profiles/bulk-service-charge/",
            {
                "tenant_ids": [self.tenant_alpha.id, self.tenant_beta.id],
                "amount": "125000.00",
                "description": "Q2 service charge",
                "due_in_days": 10,
                "send_notifications": True,
            },
            format="json",
        )
        self.assertEqual(invoice_response.status_code, status.HTTP_200_OK, invoice_response.data)
        self.assertEqual(invoice_response.data["generated_count"], 2)
        self.assertEqual(invoice_response.data["notification_count"], 2)
        self.assertTrue(
            Invoice.objects.filter(
                organization=self.org,
                customer=self.customer_alpha,
                status=Invoice.Status.SENT,
                total_amount=Decimal("125000.00"),
            ).exists()
        )

        holiday_response = self.client.post(
            "/api/tenants/profiles/bulk-holiday-announcement/",
            {
                "tenant_ids": [self.tenant_alpha.id, self.tenant_beta.id],
                "subject": "Eid public holiday",
                "message": "Our offices will operate on a reduced schedule during the holiday period.",
                "delivery_mode": "all_available",
            },
            format="json",
        )
        self.assertEqual(holiday_response.status_code, status.HTTP_200_OK, holiday_response.data)
        self.assertEqual(holiday_response.data["delivery_count"], 3)
        self.assertEqual(holiday_response.data["successful_dispatches"], 3)
        self.assertGreaterEqual(
            TenantCommunicationLog.objects.filter(
                tenant_profile__in=[self.tenant_alpha, self.tenant_beta],
                metadata__bulk_action="holiday_announcement",
            ).count(),
            3,
        )

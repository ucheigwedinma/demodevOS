from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.models import Facility, UtilityBill, UtilityConsumption, UtilityMeter, UtilityMeterReading
from apps.facility_management.tasks import run_scheduled_utility_energy_workflows
from apps.finance.models import Bill
from apps.procurement.models import Vendor
from apps.properties.models import Property

User = get_user_model()


class FacilityUtilitiesApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Utility Automation Org")
        self.user = User.objects.create_superuser(
            username="utility-admin@example.com",
            email="utility-admin@example.com",
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
            name="Civic Plaza",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="5 Marina Boulevard, Lagos",
            total_area_sqft=Decimal("12000.00"),
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-CIV-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.vendor = Vendor.objects.create(
            organization=self.org,
            name="Gridline Utilities Limited",
            category=Vendor.Category.OTHER,
            is_active=True,
        )

    def _dt(self, days_offset: int, hour: int = 9) -> datetime:
        target = timezone.now() + timedelta(days=days_offset)
        return target.replace(hour=hour, minute=0, second=0, microsecond=0)

    def _create_meter(self, meter_number: str = "ELEC-001") -> UtilityMeter:
        response = self.client.post(
            "/api/facility-management/utilities/meters/",
            {
                "facility": self.facility.id,
                "vendor": self.vendor.id,
                "meter_number": meter_number,
                "utility_type": UtilityMeter.UtilityType.ELECTRICITY,
                "location_label": "Main incomer room",
                "is_smart_meter": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return UtilityMeter.objects.get(meter_number=meter_number)

    def _log_reading(self, meter: UtilityMeter, *, when: datetime, value: str):
        response = self.client.post(
            "/api/facility-management/utilities/readings/",
            {
                "meter": meter.id,
                "reading_at": when.isoformat(),
                "reading_value": value,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_meter_reading_flow_derives_consumption_and_flags_spike(self):
        meter = self._create_meter()

        self.assertEqual(meter.provider_name, self.vendor.name)
        self.assertEqual(meter.unit_of_measure, "kWh")

        self._log_reading(meter, when=self._dt(-3), value="100.000")
        self._log_reading(meter, when=self._dt(-2), value="150.000")
        self._log_reading(meter, when=self._dt(-1), value="400.000")

        readings = list(UtilityMeterReading.objects.filter(meter=meter).order_by("reading_at", "id"))
        self.assertEqual(readings[0].consumption_delta, Decimal("0.000"))
        self.assertEqual(readings[1].consumption_delta, Decimal("50.000"))
        self.assertEqual(readings[2].consumption_delta, Decimal("250.000"))
        self.assertTrue(readings[2].is_anomaly)
        self.assertIn("spike", readings[2].anomaly_reason.lower())

        day_two_row = UtilityConsumption.objects.get(
            organization=self.org,
            property=self.property,
            reading_date=timezone.localdate(self._dt(-2)),
        )
        day_three_row = UtilityConsumption.objects.get(
            organization=self.org,
            property=self.property,
            reading_date=timezone.localdate(self._dt(-1)),
        )
        self.assertEqual(day_two_row.electricity_kwh, Decimal("50.00"))
        self.assertEqual(day_three_row.electricity_kwh, Decimal("250.00"))

    def test_utility_bill_create_derives_usage_and_syncs_finance_bill(self):
        meter = self._create_meter("ELEC-002")
        self._log_reading(meter, when=self._dt(-5), value="100.000")
        self._log_reading(meter, when=self._dt(-4), value="160.000")
        self._log_reading(meter, when=self._dt(-3), value="230.000")

        response = self.client.post(
            "/api/facility-management/utilities/bills/",
            {
                "facility": self.facility.id,
                "meter": meter.id,
                "vendor": self.vendor.id,
                "bill_number": "UTIL-0001",
                "billing_period_start": timezone.localdate(self._dt(-4)).isoformat(),
                "billing_period_end": timezone.localdate(self._dt(-3)).isoformat(),
                "issue_date": timezone.localdate(self._dt(-2)).isoformat(),
                "due_date": timezone.localdate(self._dt(7)).isoformat(),
                "unit_rate": "10.00",
                "tax_amount": "5.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        utility_bill = UtilityBill.objects.get(bill_number="UTIL-0001")
        self.assertEqual(utility_bill.usage_quantity, Decimal("130.000"))
        self.assertEqual(utility_bill.subtotal, Decimal("1300.00"))
        self.assertEqual(utility_bill.total_amount, Decimal("1305.00"))
        self.assertEqual(utility_bill.provider_name, self.vendor.name)
        self.assertEqual(utility_bill.status, UtilityBill.Status.ISSUED)
        self.assertIsNotNone(utility_bill.finance_bill_id)

        finance_bill = utility_bill.finance_bill
        self.assertEqual(finance_bill.vendor_id, self.vendor.id)
        self.assertEqual(finance_bill.property_id, self.property.id)
        self.assertEqual(finance_bill.total_amount, Decimal("1305.00"))
        self.assertEqual(finance_bill.status, Bill.Status.APPROVED)

    def test_overview_returns_analytics_and_sustainability_metrics(self):
        meter = self._create_meter("ELEC-003")
        self._log_reading(meter, when=self._dt(-4), value="50.000")
        self._log_reading(meter, when=self._dt(-3), value="95.000")
        self._log_reading(meter, when=self._dt(-2), value="160.000")

        UtilityBill.objects.create(
            organization=self.org,
            property=self.property,
            meter=meter,
            vendor=self.vendor,
            provider_name=self.vendor.name,
            utility_type=UtilityMeter.UtilityType.ELECTRICITY,
            bill_number="UTIL-OVD-01",
            billing_period_start=timezone.localdate(self._dt(-10)),
            billing_period_end=timezone.localdate(self._dt(-2)),
            issue_date=timezone.localdate(self._dt(-2)),
            due_date=timezone.localdate(self._dt(-1)),
            usage_quantity=Decimal("110.000"),
            unit_rate=Decimal("9.50"),
            subtotal=Decimal("1045.00"),
            total_amount=Decimal("1045.00"),
            status=UtilityBill.Status.OVERDUE,
        )

        response = self.client.get("/api/facility-management/utilities/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["active_meters"], 1)
        self.assertEqual(response.data["kpis"]["overdue_bills"], 1)
        self.assertEqual(response.data["kpis"]["readings_logged_30d"], 3)
        self.assertGreater(float(response.data["kpis"]["carbon_kg_co2e_30d"]), 0)
        self.assertGreaterEqual(response.data["kpis"]["sustainability_score"], 0)
        self.assertEqual(response.data["meter_type_breakdown"][0]["utility_type"], UtilityMeter.UtilityType.ELECTRICITY)
        self.assertEqual(len(response.data["recent_readings_watchlist"]), 3)
        self.assertEqual(len(response.data["overdue_bill_watchlist"]), 1)

    def test_scheduled_task_runs_utility_energy_automation(self):
        meter = UtilityMeter.objects.create(
            organization=self.org,
            property=self.property,
            vendor=self.vendor,
            meter_number="ELEC-004",
            utility_type=UtilityMeter.UtilityType.ELECTRICITY,
            is_smart_meter=True,
        )
        UtilityMeterReading.objects.create(
            organization=self.org,
            meter=meter,
            reading_at=self._dt(-3),
            reading_date=timezone.localdate(self._dt(-3)),
            reading_value=Decimal("75.000"),
            entered_by=self.user,
        )
        UtilityMeterReading.objects.create(
            organization=self.org,
            meter=meter,
            reading_at=self._dt(-2),
            reading_date=timezone.localdate(self._dt(-2)),
            reading_value=Decimal("130.000"),
            entered_by=self.user,
        )
        utility_bill = UtilityBill.objects.create(
            organization=self.org,
            property=self.property,
            meter=meter,
            vendor=self.vendor,
            utility_type=UtilityMeter.UtilityType.ELECTRICITY,
            bill_number="UTIL-TASK-01",
            billing_period_start=timezone.localdate(self._dt(-3)),
            billing_period_end=timezone.localdate(self._dt(-2)),
            issue_date=timezone.localdate(self._dt(-1)),
            due_date=timezone.localdate(self._dt(-1)),
            unit_rate=Decimal("8.00"),
            tax_amount=Decimal("10.00"),
        )

        summary = run_scheduled_utility_energy_workflows([self.org.id])

        self.assertEqual(summary["organizations_processed"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertGreaterEqual(summary["meters_synced"], 1)
        self.assertGreaterEqual(summary["readings_synced"], 1)
        self.assertGreaterEqual(summary["consumption_days_synced"], 1)
        self.assertGreaterEqual(summary["finance_bills_synced"], 1)
        self.assertGreaterEqual(summary["overdue_bills"], 1)

        meter.refresh_from_db()
        utility_bill.refresh_from_db()
        latest_reading = UtilityMeterReading.objects.filter(meter=meter).order_by("-reading_at", "-id").first()
        self.assertEqual(meter.provider_name, self.vendor.name)
        self.assertEqual(meter.unit_of_measure, "kWh")
        self.assertEqual(meter.last_reading_at, latest_reading.reading_at)
        self.assertEqual(latest_reading.consumption_delta, Decimal("55.000"))
        self.assertEqual(utility_bill.usage_quantity, Decimal("55.000"))
        self.assertEqual(utility_bill.subtotal, Decimal("440.00"))
        self.assertEqual(utility_bill.total_amount, Decimal("450.00"))
        self.assertEqual(utility_bill.status, UtilityBill.Status.OVERDUE)
        self.assertIsNotNone(utility_bill.finance_bill_id)

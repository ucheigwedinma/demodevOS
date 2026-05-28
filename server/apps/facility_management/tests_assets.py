from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone
from apps.finance.models import Account, AccountSubType, AccountType, JournalEntry, JournalSourceType
from apps.properties.asset_workflows import sync_asset_workflows
from apps.properties.models import AssetComponent, MaintenanceVendor, PreventiveSchedule, Property, Unit

User = get_user_model()


def ensure_depreciation_accounts(org):
    Account.objects.update_or_create(
        organization=org,
        code="5400",
        defaults={
            "name": "Depreciation Expense",
            "account_type": AccountType.EXPENSE,
            "sub_type": AccountSubType.OPERATING_EXPENSE,
            "is_active": True,
        },
    )
    Account.objects.update_or_create(
        organization=org,
        code="1530",
        defaults={
            "name": "Accumulated Depreciation",
            "account_type": AccountType.ASSET,
            "sub_type": AccountSubType.FIXED_ASSET,
            "is_active": True,
        },
    )


class FacilityAssetApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Facility Asset Org")
        self.user = User.objects.create_superuser(
            username="facility-assets-admin@example.com",
            email="facility-assets-admin@example.com",
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
            name="Atlantic Operations Hub",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="22 Marina Road, Lagos",
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="RM-101",
            floor=1,
            area_sqft=420,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-AOH-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Plant Level",
            floor_code="PL",
            floor_number=1,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="Mechanical Zone",
            zone_code="MZ-01",
            zone_type=FacilityZone.ZoneType.SERVICE,
        )
        self.space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit,
            space_label="Generator Room A",
        )

        self.vendor = MaintenanceVendor.objects.create(
            organization=self.org,
            name="Prime Mechanical Services",
            specialization=MaintenanceVendor.Specialization.GENERATOR,
        )
        self.amc_vendor = MaintenanceVendor.objects.create(
            organization=self.org,
            name="Atlas Asset Care",
            specialization=MaintenanceVendor.Specialization.GENERAL,
        )

        ensure_depreciation_accounts(self.org)

    def test_asset_create_automates_location_schedule_and_depreciation_journal(self):
        payload = {
            "facility": self.facility.id,
            "facility_space": self.space.id,
            "vendor": self.vendor.id,
            "amc_vendor": self.amc_vendor.id,
            "name": "Backup Generator A",
            "component_id": "AST-GEN-001",
            "category": AssetComponent.Category.GENERATOR,
            "lifecycle_stage": AssetComponent.LifecycleStage.OPERATE,
            "condition_rating": AssetComponent.ConditionRating.GOOD,
            "serial_number": "GEN-SN-1001",
            "manufacturer": "Cummins",
            "model_number": "C220D5",
            "commissioned_date": "2026-01-15",
            "maintenance_frequency": "monthly",
            "auto_schedule_maintenance": True,
            "expected_useful_life_years": 10,
            "acquisition_cost": "120000.00",
            "salvage_value": "0.00",
            "depreciation_enabled": True,
            "depreciation_method": AssetComponent.DepreciationMethod.STRAIGHT_LINE,
            "depreciation_start_date": "2026-01-15",
            "amc_start_date": "2026-01-15",
            "amc_end_date": "2027-01-14",
            "amc_amount": "15000.00",
            "is_iot_enabled": True,
            "iot_device_id": "gen-room-a-sensor-01",
            "iot_status": AssetComponent.IoTStatus.CONNECTED,
        }

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/facility-management/assets/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        asset = AssetComponent.objects.get(component_id="AST-GEN-001")
        self.assertEqual(asset.property_id, self.property.id)
        self.assertEqual(asset.facility_id, self.facility.id)
        self.assertEqual(asset.unit_id, self.unit.id)
        self.assertEqual(asset.location_description, "Generator Room A")
        self.assertEqual(asset.maintenance_next_due_date.isoformat(), "2026-02-15")

        schedule = PreventiveSchedule.objects.get(asset_component=asset, auto_generated=True)
        self.assertEqual(schedule.property_id, self.property.id)
        self.assertEqual(schedule.vendor_id, self.amc_vendor.id)
        self.assertEqual(schedule.frequency, PreventiveSchedule.Frequency.MONTHLY)
        self.assertEqual(schedule.next_due_date.isoformat(), "2026-02-15")
        self.assertEqual(schedule.status, PreventiveSchedule.Status.ACTIVE)

        journal = JournalEntry.objects.get(
            organization=self.org,
            source_type=JournalSourceType.ADJUSTMENT,
            source_id=asset.id,
        )
        self.assertEqual(journal.status, JournalEntry.Status.DRAFT)
        self.assertTrue(journal.reference.startswith(f"ASSET-DEPR-{asset.id}-"))
        self.assertEqual(journal.lines.count(), 2)
        self.assertEqual(journal.lines.get(line_number=1).account.code, "5400")
        self.assertEqual(journal.lines.get(line_number=1).debit_amount, Decimal("1000.00"))
        self.assertEqual(journal.lines.get(line_number=2).account.code, "1530")
        self.assertEqual(journal.lines.get(line_number=2).credit_amount, Decimal("1000.00"))

    def test_asset_overview_returns_expected_kpis_and_watchlists(self):
        today = timezone.localdate()

        asset_one = AssetComponent.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            vendor=self.vendor,
            amc_vendor=self.amc_vendor,
            component_id="AST-HVAC-001",
            name="Main Chiller",
            category=AssetComponent.Category.HVAC,
            condition_rating=AssetComponent.ConditionRating.CRITICAL,
            lifecycle_stage=AssetComponent.LifecycleStage.MAINTAIN,
            serial_number="CH-001",
            manufacturer="Carrier",
            model_number="30XA",
            commissioned_date=today - timedelta(days=45),
            maintenance_frequency="monthly",
            maintenance_next_due_date=today + timedelta(days=7),
            warranty_expiry=today + timedelta(days=40),
            expected_useful_life_years=8,
            acquisition_cost="96000.00",
            salvage_value="0.00",
            depreciation_enabled=True,
            depreciation_start_date=today - timedelta(days=120),
            is_iot_enabled=True,
            iot_device_id="chiller-sensor-01",
            iot_status=AssetComponent.IoTStatus.CONNECTED,
        )
        asset_two = AssetComponent.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            vendor=self.vendor,
            amc_vendor=self.amc_vendor,
            component_id="AST-ELV-001",
            name="Passenger Lift 1",
            category=AssetComponent.Category.ELEVATOR,
            condition_rating=AssetComponent.ConditionRating.GOOD,
            lifecycle_stage=AssetComponent.LifecycleStage.OPERATE,
            serial_number="ELV-001",
            maintenance_frequency="monthly",
            maintenance_next_due_date=today - timedelta(days=2),
            amc_end_date=today + timedelta(days=25),
            is_iot_enabled=True,
            iot_device_id="lift-sensor-02",
            iot_status=AssetComponent.IoTStatus.OFFLINE,
        )

        sync_asset_workflows(asset_one.id)
        sync_asset_workflows(asset_two.id)

        response = self.client.get("/api/facility-management/assets/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["total_assets"], 2)
        self.assertEqual(response.data["kpis"]["active_assets"], 2)
        self.assertEqual(response.data["kpis"]["critical_assets"], 1)
        self.assertEqual(response.data["kpis"]["maintenance_due_30_days"], 2)
        self.assertEqual(response.data["kpis"]["warranty_expiring_90_days"], 1)
        self.assertEqual(response.data["kpis"]["amc_expiring_90_days"], 1)
        self.assertEqual(response.data["kpis"]["depreciating_assets"], 1)
        self.assertEqual(response.data["kpis"]["iot_connected_assets"], 1)
        self.assertEqual(response.data["depreciation"]["tracked_assets"], 1)
        self.assertEqual(response.data["depreciation"]["synced_this_month"], 1)
        self.assertEqual(response.data["iot"]["enabled"], 2)
        self.assertEqual(response.data["iot"]["connected"], 1)
        self.assertEqual(response.data["iot"]["offline"], 1)
        self.assertGreaterEqual(len(response.data["maintenance_watchlist"]), 2)
        self.assertEqual(len(response.data["warranty_watchlist"]), 1)
        self.assertEqual(len(response.data["amc_watchlist"]), 1)
        self.assertEqual(len(response.data["depreciation_watchlist"]), 1)


class FacilityAssetWorkflowTests(TestCase):
    def test_depreciation_sync_reuses_existing_draft_journal(self):
        org = Organization.objects.create(name="Facility Asset Sync Org")

        property_obj = Property.objects.create(
            organization=org,
            name="Operations Annex",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="17 Alfred Rewane Road, Ikoyi",
        )
        facility = Facility.objects.create(
            organization=org,
            property=property_obj,
            facility_code="FAC-OA-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
        )

        ensure_depreciation_accounts(org)

        asset = AssetComponent.objects.create(
            organization=org,
            property=property_obj,
            facility=facility,
            component_id="AST-PMP-001",
            name="Water Pump",
            category=AssetComponent.Category.WATER_SYSTEMS,
            condition_rating=AssetComponent.ConditionRating.GOOD,
            lifecycle_stage=AssetComponent.LifecycleStage.OPERATE,
            acquisition_cost="48000.00",
            salvage_value="0.00",
            depreciation_enabled=True,
            expected_useful_life_years=4,
            depreciation_start_date=timezone.localdate() - timedelta(days=90),
        )

        first = sync_asset_workflows(asset.id)
        second = sync_asset_workflows(asset.id)

        self.assertIsNotNone(first["journal_id"])
        self.assertEqual(first["journal_id"], second["journal_id"])
        self.assertEqual(
            JournalEntry.objects.filter(
                organization=org,
                source_type=JournalSourceType.ADJUSTMENT,
                source_id=asset.id,
            ).count(),
            1,
        )

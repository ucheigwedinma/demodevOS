from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone
from apps.facility_management.tasks import run_scheduled_maintenance_workflows
from apps.properties.asset_workflows import derive_maintenance_due_date
from apps.properties.models import (
    AssetComponent,
    MaintenanceVendor,
    PredictiveMaintenanceAlert,
    PredictiveMaintenanceRule,
    PreventiveSchedule,
    Property,
    Unit,
    WorkOrder,
)

User = get_user_model()


class FacilityMaintenanceApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Facility Maintenance Org")
        self.user = User.objects.create_superuser(
            username="facility-maintenance-admin@example.com",
            email="facility-maintenance-admin@example.com",
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
            name="Harbour Point Operations Centre",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="7 Commercial Avenue, Victoria Island",
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="RM-204",
            floor=2,
            area_sqft=365,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-HPO-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Operations Level",
            floor_code="OPS",
            floor_number=2,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="Mechanical Core",
            zone_code="MEC-02",
            zone_type=FacilityZone.ZoneType.SERVICE,
        )
        self.space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit,
            space_label="Switch Room 2B",
        )
        self.vendor = MaintenanceVendor.objects.create(
            organization=self.org,
            name="Atlas Facility Services",
            specialization=MaintenanceVendor.Specialization.GENERAL,
        )
        self.asset = AssetComponent.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            vendor=self.vendor,
            component_id="AST-HVAC-204",
            name="VRF Condensing Unit",
            category=AssetComponent.Category.HVAC,
            condition_rating=AssetComponent.ConditionRating.GOOD,
            maintenance_frequency="monthly",
            maintenance_next_due_date=timezone.localdate() + timedelta(days=7),
            is_iot_enabled=True,
            iot_device_id="vrf-204",
            iot_status=AssetComponent.IoTStatus.CONNECTED,
        )

    def test_work_order_create_derives_facility_context_and_sla(self):
        payload = {
            "facility_space": self.space.id,
            "asset_component": self.asset.id,
            "vendor": self.vendor.id,
            "title": "Restore cooling in switch room",
            "description": "Cooling dropped below threshold after compressor short-cycle alarm.",
            "category": WorkOrder.Category.HVAC,
            "priority": WorkOrder.Priority.MEDIUM,
            "status": WorkOrder.Status.OPEN,
            "assigned_to": "Musa Bello",
            "reported_by": "Control Room",
            "maintenance_mode": WorkOrder.MaintenanceMode.CORRECTIVE,
            "is_breakdown": True,
            "root_cause": "Compressor thermal overload trip",
        }

        response = self.client.post("/api/facility-management/maintenance/work-orders/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        work_order = WorkOrder.objects.get(title="Restore cooling in switch room")
        self.assertEqual(work_order.property_id, self.property.id)
        self.assertEqual(work_order.facility_id, self.facility.id)
        self.assertEqual(work_order.facility_space_id, self.space.id)
        self.assertEqual(work_order.unit_id, self.unit.id)
        self.assertEqual(work_order.status, WorkOrder.Status.ASSIGNED)
        self.assertEqual(work_order.maintenance_mode, WorkOrder.MaintenanceMode.CORRECTIVE)
        self.assertEqual(work_order.sla_target_hours, 24)
        self.assertIsNotNone(work_order.sla_due_at)
        self.assertIsNotNone(work_order.due_date)
        self.assertTrue(work_order.is_breakdown)
        self.assertEqual(work_order.root_cause, "Compressor thermal overload trip")

    def test_preventive_schedule_generates_work_order_and_rolls_forward_on_completion(self):
        today = timezone.localdate()
        schedule_payload = {
            "facility": self.facility.id,
            "facility_space": self.space.id,
            "asset_component": self.asset.id,
            "vendor": self.vendor.id,
            "title": "Monthly VRF service",
            "description": "Routine pressure check, filter cleaning, and control panel inspection.",
            "category": WorkOrder.Category.HVAC,
            "frequency": PreventiveSchedule.Frequency.MONTHLY,
            "priority": WorkOrder.Priority.MEDIUM,
            "assigned_to": "Ada Nwosu",
            "next_due_date": today.isoformat(),
            "generate_days_before": 0,
            "auto_create_work_orders": True,
            "status": PreventiveSchedule.Status.ACTIVE,
        }

        create_response = self.client.post("/api/facility-management/maintenance/preventive/", schedule_payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)

        sync_response = self.client.post("/api/facility-management/maintenance/sync/", {}, format="json")
        self.assertEqual(sync_response.status_code, status.HTTP_200_OK, sync_response.data)
        self.assertEqual(sync_response.data["preventive_work_orders_created"], 1)

        schedule = PreventiveSchedule.objects.get(title="Monthly VRF service")
        work_order = WorkOrder.objects.get(preventive_schedule=schedule)
        self.assertEqual(work_order.maintenance_mode, WorkOrder.MaintenanceMode.PREVENTIVE)
        self.assertEqual(work_order.facility_id, self.facility.id)
        self.assertEqual(schedule.last_work_order_id, work_order.id)

        with self.captureOnCommitCallbacks(execute=True):
            update_response = self.client.patch(
                f"/api/facility-management/maintenance/work-orders/{work_order.id}/",
                {"status": WorkOrder.Status.COMPLETED, "completed_date": today.isoformat()},
                format="json",
            )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK, update_response.data)

        schedule.refresh_from_db()
        self.assertEqual(schedule.last_completed_date, today)
        self.assertEqual(
            schedule.next_due_date,
            derive_maintenance_due_date(
                frequency=PreventiveSchedule.Frequency.MONTHLY,
                commissioned_date=today,
                installation_date=None,
                today=today,
            ),
        )

    def test_predictive_rule_evaluation_creates_alert_and_work_order(self):
        self.asset.iot_status = AssetComponent.IoTStatus.FAULT
        self.asset.save(update_fields=["iot_status", "updated_at"])

        rule_payload = {
            "asset_component": self.asset.id,
            "title": "VRF fault-state trigger",
            "description": "Raise an alert whenever the VRF controller reports a fault state.",
            "priority": WorkOrder.Priority.MEDIUM,
            "assigned_to": "Predictive Team",
            "alert_on_offline": False,
            "alert_on_fault": True,
            "auto_create_work_order": True,
            "is_active": True,
        }
        create_response = self.client.post("/api/facility-management/maintenance/predictive-rules/", rule_payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)

        rule = PredictiveMaintenanceRule.objects.get(title="VRF fault-state trigger")

        sync_response = self.client.post(
            "/api/facility-management/maintenance/sync/",
            {"rule_ids": [rule.id]},
            format="json",
        )
        self.assertEqual(sync_response.status_code, status.HTTP_200_OK, sync_response.data)
        self.assertEqual(sync_response.data["predictive_alerts_created"], 1)
        self.assertEqual(sync_response.data["predictive_work_orders_created"], 1)

        alert = PredictiveMaintenanceAlert.objects.get(rule=rule)
        self.assertEqual(alert.trigger_type, PredictiveMaintenanceAlert.TriggerType.IOT_FAULT)
        self.assertEqual(alert.status, PredictiveMaintenanceAlert.Status.WORK_ORDER_CREATED)
        self.assertIsNotNone(alert.work_order_id)
        self.assertEqual(alert.work_order.maintenance_mode, WorkOrder.MaintenanceMode.PREDICTIVE)
        self.assertEqual(alert.work_order.facility_id, self.facility.id)

    def test_overview_returns_maintenance_operating_snapshot(self):
        today = timezone.localdate()

        WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            asset_component=self.asset,
            title="Investigate chilled water leak",
            category=WorkOrder.Category.PLUMBING,
            priority=WorkOrder.Priority.HIGH,
            status=WorkOrder.Status.IN_PROGRESS,
            assigned_to="Team Alpha",
            maintenance_mode=WorkOrder.MaintenanceMode.CORRECTIVE,
            due_date=today,
            sla_due_at=timezone.now() + timedelta(hours=2),
            is_breakdown=True,
        )
        WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            asset_component=self.asset,
            title="Verify BMS patch",
            category=WorkOrder.Category.ELECTRICAL,
            priority=WorkOrder.Priority.MEDIUM,
            status=WorkOrder.Status.VERIFIED,
            maintenance_mode=WorkOrder.MaintenanceMode.CORRECTIVE,
            completed_date=today,
            verified_at=timezone.now(),
        )
        PreventiveSchedule.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            asset_component=self.asset,
            vendor=self.vendor,
            title="Quarterly controls inspection",
            category=WorkOrder.Category.HVAC,
            frequency=PreventiveSchedule.Frequency.QUARTERLY,
            priority=WorkOrder.Priority.MEDIUM,
            next_due_date=today + timedelta(days=5),
            status=PreventiveSchedule.Status.ACTIVE,
            auto_create_work_orders=True,
        )
        rule = PredictiveMaintenanceRule.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            asset_component=self.asset,
            title="Runtime threshold",
            priority=WorkOrder.Priority.MEDIUM,
            runtime_hours_threshold="1000.00",
            runtime_hours_reading="1024.00",
            alert_on_offline=False,
            alert_on_fault=False,
        )
        PredictiveMaintenanceAlert.objects.create(
            organization=self.org,
            rule=rule,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            asset_component=self.asset,
            title="Runtime threshold alert",
            message="Runtime reading exceeded the configured limit.",
            priority=WorkOrder.Priority.MEDIUM,
            trigger_type=PredictiveMaintenanceAlert.TriggerType.RUNTIME_HOURS,
            status=PredictiveMaintenanceAlert.Status.OPEN,
            runtime_hours_reading="1024.00",
        )

        response = self.client.get("/api/facility-management/maintenance/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["open_work_orders"], 1)
        self.assertEqual(response.data["kpis"]["in_progress_work_orders"], 1)
        self.assertEqual(response.data["kpis"]["verified_work_orders"], 1)
        self.assertEqual(response.data["kpis"]["breakdown_open"], 1)
        self.assertEqual(response.data["kpis"]["preventive_active"], 1)
        self.assertEqual(response.data["kpis"]["preventive_due_30_days"], 1)
        self.assertEqual(response.data["kpis"]["predictive_rules_active"], 1)
        self.assertEqual(response.data["kpis"]["predictive_alerts_open"], 1)
        self.assertGreaterEqual(len(response.data["work_orders_watchlist"]), 1)
        self.assertGreaterEqual(len(response.data["preventive_watchlist"]), 1)
        self.assertGreaterEqual(len(response.data["predictive_alerts_watchlist"]), 1)

    def test_scheduled_task_runs_maintenance_automation(self):
        today = timezone.localdate()
        self.asset.iot_status = AssetComponent.IoTStatus.FAULT
        self.asset.save(update_fields=["iot_status", "updated_at"])

        PreventiveSchedule.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            asset_component=self.asset,
            vendor=self.vendor,
            title="Daily VRF check",
            category=WorkOrder.Category.HVAC,
            frequency=PreventiveSchedule.Frequency.DAILY,
            priority=WorkOrder.Priority.MEDIUM,
            next_due_date=today,
            status=PreventiveSchedule.Status.ACTIVE,
            auto_create_work_orders=True,
        )
        PredictiveMaintenanceRule.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            asset_component=self.asset,
            title="Fault-state automation",
            priority=WorkOrder.Priority.HIGH,
            alert_on_offline=False,
            alert_on_fault=True,
            auto_create_work_order=True,
            is_active=True,
        )

        result = run_scheduled_maintenance_workflows([self.org.id])

        self.assertEqual(result["organizations_processed"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["preventive_work_orders_created"], 1)
        self.assertEqual(result["predictive_alerts_created"], 1)
        self.assertEqual(result["predictive_work_orders_created"], 1)
        self.assertEqual(
            WorkOrder.objects.filter(maintenance_mode=WorkOrder.MaintenanceMode.PREVENTIVE).count(),
            1,
        )
        self.assertEqual(
            WorkOrder.objects.filter(maintenance_mode=WorkOrder.MaintenanceMode.PREDICTIVE).count(),
            1,
        )

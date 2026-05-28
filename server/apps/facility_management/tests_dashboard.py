from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.models import FacilityIncident, UtilityConsumption
from apps.properties.models import AssetComponent, Inspection, PreventiveSchedule, Property, ServiceRequest, WorkOrder

User = get_user_model()


class FacilityDashboardOverviewTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Facility Test Org")
        self.user = User.objects.create_superuser(
            username="facility-admin@example.com",
            email="facility-admin@example.com",
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
            name="Emerald Residences",
            property_type=Property.PropertyType.BUILDING,
            address="21 Admiralty Way, Lekki",
            classification=Property.Classification.OWNED,
        )

        AssetComponent.objects.create(
            organization=self.org,
            property=self.property,
            component_id="AST-0001",
            name="Generator A",
            category=AssetComponent.Category.GENERATOR,
            condition_rating=AssetComponent.ConditionRating.GOOD,
        )
        AssetComponent.objects.create(
            organization=self.org,
            property=self.property,
            component_id="AST-0002",
            name="Main Lift 01",
            category=AssetComponent.Category.ELEVATOR,
            condition_rating=AssetComponent.ConditionRating.CRITICAL,
        )

        today = timezone.localdate()

        WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            title="Fix corridor lights",
            status=WorkOrder.Status.COMPLETED,
            priority=WorkOrder.Priority.MEDIUM,
            due_date=today - timedelta(days=2),
            completed_date=today - timedelta(days=3),
        )
        WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            title="Repair water pump",
            status=WorkOrder.Status.COMPLETED,
            priority=WorkOrder.Priority.HIGH,
            due_date=today - timedelta(days=5),
            completed_date=today - timedelta(days=2),
        )
        WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            title="Fire alarm fault",
            status=WorkOrder.Status.OPEN,
            priority=WorkOrder.Priority.URGENT,
        )

        ServiceRequest.objects.create(
            organization=self.org,
            property=self.property,
            title="AC not cooling",
            status=ServiceRequest.Status.OPEN,
            priority=ServiceRequest.Priority.HIGH,
            requested_by="Tenant 14B",
        )

        PreventiveSchedule.objects.create(
            organization=self.org,
            property=self.property,
            title="Monthly generator service",
            category=WorkOrder.Category.GENERATOR,
            frequency=PreventiveSchedule.Frequency.MONTHLY,
            next_due_date=today + timedelta(days=7),
            status=PreventiveSchedule.Status.ACTIVE,
        )
        PreventiveSchedule.objects.create(
            organization=self.org,
            property=self.property,
            title="Fire suppression routine check",
            category=WorkOrder.Category.FIRE_SAFETY,
            frequency=PreventiveSchedule.Frequency.MONTHLY,
            next_due_date=today - timedelta(days=2),
            status=PreventiveSchedule.Status.ACTIVE,
        )

        UtilityConsumption.objects.create(
            organization=self.org,
            property=self.property,
            reading_date=today - timedelta(days=10),
            electricity_kwh=120,
            water_m3=70,
            diesel_liters=40,
            gas_m3=10,
        )
        UtilityConsumption.objects.create(
            organization=self.org,
            property=self.property,
            reading_date=today - timedelta(days=40),
            electricity_kwh=60,
            water_m3=40,
            diesel_liters=20,
            gas_m3=5,
        )

        FacilityIncident.objects.create(
            organization=self.org,
            property=self.property,
            title="Electrical spark in switch room",
            category=FacilityIncident.Category.SAFETY,
            severity=FacilityIncident.Severity.CRITICAL,
            status=FacilityIncident.Status.OPEN,
            occurred_at=timezone.now() - timedelta(hours=8),
        )
        FacilityIncident.objects.create(
            organization=self.org,
            property=self.property,
            title="Unauthorized access attempt",
            category=FacilityIncident.Category.SECURITY,
            severity=FacilityIncident.Severity.HIGH,
            status=FacilityIncident.Status.INVESTIGATING,
            occurred_at=timezone.now() - timedelta(hours=18),
        )
        FacilityIncident.objects.create(
            organization=self.org,
            property=self.property,
            title="Resolved minor leak",
            category=FacilityIncident.Category.OTHER,
            severity=FacilityIncident.Severity.LOW,
            status=FacilityIncident.Status.RESOLVED,
            occurred_at=timezone.now() - timedelta(days=2),
            resolved_at=timezone.now() - timedelta(days=1),
        )

        Inspection.objects.create(
            organization=self.org,
            property=self.property,
            title="Post-incident safety walkthrough",
            inspection_type=Inspection.InspectionType.POST_INCIDENT,
            status=Inspection.Status.SCHEDULED,
            scheduled_date=today + timedelta(days=1),
            risk_level=Inspection.RiskLevel.HIGH,
        )

    def test_dashboard_overview_returns_expected_operational_kpis(self):
        response = self.client.get("/api/facility-management/dashboard/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data

        self.assertIn("facility_health_score", data)
        self.assertIn("active_maintenance_requests", data)
        self.assertIn("sla_compliance_rate", data)
        self.assertIn("asset_uptime_downtime", data)
        self.assertIn("energy_utility_consumption", data)
        self.assertIn("incident_alerts", data)
        self.assertIn("upcoming_preventive_maintenance", data)

        self.assertEqual(data["active_maintenance_requests"]["work_orders"], 1)
        self.assertEqual(data["active_maintenance_requests"]["service_requests"], 1)
        self.assertEqual(data["active_maintenance_requests"]["total"], 2)

        self.assertEqual(data["sla_compliance_rate"]["measured_count"], 2)
        self.assertEqual(data["sla_compliance_rate"]["on_time_count"], 1)
        self.assertEqual(data["sla_compliance_rate"]["value"], 50.0)

        self.assertEqual(data["asset_uptime_downtime"]["tracked_assets"], 2)
        self.assertEqual(data["asset_uptime_downtime"]["degraded_assets"], 1)
        self.assertEqual(data["asset_uptime_downtime"]["uptime_pct"], 50.0)
        self.assertEqual(data["asset_uptime_downtime"]["downtime_pct"], 50.0)

        self.assertEqual(data["incident_alerts"]["open_incidents"], 2)
        self.assertEqual(data["incident_alerts"]["critical_incidents"], 1)
        self.assertEqual(data["incident_alerts"]["high_incidents"], 1)
        self.assertEqual(data["incident_alerts"]["post_incident_inspections"], 1)

        self.assertEqual(data["upcoming_preventive_maintenance"]["upcoming_count"], 1)
        self.assertEqual(data["upcoming_preventive_maintenance"]["overdue_count"], 1)
        self.assertEqual(len(data["upcoming_preventive_maintenance"]["items"]), 1)

        self.assertEqual(data["energy_utility_consumption"]["energy_index"], 170.0)
        self.assertEqual(data["energy_utility_consumption"]["energy_change_vs_previous_pct"], 100.0)

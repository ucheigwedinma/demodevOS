from __future__ import annotations

import shutil
import tempfile
from datetime import timedelta

from auditlog.context import disable_auditlog
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.compliance.models import ComplianceRequirement, ComplianceViolation, PropertyCompliance
from apps.facility_management.health_safety_workflows import (
    ensure_checklist_defaults,
    ensure_regulatory_document_defaults,
)
from apps.facility_management.models import (
    Facility,
    FacilityComplianceChecklist,
    FacilityComplianceChecklistItem,
    FacilityFloor,
    FacilityIncident,
    FacilityRegulatoryDocument,
    FacilitySafetyAuditLog,
    FacilityUnitSpace,
    FacilityZone,
)
from apps.facility_management.tasks import run_scheduled_health_safety_compliance_workflows
from apps.properties.models import Inspection, Property, PropertyDocument, Unit, WorkOrder

User = get_user_model()


class FacilityHealthSafetyApiTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="facility-hsc-tests-")
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        # Keep these module tests independent from unrelated notification-settings
        # schema drift in the shared Organization audit trail.
        with disable_auditlog():
            self.org = Organization.objects.create(name="Facility HSC Org")
        self.user = User.objects.create_superuser(
            username="facility-hsc-admin@example.com",
            email="facility-hsc-admin@example.com",
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
            name="Atlas Commercial Centre",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="7 Ligali Ayorinde Street, Lagos",
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-ACC-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Operations Floor",
            floor_code="OPS-1",
            floor_number=1,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="North Core",
            zone_code="NC-1",
            zone_type=FacilityZone.ZoneType.SERVICE,
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="OPS-101",
            floor=1,
            area_sqft=180,
            unit_category=Unit.UnitCategory.OTHER,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit,
            space_label="Operations Control Room",
        )
        self.requirement = ComplianceRequirement.objects.create(
            organization=self.org,
            name="Quarterly Fire Compliance",
            category=ComplianceRequirement.Category.FIRE_SAFETY,
            renewal_frequency=ComplianceRequirement.RenewalFrequency.QUARTERLY,
            is_active=True,
        )

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)
        super().tearDown()

    def _pdf_upload(self, name: str = "certificate.pdf"):
        return SimpleUploadedFile(
            name,
            b"%PDF-1.4 health safety compliance test payload",
            content_type="application/pdf",
        )

    def test_incident_create_auto_generates_follow_up_actions_and_audit_logs(self):
        occurred_at = timezone.now() - timedelta(hours=2)

        response = self.client.post(
            "/api/facility-management/health-safety/incidents/",
            {
                "facility_space": self.space.id,
                "title": "Fire alarm discharge at control room",
                "description": "Smoke detector triggered emergency response in the control room.",
                "category": FacilityIncident.Category.FIRE,
                "severity": FacilityIncident.Severity.CRITICAL,
                "status": FacilityIncident.Status.OPEN,
                "occurred_at": occurred_at.isoformat(),
                "assigned_to": "Safety Officer A",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        incident = FacilityIncident.objects.get(title="Fire alarm discharge at control room")
        incident.refresh_from_db()

        self.assertEqual(incident.property_id, self.property.id)
        self.assertEqual(incident.facility_id, self.facility.id)
        self.assertEqual(incident.facility_space_id, self.space.id)
        self.assertTrue(incident.incident_code.startswith("INC-"))
        self.assertTrue(incident.requires_regulatory_report)
        self.assertIsNotNone(incident.follow_up_inspection_id)
        self.assertIsNotNone(incident.work_order_id)
        self.assertEqual(incident.follow_up_inspection.inspection_type, Inspection.InspectionType.FIRE_SAFETY)
        self.assertEqual(incident.work_order.category, WorkOrder.Category.FIRE_SAFETY)
        self.assertEqual(incident.work_order.priority, WorkOrder.Priority.CRITICAL)
        self.assertEqual(incident.work_order.status, WorkOrder.Status.ASSIGNED)

        audit_events = set(
            FacilitySafetyAuditLog.objects.filter(organization=self.org).values_list("event_type", flat=True)
        )
        self.assertIn(FacilitySafetyAuditLog.EventType.INCIDENT_REPORTED, audit_events)
        self.assertIn(FacilitySafetyAuditLog.EventType.FOLLOW_UP_INSPECTION_CREATED, audit_events)
        self.assertIn(FacilitySafetyAuditLog.EventType.CORRECTIVE_WORK_ORDER_CREATED, audit_events)

    def test_checklist_and_regulatory_document_create_sync_compliance_and_violations(self):
        today = timezone.localdate()

        checklist_response = self.client.post(
            "/api/facility-management/health-safety/checklists/",
            {
                "facility_space": self.space.id,
                "compliance_requirement": self.requirement.id,
                "title": "Quarterly Fire Readiness Checklist",
                "checklist_type": FacilityComplianceChecklist.ChecklistType.FIRE_SAFETY,
                "frequency": FacilityComplianceChecklist.Frequency.QUARTERLY,
                "status": FacilityComplianceChecklist.Status.ACTIVE,
                "responsible_person": "Safety Officer A",
                "due_date": today.isoformat(),
                "auto_create_violation": True,
                "auto_create_follow_up_inspection": True,
                "items": [
                    {
                        "title": "Emergency exit signage visible",
                        "is_mandatory": True,
                        "is_compliant": False,
                        "corrective_action": "Replace exit signage battery pack.",
                        "sort_order": 1,
                    },
                    {
                        "title": "Alarm panel operational",
                        "is_mandatory": True,
                        "is_compliant": True,
                        "sort_order": 2,
                    },
                ],
            },
            format="json",
        )

        self.assertEqual(checklist_response.status_code, status.HTTP_201_CREATED, checklist_response.data)

        checklist = FacilityComplianceChecklist.objects.get(title="Quarterly Fire Readiness Checklist")
        checklist.refresh_from_db()
        self.assertEqual(checklist.property_id, self.property.id)
        self.assertEqual(checklist.facility_id, self.facility.id)
        self.assertEqual(checklist.status, FacilityComplianceChecklist.Status.COMPLETED)
        self.assertEqual(checklist.total_items_count, 2)
        self.assertEqual(checklist.compliant_items_count, 1)
        self.assertIsNotNone(checklist.linked_inspection_id)

        compliance_record = PropertyCompliance.objects.get(
            organization=self.org,
            property=self.property,
            requirement=self.requirement,
        )
        self.assertEqual(compliance_record.status, PropertyCompliance.Status.NON_COMPLIANT)

        checklist_violation = ComplianceViolation.objects.get(
            organization=self.org,
            property=self.property,
            title=f"Checklist failure: {checklist.title}",
        )
        self.assertEqual(checklist_violation.status, ComplianceViolation.Status.OPEN)
        self.assertIn("Replace exit signage battery pack.", checklist_violation.corrective_action)

        regulatory_response = self.client.post(
            "/api/facility-management/health-safety/regulatory-documents/",
            {
                "facility": self.facility.id,
                "title": "Expired Fire Permit",
                "document_type": PropertyDocument.DocumentType.PERMIT,
                "description": "Legacy fire permit awaiting renewal.",
                "compliance_requirement": self.requirement.id,
                "issuing_authority": "Lagos Fire Service",
                "reference_number": "FIRE-PERMIT-001",
                "issue_date": (today - timedelta(days=365)).isoformat(),
                "expiry_date": (today - timedelta(days=1)).isoformat(),
                "review_due_date": today.isoformat(),
                "notes": "Renew immediately.",
                "file": self._pdf_upload("expired-fire-permit.pdf"),
            },
            format="multipart",
        )

        self.assertEqual(regulatory_response.status_code, status.HTTP_201_CREATED, regulatory_response.data)

        regulatory_document = FacilityRegulatoryDocument.objects.get(reference_number="FIRE-PERMIT-001")
        regulatory_document.refresh_from_db()
        self.assertEqual(regulatory_document.property_id, self.property.id)
        self.assertEqual(regulatory_document.facility_id, self.facility.id)
        self.assertEqual(regulatory_document.status, FacilityRegulatoryDocument.Status.EXPIRED)
        self.assertEqual(regulatory_document.property_document.document_type, PropertyDocument.DocumentType.PERMIT)

        document_violation = ComplianceViolation.objects.get(
            organization=self.org,
            property=self.property,
            title=f"Expired regulatory document: {regulatory_document.property_document.title}",
        )
        self.assertEqual(document_violation.status, ComplianceViolation.Status.OPEN)

    def test_overview_and_lookups_return_health_safety_operational_data(self):
        today = timezone.localdate()

        incident = FacilityIncident.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            title="Employee slip near stairwell",
            category=FacilityIncident.Category.SAFETY,
            severity=FacilityIncident.Severity.HIGH,
            status=FacilityIncident.Status.INVESTIGATING,
            occurred_at=timezone.now() - timedelta(hours=5),
            incident_code="INC-OV-001",
            requires_regulatory_report=True,
        )
        inspection = Inspection.objects.create(
            organization=self.org,
            property=self.property,
            unit=self.unit,
            title="Safety walkway inspection",
            inspection_type=Inspection.InspectionType.SAFETY,
            status=Inspection.Status.SCHEDULED,
            scheduled_date=today - timedelta(days=1),
            inspector="Safety Officer A",
            risk_level=Inspection.RiskLevel.HIGH,
        )
        checklist = FacilityComplianceChecklist.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            compliance_requirement=self.requirement,
            title="Monthly Safety Walkthrough",
            checklist_type=FacilityComplianceChecklist.ChecklistType.SAFETY,
            frequency=FacilityComplianceChecklist.Frequency.MONTHLY,
            status=FacilityComplianceChecklist.Status.ACTIVE,
            responsible_person="Safety Officer A",
            due_date=today - timedelta(days=2),
        )
        FacilityComplianceChecklistItem.objects.create(
            checklist=checklist,
            title="Hazard signage present",
            is_mandatory=True,
            is_compliant=None,
            corrective_action="Replace missing signage.",
        )
        ensure_checklist_defaults(checklist, actor=self.user)

        property_document = PropertyDocument.objects.create(
            organization=self.org,
            property=self.property,
            file=self._pdf_upload("expiring-certificate.pdf"),
            title="Lift Operations Certificate",
            document_type=PropertyDocument.DocumentType.INSPECTION,
            description="Lift operations certificate nearing expiry.",
        )
        regulatory_document = FacilityRegulatoryDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            property_document=property_document,
            compliance_requirement=self.requirement,
            status=FacilityRegulatoryDocument.Status.PENDING_REVIEW,
            expiry_date=today + timedelta(days=14),
            uploaded_by=self.user,
        )
        ensure_regulatory_document_defaults(regulatory_document, actor=self.user)

        violation = ComplianceViolation.objects.create(
            organization=self.org,
            property=self.property,
            title="Open stairwell safety finding",
            description="Investigate stairwell slip hazard.",
            violation_type=ComplianceRequirement.Category.SAFETY,
            severity=ComplianceViolation.Severity.MAJOR,
            status=ComplianceViolation.Status.OPEN,
            reported_date=today - timedelta(days=1),
            due_date=today + timedelta(days=2),
            corrective_action="Install anti-slip tape.",
            assigned_to="Safety Officer A",
        )
        FacilitySafetyAuditLog.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            entity_type=FacilitySafetyAuditLog.EntityType.INCIDENT,
            event_type=FacilitySafetyAuditLog.EventType.INCIDENT_REPORTED,
            entity_id=incident.id,
            actor=self.user,
            summary="Reported slip incident at stairwell.",
        )

        overview_response = self.client.get("/api/facility-management/health-safety/overview/")
        lookups_response = self.client.get("/api/facility-management/health-safety/lookups/")

        self.assertEqual(overview_response.status_code, status.HTTP_200_OK, overview_response.data)
        self.assertEqual(lookups_response.status_code, status.HTTP_200_OK, lookups_response.data)

        overview = overview_response.data
        self.assertEqual(overview["kpis"]["open_incidents"], 1)
        self.assertEqual(overview["kpis"]["scheduled_inspections"], 1)
        self.assertEqual(overview["kpis"]["overdue_inspections"], 1)
        self.assertEqual(overview["kpis"]["open_checklists"], 1)
        self.assertEqual(overview["kpis"]["overdue_checklists"], 1)
        self.assertEqual(overview["kpis"]["total_regulatory_documents"], 1)
        self.assertEqual(overview["kpis"]["expiring_documents"], 1)
        self.assertEqual(overview["kpis"]["open_violations"], 1)
        self.assertEqual(len(overview["incident_watchlist"]), 1)
        self.assertEqual(len(overview["document_watchlist"]), 1)
        self.assertEqual(len(overview["violation_watchlist"]), 1)
        self.assertEqual(len(overview["audit_log_watchlist"]), 1)

        lookups = lookups_response.data
        self.assertEqual(len(lookups["facilities"]), 1)
        self.assertEqual(len(lookups["spaces"]), 1)
        self.assertEqual(len(lookups["compliance_requirements"]), 1)
        self.assertGreaterEqual(len(lookups["incidents"]), 1)
        self.assertGreaterEqual(len(lookups["inspections"]), 1)

        self.assertEqual(violation.title, "Open stairwell safety finding")
        self.assertEqual(inspection.title, "Safety walkway inspection")

    def test_scheduled_task_runs_health_safety_compliance_automation(self):
        today = timezone.localdate()

        incident = FacilityIncident.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            title="Generator smoke emission",
            description="Generator emitted smoke during startup.",
            category=FacilityIncident.Category.ENVIRONMENTAL,
            severity=FacilityIncident.Severity.HIGH,
            status=FacilityIncident.Status.OPEN,
            occurred_at=timezone.now() - timedelta(hours=3),
        )

        checklist = FacilityComplianceChecklist.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            compliance_requirement=self.requirement,
            title="Generator Environmental Checklist",
            checklist_type=FacilityComplianceChecklist.ChecklistType.ENVIRONMENTAL,
            frequency=FacilityComplianceChecklist.Frequency.MONTHLY,
            status=FacilityComplianceChecklist.Status.ACTIVE,
            responsible_person="HSE Lead",
            due_date=today,
            auto_create_violation=True,
            auto_create_follow_up_inspection=True,
        )
        FacilityComplianceChecklistItem.objects.create(
            checklist=checklist,
            title="Emission filter functional",
            is_mandatory=True,
            is_compliant=False,
            corrective_action="Replace emission filter.",
        )

        property_document = PropertyDocument.objects.create(
            organization=self.org,
            property=self.property,
            file=self._pdf_upload("expired-generator-certificate.pdf"),
            title="Generator Emissions Permit",
            document_type=PropertyDocument.DocumentType.PERMIT,
            description="Expired permit pending renewal.",
        )
        FacilityRegulatoryDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            property_document=property_document,
            compliance_requirement=self.requirement,
            status=FacilityRegulatoryDocument.Status.PENDING_REVIEW,
            expiry_date=today - timedelta(days=1),
        )

        summary = run_scheduled_health_safety_compliance_workflows([self.org.id])

        self.assertEqual(summary["organizations_processed"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertGreaterEqual(summary["follow_up_inspections_created"], 2)
        self.assertGreaterEqual(summary["corrective_work_orders_created"], 1)
        self.assertGreaterEqual(summary["violations_created"], 2)
        self.assertGreaterEqual(summary["regulatory_documents_synced"], 1)
        self.assertEqual(summary["expired_documents_flagged"], 1)
        self.assertEqual(summary["audit_logs_created"], 1)

        incident.refresh_from_db()
        checklist.refresh_from_db()
        self.assertIsNotNone(incident.follow_up_inspection_id)
        self.assertIsNotNone(incident.work_order_id)
        self.assertIsNotNone(checklist.linked_inspection_id)

        self.assertTrue(
            ComplianceViolation.objects.filter(
                organization=self.org,
                property=self.property,
                title__in=[
                    f"Checklist failure: {checklist.title}",
                    f"Expired regulatory document: {property_document.title}",
                ],
            ).count()
            >= 2
        )

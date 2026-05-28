from __future__ import annotations

import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.facility_management.document_drawings_workflows import ensure_facility_document_defaults
from apps.facility_management.models import Facility, FacilityDocument, FacilityFloor, FacilityUnitSpace, FacilityZone
from apps.facility_management.tasks import run_scheduled_documents_drawings_workflows
from apps.properties.models import AssetComponent, Property, Unit, WorkOrder

User = get_user_model()


class FacilityDocumentsApiTests(APITestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="facility-doc-tests-")
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        self.org = Organization.objects.create(name="Facility Documents Org")
        self.user = User.objects.create_superuser(
            username="facility-docs-admin@example.com",
            email="facility-docs-admin@example.com",
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
            name="Harbor Exchange",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="22 Marina Road, Lagos",
        )
        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-HX-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Ground Floor",
            floor_code="GF",
            floor_number=0,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="Plant Room Zone",
            zone_code="PLT",
            zone_type=FacilityZone.ZoneType.SERVICE,
        )
        self.unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="PLT-01",
            floor=0,
            area_sqft=250,
            unit_category=Unit.UnitCategory.OTHER,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit,
            space_label="Main Plant Room",
        )
        self.asset = AssetComponent.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            component_id="AST-CH-001",
            name="Central Chiller Pump",
            category=AssetComponent.Category.HVAC,
            serial_number="CH-PUMP-7781",
            condition_rating=AssetComponent.ConditionRating.GOOD,
        )

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)
        super().tearDown()

    def _pdf_upload(self, name: str = "document.pdf"):
        return SimpleUploadedFile(
            name,
            b"%PDF-1.4 facility document test payload",
            content_type="application/pdf",
        )

    def _completed_work_order(self, title: str = "Repair chilled water leak") -> WorkOrder:
        return WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            unit=self.unit,
            asset_component=self.asset,
            title=title,
            description="Repair leak and restore normal chiller operation.",
            maintenance_mode=WorkOrder.MaintenanceMode.CORRECTIVE,
            category=WorkOrder.Category.HVAC,
            priority=WorkOrder.Priority.HIGH,
            status=WorkOrder.Status.COMPLETED,
            reported_by="Facilities Ops",
            assigned_to="Technician A",
            completed_date=timezone.localdate() - timedelta(days=1),
            root_cause="Valve seal failure",
            verification_notes="Pressure stabilized after seal replacement.",
        )

    def test_document_create_with_asset_derives_facility_context(self):
        response = self.client.post(
            "/api/facility-management/documents/records/",
            {
                "asset_component": self.asset.id,
                "title": "Main Plant Room Blueprint",
                "document_type": FacilityDocument.DocumentType.BLUEPRINT,
                "issued_date": timezone.localdate().isoformat(),
                "version_label": "Rev-B",
                "reference_number": "BLP-PLT-002",
                "description": "Current blueprint for the plant room layout.",
                "file": self._pdf_upload("plant-room-blueprint.pdf"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        document = FacilityDocument.objects.get(title="Main Plant Room Blueprint")
        self.assertEqual(document.organization_id, self.org.id)
        self.assertEqual(document.property_id, self.property.id)
        self.assertEqual(document.facility_id, self.facility.id)
        self.assertEqual(document.facility_space_id, self.space.id)
        self.assertEqual(document.asset_component_id, self.asset.id)
        self.assertEqual(document.uploaded_by_id, self.user.id)
        self.assertIsNotNone(document.review_due_date)
        self.assertEqual(document.status, FacilityDocument.Status.ACTIVE)
        self.assertTrue(
            document.file.name.startswith(
                f"facility_documents/org_{self.org.id}/facility_{self.facility.id}/blueprint/"
            )
        )

    def test_overview_returns_document_kpis_and_watchlists(self):
        today = timezone.localdate()

        expired_certificate = FacilityDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            title="Fire Safety Certificate 2025",
            document_type=FacilityDocument.DocumentType.COMPLIANCE_CERTIFICATE,
            reference_number="CERT-FIRE-2025",
            issued_date=today - timedelta(days=400),
            expiry_date=today - timedelta(days=1),
            status=FacilityDocument.Status.ACTIVE,
        )
        review_blueprint = FacilityDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            title="Cooling Tower Drawing",
            document_type=FacilityDocument.DocumentType.DRAWING,
            version_label="Rev-4",
            issued_date=today - timedelta(days=220),
            review_due_date=today,
            status=FacilityDocument.Status.ACTIVE,
        )
        generated_log = FacilityDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            asset_component=self.asset,
            title="Maintenance Log - WO-100",
            document_type=FacilityDocument.DocumentType.MAINTENANCE_LOG,
            source=FacilityDocument.Source.GENERATED,
            generated_summary="Valve replaced and system recommissioned.",
            issued_date=today - timedelta(days=2),
            status=FacilityDocument.Status.ACTIVE,
        )
        FacilityDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            asset_component=self.asset,
            title="Chiller Pump OEM Manual",
            document_type=FacilityDocument.DocumentType.EQUIPMENT_MANUAL,
            file=self._pdf_upload("pump-manual.pdf"),
            issued_date=today - timedelta(days=90),
            status=FacilityDocument.Status.ACTIVE,
        )

        ensure_facility_document_defaults(expired_certificate, today=today)
        ensure_facility_document_defaults(review_blueprint, today=today)
        ensure_facility_document_defaults(generated_log, today=today)

        response = self.client.get("/api/facility-management/documents/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["total_documents"], 4)
        self.assertEqual(response.data["kpis"]["blueprints_drawings"], 1)
        self.assertEqual(response.data["kpis"]["equipment_manuals"], 1)
        self.assertEqual(response.data["kpis"]["maintenance_logs"], 1)
        self.assertEqual(response.data["kpis"]["generated_maintenance_logs"], 1)
        self.assertEqual(response.data["kpis"]["compliance_certificates"], 1)
        self.assertEqual(response.data["kpis"]["review_due_documents"], 1)
        self.assertEqual(response.data["kpis"]["expired_documents"], 1)
        self.assertEqual(len(response.data["review_watchlist"]), 2)
        self.assertEqual(len(response.data["maintenance_log_watchlist"]), 1)
        self.assertEqual(len(response.data["blueprint_watchlist"]), 1)
        self.assertEqual(
            response.data["maintenance_log_watchlist"][0]["source"],
            FacilityDocument.Source.GENERATED,
        )

    def test_scheduled_task_syncs_document_statuses_and_generates_maintenance_logs(self):
        today = timezone.localdate()
        FacilityDocument.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space,
            title="Plant Room As-Built",
            document_type=FacilityDocument.DocumentType.BLUEPRINT,
            issued_date=today - timedelta(days=210),
            status=FacilityDocument.Status.ACTIVE,
        )
        work_order = self._completed_work_order()

        summary = run_scheduled_documents_drawings_workflows([self.org.id])

        self.assertEqual(summary["organizations_processed"], 1)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(summary["documents_synced"], 1)
        self.assertEqual(summary["maintenance_logs_generated"], 1)
        self.assertEqual(summary["review_due_documents"], 1)

        generated_log = FacilityDocument.objects.get(linked_work_order=work_order)
        self.assertEqual(generated_log.document_type, FacilityDocument.DocumentType.MAINTENANCE_LOG)
        self.assertEqual(generated_log.source, FacilityDocument.Source.GENERATED)
        self.assertEqual(generated_log.facility_id, self.facility.id)
        self.assertEqual(generated_log.facility_space_id, self.space.id)
        self.assertIn("Valve seal failure", generated_log.generated_summary)

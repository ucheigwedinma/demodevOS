from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from auditlog.context import disable_auditlog
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import ContactAccount
from apps.facility_management.models import Facility, FacilityFloor, FacilityUnitSpace, FacilityZone
from apps.finance.models import Customer, Invoice, InvoiceLineItem, InvoicePayment
from apps.properties.models import Property, Unit, WorkOrder
from apps.tenants.models import (
    LeaseAgreement,
    TenantIdentityDocument,
    TenantIncidentRecord,
    TenantInventoryItem,
    TenantProfile,
    TenantRelationshipContact,
)

User = get_user_model()


class TenantRegistryApiTests(APITestCase):
    def setUp(self):
        today = timezone.localdate()

        with disable_auditlog():
            self.org = Organization.objects.create(name="Tenant Registry Org")

        self.user = User.objects.create_superuser(
            username="tenant-registry-admin@example.com",
            email="tenant-registry-admin@example.com",
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
            name="Atlas Towers",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="18 Admiralty Way, Lagos",
        )
        self.unit_101 = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="101",
            floor=1,
            area_sqft=400,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.unit_102 = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="102",
            floor=1,
            area_sqft=420,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.unit_103 = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="103",
            floor=1,
            area_sqft=430,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )

        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="ATL-LAG",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="First Floor",
            floor_code="L1",
            floor_number=1,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="Workspace Wing",
            zone_code="W1",
            zone_type=FacilityZone.ZoneType.COMMERCIAL,
        )
        self.space_101 = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit_101,
            space_label="Suite 101",
        )
        self.space_102 = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit_102,
            space_label="Suite 102",
        )
        self.space_103 = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit_103,
            space_label="Suite 103",
        )

        self.customer_active = Customer.objects.create(
            organization=self.org,
            name="Northwind Advisory",
            email="northwind@example.com",
            phone="+2348011111111",
        )
        self.customer_archive = Customer.objects.create(
            organization=self.org,
            name="Legacy Occupant",
            email="legacy@example.com",
            phone="+2348022222222",
        )
        self.customer_contact_sync = Customer.objects.create(
            organization=self.org,
            name="Orbit Workspace",
            email="orbit@example.com",
            phone="+2348033333333",
        )
        self.contact_synced = ContactAccount.objects.create(
            organization=self.org,
            entity_type=ContactAccount.EntityType.ORGANIZATION,
            legal_name="Orbit Workspace",
            email="ops@orbit.example.com",
            phone="+2348044444444",
            finance_customer=self.customer_contact_sync,
        )

        self.active_tenant = TenantProfile.objects.create(
            organization=self.org,
            customer=self.customer_active,
            primary_user=self.user,
            property=self.property,
            unit=self.unit_101,
            facility=self.facility,
            facility_space=self.space_101,
            status=TenantProfile.Status.ACTIVE,
            display_name="Northwind Advisory",
            lease_start_date=today - timedelta(days=120),
            lease_end_date=today + timedelta(days=45),
            move_in_date=today - timedelta(days=120),
        )
        self.moved_out_tenant = TenantProfile.objects.create(
            organization=self.org,
            customer=self.customer_archive,
            property=self.property,
            unit=self.unit_102,
            facility=self.facility,
            facility_space=self.space_102,
            status=TenantProfile.Status.MOVED_OUT,
            display_name="Legacy Occupant",
            lease_start_date=today - timedelta(days=500),
            lease_end_date=today - timedelta(days=7),
            move_in_date=today - timedelta(days=500),
            move_out_date=today - timedelta(days=7),
        )
        self.pending_unassigned_tenant = TenantProfile.objects.create(
            organization=self.org,
            status=TenantProfile.Status.PENDING_MOVE_IN,
            tenant_type=TenantProfile.TenantType.INDIVIDUAL,
            display_name="Walk-in Prospect",
            move_in_date=today + timedelta(days=7),
        )

        self.overdue_invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer_active,
            property=self.property,
            status=Invoice.Status.OVERDUE,
            issue_date=today - timedelta(days=35),
            due_date=today - timedelta(days=10),
            subtotal=Decimal("120000.00"),
            total_amount=Decimal("120000.00"),
        )
        self.paid_invoice = Invoice.objects.create(
            organization=self.org,
            customer=self.customer_archive,
            property=self.property,
            status=Invoice.Status.PAID,
            issue_date=today - timedelta(days=60),
            due_date=today - timedelta(days=45),
            subtotal=Decimal("85000.00"),
            total_amount=Decimal("85000.00"),
        )
        InvoicePayment.objects.create(
            invoice=self.paid_invoice,
            amount=Decimal("85000.00"),
            payment_date=today - timedelta(days=44),
        )
        InvoiceLineItem.objects.create(
            invoice=self.overdue_invoice,
            description="Annual rent",
            quantity=Decimal("1.00"),
            unit_price=Decimal("120000.00"),
            sort_order=1,
        )
        InvoicePayment.objects.create(
            invoice=self.overdue_invoice,
            amount=Decimal("20000.00"),
            payment_date=today - timedelta(days=20),
            reference_number="NW-20000",
        )
        self.priority_work_order = WorkOrder.objects.create(
            organization=self.org,
            property=self.property,
            facility=self.facility,
            facility_space=self.space_101,
            unit=self.unit_101,
            title="Critical HVAC issue",
            description="Boardroom AC failure affecting the tenant suite.",
            category=WorkOrder.Category.HVAC,
            priority=WorkOrder.Priority.CRITICAL,
            status=WorkOrder.Status.IN_PROGRESS,
            is_breakdown=True,
            notes="Escalated for urgent repair",
        )
        self.identity_document = TenantIdentityDocument.objects.create(
            organization=self.org,
            tenant_profile=self.active_tenant,
            document_type=TenantIdentityDocument.DocumentType.NIN,
            document_number="NIN-000-111-222",
            holder_name="Northwind Advisory",
            issuing_country="Nigeria",
            scan_on_file=True,
            scan_reference="vault://tenant/northwind/nin.pdf",
            is_verified=True,
            notes="Primary corporate identity document",
        )
        self.next_of_kin = TenantRelationshipContact.objects.create(
            organization=self.org,
            tenant_profile=self.active_tenant,
            contact_role=TenantRelationshipContact.ContactRole.NEXT_OF_KIN,
            full_name="Ada Northwind",
            relationship="Operations Lead",
            phone="+2348055555555",
            email="ada@northwind.example.com",
            is_primary=True,
        )
        self.emergency_contact = TenantRelationshipContact.objects.create(
            organization=self.org,
            tenant_profile=self.active_tenant,
            contact_role=TenantRelationshipContact.ContactRole.EMERGENCY,
            full_name="Facility Control",
            relationship="Emergency Response",
            phone="+2348066666666",
            email="control@northwind.example.com",
        )
        self.inventory_item = TenantInventoryItem.objects.create(
            organization=self.org,
            tenant_profile=self.active_tenant,
            item_name="Bluegate Inverter",
            quantity=3,
            condition=TenantInventoryItem.Condition.GOOD,
            status=TenantInventoryItem.Status.PROVIDED,
            notes="Issued at move-in",
        )
        self.incident_record = TenantIncidentRecord.objects.create(
            organization=self.org,
            tenant_profile=self.active_tenant,
            work_order=self.priority_work_order,
            incident_type=TenantIncidentRecord.IncidentType.LEASE_VIOLATION,
            severity=TenantIncidentRecord.Severity.HIGH,
            status=TenantIncidentRecord.Status.OPEN,
            title="Unauthorized signage",
            description="Tenant installed signage without prior approval.",
            notes="Compliance follow-up required.",
        )

    def test_registry_overview_returns_master_data_metrics(self):
        response = self.client.get("/api/tenants/registry/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["totals"]["profiles"], 3)
        self.assertEqual(response.data["totals"]["active"], 1)
        self.assertEqual(response.data["totals"]["pending_move_in"], 1)
        self.assertEqual(response.data["totals"]["moved_out"], 1)
        self.assertEqual(response.data["hygiene"]["missing_customer_links"], 1)
        self.assertEqual(response.data["hygiene"]["missing_contact_channels"], 1)
        self.assertEqual(response.data["hygiene"]["missing_location_mapping"], 1)
        self.assertEqual(response.data["allocation"]["assigned_units"], 2)
        self.assertEqual(response.data["allocation"]["assigned_spaces"], 2)
        self.assertEqual(response.data["allocation"]["unassigned_profiles"], 1)
        self.assertEqual(response.data["lease_watch"]["expiring_next_60_days"], 1)
        self.assertEqual(response.data["lease_watch"]["move_ins_next_30_days"], 1)
        self.assertEqual(response.data["lease_watch"]["recent_move_outs"], 1)

    def test_registry_lookups_return_reference_data(self):
        response = self.client.get("/api/tenants/registry/lookups/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["properties"]), 1)
        self.assertEqual(len(response.data["facilities"]), 1)
        self.assertEqual(len(response.data["units"]), 3)
        self.assertEqual(len(response.data["spaces"]), 3)
        self.assertTrue(any(item["name"] == "Orbit Workspace" for item in response.data["customers"]))
        self.assertTrue(any(item["name"] == "Orbit Workspace" for item in response.data["contact_accounts"]))

    def test_create_profile_derives_links_and_reserves_unit(self):
        today = timezone.localdate()

        response = self.client.post(
            "/api/tenants/profiles/",
            {
                "contact_account": self.contact_synced.id,
                "facility_space": self.space_103.id,
                "tenant_type": TenantProfile.TenantType.CORPORATE,
                "status": TenantProfile.Status.PENDING_MOVE_IN,
                "display_name": "",
                "lease_start_date": today.isoformat(),
                "lease_end_date": (today + timedelta(days=365)).isoformat(),
                "move_in_date": (today + timedelta(days=14)).isoformat(),
                "occupant_count": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        created = TenantProfile.objects.get(id=response.data["id"])
        self.assertEqual(created.customer_id, self.customer_contact_sync.id)
        self.assertEqual(created.property_id, self.property.id)
        self.assertEqual(created.facility_id, self.facility.id)
        self.assertEqual(created.unit_id, self.unit_103.id)
        self.assertEqual(created.facility_space_id, self.space_103.id)
        self.assertEqual(created.display_name, "Orbit Workspace")
        lease = created.lease_agreements.get()
        self.assertEqual(lease.start_date, today)
        self.assertEqual(lease.end_date, today + timedelta(days=365))
        self.assertEqual(lease.property_id, self.property.id)
        self.assertEqual(lease.facility_id, self.facility.id)
        self.assertEqual(lease.unit_id, self.unit_103.id)
        self.assertEqual(lease.facility_space_id, self.space_103.id)
        self.assertEqual(lease.status, LeaseAgreement.Status.DRAFT)
        self.unit_103.refresh_from_db()
        self.assertEqual(self.unit_103.status, Unit.UnitStatus.RESERVED)

    def test_create_profile_provisions_lease_context_before_dates_are_finalized(self):
        today = timezone.localdate()
        response = self.client.post(
            "/api/tenants/profiles/",
            {
                "customer": self.customer_contact_sync.id,
                "unit": self.unit_103.id,
                "tenant_type": TenantProfile.TenantType.CORPORATE,
                "status": TenantProfile.Status.PENDING_MOVE_IN,
                "display_name": "Orbit Workspace",
                "occupant_count": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        tenant = TenantProfile.objects.get(id=response.data["id"])
        lease = tenant.lease_agreements.get()
        self.assertEqual(lease.status, LeaseAgreement.Status.DRAFT)
        self.assertEqual(lease.start_date, today)
        self.assertEqual(lease.end_date, today + timedelta(days=365))
        self.assertEqual(lease.unit_id, self.unit_103.id)
        self.assertEqual(lease.facility_id, self.facility.id)

        patch_response = self.client.patch(
            f"/api/tenants/profiles/{tenant.id}/",
            {
                "lease_start_date": today.isoformat(),
                "lease_end_date": (today + timedelta(days=180)).isoformat(),
                "move_in_date": (today + timedelta(days=7)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK, patch_response.data)
        tenant.refresh_from_db()
        lease.refresh_from_db()
        self.assertEqual(lease.start_date, today)
        self.assertEqual(lease.end_date, today + timedelta(days=180))
        self.assertEqual(lease.unit_id, self.unit_103.id)
        self.assertEqual(lease.facility_id, self.facility.id)

    def test_create_profile_without_location_context_is_rejected(self):
        response = self.client.post(
            "/api/tenants/profiles/",
            {
                "customer": self.customer_contact_sync.id,
                "tenant_type": TenantProfile.TenantType.CORPORATE,
                "status": TenantProfile.Status.PENDING_MOVE_IN,
                "display_name": "No Lease Context Ltd",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("property", response.data)

    def test_update_profile_moves_unit_and_syncs_statuses(self):
        today = timezone.localdate()
        create_response = self.client.post(
            "/api/tenants/profiles/",
            {
                "customer": self.customer_contact_sync.id,
                "unit": self.unit_103.id,
                "tenant_type": TenantProfile.TenantType.CORPORATE,
                "status": TenantProfile.Status.PENDING_MOVE_IN,
                "display_name": "Orbit Workspace",
                "move_in_date": (today + timedelta(days=10)).isoformat(),
                "occupant_count": 3,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)
        tenant_id = create_response.data["id"]

        update_response = self.client.patch(
            f"/api/tenants/profiles/{tenant_id}/",
            {
                "status": TenantProfile.Status.ACTIVE,
                "facility_space": self.space_102.id,
                "move_in_date": today.isoformat(),
            },
            format="json",
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK, update_response.data)
        tenant = TenantProfile.objects.get(id=tenant_id)
        self.assertEqual(tenant.unit_id, self.unit_102.id)
        self.assertEqual(tenant.facility_space_id, self.space_102.id)
        self.assertEqual(tenant.status, TenantProfile.Status.ACTIVE)
        self.unit_103.refresh_from_db()
        self.unit_102.refresh_from_db()
        self.assertEqual(self.unit_103.status, Unit.UnitStatus.AVAILABLE)
        self.assertEqual(self.unit_102.status, Unit.UnitStatus.LEASED)

    def test_create_blocks_duplicate_active_assignment(self):
        response = self.client.post(
            "/api/tenants/profiles/",
            {
                "customer": self.customer_contact_sync.id,
                "unit": self.unit_101.id,
                "tenant_type": TenantProfile.TenantType.CORPORATE,
                "status": TenantProfile.Status.ACTIVE,
                "display_name": "Conflicting Occupant",
                "occupant_count": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("unit", response.data)

    def test_registry_list_includes_payment_status(self):
        response = self.client.get("/api/tenants/profiles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        rows_payload = response.data["results"] if isinstance(response.data, dict) else response.data
        rows = {item["resolved_display_name"]: item for item in rows_payload}
        self.assertEqual(rows["Northwind Advisory"]["payment_status"], "delinquent")
        self.assertEqual(rows["Northwind Advisory"]["payment_status_display"], "Delinquent")
        self.assertEqual(rows["Legacy Occupant"]["payment_status"], "debt_free")
        self.assertEqual(rows["Walk-in Prospect"]["payment_status"], "unknown")

    def test_registry_export_csv_returns_portfolio_rows(self):
        response = self.client.get("/api/tenants/profiles/export/?export_format=csv")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode("utf-8")
        self.assertIn("display_name,customer_name", content)
        self.assertIn("Northwind Advisory", content)
        self.assertIn("Legacy Occupant", content)

    def test_registry_export_xlsx_returns_excel_workbook(self):
        response = self.client.get("/api/tenants/profiles/export/?export_format=xlsx")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        workbook = load_workbook(filename=BytesIO(response.content), data_only=True)
        worksheet = workbook.active
        self.assertEqual(worksheet["A1"].value, "display_name")
        self.assertEqual(worksheet["A2"].value, "Legacy Occupant")

    def test_registry_import_csv_creates_rows_and_reports_failures(self):
        csv_body = "\n".join(
            [
                "display_name,customer_name,customer_email,customer_phone,contact_account_name,contact_email,contact_phone,primary_user_email,property_name,property_location,unit_number,facility_code,space_label,tenant_type,status,lease_start_date,lease_end_date,move_in_date,move_out_date,occupant_count,notes",
                "Orbit Workspace,,,,Orbit Workspace,ops@orbit.example.com,+2348044444444,,Atlas Towers,Lagos,103,ATL-LAG,Suite 103,Corporate,Prospective,2026-04-01,2027-03-31,2026-04-15,,4,Imported from spreadsheet",
                "Broken Row,,,,,,,,Atlas Towers,Lagos,101,ATL-LAG,Suite 101,Corporate,Active,,,,,abc,Should fail on occupant count",
            ]
        )
        upload = SimpleUploadedFile("tenant-registry-import.csv", csv_body.encode("utf-8"), content_type="text/csv")

        response = self.client.post("/api/tenants/profiles/import/", {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["created_count"], 1)
        self.assertEqual(len(response.data["failed_rows"]), 1)

        imported = TenantProfile.objects.get(display_name="Orbit Workspace")
        self.assertEqual(imported.customer_id, self.customer_contact_sync.id)
        self.assertEqual(imported.contact_account_id, self.contact_synced.id)
        self.assertEqual(imported.unit_id, self.unit_103.id)
        self.assertEqual(imported.facility_space_id, self.space_103.id)
        self.assertEqual(imported.status, TenantProfile.Status.PENDING_MOVE_IN)
        self.unit_103.refresh_from_db()
        self.assertEqual(self.unit_103.status, Unit.UnitStatus.RESERVED)

    def test_source_of_truth_returns_identity_financial_inventory_and_incidents(self):
        response = self.client.get(f"/api/tenants/profiles/{self.active_tenant.id}/source-of-truth/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["tenant"]["resolved_display_name"], "Northwind Advisory")
        self.assertEqual(len(response.data["identity"]["documents"]), 1)
        self.assertEqual(len(response.data["identity"]["next_of_kin"]), 1)
        self.assertEqual(len(response.data["identity"]["emergency_contacts"]), 1)
        self.assertEqual(response.data["financial"]["summary"]["invoice_count"], 1)
        self.assertEqual(len(response.data["financial"]["ledger"][0]["line_items"]), 1)
        self.assertEqual(len(response.data["financial"]["ledger"][0]["payments"]), 1)
        self.assertEqual(response.data["inventory"]["summary"]["item_count"], 1)
        self.assertGreaterEqual(len(response.data["incident_log"]["entries"]), 2)
        sources = {entry["source_label"] for entry in response.data["incident_log"]["entries"]}
        self.assertIn("Tenant Incident", sources)
        self.assertIn("Maintenance Work Order", sources)

    def test_create_identity_document_action_adds_profile_document(self):
        response = self.client.post(
            f"/api/tenants/profiles/{self.active_tenant.id}/identity-documents/",
            {
                "document_type": TenantIdentityDocument.DocumentType.PASSPORT,
                "document_number": "P-12345",
                "holder_name": "Northwind Advisory",
                "issuing_country": "Nigeria",
                "scan_on_file": True,
                "scan_reference": "passport-ref",
                "is_verified": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            TenantIdentityDocument.objects.filter(
                tenant_profile=self.active_tenant,
                document_type=TenantIdentityDocument.DocumentType.PASSPORT,
                document_number="P-12345",
            ).exists()
        )

    def test_create_relationship_contact_action_adds_profile_contact(self):
        response = self.client.post(
            f"/api/tenants/profiles/{self.active_tenant.id}/relationship-contacts/",
            {
                "contact_role": TenantRelationshipContact.ContactRole.EMERGENCY,
                "full_name": "Rapid Response Team",
                "relationship": "Emergency Support",
                "phone": "+2348077777777",
                "email": "response@example.com",
                "is_primary": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            TenantRelationshipContact.objects.filter(
                tenant_profile=self.active_tenant,
                full_name="Rapid Response Team",
                contact_role=TenantRelationshipContact.ContactRole.EMERGENCY,
            ).exists()
        )

    def test_create_inventory_item_action_adds_profile_checklist_row(self):
        response = self.client.post(
            f"/api/tenants/profiles/{self.active_tenant.id}/inventory-items/",
            {
                "item_name": "Panasonic AC",
                "quantity": 2,
                "condition": TenantInventoryItem.Condition.NEW,
                "status": TenantInventoryItem.Status.PROVIDED,
                "notes": "Installed before move-in",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            TenantInventoryItem.objects.filter(
                tenant_profile=self.active_tenant,
                item_name="Panasonic AC",
                quantity=2,
            ).exists()
        )

    def test_create_incident_record_action_adds_profile_incident(self):
        response = self.client.post(
            f"/api/tenants/profiles/{self.active_tenant.id}/incident-records/",
            {
                "incident_type": TenantIncidentRecord.IncidentType.SECURITY,
                "severity": TenantIncidentRecord.Severity.CRITICAL,
                "status": TenantIncidentRecord.Status.UNDER_REVIEW,
                "title": "Security breach",
                "description": "Access card was used outside approved window.",
                "occurred_at": timezone.localdate().isoformat(),
                "notes": "Awaiting security report.",
                "work_order": self.priority_work_order.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            TenantIncidentRecord.objects.filter(
                tenant_profile=self.active_tenant,
                title="Security breach",
                work_order=self.priority_work_order,
            ).exists()
        )

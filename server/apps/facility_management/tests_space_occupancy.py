from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import ContactAccount
from apps.facility_management.models import (
    Facility,
    FacilityFloor,
    FacilitySpaceProfile,
    FacilityUnitSpace,
    FacilityZone,
    SpaceAllocation,
    SpaceBooking,
)
from apps.facility_management.space_occupancy_workflows import (
    ensure_allocation_defaults,
    ensure_space_profile_defaults,
    run_space_occupancy_automation,
    sync_inventory_for_tenant_allocation,
    sync_tenant_profile_for_allocation,
)
from apps.facility_management.tasks import run_scheduled_space_occupancy_workflows
from apps.finance.models import Customer
from apps.properties.models import Property, PropertyInventory, Unit
from apps.settings.models import Department, Division
from apps.tenants.models import LeaseAgreement, TenantProfile

User = get_user_model()


class FacilitySpaceOccupancyApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Facility Occupancy Org")
        self.user = User.objects.create_superuser(
            username="facility-occupancy-admin@example.com",
            email="facility-occupancy-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])

        self.employee = User.objects.create_user(
            username="adebayo.ade@example.com",
            email="adebayo.ade@example.com",
            password="Pass123!",
            first_name="Adebayo",
            last_name="Ade",
        )
        employee_profile = self.employee.profile
        employee_profile.organization = self.org
        employee_profile.role = "manager"
        employee_profile.user_status = "active"
        employee_profile.mfa_enabled = True
        employee_profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])

        self.client.force_authenticate(self.user)

        self.division = Division.objects.create(
            organization=self.org,
            name="Corporate Services",
            code="CORP-SVC",
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Operations",
            code="OPS",
        )

        self.property = Property.objects.create(
            organization=self.org,
            name="Maple Business Hub",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.OWNED,
            address="10 Independence Avenue, Lagos",
        )
        self.unit_room = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="MR-101",
            floor=1,
            area_sqft=320,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.unit_desk = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="DSK-014",
            floor=1,
            area_sqft=80,
            unit_category=Unit.UnitCategory.OFFICE,
            status=Unit.UnitStatus.AVAILABLE,
        )
        self.unit_suite = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="STE-301",
            floor=3,
            area_sqft=920,
            unit_category=Unit.UnitCategory.RETAIL,
            status=Unit.UnitStatus.AVAILABLE,
        )

        self.facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-MBH-001",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
            ownership_type=Facility.OwnershipType.OWNED,
        )
        self.floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=self.facility,
            name="Main Floor",
            floor_code="MF-1",
            floor_number=1,
        )
        self.zone = FacilityZone.objects.create(
            organization=self.org,
            facility=self.facility,
            floor=self.floor,
            name="North Wing",
            zone_code="NW-1",
            zone_type=FacilityZone.ZoneType.COMMERCIAL,
        )

        self.room_space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit_room,
            space_label="Board Room 101",
        )
        self.desk_space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit_desk,
            space_label="Desk 014",
        )
        self.suite_space = FacilityUnitSpace.objects.create(
            organization=self.org,
            facility=self.facility,
            zone=self.zone,
            unit=self.unit_suite,
            space_label="Tenant Suite 301",
        )

        self.room_profile, _ = ensure_space_profile_defaults(self.room_space)
        self.room_profile.space_type = FacilitySpaceProfile.SpaceType.MEETING_ROOM
        self.room_profile.capacity = 8
        self.room_profile.is_bookable = True
        self.room_profile.booking_requires_approval = False
        self.room_profile.requires_check_in = False
        self.room_profile.save(
            update_fields=[
                "space_type",
                "capacity",
                "is_bookable",
                "booking_requires_approval",
                "requires_check_in",
                "updated_at",
            ]
        )

        self.desk_profile, _ = ensure_space_profile_defaults(self.desk_space)
        self.desk_profile.space_type = FacilitySpaceProfile.SpaceType.DESK
        self.desk_profile.capacity = 1
        self.desk_profile.is_bookable = True
        self.desk_profile.booking_requires_approval = False
        self.desk_profile.requires_check_in = True
        self.desk_profile.save(
            update_fields=[
                "space_type",
                "capacity",
                "is_bookable",
                "booking_requires_approval",
                "requires_check_in",
                "updated_at",
            ]
        )

        self.suite_profile, _ = ensure_space_profile_defaults(self.suite_space)
        self.suite_profile.space_type = FacilitySpaceProfile.SpaceType.TENANT_SUITE
        self.suite_profile.capacity = 4
        self.suite_profile.is_bookable = False
        self.suite_profile.save(update_fields=["space_type", "capacity", "is_bookable", "updated_at"])

        self.customer = Customer.objects.create(
            organization=self.org,
            name="Summit Advisory Limited",
            email="admin@summit.example.com",
            phone="+2348011111111",
            support_ticketing_enabled=True,
        )
        self.contact_account = ContactAccount.objects.create(
            organization=self.org,
            entity_type=ContactAccount.EntityType.ORGANIZATION,
            legal_name="Summit Advisory Limited",
            email="facilities@summit.example.com",
            phone="+2348022222222",
            finance_customer=self.customer,
            is_active=True,
        )

    def test_tenant_allocation_create_syncs_tenant_profile_and_inventory(self):
        today = timezone.localdate()
        payload = {
            "facility_space": self.suite_space.id,
            "allocation_type": SpaceAllocation.AllocationType.TENANT,
            "tenant_contact_account": self.contact_account.id,
            "occupant_count": 3,
            "start_date": (today - timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=90)).isoformat(),
            "notes": "Allocate executive suite to Summit Advisory.",
        }

        response = self.client.post("/api/facility-management/space-occupancy/allocations/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        allocation = SpaceAllocation.objects.get(facility_space=self.suite_space)
        tenant_profile = TenantProfile.objects.get(facility_space=self.suite_space)
        lease = tenant_profile.lease_agreements.get()
        inventory = PropertyInventory.objects.get(unit=self.unit_suite)
        self.unit_suite.refresh_from_db()

        self.assertEqual(allocation.status, SpaceAllocation.Status.ACTIVE)
        self.assertEqual(allocation.tenant_customer_id, self.customer.id)
        self.assertEqual(allocation.allocated_by_id, self.user.id)
        self.assertEqual(tenant_profile.status, TenantProfile.Status.ACTIVE)
        self.assertEqual(tenant_profile.customer_id, self.customer.id)
        self.assertEqual(tenant_profile.facility_id, self.facility.id)
        self.assertEqual(lease.status, LeaseAgreement.Status.DRAFT)
        self.assertEqual(lease.property_id, self.property.id)
        self.assertEqual(lease.unit_id, self.unit_suite.id)
        self.assertEqual(inventory.status, PropertyInventory.InventoryStatus.LEASED)
        self.assertEqual(inventory.allocated_to, self.customer.name)
        self.assertEqual(self.unit_suite.status, Unit.UnitStatus.LEASED)

        tenants_response = self.client.get("/api/tenants/profiles/")
        self.assertEqual(tenants_response.status_code, status.HTTP_200_OK, tenants_response.data)
        self.assertEqual(tenants_response.data["count"], 1)
        self.assertEqual(tenants_response.data["results"][0]["resolved_display_name"], self.customer.name)

    def test_releasing_tenant_allocation_restores_inventory_to_available(self):
        today = timezone.localdate()
        allocation = SpaceAllocation.objects.create(
            organization=self.org,
            facility_space=self.suite_space,
            allocation_type=SpaceAllocation.AllocationType.TENANT,
            tenant_customer=self.customer,
            tenant_contact_account=self.contact_account,
            occupant_count=2,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            allocated_by=self.user,
        )
        ensure_allocation_defaults(allocation)
        sync_tenant_profile_for_allocation(allocation)
        sync_inventory_for_tenant_allocation(allocation)

        response = self.client.post(
            f"/api/facility-management/space-occupancy/allocations/{allocation.id}/release/",
            {"note": "Tenant requested early move-out."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        allocation.refresh_from_db()
        tenant_profile = TenantProfile.objects.get(facility_space=self.suite_space)
        inventory = PropertyInventory.objects.get(unit=self.unit_suite)
        self.unit_suite.refresh_from_db()

        self.assertEqual(allocation.status, SpaceAllocation.Status.ENDED)
        self.assertIsNotNone(allocation.released_at)
        self.assertEqual(tenant_profile.status, TenantProfile.Status.MOVED_OUT)
        self.assertEqual(inventory.status, PropertyInventory.InventoryStatus.AVAILABLE)
        self.assertEqual(self.unit_suite.status, Unit.UnitStatus.AVAILABLE)

    def test_booking_create_and_automation_handle_confirmation_and_no_show(self):
        now = timezone.now()

        create_response = self.client.post(
            "/api/facility-management/space-occupancy/bookings/",
            {
                "facility_space": self.room_space.id,
                "title": "Monthly leadership review",
                "purpose": "Executive operating review.",
                "start_at": (now + timedelta(hours=1)).isoformat(),
                "end_at": (now + timedelta(hours=2)).isoformat(),
                "attendee_count": 6,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED, create_response.data)

        created_booking = SpaceBooking.objects.get(title="Monthly leadership review")
        self.assertEqual(created_booking.status, SpaceBooking.Status.CONFIRMED)

        no_show_booking = SpaceBooking.objects.create(
            organization=self.org,
            facility_space=self.desk_space,
            title="Desk check-in test",
            requested_by=self.user,
            start_at=now - timedelta(minutes=45),
            end_at=now + timedelta(minutes=15),
            attendee_count=1,
            status=SpaceBooking.Status.CONFIRMED,
        )

        result = run_space_occupancy_automation(self.org)

        no_show_booking.refresh_from_db()
        self.assertEqual(no_show_booking.status, SpaceBooking.Status.NO_SHOW)
        self.assertGreaterEqual(result["bookings_no_show"], 1)

    def test_overview_returns_occupancy_snapshot(self):
        today = timezone.localdate()
        employee_allocation = SpaceAllocation.objects.create(
            organization=self.org,
            facility_space=self.room_space,
            allocation_type=SpaceAllocation.AllocationType.EMPLOYEE,
            employee=self.employee,
            occupant_count=2,
            start_date=today - timedelta(days=3),
            end_date=today + timedelta(days=10),
            allocated_by=self.user,
        )
        ensure_allocation_defaults(employee_allocation)

        tenant_allocation = SpaceAllocation.objects.create(
            organization=self.org,
            facility_space=self.suite_space,
            allocation_type=SpaceAllocation.AllocationType.TENANT,
            tenant_customer=self.customer,
            tenant_contact_account=self.contact_account,
            occupant_count=3,
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=90),
            allocated_by=self.user,
        )
        ensure_allocation_defaults(tenant_allocation)
        sync_tenant_profile_for_allocation(tenant_allocation)
        sync_inventory_for_tenant_allocation(tenant_allocation)

        SpaceBooking.objects.create(
            organization=self.org,
            facility_space=self.room_space,
            title="Investor presentation",
            requested_by=self.user,
            start_at=timezone.now() + timedelta(hours=2),
            end_at=timezone.now() + timedelta(hours=3),
            attendee_count=5,
            status=SpaceBooking.Status.CONFIRMED,
        )

        response = self.client.get("/api/facility-management/space-occupancy/overview/")

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["kpis"]["total_spaces"], 3)
        self.assertEqual(response.data["kpis"]["occupied_spaces"], 2)
        self.assertEqual(response.data["kpis"]["vacant_spaces"], 1)
        self.assertEqual(response.data["kpis"]["bookable_spaces"], 2)
        self.assertEqual(response.data["kpis"]["tenant_profiles_active"], 1)
        self.assertEqual(response.data["kpis"]["active_bookings"], 1)
        self.assertGreaterEqual(len(response.data["vacancy_watchlist"]), 1)
        self.assertGreaterEqual(len(response.data["tenant_watchlist"]), 1)

    def test_scheduled_task_runs_space_occupancy_automation(self):
        today = timezone.localdate()
        allocation = SpaceAllocation.objects.create(
            organization=self.org,
            facility_space=self.suite_space,
            allocation_type=SpaceAllocation.AllocationType.TENANT,
            tenant_customer=self.customer,
            tenant_contact_account=self.contact_account,
            occupant_count=2,
            start_date=today - timedelta(days=90),
            end_date=today - timedelta(days=1),
            status=SpaceAllocation.Status.ACTIVE,
            allocated_by=self.user,
        )
        sync_tenant_profile_for_allocation(allocation)
        sync_inventory_for_tenant_allocation(allocation)

        booking = SpaceBooking.objects.create(
            organization=self.org,
            facility_space=self.desk_space,
            title="Late desk booking",
            requested_by=self.user,
            start_at=timezone.now() - timedelta(minutes=50),
            end_at=timezone.now() + timedelta(minutes=10),
            attendee_count=1,
            status=SpaceBooking.Status.CONFIRMED,
        )

        result = run_scheduled_space_occupancy_workflows([self.org.id])

        allocation.refresh_from_db()
        booking.refresh_from_db()
        tenant_profile = TenantProfile.objects.get(facility_space=self.suite_space)
        inventory = PropertyInventory.objects.get(unit=self.unit_suite)
        self.unit_suite.refresh_from_db()

        self.assertEqual(result["organizations_processed"], 1)
        self.assertEqual(result["errors"], 0)
        self.assertEqual(allocation.status, SpaceAllocation.Status.ENDED)
        self.assertEqual(booking.status, SpaceBooking.Status.NO_SHOW)
        self.assertEqual(tenant_profile.status, TenantProfile.Status.MOVED_OUT)
        self.assertEqual(inventory.status, PropertyInventory.InventoryStatus.AVAILABLE)
        self.assertEqual(self.unit_suite.status, Unit.UnitStatus.AVAILABLE)
        self.assertGreaterEqual(result["allocations_ended"], 1)
        self.assertGreaterEqual(result["bookings_no_show"], 1)

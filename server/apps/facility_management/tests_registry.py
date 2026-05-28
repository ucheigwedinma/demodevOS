from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.properties.models import Property, Unit

from .models import Facility, FacilityFloor, FacilityZone

User = get_user_model()


class FacilityRegistryApiTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Facility Registry Org")
        self.user = User.objects.create_superuser(
            username="facility-registry-admin@example.com",
            email="facility-registry-admin@example.com",
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
            name="Maple Business Park",
            property_type=Property.PropertyType.BUILDING,
            classification=Property.Classification.LEASE,
            address="12A Admiralty Way, Lekki",
        )
        self.unit_1 = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="A-101",
            floor=1,
            area_sqft=840,
            status=Unit.UnitStatus.AVAILABLE,
        )

    def test_registry_hierarchy_crud_and_overview(self):
        create_facility = self.client.post(
            "/api/facility-management/registry/facilities/",
            {
                "property": self.property.id,
                "facility_code": "FAC-MBP-001",
                "facility_classification": Facility.FacilityClassification.COMMERCIAL,
                "ownership_type": Facility.OwnershipType.LEASED,
                "lease_party_name": "Lekki Landlords Ltd",
                "lease_start_date": "2025-01-01",
                "lease_end_date": "2030-12-31",
                "lease_amount": "5500000.00",
            },
            format="json",
        )
        self.assertEqual(create_facility.status_code, status.HTTP_201_CREATED, create_facility.data)
        facility_id = create_facility.data["id"]

        create_floor = self.client.post(
            "/api/facility-management/registry/floors/",
            {
                "facility": facility_id,
                "name": "Ground Floor",
                "floor_code": "GF",
                "floor_number": 0,
                "gross_area_sqft": "12000.00",
                "usage_type": "Retail and Access",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_floor.status_code, status.HTTP_201_CREATED, create_floor.data)
        floor_id = create_floor.data["id"]

        create_zone = self.client.post(
            "/api/facility-management/registry/zones/",
            {
                "facility": facility_id,
                "floor": floor_id,
                "name": "North Wing",
                "zone_code": "NW-01",
                "zone_type": FacilityZone.ZoneType.COMMERCIAL,
                "gross_area_sqft": "5000.00",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_zone.status_code, status.HTTP_201_CREATED, create_zone.data)
        zone_id = create_zone.data["id"]

        create_space = self.client.post(
            "/api/facility-management/registry/unit-spaces/",
            {
                "facility": facility_id,
                "zone": zone_id,
                "unit": self.unit_1.id,
                "space_label": "Showroom A1",
                "notes": "Flagship display suite",
            },
            format="json",
        )
        self.assertEqual(create_space.status_code, status.HTTP_201_CREATED, create_space.data)

        facilities_list = self.client.get("/api/facility-management/registry/facilities/")
        self.assertEqual(facilities_list.status_code, status.HTTP_200_OK, facilities_list.data)
        first_facility = facilities_list.data["results"][0]
        self.assertEqual(first_facility["facility_code"], "FAC-MBP-001")
        self.assertEqual(first_facility["floors_count"], 1)
        self.assertEqual(first_facility["zones_count"], 1)
        self.assertEqual(first_facility["unit_spaces_count"], 1)

        overview = self.client.get("/api/facility-management/registry/overview/")
        self.assertEqual(overview.status_code, status.HTTP_200_OK, overview.data)
        self.assertEqual(overview.data["kpis"]["facilities"], 1)
        self.assertEqual(overview.data["kpis"]["floors"], 1)
        self.assertEqual(overview.data["kpis"]["zones"], 1)
        self.assertEqual(overview.data["kpis"]["unit_spaces"], 1)

    def test_unit_space_rejects_mismatched_property_unit(self):
        facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-MBP-002",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
        )
        floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=facility,
            name="Level 1",
            floor_code="L1",
            floor_number=1,
        )
        zone = FacilityZone.objects.create(
            organization=self.org,
            facility=facility,
            floor=floor,
            name="South Wing",
            zone_code="SW-01",
            zone_type=FacilityZone.ZoneType.COMMERCIAL,
        )

        other_property = Property.objects.create(
            organization=self.org,
            name="Eko Residential Annex",
            property_type=Property.PropertyType.ESTATE,
            classification=Property.Classification.OWNED,
            address="77 Bourdillon Road, Ikoyi",
        )
        wrong_unit = Unit.objects.create(
            organization=self.org,
            property=other_property,
            unit_number="B-204",
            floor=2,
            area_sqft=1120,
            status=Unit.UnitStatus.AVAILABLE,
        )

        response = self.client.post(
            "/api/facility-management/registry/unit-spaces/",
            {
                "facility": facility.id,
                "zone": zone.id,
                "unit": wrong_unit.id,
                "space_label": "Invalid mapping",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("unit", response.data)

    def test_registry_units_lookup_returns_available_units_for_selected_facility(self):
        facility = Facility.objects.create(
            organization=self.org,
            property=self.property,
            facility_code="FAC-MBP-003",
            facility_classification=Facility.FacilityClassification.COMMERCIAL,
        )
        floor = FacilityFloor.objects.create(
            organization=self.org,
            facility=facility,
            name="Level 2",
            floor_code="L2",
            floor_number=2,
        )
        zone = FacilityZone.objects.create(
            organization=self.org,
            facility=facility,
            floor=floor,
            name="East Wing",
            zone_code="EW-01",
            zone_type=FacilityZone.ZoneType.COMMERCIAL,
        )

        available_unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="A-102",
            floor=1,
            area_sqft=920,
            status=Unit.UnitStatus.AVAILABLE,
        )
        already_mapped_unit = Unit.objects.create(
            organization=self.org,
            property=self.property,
            unit_number="A-103",
            floor=1,
            area_sqft=860,
            status=Unit.UnitStatus.AVAILABLE,
        )

        create_space = self.client.post(
            "/api/facility-management/registry/unit-spaces/",
            {
                "facility": facility.id,
                "zone": zone.id,
                "unit": already_mapped_unit.id,
                "space_label": "Mapped Suite",
            },
            format="json",
        )
        self.assertEqual(create_space.status_code, status.HTTP_201_CREATED, create_space.data)

        response = self.client.get(
            "/api/facility-management/registry/units/",
            {"facility": facility.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertIn(self.unit_1.id, returned_ids)
        self.assertIn(available_unit.id, returned_ids)
        self.assertNotIn(already_mapped_unit.id, returned_ids)

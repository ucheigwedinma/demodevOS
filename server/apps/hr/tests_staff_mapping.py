from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import EmployeeRecord, Position, PositionAssignment
from apps.settings.models import Department, Division


class StaffMappingSignalTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()

        self.org = Organization.objects.create(name="Staff Mapping Org")
        self.user = user_model.objects.create_user(
            username="staff-map-user",
            email="staff-map-user@example.com",
            password="pass1234",
            first_name="Mary",
            last_name="Stone",
        )

        UserProfile.objects.filter(user=self.user).update(
            organization=self.org,
            department=None,
            business_unit="",
            job_title="Engineer",
        )

        self.division_a = Division.objects.create(
            organization=self.org,
            name="Construction",
            code="CON",
        )
        self.division_b = Division.objects.create(
            organization=self.org,
            name="Operations",
            code="OPS",
        )
        self.department_a = Department.objects.create(
            division=self.division_a,
            name="Site Works",
            code="SITE",
        )
        self.department_b = Department.objects.create(
            division=self.division_b,
            name="Facilities",
            code="FAC",
        )
        self.position_a = Position.objects.create(
            organization=self.org,
            title="Site Engineer",
            code="POS-SITE-001",
            department=self.department_a,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
        )
        self.position_b = Position.objects.create(
            organization=self.org,
            title="Facilities Engineer",
            code="POS-FAC-001",
            department=self.department_b,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
        )

    def test_assignment_create_tags_profile_department_and_business_unit(self):
        PositionAssignment.objects.create(
            organization=self.org,
            user=self.user,
            position=self.position_a,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.department_id, self.department_a.id)
        self.assertEqual(profile.business_unit, self.division_a.name)

    def test_assignment_update_retags_profile_department_and_business_unit(self):
        assignment = PositionAssignment.objects.create(
            organization=self.org,
            user=self.user,
            position=self.position_a,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )

        assignment.position = self.position_b
        assignment.save(update_fields=["position"])

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.department_id, self.department_b.id)
        self.assertEqual(profile.business_unit, self.division_b.name)

    def test_assignment_delete_uses_fallback_then_clears_profile_mapping(self):
        primary_assignment = PositionAssignment.objects.create(
            organization=self.org,
            user=self.user,
            position=self.position_a,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )
        fallback_assignment = PositionAssignment.objects.create(
            organization=self.org,
            user=self.user,
            position=self.position_b,
            start_date=date(2026, 2, 20),
            is_primary=False,
            is_active=True,
        )

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.department_id, self.department_a.id)
        self.assertEqual(profile.business_unit, self.division_a.name)

        primary_assignment.delete()
        profile.refresh_from_db()
        self.assertEqual(profile.department_id, self.department_b.id)
        self.assertEqual(profile.business_unit, self.division_b.name)

        fallback_assignment.delete()
        profile.refresh_from_db()
        self.assertIsNone(profile.department_id)
        self.assertEqual(profile.business_unit, "")

    def test_employee_record_creation_preserves_profile_mapping_without_assignment(self):
        UserProfile.objects.filter(user=self.user).update(
            organization=self.org,
            department=self.department_a,
            business_unit="",
        )

        EmployeeRecord.objects.create(
            organization=self.org,
            user=self.user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.department_id, self.department_a.id)
        self.assertEqual(profile.business_unit, self.division_a.name)

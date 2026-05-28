from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import Position, PositionAssignment, SalaryStructure
from apps.settings.models import CostCenter, Department, Division


class PositionRoleAPITests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Position Role Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create(
            username="position-role-admin",
            email="position-role-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={"organization": self.org},
        )
        profile.organization = self.org
        profile.save(update_fields=["organization"])
        self.client.force_authenticate(self.admin)

        self.division = Division.objects.create(
            organization=self.org,
            name="Engineering",
            code="ENG",
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Structural Engineering",
            code="STR",
        )
        self.cost_center = CostCenter.objects.create(
            organization=self.org,
            department=self.department,
            code="CC-STR",
            name="Structural Engineering Cost Center",
            is_active=True,
        )

    def test_positions_can_share_a_single_role_template(self):
        role_response = self.client.post(
            "/api/hr/position-roles/",
            {
                "name": "Senior Structural Engineer",
                "grade": "Grade 4",
                "code": "ROLE-SSE",
                "description": "Functional template for senior structural engineering oversight.",
                "requirements": "COREN registered engineer with 8+ years experience.",
                "key_responsibilities": "- Lead weekly planning\n- Approve structural method statements",
                "hard_skills": ["AutoCAD", "Revit"],
                "soft_skills": ["Stakeholder Management", "Team Leadership"],
                "kpi_metrics": ["% milestones met on time", "Rework rate"],
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(role_response.status_code, 201)
        role_id = role_response.json()["id"]

        first_position = self.client.post(
            "/api/hr/positions/",
            {
                "role": role_id,
                "title": "Senior Structural Engineer - Project A",
                "code": "POS-SSE-A",
                "department": self.department.id,
                "cost_center": self.cost_center.id,
                "employment_type": "full_time",
                "level": "senior",
                "status": "active",
                "headcount_budget": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(first_position.status_code, 201)

        second_position = self.client.post(
            "/api/hr/positions/",
            {
                "role": role_id,
                "title": "Senior Structural Engineer - Project B",
                "code": "POS-SSE-B",
                "department": self.department.id,
                "cost_center": self.cost_center.id,
                "employment_type": "full_time",
                "level": "senior",
                "status": "active",
                "headcount_budget": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(second_position.status_code, 201)

        position_list = self.client.get("/api/hr/positions/")
        self.assertEqual(position_list.status_code, 200)
        payload = position_list.json()
        by_code = {row["code"]: row for row in payload["results"]}
        self.assertEqual(by_code["POS-SSE-A"]["role_name"], "Senior Structural Engineer")
        self.assertEqual(by_code["POS-SSE-B"]["role_code"], "ROLE-SSE")

        role_list = self.client.get("/api/hr/position-roles/")
        self.assertEqual(role_list.status_code, 200)
        role_row = next(row for row in role_list.json()["results"] if row["id"] == role_id)
        self.assertEqual(role_row["position_count"], 2)
        self.assertEqual(role_row["grade"], "Grade 4")

        role_detail = self.client.get(f"/api/hr/position-roles/{role_id}/")
        self.assertEqual(role_detail.status_code, 200)
        detail_payload = role_detail.json()
        self.assertEqual(detail_payload["hard_skills"], ["AutoCAD", "Revit"])
        self.assertEqual(
            detail_payload["soft_skills"],
            ["Stakeholder Management", "Team Leadership"],
        )
        self.assertEqual(
            detail_payload["kpi_metrics"],
            ["% milestones met on time", "Rework rate"],
        )

    def test_position_requires_cost_center(self):
        role_response = self.client.post(
            "/api/hr/position-roles/",
            {
                "name": "Senior Structural Engineer",
                "grade": "Grade 4",
                "code": "ROLE-SSE",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(role_response.status_code, 201)
        role_id = role_response.json()["id"]

        response = self.client.post(
            "/api/hr/positions/",
            {
                "role": role_id,
                "title": "Senior Structural Engineer - Project C",
                "code": "POS-SSE-C",
                "department": self.department.id,
                "employment_type": "full_time",
                "level": "senior",
                "status": "active",
                "headcount_budget": 1,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cost_center", response.data)

    def test_position_slot_reporting_line_and_salary_band_data(self):
        salary_structure = SalaryStructure.objects.create(
            organization=self.org,
            name="Grade 4 Band",
            code="G4",
            grade_level=4,
            min_salary="7500000.00",
            max_salary="12000000.00",
            currency="NGN",
            is_active=True,
        )
        role_response = self.client.post(
            "/api/hr/position-roles/",
            {
                "name": "Site Engineering Manager",
                "grade": "Grade 4",
                "code": "ROLE-SEM",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(role_response.status_code, 201)
        role_id = role_response.json()["id"]

        manager_position = Position.objects.create(
            organization=self.org,
            role_id=role_id,
            title="Engineering Manager",
            code="POS-MGR-001",
            department=self.department,
            cost_center=self.cost_center,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.MANAGER,
            status=Position.Status.ACTIVE,
            slot_status=Position.SlotStatus.VACANT,
            headcount_budget=1,
            is_active=True,
        )
        subordinate_position = Position.objects.create(
            organization=self.org,
            role_id=role_id,
            title="Senior Site Engineer - Project A",
            code="POS-SSE-001",
            department=self.department,
            reports_to=manager_position,
            cost_center=self.cost_center,
            salary_structure=salary_structure,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
            status=Position.Status.ACTIVE,
            slot_status=Position.SlotStatus.VACANT,
            headcount_budget=1,
            is_active=True,
        )

        position_list = self.client.get("/api/hr/positions/")
        self.assertEqual(position_list.status_code, 200)
        by_code = {row["code"]: row for row in position_list.json()["results"]}
        subordinate_row = by_code[subordinate_position.code]
        self.assertEqual(subordinate_row["reports_to_title"], manager_position.title)
        self.assertEqual(subordinate_row["salary_structure"], salary_structure.id)
        self.assertEqual(subordinate_row["salary_structure_name"], salary_structure.name)
        self.assertEqual(subordinate_row["salary_range_min"], "7500000.00")
        self.assertEqual(subordinate_row["salary_range_max"], "12000000.00")
        self.assertEqual(subordinate_row["salary_currency"], "NGN")
        self.assertEqual(
            subordinate_row["salary_band_link"],
            f"/hr/salary-structures?focus={salary_structure.id}",
        )
        self.assertEqual(subordinate_row["slot_status"], Position.SlotStatus.VACANT)

        assignee = get_user_model().objects.create(
            username="slot-assignee",
            email="slot-assignee@example.com",
            is_active=True,
        )
        UserProfile.objects.get_or_create(
            user=assignee,
            defaults={"organization": self.org},
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=assignee,
            position=subordinate_position,
            start_date=date(2026, 3, 15),
            is_primary=True,
            is_active=True,
        )

        refreshed_list = self.client.get("/api/hr/positions/")
        self.assertEqual(refreshed_list.status_code, 200)
        refreshed_by_code = {row["code"]: row for row in refreshed_list.json()["results"]}
        self.assertEqual(
            refreshed_by_code[subordinate_position.code]["slot_status"],
            Position.SlotStatus.FILLED,
        )
        self.assertEqual(
            refreshed_by_code[manager_position.code]["direct_report_count"],
            1,
        )

    def test_employee_can_view_own_job_description_without_salary_band(self):
        salary_structure = SalaryStructure.objects.create(
            organization=self.org,
            name="Grade 3 Band",
            code="G3",
            grade_level=3,
            min_salary="5000000.00",
            max_salary="8000000.00",
            currency="NGN",
            is_active=True,
        )
        role = PositionRole.objects.create(
            organization=self.org,
            name="Site Supervisor",
            code="ROLE-SS",
            is_active=True,
        )
        position = Position.objects.create(
            organization=self.org,
            role=role,
            title="Site Supervisor - Project Z",
            code="POS-SS-001",
            department=self.department,
            cost_center=self.cost_center,
            salary_structure=salary_structure,
            description="Supervise daily construction activity and coordinate subcontractors.",
            requirements="HND Civil Engineering and 5+ years site supervision.",
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
            status=Position.Status.ACTIVE,
            slot_status=Position.SlotStatus.FILLED,
            headcount_budget=1,
            is_active=True,
        )

        employee = get_user_model().objects.create(
            username="site-worker-01",
            email="site-worker-01@example.com",
            is_active=True,
        )
        employee_profile, _ = UserProfile.objects.get_or_create(
            user=employee,
            defaults={"organization": self.org},
        )
        employee_profile.organization = self.org
        employee_profile.save(update_fields=["organization"])
        PositionAssignment.objects.create(
            organization=self.org,
            user=employee,
            position=position,
            start_date=date(2026, 3, 15),
            is_primary=True,
            is_active=True,
        )

        self.client.force_authenticate(employee)
        response = self.client.get("/api/hr/positions/my-position/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["id"], position.id)
        self.assertEqual(payload["description"], position.description)
        self.assertEqual(payload["requirements"], position.requirements)
        self.assertIsNone(payload["salary_structure"])
        self.assertIsNone(payload["salary_structure_name"])
        self.assertIsNone(payload["salary_range_min"])
        self.assertIsNone(payload["salary_range_max"])
        self.assertIsNone(payload["salary_currency"])
        self.assertIsNone(payload["salary_band_link"])

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import (
    CompensationRecord,
    Position,
    PositionAssignment,
    SalaryStructure,
    Team,
)
from apps.projects.models import Project, ProjectPhase, ProjectTask
from apps.settings.models import Department, Division


class HROrgChartViewTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Org Chart Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="hr-admin",
            email="hr-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.admin)

        self.manager = user_model.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="pass1234",
            first_name="Ava",
            last_name="Manager",
        )
        self.worker = user_model.objects.create_user(
            username="worker",
            email="worker@example.com",
            password="pass1234",
            first_name="Noah",
            last_name="Worker",
        )

        self.division = Division.objects.create(
            organization=self.org,
            name="Development",
            code="DEV",
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Construction",
            code="CNS",
        )
        self.team = Team.objects.create(
            organization=self.org,
            department=self.department,
            name="Block A Team",
            code="BLKA",
        )

        self.manager_profile = self._upsert_profile(
            self.manager,
            department=self.department,
            phone="+23490000001",
            office_location="Lagos HQ",
            employee_id="MGR-001",
        )
        self.worker_profile = self._upsert_profile(
            self.worker,
            department=self.department,
            phone="+23490000002",
            office_location="Site A",
            employee_id="WRK-001",
            reporting_manager=self.manager,
        )

    def _upsert_profile(self, user, **values):
        defaults = {"organization": self.org, **values}
        profile, created = UserProfile.objects.get_or_create(user=user, defaults=defaults)
        if not created:
            for key, value in defaults.items():
                setattr(profile, key, value)
            profile.save()
        return profile

    def test_org_chart_returns_vacancy_and_detail_fields(self):
        today = timezone.localdate()

        manager_position = Position.objects.create(
            organization=self.org,
            title="Site Manager",
            code="POS-MGR",
            department=self.department,
            team=self.team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.MANAGER,
        )
        worker_position = Position.objects.create(
            organization=self.org,
            title="Site Engineer",
            code="POS-ENG",
            department=self.department,
            team=self.team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
        )
        vacant_position = Position.objects.create(
            organization=self.org,
            title="QA Engineer",
            code="POS-QA",
            department=self.department,
            team=self.team,
            employment_type=Position.EmploymentType.CONTRACT,
            level=Position.Level.MID,
        )

        PositionAssignment.objects.create(
            organization=self.org,
            user=self.manager,
            position=manager_position,
            start_date=today - timedelta(days=180),
            is_primary=True,
            is_active=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=self.worker,
            position=worker_position,
            start_date=today - timedelta(days=30),
            is_primary=True,
            is_active=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=self.worker,
            position=manager_position,
            start_date=today - timedelta(days=7),
            is_primary=False,
            is_active=True,
        )

        SalaryStructure.objects.create(
            organization=self.org,
            name="Band A",
            code="A",
            grade_level=1,
            min_salary=Decimal("2000.00"),
            max_salary=Decimal("4000.00"),
            currency="NGN",
            is_active=True,
        )
        CompensationRecord.objects.create(
            organization=self.org,
            user=self.worker,
            effective_date=today - timedelta(days=5),
            base_salary=Decimal("2500.00"),
            total_package=Decimal("2500.00"),
            status=CompensationRecord.Status.ACTIVE,
        )

        project = Project.objects.create(
            organization=self.org,
            name="Lakeside Residences",
            status=Project.Status.IN_PROGRESS,
        )
        phase = ProjectPhase.objects.create(
            organization=self.org,
            project=project,
            name="Foundation",
            status=ProjectPhase.Status.IN_PROGRESS,
        )
        task = ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name="Rebar placement",
            status=ProjectTask.Status.IN_PROGRESS,
            assigned_user=self.worker,
            assigned_to=self.worker.get_full_name(),
        )

        response = self.client.get("/api/hr/org-chart/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data)

        team_positions = data[0]["departments"][0]["teams"][0]["positions"]
        by_code = {position["code"]: position for position in team_positions}

        self.assertFalse(by_code["POS-ENG"]["is_vacant"])
        self.assertTrue(by_code["POS-QA"]["is_vacant"])

        worker_node = by_code["POS-ENG"]["assigned_users"][0]
        manager_node = by_code["POS-MGR"]["assigned_users"][0]

        self.assertEqual(worker_node["name"], self.worker.get_full_name())
        self.assertEqual(worker_node["department_name"], self.department.name)
        self.assertEqual(worker_node["employment_type"], Position.EmploymentType.FULL_TIME)
        self.assertEqual(worker_node["project_assignment_count"], 1)
        self.assertEqual(worker_node["project_assignments"][0]["task_name"], task.name)
        self.assertIn("Band A", worker_node["salary_band"])
        self.assertTrue(worker_node["acting_roles"])
        self.assertEqual(manager_node["direct_report_count"], 1)

    def test_reporting_line_update_endpoint(self):
        user_model = get_user_model()
        new_manager = user_model.objects.create_user(
            username="new-manager",
            email="new-manager@example.com",
            password="pass1234",
            first_name="Zara",
            last_name="Lead",
        )
        self._upsert_profile(
            new_manager,
            department=self.department,
            phone="+23490000003",
            office_location="Abuja",
            employee_id="MGR-002",
        )

        response = self.client.patch(
            f"/api/hr/reporting-lines/{self.worker.id}/",
            {"reports_to": new_manager.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        self.worker_profile.refresh_from_db()
        self.assertEqual(self.worker_profile.reporting_manager_id, new_manager.id)

        invalid = self.client.patch(
            f"/api/hr/reporting-lines/{self.worker.id}/",
            {"reports_to": self.worker.id},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import Position, PositionRole, Team
from apps.projects.models import Project
from apps.settings.models import CostCenter, Department, Division


class ProjectRoleLibraryProvisioningTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Role Library Org")
        user_model = get_user_model()
        self.user = user_model.objects.create(
            username="role-library-admin",
            email="role-library-admin@example.com",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={"organization": self.org},
        )
        profile.organization = self.org
        profile.role = "admin"
        profile.save(update_fields=["organization", "role"])
        self.client.force_authenticate(self.user)

        self.division = Division.objects.create(
            organization=self.org,
            name="Construction",
            code="CON",
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Site Operations",
            code="SITE",
        )
        self.other_department = Department.objects.create(
            division=self.division,
            name="Design",
            code="DSN",
        )
        self.team = Team.objects.create(
            organization=self.org,
            department=self.department,
            name="Northgate Site Team",
            code="TEAM-NORTH",
            team_type=Team.TeamType.PROJECT_BASED,
            is_active=True,
        )
        self.cost_center = CostCenter.objects.create(
            organization=self.org,
            department=self.department,
            code="CC-SITE",
            name="Site Operations Cost Center",
            is_active=True,
        )
        self.other_cost_center = CostCenter.objects.create(
            organization=self.org,
            department=self.other_department,
            code="CC-DSN",
            name="Design Cost Center",
            is_active=True,
        )
        self.other_team = Team.objects.create(
            organization=self.org,
            department=self.other_department,
            name="Design Team",
            code="TEAM-DSN",
            team_type=Team.TeamType.PERMANENT,
            is_active=True,
        )
        self.role = PositionRole.objects.create(
            organization=self.org,
            name="Site Supervisor",
            code="SUP",
            description="Leads site execution and daily work plans.",
            requirements="8+ years supervision experience.",
            is_active=True,
        )
        self.project = Project.objects.create(
            organization=self.org,
            name="Northgate Estate Phase 1",
            status=Project.Status.PLANNING,
        )

    def test_project_role_library_provisions_multiple_position_slots(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/provision-role-library/",
            {
                "append_project_name": True,
                "entries": [
                    {
                        "role": self.role.id,
                        "department": self.department.id,
                        "cost_center": self.cost_center.id,
                        "team": self.team.id,
                        "quantity": 3,
                        "employment_type": Position.EmploymentType.FULL_TIME,
                        "level": Position.Level.SENIOR,
                        "criticality_score": 82,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_count"], 3)

        created_positions = Position.objects.filter(
            organization=self.org,
            role=self.role,
            department=self.department,
            team=self.team,
            title=f"{self.role.name} — {self.project.name}",
        ).order_by("id")
        self.assertEqual(created_positions.count(), 3)

        codes = list(created_positions.values_list("code", flat=True))
        self.assertEqual(len(set(codes)), 3)
        for position in created_positions:
            self.assertEqual(position.description, self.role.description)
            self.assertEqual(position.requirements, self.role.requirements)
            self.assertEqual(position.headcount_budget, 1)
            self.assertEqual(position.slot_status, Position.SlotStatus.PROPOSED)
            self.assertEqual(position.cost_center_id, self.cost_center.id)

    def test_project_role_library_rejects_team_department_mismatch(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/provision-role-library/",
            {
                "entries": [
                    {
                        "role": self.role.id,
                        "department": self.department.id,
                        "cost_center": self.cost_center.id,
                        "team": self.other_team.id,
                        "quantity": 2,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)
        self.assertEqual(
            Position.objects.filter(organization=self.org, role=self.role).count(),
            0,
        )

    def test_project_role_library_rejects_cost_center_department_mismatch(self):
        response = self.client.post(
            f"/api/projects/{self.project.id}/provision-role-library/",
            {
                "entries": [
                    {
                        "role": self.role.id,
                        "department": self.department.id,
                        "cost_center": self.other_cost_center.id,
                        "quantity": 1,
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.data)
        self.assertEqual(
            Position.objects.filter(organization=self.org, role=self.role).count(),
            0,
        )

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import Position, PositionAssignment, PositionBudget, Team
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectPhase, ProjectTask
from apps.settings.models import Department, Division


class ProjectBasedTeamDissolutionTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Dissolution Org")
        user_model = get_user_model()
        self.user = user_model.objects.create(
            username="project-team-user",
            email="project-team-user@example.com",
            first_name="Tayo",
            last_name="Builder",
            is_active=True,
        )

        self.division = Division.objects.create(
            organization=self.org,
            name="Construction",
            code="CON",
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Site Delivery",
            code="SITE",
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={"organization": self.org},
        )
        profile.organization = self.org
        profile.department = self.department
        profile.save(update_fields=["organization", "department"])

        self.admin = user_model.objects.create(
            username="project-team-admin",
            email="project-team-admin@example.com",
            first_name="Ayo",
            last_name="Admin",
            is_active=True,
        )
        admin_profile, _ = UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={"organization": self.org},
        )
        admin_profile.organization = self.org
        admin_profile.role = "admin"
        admin_profile.department = self.department
        admin_profile.job_title = "HR Business Partner"
        admin_profile.save(update_fields=["organization", "role", "department", "job_title"])

        self.team = Team.objects.create(
            organization=self.org,
            department=self.department,
            name="Northgate Site Team",
            code="TM-NORTHGATE",
            team_type=Team.TeamType.PROJECT_BASED,
            is_active=True,
        )
        self.position = Position.objects.create(
            organization=self.org,
            title="Site Engineer",
            code="POS-SITE-ENG",
            department=self.department,
            team=self.team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=self.user,
            position=self.position,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )

    def _create_project_with_single_task(self, *, name, status=Project.Status.IN_PROGRESS, task_status=ProjectTask.Status.PENDING):
        project = Project.objects.create(
            organization=self.org,
            name=name,
            status=status,
        )
        phase = ProjectPhase.objects.create(
            organization=self.org,
            project=project,
            name="Execution",
            status=ProjectPhase.Status.IN_PROGRESS,
        )
        task = ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name=f"{name} task",
            assigned_user=self.user,
            status=task_status,
            estimated_effort_hours="8.0",
        )
        return project, phase, task

    def test_project_based_team_auto_archives_on_task_completion_100_percent(self):
        _, _, task = self._create_project_with_single_task(
            name="Northgate Mall",
            task_status=ProjectTask.Status.PENDING,
        )
        self.team.refresh_from_db()
        self.assertTrue(self.team.is_active)

        task.status = ProjectTask.Status.COMPLETED
        task.save(update_fields=["status"])

        self.team.refresh_from_db()
        self.assertFalse(self.team.is_active)

    def test_project_based_team_not_archived_when_other_active_project_work_exists(self):
        _, _, task = self._create_project_with_single_task(
            name="Northgate Mall",
            task_status=ProjectTask.Status.PENDING,
        )
        self._create_project_with_single_task(
            name="Riverside Estate",
            task_status=ProjectTask.Status.IN_PROGRESS,
        )

        task.status = ProjectTask.Status.COMPLETED
        task.save(update_fields=["status"])

        self.team.refresh_from_db()
        self.assertTrue(self.team.is_active)

    def test_project_based_team_archives_when_project_marked_completed(self):
        project, _, _ = self._create_project_with_single_task(
            name="Westfield Towers",
            task_status=ProjectTask.Status.PENDING,
        )
        self.team.refresh_from_db()
        self.assertTrue(self.team.is_active)

        project.status = Project.Status.COMPLETED
        project.save(update_fields=["status"])

        self.team.refresh_from_db()
        self.assertFalse(self.team.is_active)

    def test_project_completion_archives_project_position_budget_and_notifies_hr(self):
        project, _, task = self._create_project_with_single_task(
            name="Harbor View Residences",
            task_status=ProjectTask.Status.PENDING,
        )
        position_budget = PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            position=self.position,
            fiscal_period_label="Harbor View Residences Phase 1",
            fiscal_year=2026,
            budget_source=PositionBudget.BudgetSource.PROJECT_FUNDING,
            currency="NGN",
            approved_headcount=1,
            filled_headcount=1,
            budget_amount="15000.00",
            status=PositionBudget.Status.APPROVED,
            notes="Initial project staffing budget.",
        )

        task.status = ProjectTask.Status.COMPLETED
        task.save(update_fields=["status"])

        position_budget.refresh_from_db()
        self.assertEqual(position_budget.status, PositionBudget.Status.FROZEN)
        self.assertIn("Project wind-down archive", position_budget.notes)
        self.assertTrue(
            Notification.objects.filter(
                organization=self.org,
                recipient=self.admin,
                category=Notification.Category.HR_LIFECYCLE,
                title__icontains=project.name,
            ).exists()
        )

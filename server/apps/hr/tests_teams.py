from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import (
    AttendanceLog,
    EmployeeRecord,
    LeaveRequest,
    LeaveType,
    Position,
    PositionAssignment,
    Team,
)
from apps.projects.models import Project, ProjectCostEntry, ProjectMilestone, ProjectPhase, ProjectTask
from apps.settings.models import Department, Division


class TeamAPITests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Team API Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create(
            username="team-admin",
            email="team-admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self._set_profile(self.admin)
        self.client.force_authenticate(self.admin)

        self.lead = user_model.objects.create(
            username="team-lead",
            email="team-lead@example.com",
            first_name="Nadia",
            last_name="Lawson",
        )
        self._set_profile(self.lead)
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
        self.legal_department = Department.objects.create(
            division=self.division,
            name="Legal",
            code="LGL",
        )

    def _set_profile(self, user, department=None):
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "organization": self.org,
            },
        )
        profile.organization = self.org
        profile.department = department
        profile.save(update_fields=["organization", "department"])

    def _create_roster_data(self, team):
        user_model = get_user_model()
        active_member = user_model.objects.create(
            username="active-member",
            email="active-member@example.com",
            first_name="Amina",
            last_name="Udeh",
        )
        leave_member = user_model.objects.create(
            username="leave-member",
            email="leave-member@example.com",
            first_name="David",
            last_name="Kim",
        )
        cross_member = user_model.objects.create(
            username="cross-member",
            email="cross-member@example.com",
            first_name="Lara",
            last_name="Stone",
        )

        self._set_profile(active_member, department=self.department)
        self._set_profile(leave_member, department=self.department)
        self._set_profile(cross_member, department=self.legal_department)

        active_employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=active_member,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        leave_employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=leave_member,
            employment_status=EmployeeRecord.EmploymentStatus.ON_LEAVE,
        )
        EmployeeRecord.objects.create(
            organization=self.org,
            user=cross_member,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        other_team = Team.objects.create(
            organization=self.org,
            department=self.department,
            name="HQ Core Team",
            code="TM-HQ-CORE",
            team_type=Team.TeamType.PERMANENT,
        )

        surveyor = Position.objects.create(
            organization=self.org,
            title="Senior Surveyor",
            code="POS-SURV-001",
            department=self.department,
            team=team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
        )
        architect = Position.objects.create(
            organization=self.org,
            title="Junior Architect",
            code="POS-ARCH-001",
            department=self.department,
            team=team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.JUNIOR,
        )
        legal_liaison = Position.objects.create(
            organization=self.org,
            title="Legal Liaison",
            code="POS-LGL-001",
            department=self.department,
            team=team,
            employment_type=Position.EmploymentType.CONTRACT,
            level=Position.Level.MID,
        )
        hq_manager = Position.objects.create(
            organization=self.org,
            title="HQ Program Manager",
            code="POS-HQ-001",
            department=self.department,
            team=other_team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.MANAGER,
        )

        PositionAssignment.objects.create(
            organization=self.org,
            user=active_member,
            position=surveyor,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=leave_member,
            position=architect,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=cross_member,
            position=hq_manager,
            start_date=date(2026, 3, 1),
            is_primary=True,
            is_active=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=cross_member,
            position=legal_liaison,
            start_date=date(2026, 3, 5),
            is_primary=False,
            is_active=True,
        )

        project = Project.objects.create(
            organization=self.org,
            name="Northgate Mall",
            status=Project.Status.IN_PROGRESS,
        )
        phase = ProjectPhase.objects.create(
            organization=self.org,
            project=project,
            name="Foundation Works",
            status=ProjectPhase.Status.IN_PROGRESS,
        )

        ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name="Set-out baseline points",
            assigned_user=active_member,
            status=ProjectTask.Status.IN_PROGRESS,
            due_date=date(2026, 3, 20),
            estimated_effort_hours=Decimal("32.0"),
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name="Design coordination closeout",
            assigned_user=leave_member,
            status=ProjectTask.Status.PENDING,
            due_date=date(2026, 3, 1),
            estimated_effort_hours=Decimal("12.0"),
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name="QA report finalization",
            assigned_user=active_member,
            status=ProjectTask.Status.COMPLETED,
            completed_date=date(2026, 3, 8),
            estimated_effort_hours=Decimal("8.0"),
        )

        ProjectMilestone.objects.create(
            organization=self.org,
            phase=phase,
            name="Foundation Approval",
            target_date=date(2026, 3, 2),
            is_completed=False,
        )
        ProjectMilestone.objects.create(
            organization=self.org,
            phase=phase,
            name="Steel Fixing Signoff",
            target_date=date(2026, 3, 28),
            is_completed=True,
            completed_date=date(2026, 3, 25),
        )
        ProjectMilestone.objects.create(
            organization=self.org,
            phase=phase,
            name="Concrete Pour Clearance",
            target_date=date(2026, 3, 18),
            is_completed=False,
        )

        today = timezone.localdate()
        AttendanceLog.objects.create(
            organization=self.org,
            employee=active_employee,
            date=today,
            status=AttendanceLog.Status.PRESENT,
            total_hours=Decimal("8.00"),
        )
        AttendanceLog.objects.create(
            organization=self.org,
            employee=leave_employee,
            date=today,
            status=AttendanceLog.Status.ON_LEAVE,
            total_hours=Decimal("0.00"),
        )

        ProjectCostEntry.objects.create(
            organization=self.org,
            phase=phase,
            description="Team petty cash - site fuel and supplies",
            amount=Decimal("2500.00"),
            date=today,
            category=ProjectCostEntry.Category.OTHER,
            reference_number="HOOK:hr_team_petty_cash:test:1",
        )

    def test_create_team_exposes_identity_and_functional_parent_fields(self):
        create_response = self.client.post(
            "/api/hr/teams/",
            {
                "name": "Northgate Mall Foundation Team",
                "code": "TM-NGM-FOUND",
                "department": self.department.id,
                "team_type": Team.TeamType.PROJECT_BASED,
                "lead": self.lead.id,
                "description": "Delivers all foundation-stage activities for Northgate Mall.",
                "is_active": True,
                "sort_order": 1,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["team_type"], Team.TeamType.PROJECT_BASED)
        team_id = create_response.json()["id"]
        team = Team.objects.get(id=team_id)
        self._create_roster_data(team)

        list_response = self.client.get("/api/hr/teams/")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        team_row = next(
            row
            for row in payload["results"]
            if row["name"] == "Northgate Mall Foundation Team"
        )
        self.assertEqual(team_row["department_name"], "Structural Engineering")
        self.assertEqual(team_row["business_unit_id"], self.division.id)
        self.assertEqual(team_row["business_unit_name"], "Engineering")
        self.assertEqual(team_row["team_type"], Team.TeamType.PROJECT_BASED)
        self.assertEqual(team_row["team_type_display"], "Project-Based")
        self.assertEqual(team_row["lead_name"], self.lead.get_full_name())

        detail_response = self.client.get(f"/api/hr/teams/{team_id}/")
        self.assertEqual(detail_response.status_code, 200)
        detail_payload = detail_response.json()
        self.assertEqual(len(detail_payload["member_roster"]), 3)

        roster = {
            member["full_name"]: member
            for member in detail_payload["member_roster"]
        }
        self.assertEqual(roster["Amina Udeh"]["role_title"], "Senior Surveyor")
        self.assertEqual(roster["Amina Udeh"]["availability_status"], "active")

        self.assertEqual(roster["David Kim"]["role_title"], "Junior Architect")
        self.assertEqual(roster["David Kim"]["availability_status"], "on_leave")

        self.assertEqual(roster["Lara Stone"]["availability_status"], "reassigned")
        self.assertEqual(roster["Lara Stone"]["is_cross_functional"], True)
        self.assertEqual(roster["Lara Stone"]["home_department_name"], "Legal")

        performance = detail_payload["operational_performance"]
        self.assertEqual(len(performance["active_project_links"]), 1)
        self.assertEqual(performance["active_project_links"][0]["project_name"], "Northgate Mall")
        self.assertGreater(performance["workload"]["workload_percent"], 0)
        self.assertEqual(performance["milestone_progress"]["total_milestones"], 3)
        self.assertEqual(performance["milestone_progress"]["health"], "delayed")

        automation = detail_payload["automation_triggers"]
        self.assertIn("timesheets", automation)
        self.assertIn("expense_claims", automation)
        self.assertIn("kpis", automation)

        self.assertEqual(automation["timesheets"]["data_field"], "Total Hours Logged")
        self.assertGreater(automation["timesheets"]["total_hours_logged"], 0)
        self.assertGreater(automation["timesheets"]["billable_hours"], 0)
        self.assertEqual(automation["timesheets"]["trigger_status"], "triggered")

        self.assertEqual(automation["expense_claims"]["data_field"], "Team Petty Cash")
        self.assertEqual(automation["expense_claims"]["trigger_status"], "triggered")
        self.assertGreater(automation["expense_claims"]["team_petty_cash"], 0)
        self.assertGreaterEqual(automation["expense_claims"]["reimbursement_item_count"], 1)

        self.assertEqual(automation["kpis"]["data_field"], "Team Success Rate")
        self.assertFalse(automation["kpis"]["high_performance_tag"])
        self.assertEqual(automation["kpis"]["trigger_status"], "pending")

    def test_team_type_defaults_to_permanent(self):
        create_response = self.client.post(
            "/api/hr/teams/",
            {
                "name": "Payroll Team",
                "code": "TM-PAYROLL",
                "department": self.department.id,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)

        team = Team.objects.get(name="Payroll Team")
        self.assertEqual(team.team_type, Team.TeamType.PERMANENT)

    def test_kpi_trigger_marks_high_performance_when_threshold_met(self):
        create_response = self.client.post(
            "/api/hr/teams/",
            {
                "name": "Foundation Delivery Team",
                "code": "TM-FOUND",
                "department": self.department.id,
                "team_type": Team.TeamType.PROJECT_BASED,
                "lead": self.lead.id,
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        team_id = create_response.json()["id"]
        team = Team.objects.get(id=team_id)
        self._create_roster_data(team)

        ProjectMilestone.objects.all().update(
            is_completed=True,
            completed_date=date(2026, 3, 1),
        )

        detail_response = self.client.get(f"/api/hr/teams/{team_id}/")
        self.assertEqual(detail_response.status_code, 200)
        kpi_trigger = detail_response.json()["automation_triggers"]["kpis"]
        self.assertTrue(kpi_trigger["high_performance_tag"])
        self.assertEqual(kpi_trigger["trigger_status"], "triggered")

    def test_member_picker_sync_adds_members_and_blocks_locked_removals(self):
        team = Team.objects.create(
            organization=self.org,
            department=self.department,
            name="Site Team",
            code="TM-SITE",
            team_type=Team.TeamType.PROJECT_BASED,
            lead=self.lead,
            is_active=True,
        )

        user_model = get_user_model()
        locked_user = user_model.objects.create(
            username="locked-member",
            email="locked-member@example.com",
            first_name="Locked",
            last_name="Member",
        )
        available_user = user_model.objects.create(
            username="available-member",
            email="available-member@example.com",
            first_name="Available",
            last_name="Member",
        )
        self._set_profile(locked_user, department=self.department)
        self._set_profile(available_user, department=self.department)

        locked_record = EmployeeRecord.objects.create(
            organization=self.org,
            user=locked_user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        available_record = EmployeeRecord.objects.create(
            organization=self.org,
            user=available_user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        locked_position = Position.objects.create(
            organization=self.org,
            title="Site Engineer",
            code="POS-SITE-LOCK",
            department=self.department,
            team=team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=locked_user,
            position=locked_position,
            start_date=timezone.localdate(),
            is_primary=True,
            is_active=True,
        )

        picker_response = self.client.get(f"/api/hr/teams/{team.id}/member-picker/")
        self.assertEqual(picker_response.status_code, 200)
        picker_payload = picker_response.json()
        assigned_by_user = {row["user_id"]: row for row in picker_payload["assigned"]}
        available_by_user = {row["user_id"]: row for row in picker_payload["available"]}
        self.assertIn(locked_user.id, assigned_by_user)
        self.assertTrue(assigned_by_user[locked_user.id]["is_locked"])
        self.assertIn(available_user.id, available_by_user)
        self.assertFalse(available_by_user[available_user.id]["is_locked"])
        self.assertEqual(assigned_by_user[locked_user.id]["employee_record_id"], locked_record.id)
        self.assertEqual(available_by_user[available_user.id]["employee_record_id"], available_record.id)

        blocked_sync = self.client.post(
            f"/api/hr/teams/{team.id}/sync-member-picker/",
            {"user_ids": [available_user.id]},
            format="json",
        )
        self.assertEqual(blocked_sync.status_code, 400)
        self.assertIn("Cannot remove locked members", str(blocked_sync.json()))

        sync_response = self.client.post(
            f"/api/hr/teams/{team.id}/sync-member-picker/",
            {"user_ids": [locked_user.id, available_user.id]},
            format="json",
        )
        self.assertEqual(sync_response.status_code, 200)
        synced_payload = sync_response.json()
        synced_assigned = {row["user_id"]: row for row in synced_payload["assigned"]}
        self.assertIn(available_user.id, synced_assigned)
        self.assertTrue(synced_assigned[available_user.id]["is_picker_managed"])

        picker_assignments = PositionAssignment.objects.filter(
            organization=self.org,
            user=available_user,
            position__team=team,
            is_active=True,
            notes="Managed by Team dynamic member picker.",
        )
        self.assertTrue(picker_assignments.exists())

    def test_leave_request_approval_requires_assigned_team_lead(self):
        user_model = get_user_model()
        team_lead = user_model.objects.create(
            username="site-team-lead",
            email="site-team-lead@example.com",
            first_name="Grace",
            last_name="Leader",
        )
        outsider_manager = user_model.objects.create(
            username="outside-manager",
            email="outside-manager@example.com",
            first_name="Omar",
            last_name="Manager",
        )
        worker = user_model.objects.create(
            username="site-worker",
            email="site-worker@example.com",
            first_name="Sam",
            last_name="Worker",
        )

        self._set_profile(team_lead, department=self.department)
        self._set_profile(outsider_manager, department=self.department)
        self._set_profile(worker, department=self.department)

        # Give both reviewers org-admin access so RBAC allows endpoint access.
        team_lead.profile.role = "admin"
        team_lead.profile.save(update_fields=["role"])
        outsider_manager.profile.role = "admin"
        outsider_manager.profile.save(update_fields=["role"])

        team = Team.objects.create(
            organization=self.org,
            department=self.department,
            name="Foundation Site Team",
            code="TM-FOUND-SITE",
            team_type=Team.TeamType.PROJECT_BASED,
            lead=team_lead,
            is_active=True,
        )

        worker_record = EmployeeRecord.objects.create(
            organization=self.org,
            user=worker,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        team_position = Position.objects.create(
            organization=self.org,
            title="Concrete Technician",
            code="POS-CONCRETE-001",
            department=self.department,
            team=team,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.MID,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=worker,
            position=team_position,
            start_date=timezone.localdate(),
            is_primary=True,
            is_active=True,
        )

        leave_type = LeaveType.objects.create(
            organization=self.org,
            name="Annual Leave",
            code="AL",
            default_days_per_year=Decimal("20.0"),
            is_active=True,
        )
        leave_request = LeaveRequest.objects.create(
            organization=self.org,
            employee=worker_record,
            leave_type=leave_type,
            start_date=date(2026, 3, 20),
            end_date=date(2026, 3, 22),
            total_days=Decimal("3.0"),
            status=LeaveRequest.Status.PENDING,
            reason="Family event",
        )

        self.client.force_authenticate(outsider_manager)
        forbidden_response = self.client.post(
            f"/api/hr/leave-requests/{leave_request.id}/approve/",
            {"reviewer_notes": "Approved"},
            format="json",
        )
        self.assertEqual(forbidden_response.status_code, 403)
        self.assertIn(
            "Only the assigned Team Lead can approve or reject this leave request.",
            str(forbidden_response.json()),
        )

        self.client.force_authenticate(team_lead)
        approved_response = self.client.post(
            f"/api/hr/leave-requests/{leave_request.id}/approve/",
            {"reviewer_notes": "Approved by Team Lead"},
            format="json",
        )
        self.assertEqual(approved_response.status_code, 200)
        leave_request.refresh_from_db()
        self.assertEqual(leave_request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(leave_request.reviewed_by_id, team_lead.id)

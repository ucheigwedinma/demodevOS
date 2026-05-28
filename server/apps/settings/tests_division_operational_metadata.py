from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.documents.models import (
    Document,
    DocumentOwnerRole,
    DocumentRetentionPolicy,
    DocumentType,
    DocumentWorkflowPhase,
)
from apps.finance.models import Account, AccountSubType, AccountType, Budget, BudgetLineItem
from apps.hr.models import EmployeeRecord, Position, PositionAssignment, PositionBudget, Skill
from apps.projects.models import Project, ProjectPhase, ProjectTask
from apps.settings.models import CostCenter, Department, Division, ProfitCenter


class DivisionOperationalMetadataTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Metadata Test Org")
        self.admin = get_user_model().objects.create_superuser(
            username="settings-admin",
            email="settings-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(self.admin)

        self.division = Division.objects.create(
            organization=self.org,
            name="Commercial Operations",
            code="COM-OPS",
            unit_category=Division.UnitCategory.PROFIT_CENTER,
            location_region="Lagos / West",
        )
        self.department = Department.objects.create(
            division=self.division,
            name="Sales",
            code="SLS",
        )

    def test_division_list_exposes_operational_metadata(self):
        user_model = get_user_model()
        active_user = user_model.objects.create_user(
            username="active-user",
            email="active@example.com",
            password="pass1234",
            first_name="Active",
            last_name="User",
        )
        inactive_user = user_model.objects.create_user(
            username="inactive-user",
            email="inactive@example.com",
            password="pass1234",
            first_name="Inactive",
            last_name="User",
        )

        EmployeeRecord.objects.create(
            organization=self.org,
            user=active_user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        EmployeeRecord.objects.create(
            organization=self.org,
            user=inactive_user,
            employment_status=EmployeeRecord.EmploymentStatus.TERMINATED,
        )

        position = Position.objects.create(
            organization=self.org,
            title="Sales Executive",
            code="POS-SALES-001",
            department=self.department,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.MID,
        )

        PositionAssignment.objects.create(
            organization=self.org,
            user=active_user,
            position=position,
            start_date=date(2026, 1, 1),
            is_active=True,
            is_primary=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=inactive_user,
            position=position,
            start_date=date(2026, 1, 1),
            is_active=True,
            is_primary=True,
        )

        opex_account = Account.objects.create(
            organization=self.org,
            code="6000",
            name="Operating Expense",
            account_type=AccountType.EXPENSE,
            sub_type=AccountSubType.OPERATING_EXPENSE,
        )
        other_expense_account = Account.objects.create(
            organization=self.org,
            code="6999",
            name="Other Expense",
            account_type=AccountType.EXPENSE,
            sub_type=AccountSubType.OTHER_EXPENSE,
        )
        budget = Budget.objects.create(
            organization=self.org,
            name="FY2026 Opex",
            status=Budget.Status.ACTIVE,
            period_type=Budget.PeriodType.ANNUAL,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            total_amount=Decimal("1000000.00"),
        )
        BudgetLineItem.objects.create(
            budget=budget,
            account=opex_account,
            department=self.department,
            budgeted_amount=Decimal("350000.00"),
        )
        BudgetLineItem.objects.create(
            budget=budget,
            account=other_expense_account,
            department=self.department,
            budgeted_amount=Decimal("120000.00"),
        )

        response = self.client.get("/api/settings/divisions/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)

        division_row = next(
            row for row in payload["results"] if row["id"] == self.division.id
        )
        self.assertEqual(division_row["unit_category"], Division.UnitCategory.PROFIT_CENTER)
        self.assertEqual(division_row["unit_category_display"], "Profit Center")
        self.assertEqual(division_row["location_region"], "Lagos / West")
        self.assertEqual(division_row["total_headcount"], 1)
        self.assertEqual(Decimal(division_row["operating_budget"]), Decimal("350000.00"))

    def test_division_patch_updates_operational_metadata_fields(self):
        response = self.client.patch(
            f"/api/settings/divisions/{self.division.id}/",
            {
                "unit_category": Division.UnitCategory.COST_CENTER,
                "location_region": "Abuja / North",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.division.refresh_from_db()
        self.assertEqual(self.division.unit_category, Division.UnitCategory.COST_CENTER)
        self.assertEqual(self.division.location_region, "Abuja / North")

    def test_department_identity_payload_includes_parent_bu_and_cost_center_id(self):
        CostCenter.objects.create(
            organization=self.org,
            code="CC-SALES-001",
            name="Sales Opex",
            department=self.department,
            is_active=True,
        )

        response = self.client.get("/api/settings/divisions/?include_departments=true")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        division_row = next(
            row for row in payload["results"] if row["id"] == self.division.id
        )
        department_row = next(
            row for row in division_row["departments"] if row["id"] == self.department.id
        )
        self.assertEqual(department_row["parent_business_unit_id"], self.division.id)
        self.assertEqual(department_row["parent_business_unit_name"], self.division.name)
        self.assertEqual(department_row["parent_business_unit_code"], self.division.code)
        self.assertEqual(department_row["cost_center_id"], "CC-SALES-001")

    def test_department_create_requires_cost_center_id(self):
        response = self.client.post(
            f"/api/settings/divisions/{self.division.id}/departments/",
            {
                "name": "Legal",
                "code": "LGL",
                "description": "Legal and statutory compliance",
                "is_active": True,
                "sort_order": 10,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("cost_center_id", response.json())

    def test_department_create_with_cost_center_id_auto_links_cost_center(self):
        response = self.client.post(
            f"/api/settings/divisions/{self.division.id}/departments/",
            {
                "name": "Legal",
                "code": "LGL",
                "description": "Legal and statutory compliance",
                "cost_center_id": "CC-LGL-001",
                "is_active": True,
                "sort_order": 10,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        legal_department = Department.objects.get(division=self.division, code="LGL")
        linked_cost_center = CostCenter.objects.get(
            organization=self.org,
            code="CC-LGL-001",
        )
        self.assertEqual(linked_cost_center.department_id, legal_department.id)

    def test_department_payload_includes_talent_headcount_and_skills_summary(self):
        user_model = get_user_model()
        engineer_one = user_model.objects.create_user(
            username="sales-eng-1",
            email="sales-eng-1@example.com",
            password="pass1234",
            first_name="Aisha",
            last_name="Okafor",
        )
        engineer_two = user_model.objects.create_user(
            username="sales-eng-2",
            email="sales-eng-2@example.com",
            password="pass1234",
            first_name="Tunde",
            last_name="Adeyemi",
        )

        for user, employee_id in [
            (engineer_one, "EMP-101"),
            (engineer_two, "EMP-102"),
        ]:
            UserProfile.objects.filter(user=user).update(
                organization=self.org,
                department=self.department,
                job_title="Sales Engineer",
                employee_id=employee_id,
            )

        employee_one = EmployeeRecord.objects.create(
            organization=self.org,
            user=engineer_one,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        employee_two = EmployeeRecord.objects.create(
            organization=self.org,
            user=engineer_two,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        position = Position.objects.create(
            organization=self.org,
            title="Sales Engineer",
            code="POS-SALES-002",
            department=self.department,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.MID,
        )

        PositionAssignment.objects.create(
            organization=self.org,
            user=engineer_one,
            position=position,
            start_date=date(2026, 1, 1),
            is_active=True,
            is_primary=True,
        )
        PositionAssignment.objects.create(
            organization=self.org,
            user=engineer_two,
            position=position,
            start_date=date(2026, 1, 1),
            is_active=True,
            is_primary=True,
        )

        PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            position=position,
            fiscal_year=timezone.localdate().year,
            approved_headcount=10,
            filled_headcount=2,
            budget_amount=Decimal("120000.00"),
            status=PositionBudget.Status.APPROVED,
        )

        Skill.objects.create(
            organization=self.org,
            employee=employee_one,
            name="Revit",
            category=Skill.Category.TECHNICAL,
            proficiency=Skill.ProficiencyLevel.EXPERT,
        )
        Skill.objects.create(
            organization=self.org,
            employee=employee_two,
            name="Revit",
            category=Skill.Category.TECHNICAL,
            proficiency=Skill.ProficiencyLevel.ADVANCED,
        )
        Skill.objects.create(
            organization=self.org,
            employee=employee_two,
            name="Contract Negotiation",
            category=Skill.Category.MANAGEMENT,
            proficiency=Skill.ProficiencyLevel.INTERMEDIATE,
        )

        response = self.client.get("/api/settings/divisions/?include_departments=true")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        division_row = next(
            row for row in payload["results"] if row["id"] == self.division.id
        )
        department_row = next(
            row for row in division_row["departments"] if row["id"] == self.department.id
        )

        self.assertEqual(department_row["headcount_summary"]["active_employees"], 2)
        self.assertEqual(department_row["headcount_summary"]["approved_roles"], 10)
        self.assertEqual(department_row["headcount_summary"]["filled_vs_approved"], "2/10")
        self.assertEqual(department_row["headcount_summary"]["vacant_roles"], 8)

        directory_names = {person["full_name"] for person in department_row["employee_directory"]}
        self.assertEqual(directory_names, {"Aisha Okafor", "Tunde Adeyemi"})
        self.assertEqual(len(department_row["employee_directory"]), 2)

        skills_by_name = {
            item["skill_name"]: item["employee_count"]
            for item in department_row["skills_matrix"]
        }
        self.assertEqual(skills_by_name.get("Revit"), 2)
        self.assertEqual(skills_by_name.get("Contract Negotiation"), 1)

    def test_profit_center_payload_includes_department_assignment(self):
        profit_center = ProfitCenter.objects.create(
            organization=self.org,
            code="PC-SALES-001",
            name="Sales Revenue Center",
            department=self.department,
            is_active=True,
        )

        response = self.client.get("/api/settings/profit-centers/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("results", payload)
        profit_center_row = next(
            row for row in payload["results"] if row["id"] == profit_center.id
        )
        self.assertEqual(profit_center_row["department"], self.department.id)
        self.assertEqual(profit_center_row["department_name"], self.department.name)

    def test_department_operational_integration_payload_is_live(self):
        user_model = get_user_model()
        assignee = user_model.objects.create_user(
            username="dept-project-user",
            email="dept-project-user@example.com",
            password="pass1234",
            first_name="Kemi",
            last_name="Akin",
        )
        UserProfile.objects.filter(user=assignee).update(
            organization=self.org,
            department=self.department,
            job_title="Project Coordinator",
            employee_id="EMP-777",
        )
        EmployeeRecord.objects.create(
            organization=self.org,
            user=assignee,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        project = Project.objects.create(
            organization=self.org,
            name="Riverside Estate Phase 1",
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
            name="Set out foundation lines",
            assigned_user=assignee,
            status=ProjectTask.Status.IN_PROGRESS,
            estimated_effort_hours=Decimal("40.0"),
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name="Inspect reinforcement",
            assigned_user=assignee,
            status=ProjectTask.Status.COMPLETED,
            estimated_effort_hours=Decimal("16.0"),
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=phase,
            name="Pour blinding concrete",
            assigned_user=assignee,
            status=ProjectTask.Status.PENDING,
            estimated_effort_hours=Decimal("8.0"),
        )

        document_type = DocumentType.objects.create(
            organization=self.org,
            code="dept-sop",
            name="Department SOP",
            category_code="OPS",
            is_active=True,
        )
        note_document_type = DocumentType.objects.create(
            organization=self.org,
            code="dept-note",
            name="Department Memo",
            category_code="OPS",
            is_active=True,
        )
        owner_role = DocumentOwnerRole.objects.create(
            organization=self.org,
            code="ops-owner",
            name="Operations Owner",
            is_active=True,
        )
        workflow_phase = DocumentWorkflowPhase.objects.create(
            organization=self.org,
            code="phase-live",
            name="Live",
            numbering_code="PH1",
            is_active=True,
        )
        retention_policy = DocumentRetentionPolicy.objects.create(
            organization=self.org,
            code="ret-ops",
            name="Operations Retention",
            retention_years=7,
            is_active=True,
        )
        Document.objects.create(
            organization=self.org,
            title="Procurement SOP - Vendor Vetting Checklist",
            document_number="DOC-SOP-001",
            document_type=document_type,
            owner_role=owner_role,
            phase=workflow_phase,
            retention_policy=retention_policy,
            status=Document.Status.APPROVED,
            business_unit_division=self.division,
            business_unit_department=self.department,
            project=project,
        )
        Document.objects.create(
            organization=self.org,
            title="Department Weekly Meeting Notes",
            document_number="DOC-NOTE-001",
            document_type=note_document_type,
            owner_role=owner_role,
            phase=workflow_phase,
            retention_policy=retention_policy,
            status=Document.Status.DRAFT,
            business_unit_division=self.division,
            business_unit_department=self.department,
        )

        response = self.client.get("/api/settings/divisions/?include_departments=true")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        division_row = next(
            row for row in payload["results"] if row["id"] == self.division.id
        )
        department_row = next(
            row for row in division_row["departments"] if row["id"] == self.department.id
        )

        self.assertEqual(len(department_row["project_allocation"]), 1)
        project_row = department_row["project_allocation"][0]
        self.assertEqual(project_row["project_id"], project.id)
        self.assertEqual(project_row["project_name"], project.name)
        self.assertEqual(project_row["project_status"], Project.Status.IN_PROGRESS)
        self.assertEqual(project_row["task_count"], 3)
        self.assertEqual(project_row["open_task_count"], 2)
        self.assertEqual(project_row["logged_hours"], 56.0)

        today = timezone.localdate()
        business_days = sum(
            1
            for day in range(1, monthrange(today.year, today.month)[1] + 1)
            if date(today.year, today.month, day).weekday() < 5
        )
        expected_available_hours = float(business_days * 8)
        expected_percent = round((56.0 / expected_available_hours) * 100, 2)

        utilization = department_row["utilization_rate"]
        self.assertEqual(utilization["hours_logged"], 56.0)
        self.assertEqual(utilization["available_hours"], expected_available_hours)
        self.assertEqual(utilization["staff_count"], 1)
        self.assertEqual(utilization["percent"], expected_percent)
        self.assertIn("project-task effort hours", utilization["formula"])

        sop_library = department_row["sop_library"]
        self.assertEqual(sop_library["document_count"], 2)
        self.assertEqual(sop_library["sop_count"], 1)
        self.assertGreaterEqual(len(sop_library["documents"]), 2)
        self.assertEqual(sop_library["documents"][0]["is_sop"], True)

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.accounts.models import Organization, UserProfile
from apps.hr.models import Position, PositionBudget, SalaryStructure
from apps.settings.models import AuditComplianceSettings, CostCenter, Department, Division


class PositionBudgetingWorkflowTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Budgeting Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create(
            username="budget-admin",
            email="budget-admin@example.com",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={"organization": self.org},
        )
        profile.organization = self.org
        profile.role = "admin"
        profile.save(update_fields=["organization", "role"])
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
            name="Structural Cost Center",
            is_active=True,
        )
        self.salary_structure = SalaryStructure.objects.create(
            organization=self.org,
            name="Grade 4 Band",
            code="G4",
            grade_level=4,
            min_salary=Decimal("100.00"),
            max_salary=Decimal("300.00"),
            currency="NGN",
            is_active=True,
        )
        self.position = Position.objects.create(
            organization=self.org,
            title="Senior Structural Engineer",
            code="POS-SSE-001",
            department=self.department,
            cost_center=self.cost_center,
            salary_structure=self.salary_structure,
            employment_type=Position.EmploymentType.FULL_TIME,
            level=Position.Level.SENIOR,
            status=Position.Status.ACTIVE,
            slot_status=Position.SlotStatus.VACANT,
            headcount_budget=1,
            is_active=True,
        )

    def test_burden_formula_includes_local_tax_and_insurance(self):
        PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            position=self.position,
            fiscal_period_label="FY 2026",
            fiscal_year=2026,
            budget_source=PositionBudget.BudgetSource.CORPORATE_OVERHEAD,
            currency="NGN",
            fte=Decimal("1.00"),
            statutory_benefits_rate=Decimal("10.00"),
            allowances_rate=Decimal("5.00"),
            local_tax_rate=Decimal("3.00"),
            insurance_rate=Decimal("2.00"),
            approved_headcount=2,
            filled_headcount=1,
            budget_amount=Decimal("1000.00"),
            status=PositionBudget.Status.APPROVED,
        )

        response = self.client.get("/api/hr/position-budgets/")
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]

        self.assertEqual(row["burden_multiplier"], "1.2000")
        self.assertEqual(row["statutory_benefits_cost"], "20.00")
        self.assertEqual(row["allowances_cost"], "10.00")
        self.assertEqual(row["local_tax_cost"], "6.00")
        self.assertEqual(row["insurance_cost"], "4.00")
        self.assertEqual(row["fully_burdened_cost"], "240.00")

    def test_approved_budget_requires_formal_revision_workflow(self):
        budget = PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            position=self.position,
            fiscal_period_label="FY 2026",
            fiscal_year=2026,
            budget_source=PositionBudget.BudgetSource.CORPORATE_OVERHEAD,
            currency="NGN",
            approved_headcount=1,
            filled_headcount=1,
            budget_amount=Decimal("1000.00"),
            status=PositionBudget.Status.APPROVED,
        )

        blocked_patch = self.client.patch(
            f"/api/hr/position-budgets/{budget.id}/",
            {"budget_amount": "1200.00"},
            format="json",
        )
        self.assertEqual(blocked_patch.status_code, 400)
        self.assertTrue(blocked_patch.json().get("requires_revision_workflow"))

        revision_create = self.client.post(
            "/api/hr/position-budget-revisions/",
            {
                "budget": budget.id,
                "reason": "Annual board-approved staffing adjustment.",
                "proposed_changes": {
                    "budget_amount": "1200.00",
                    "allowances_rate": "12.00",
                },
            },
            format="json",
        )
        self.assertEqual(revision_create.status_code, 201)
        revision_id = revision_create.json()["id"]
        self.assertEqual(revision_create.json()["status"], "pending_approval")

        approve = self.client.post(
            f"/api/hr/position-budget-revisions/{revision_id}/approve/",
            {"review_notes": "Approved by Finance."},
            format="json",
        )
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.json()["status"], "approved")

        budget.refresh_from_db()
        self.assertEqual(str(budget.budget_amount), "1200.00")
        self.assertEqual(str(budget.allowances_rate), "12.00")
        self.assertEqual(budget.status, PositionBudget.Status.APPROVED)
        self.assertIsNotNone(budget.approved_at)

    def test_what_if_simulator_returns_margin_delta(self):
        PositionBudget.objects.create(
            organization=self.org,
            department=self.department,
            position=self.position,
            fiscal_period_label="Project Phase 1",
            fiscal_year=2026,
            budget_source=PositionBudget.BudgetSource.PROJECT_FUNDING,
            currency="NGN",
            fte=Decimal("1.00"),
            statutory_benefits_rate=Decimal("10.00"),
            allowances_rate=Decimal("5.00"),
            local_tax_rate=Decimal("3.00"),
            insurance_rate=Decimal("2.00"),
            approved_headcount=5,
            filled_headcount=3,
            budget_amount=Decimal("5000.00"),
            status=PositionBudget.Status.APPROVED,
        )

        response = self.client.post(
            "/api/hr/position-budgets/what-if/",
            {
                "fiscal_year": 2026,
                "department": self.department.id,
                "position": self.position.id,
                "additional_headcount": 2,
                "project_revenue": "15000.00",
                "other_project_costs": "3000.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["assumptions"]["additional_headcount"], 2)
        self.assertIsNotNone(payload["scenario"]["margin_delta_percent"])
        self.assertLess(payload["scenario"]["margin_delta_percent"], 0)

    def test_financial_period_lock_blocks_direct_create(self):
        AuditComplianceSettings.objects.update_or_create(
            organization=self.org,
            defaults={
                "financial_period_locking": True,
                "locked_before_date": date(2026, 12, 31),
                "change_approval_required": True,
            },
        )

        response = self.client.post(
            "/api/hr/position-budgets/",
            {
                "department": self.department.id,
                "position": self.position.id,
                "fiscal_period_label": "FY 2026",
                "fiscal_year": 2026,
                "budget_source": PositionBudget.BudgetSource.CORPORATE_OVERHEAD,
                "currency": "NGN",
                "fte": "1.00",
                "statutory_benefits_rate": "10.00",
                "allowances_rate": "5.00",
                "local_tax_rate": "3.00",
                "insurance_rate": "2.00",
                "approved_headcount": 2,
                "filled_headcount": 0,
                "budget_amount": "2000.00",
                "status": PositionBudget.Status.DRAFT,
                "notes": "",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertTrue(payload.get("locked"))
        self.assertTrue(payload.get("requires_revision_workflow"))

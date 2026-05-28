from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache as django_cache
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.analytics.cache_utils import get_analytics_cache_version
from apps.finance.models import (
    Budget,
    BudgetLineItem,
    ProjectAccountMapping,
    ProjectCostCenter,
    ProjectFinanceArtifact,
    ProjectInvestor,
    ProjectLedger,
    ProjectRevenueCenter,
)
from apps.hr.models import EmployeeRecord, EquipmentAllocation, OrientationChecklistItem, Payslip
from apps.procurement.models import GoodsReceipt, ProjectProcurementWorkspace, PurchaseOrder, Vendor
from apps.projects.cache_utils import get_project_summary_cache_version
from apps.projects.models import (
    Project,
    ProjectConstructionSchedule,
    ProjectConstructionWorkspace,
    ProjectContractorProfile,
    ProjectCostEntry,
    ProjectDailySiteReport,
    ProjectExecutionInspection,
    ProjectFieldEscalation,
    ProjectMilestone,
    ProjectPhase,
    ProjectPhaseDependency,
    ProjectRiskRegisterEntry,
    ProjectScheduleDelayLog,
    ProjectSiteMobilization,
    ProjectTask,
    ProjectWorkforceLog,
    ProjectWorkPackage,
)
from apps.projects.serializers import ProjectWriteSerializer
from apps.settings.models import CostCenter, ProfitCenter


class ProjectFinancialBootstrapTests(TestCase):
    EXPECTED_BUDGET_CATEGORY_NAMES = [
        "Land acquisition",
        "Planning & design",
        "Permits & approvals",
        "Construction",
        "Marketing & sales",
        "Finance charges",
        "Contingency",
        "Other",
    ]
    EXPECTED_PROJECT_FINANCE_ARTIFACT_TYPES = {
        "project_budget_dashboard",
        "cashflow_forecast",
        "cost_tracker",
        "variance_analysis",
    }
    EXPECTED_PROJECT_PROCUREMENT_WORKSPACE_TYPES = {
        "project_procurement_dashboard",
        "vendor_allocation_workspace",
    }
    EXPECTED_PROJECT_CONSTRUCTION_WORKSPACE_TYPES = {
        "site_overview_dashboard",
        "site_mobilization_workspace",
        "construction_schedule_workspace",
        "contractor_management_workspace",
    }

    def setUp(self):
        self.org = Organization.objects.create(name="Project Finance Test Org")

    def test_project_creation_auto_creates_project_financial_containers(self):
        support_cost_center_count = CostCenter.objects.filter(organization=self.org).count()
        support_profit_center_count = ProfitCenter.objects.filter(organization=self.org).count()
        support_budget_count = Budget.objects.filter(organization=self.org, project__isnull=True).count()

        project = Project.objects.create(
            organization=self.org,
            name="Project Atlas",
            budget="1500000.00",
        )

        ledgers = ProjectLedger.objects.filter(organization=self.org, project=project)
        project_cost_centers = ProjectCostCenter.objects.filter(
            organization=self.org,
            project=project,
        )
        project_revenue_centers = ProjectRevenueCenter.objects.filter(
            organization=self.org,
            project=project,
        )
        project_budgets = Budget.objects.filter(
            organization=self.org,
            project=project,
        )
        project_account_mappings = ProjectAccountMapping.objects.filter(
            organization=self.org,
            project=project,
        ).select_related(
            "construction_cost_account",
            "capex_account",
            "development_expense_account",
            "sales_revenue_account",
        )
        budget_line_items = BudgetLineItem.objects.filter(
            budget=project_budgets.get(),
        ).select_related("account").order_by("sort_order", "id")
        project_finance_artifacts = ProjectFinanceArtifact.objects.filter(
            organization=self.org,
            project=project,
        ).order_by("artifact_type")
        project_procurement_workspaces = ProjectProcurementWorkspace.objects.filter(
            organization=self.org,
            project=project,
        ).order_by("workspace_type")
        project_construction_workspaces = ProjectConstructionWorkspace.objects.filter(
            organization=self.org,
            project=project,
        ).order_by("workspace_type")
        project_site_mobilizations = ProjectSiteMobilization.objects.filter(
            organization=self.org,
            project=project,
        )
        project_construction_schedules = ProjectConstructionSchedule.objects.filter(
            organization=self.org,
            project=project,
        )

        self.assertEqual(ledgers.count(), 1)
        self.assertEqual(project_cost_centers.count(), 1)
        self.assertEqual(project_revenue_centers.count(), 1)
        self.assertEqual(project_budgets.count(), 1)
        self.assertEqual(project_account_mappings.count(), 1)
        self.assertEqual(budget_line_items.count(), 8)
        self.assertEqual(project_finance_artifacts.count(), 4)
        self.assertEqual(project_procurement_workspaces.count(), 2)
        self.assertEqual(project_construction_workspaces.count(), 4)
        self.assertEqual(project_site_mobilizations.count(), 1)
        self.assertEqual(project_construction_schedules.count(), 1)

        project_account_mapping = project_account_mappings.get()
        self.assertTrue(ledgers.get().code.startswith("PRJ-LDG-"))
        self.assertTrue(project_cost_centers.get().code.startswith("PRJ-COST-"))
        self.assertTrue(project_revenue_centers.get().code.startswith("PRJ-REV-"))
        self.assertTrue(project_budgets.get().name.startswith("Project Budget - Project Atlas"))
        self.assertEqual(str(project_budgets.get().total_amount), "1500000.00")
        self.assertEqual(
            project_account_mapping.construction_cost_account.account_type,
            "expense",
        )
        self.assertEqual(
            project_account_mapping.construction_cost_account.sub_type,
            "cost_of_goods_sold",
        )
        self.assertEqual(project_account_mapping.capex_account.account_type, "asset")
        self.assertEqual(project_account_mapping.capex_account.sub_type, "fixed_asset")
        self.assertEqual(
            project_account_mapping.development_expense_account.account_type,
            "expense",
        )
        self.assertEqual(
            project_account_mapping.development_expense_account.sub_type,
            "operating_expense",
        )
        self.assertEqual(
            project_account_mapping.sales_revenue_account.account_type,
            "revenue",
        )
        self.assertEqual(
            project_account_mapping.sales_revenue_account.sub_type,
            "operating_revenue",
        )
        self.assertListEqual(
            [line.account.name for line in budget_line_items],
            self.EXPECTED_BUDGET_CATEGORY_NAMES,
        )
        self.assertSetEqual(
            set(project_finance_artifacts.values_list("artifact_type", flat=True)),
            self.EXPECTED_PROJECT_FINANCE_ARTIFACT_TYPES,
        )
        self.assertTrue(
            project_finance_artifacts.filter(
                artifact_type="variance_analysis",
                menu_path="/finance/variance-analysis",
            ).exists()
        )
        self.assertSetEqual(
            set(project_procurement_workspaces.values_list("workspace_type", flat=True)),
            self.EXPECTED_PROJECT_PROCUREMENT_WORKSPACE_TYPES,
        )
        self.assertTrue(
            project_procurement_workspaces.filter(
                workspace_type="project_procurement_dashboard",
                menu_path="/procurement/overview",
            ).exists()
        )
        self.assertTrue(
            project_procurement_workspaces.filter(
                workspace_type="vendor_allocation_workspace",
                menu_path="/procurement/vendors",
            ).exists()
        )
        self.assertSetEqual(
            set(project_construction_workspaces.values_list("workspace_type", flat=True)),
            self.EXPECTED_PROJECT_CONSTRUCTION_WORKSPACE_TYPES,
        )
        self.assertTrue(
            project_construction_workspaces.filter(
                workspace_type="site_overview_dashboard",
                menu_path="/construction/site-overview",
            ).exists()
        )
        self.assertTrue(
            project_construction_workspaces.filter(
                workspace_type="site_mobilization_workspace",
                menu_path="/construction/site-mobilization",
            ).exists()
        )
        self.assertTrue(
            project_construction_workspaces.filter(
                workspace_type="construction_schedule_workspace",
                menu_path="/construction/schedule",
            ).exists()
        )
        self.assertTrue(
            project_construction_workspaces.filter(
                workspace_type="contractor_management_workspace",
                menu_path="/construction/contractor-management",
            ).exists()
        )

        # Project-scoped centers are distinct from organization support centers.
        self.assertEqual(
            CostCenter.objects.filter(organization=self.org).count(),
            support_cost_center_count,
        )
        self.assertEqual(
            ProfitCenter.objects.filter(organization=self.org).count(),
            support_profit_center_count,
        )
        self.assertEqual(
            Budget.objects.filter(organization=self.org, project__isnull=True).count(),
            support_budget_count,
        )

    def test_project_update_does_not_duplicate_project_financial_framework(self):
        project = Project.objects.create(
            organization=self.org,
            name="Project Atlas",
        )

        ledger_id = ProjectLedger.objects.get(project=project).id
        project_cost_center_id = ProjectCostCenter.objects.get(project=project).id
        project_revenue_center_id = ProjectRevenueCenter.objects.get(project=project).id
        project_budget_id = Budget.objects.get(project=project).id
        project_account_mapping_id = ProjectAccountMapping.objects.get(project=project).id
        project_finance_artifact_ids = list(
            ProjectFinanceArtifact.objects.filter(project=project)
            .order_by("artifact_type")
            .values_list("id", flat=True)
        )
        project_procurement_workspace_ids = list(
            ProjectProcurementWorkspace.objects.filter(project=project)
            .order_by("workspace_type")
            .values_list("id", flat=True)
        )
        project_construction_workspace_ids = list(
            ProjectConstructionWorkspace.objects.filter(project=project)
            .order_by("workspace_type")
            .values_list("id", flat=True)
        )
        project_site_mobilization_id = ProjectSiteMobilization.objects.get(project=project).id
        project_construction_schedule_id = ProjectConstructionSchedule.objects.get(project=project).id

        project.name = "Project Atlas - Phase 2"
        project.save(update_fields=["name"])

        self.assertEqual(ProjectLedger.objects.filter(project=project).count(), 1)
        self.assertEqual(ProjectCostCenter.objects.filter(project=project).count(), 1)
        self.assertEqual(ProjectRevenueCenter.objects.filter(project=project).count(), 1)
        self.assertEqual(Budget.objects.filter(project=project).count(), 1)
        self.assertEqual(ProjectAccountMapping.objects.filter(project=project).count(), 1)
        self.assertEqual(BudgetLineItem.objects.filter(budget__project=project).count(), 8)
        self.assertEqual(ProjectFinanceArtifact.objects.filter(project=project).count(), 4)
        self.assertEqual(ProjectProcurementWorkspace.objects.filter(project=project).count(), 2)
        self.assertEqual(ProjectConstructionWorkspace.objects.filter(project=project).count(), 4)
        self.assertEqual(ProjectSiteMobilization.objects.filter(project=project).count(), 1)
        self.assertEqual(ProjectConstructionSchedule.objects.filter(project=project).count(), 1)

        self.assertEqual(ProjectLedger.objects.get(project=project).id, ledger_id)
        self.assertEqual(
            ProjectCostCenter.objects.get(project=project).id,
            project_cost_center_id,
        )
        self.assertEqual(
            ProjectRevenueCenter.objects.get(project=project).id,
            project_revenue_center_id,
        )
        self.assertEqual(Budget.objects.get(project=project).id, project_budget_id)
        self.assertEqual(
            ProjectAccountMapping.objects.get(project=project).id,
            project_account_mapping_id,
        )
        self.assertListEqual(
            list(
                ProjectFinanceArtifact.objects.filter(project=project)
                .order_by("artifact_type")
                .values_list("id", flat=True)
            ),
            project_finance_artifact_ids,
        )
        self.assertListEqual(
            list(
                ProjectProcurementWorkspace.objects.filter(project=project)
                .order_by("workspace_type")
                .values_list("id", flat=True)
            ),
            project_procurement_workspace_ids,
        )
        self.assertListEqual(
            list(
                ProjectConstructionWorkspace.objects.filter(project=project)
                .order_by("workspace_type")
                .values_list("id", flat=True)
            ),
            project_construction_workspace_ids,
        )
        self.assertEqual(
            ProjectSiteMobilization.objects.get(project=project).id,
            project_site_mobilization_id,
        )
        self.assertEqual(
            ProjectConstructionSchedule.objects.get(project=project).id,
            project_construction_schedule_id,
        )


class ProjectOwnershipAllocationSyncTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Ownership Sync Org")

    def test_create_project_syncs_ownership_allocations_to_finance_cap_table(self):
        serializer = ProjectWriteSerializer(
            data={
                "name": "Project Equity One",
                "ownership_allocations": [
                    {"party_name": "Developer", "ownership_percentage": "60.00"},
                    {"party_name": "Investor A", "ownership_percentage": "40.00"},
                ],
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        project = serializer.save(organization=self.org)
        project.refresh_from_db()

        allocations = list(
            ProjectInvestor.objects.filter(project=project)
            .select_related("investor")
            .order_by("sort_order")
        )
        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0].investor.name, "Developer")
        self.assertEqual(str(allocations[0].ownership_percentage), "60.00")
        self.assertEqual(allocations[1].investor.name, "Investor A")
        self.assertEqual(str(allocations[1].ownership_percentage), "40.00")
        self.assertEqual(
            project.ownership_structure,
            "Developer: 60.00%; Investor A: 40.00%",
        )

    def test_update_project_reconciles_ownership_allocations(self):
        project = Project.objects.create(
            organization=self.org,
            name="Project Equity Two",
        )
        serializer = ProjectWriteSerializer(
            project,
            data={
                "ownership_allocations": [
                    {"party_name": "Developer", "ownership_percentage": "60.00"},
                    {"party_name": "Investor A", "ownership_percentage": "40.00"},
                ],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        developer_investor_id = ProjectInvestor.objects.get(
            project=project,
            investor__name="Developer",
        ).investor_id

        serializer = ProjectWriteSerializer(
            project,
            data={
                "ownership_allocations": [
                    {"investor_id": developer_investor_id, "ownership_percentage": "55.00"},
                    {"party_name": "Investor B", "ownership_percentage": "45.00"},
                ],
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        updated.refresh_from_db()

        allocations = list(
            ProjectInvestor.objects.filter(project=project)
            .select_related("investor")
            .order_by("sort_order")
        )
        self.assertEqual(len(allocations), 2)
        self.assertEqual(allocations[0].investor.name, "Developer")
        self.assertEqual(str(allocations[0].ownership_percentage), "55.00")
        self.assertEqual(allocations[1].investor.name, "Investor B")
        self.assertEqual(str(allocations[1].ownership_percentage), "45.00")
        self.assertFalse(
            ProjectInvestor.objects.filter(
                project=project,
                investor__name="Investor A",
            ).exists(),
        )
        self.assertEqual(
            updated.ownership_structure,
            "Developer: 55.00%; Investor B: 45.00%",
        )

    def test_ownership_allocations_validation_blocks_total_above_100_percent(self):
        serializer = ProjectWriteSerializer(
            data={
                "name": "Project Equity Three",
                "ownership_allocations": [
                    {"party_name": "Developer", "ownership_percentage": "70.00"},
                    {"party_name": "Investor A", "ownership_percentage": "40.00"},
                ],
            },
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("ownership_allocations", serializer.errors)


class ProjectConstructionSiteOverviewTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Construction Test Org")
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="construction-admin",
            email="construction-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.user)

        today = timezone.localdate()
        self.start_date = today - timedelta(days=30)
        self.end_date = today

        self.project = Project.objects.create(
            organization=self.org,
            name="Project Crane",
            status=Project.Status.IN_PROGRESS,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Foundation",
            status=ProjectPhase.Status.IN_PROGRESS,
            planned_budget=Decimal("100000.00"),
        )
        ProjectCostEntry.objects.create(
            organization=self.org,
            phase=self.phase,
            description="Concrete and steel",
            amount=Decimal("120000.00"),
            date=today,
            category=ProjectCostEntry.Category.MATERIALS,
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=self.phase,
            name="Pour slab",
            status=ProjectTask.Status.IN_PROGRESS,
            due_date=today - timedelta(days=2),
        )
        ProjectWorkforceLog.objects.create(
            organization=self.org,
            project=self.project,
            report_date=today,
            shift=ProjectWorkforceLog.Shift.DAY,
            laborers_count=6,
            skilled_count=4,
            supervisors_count=2,
            subcontractors_count=1,
            equipment_operators_count=1,
        )
        ProjectDailySiteReport.objects.create(
            organization=self.org,
            project=self.project,
            report_date=today,
            progress_percent=Decimal("45.00"),
            incidents="Minor first aid incident",
            status=ProjectDailySiteReport.Status.SUBMITTED,
        )
        ProjectExecutionInspection.objects.create(
            organization=self.org,
            project=self.project,
            inspection_type=ProjectExecutionInspection.InspectionType.WORKMANSHIP,
            status=ProjectExecutionInspection.Status.PLANNED,
            inspected_on=today,
            inspector_name="Inspector A",
        )
        ProjectExecutionInspection.objects.create(
            organization=self.org,
            project=self.project,
            inspection_type=ProjectExecutionInspection.InspectionType.SAFETY_QUALITY,
            status=ProjectExecutionInspection.Status.FAILED,
            inspected_on=today,
            inspector_name="Inspector B",
        )
        ProjectFieldEscalation.objects.create(
            organization=self.org,
            project=self.project,
            issue_date=today,
            issue_type=ProjectFieldEscalation.IssueType.RFI_PENDING,
            status=ProjectFieldEscalation.Status.OPEN,
            title="RFI pending - drawing clarification",
        )
        ProjectFieldEscalation.objects.create(
            organization=self.org,
            project=self.project,
            issue_date=today,
            issue_type=ProjectFieldEscalation.IssueType.MATERIAL_SHORTAGE,
            status=ProjectFieldEscalation.Status.OPEN,
            title="Rebar shortage",
        )
        ProjectFieldEscalation.objects.create(
            organization=self.org,
            project=self.project,
            issue_date=today,
            issue_type=ProjectFieldEscalation.IssueType.SAFETY_INCIDENT,
            status=ProjectFieldEscalation.Status.ACKNOWLEDGED,
            title="Safety near miss",
        )
        ProjectFieldEscalation.objects.create(
            organization=self.org,
            project=self.project,
            issue_date=today,
            issue_type=ProjectFieldEscalation.IssueType.QUALITY_DEFECT,
            status=ProjectFieldEscalation.Status.OPEN,
            title="Honeycombing in column",
        )
        ProjectScheduleDelayLog.objects.create(
            organization=self.org,
            project=self.project,
            delay_date=today,
            delay_type=ProjectScheduleDelayLog.DelayType.PROCUREMENT,
            impact_days=Decimal("4.00"),
        )

        vendor = Vendor.objects.create(
            organization=self.org,
            name="Vendor A",
        )
        po = PurchaseOrder.objects.create(
            organization=self.org,
            vendor=vendor,
            project=self.project,
            issue_date=today - timedelta(days=5),
            expected_delivery_date=today - timedelta(days=2),
        )
        GoodsReceipt.objects.create(
            organization=self.org,
            purchase_order=po,
            status=GoodsReceipt.Status.ACCEPTED,
            received_date=today - timedelta(days=1),
            received_by="Storekeeper",
        )

    def test_site_overview_dashboard_returns_expected_kpis_and_widgets(self):
        response = self.client.get(
            "/api/projects/construction/site-overview/",
            {
                "project": str(self.project.id),
                "start_date": self.start_date.isoformat(),
                "end_date": self.end_date.isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        payload = response.json()
        kpis = payload["kpis"]
        widgets = payload["widgets"]

        self.assertEqual(kpis["open_rfis"], 1)
        self.assertEqual(kpis["pending_inspections"], 1)
        self.assertEqual(kpis["material_shortages"], 1)
        self.assertEqual(kpis["safety_incidents"], 1)
        self.assertEqual(kpis["delayed_tasks"], 1)
        self.assertEqual(kpis["workforce_count"], 14)
        self.assertEqual(kpis["quality_issues"], 2)
        self.assertEqual(kpis["project_progress_percent"], 45.0)
        self.assertEqual(kpis["schedule_variance_days"], 4.0)
        self.assertEqual(kpis["cost_variance_amount"], 20000.0)

        self.assertIn("progress_curve", widgets)
        self.assertIn("cost_vs_budget", widgets)
        self.assertIn("labour_distribution", widgets)
        self.assertIn("material_consumption", widgets)
        self.assertIn("safety_index", widgets)
        self.assertIn("inspection_status", widgets)

        self.assertGreaterEqual(len(widgets["progress_curve"]), 1)
        self.assertGreaterEqual(len(widgets["cost_vs_budget"]), 1)


class ProjectMilestoneAutomationSignalTests(TestCase):
    def setUp(self):
        django_cache.clear()
        self.org = Organization.objects.create(name="Milestone Signal Org")
        self.project = Project.objects.create(
            organization=self.org,
            name="Milestone Signal Project",
            status=Project.Status.IN_PROGRESS,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Execution",
            status=ProjectPhase.Status.IN_PROGRESS,
        )

    def test_overdue_milestone_creates_auto_risk_and_completion_mitigates_it(self):
        initial_project_cache_version = get_project_summary_cache_version(self.org.id)
        initial_analytics_cache_version = get_analytics_cache_version(self.org.id)

        milestone = ProjectMilestone.objects.create(
            organization=self.org,
            phase=self.phase,
            name="Foundation Sign-off",
            target_date=timezone.localdate() - timedelta(days=3),
            is_completed=False,
        )
        auto_risk = ProjectRiskRegisterEntry.objects.get(
            project=self.project,
            title__startswith="[AUTO] Milestone Delay Risk",
        )
        self.assertEqual(auto_risk.status, ProjectRiskRegisterEntry.Status.OPEN)

        milestone.is_completed = True
        milestone.completed_date = timezone.localdate()
        milestone.save(update_fields=["is_completed", "completed_date"])

        auto_risk.refresh_from_db()
        self.assertEqual(auto_risk.status, ProjectRiskRegisterEntry.Status.MITIGATED)
        self.assertIsNotNone(auto_risk.resolved_on)
        self.assertGreater(
            get_project_summary_cache_version(self.org.id),
            initial_project_cache_version,
        )
        self.assertGreater(
            get_analytics_cache_version(self.org.id),
            initial_analytics_cache_version,
        )


class ProjectConstructionSiteOverviewMilestoneProgressTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Milestone Progress Org")
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            username="milestone-progress-admin",
            email="milestone-progress-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.user)

        self.today = timezone.localdate()
        self.project = Project.objects.create(
            organization=self.org,
            name="Milestone Progress Project",
            status=Project.Status.IN_PROGRESS,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Milestone Phase",
            status=ProjectPhase.Status.IN_PROGRESS,
            planned_budget=Decimal("50000.00"),
        )
        ProjectMilestone.objects.create(
            organization=self.org,
            phase=self.phase,
            name="Milestone A",
            target_date=self.today - timedelta(days=2),
            is_completed=True,
            completed_date=self.today - timedelta(days=1),
        )
        ProjectMilestone.objects.create(
            organization=self.org,
            phase=self.phase,
            name="Milestone B",
            target_date=self.today + timedelta(days=10),
            is_completed=False,
        )

    def test_site_overview_progress_uses_milestone_completion_when_no_site_reports(self):
        response = self.client.get(
            "/api/projects/construction/site-overview/",
            {
                "project": str(self.project.id),
                "start_date": (self.today - timedelta(days=30)).isoformat(),
                "end_date": self.today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(payload["kpis"]["project_progress_percent"], 50.0)


class ProjectConstructionSiteMobilizationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Mobilization Test Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="mobilization-admin",
            email="mobilization-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.admin)

        self.project = Project.objects.create(
            organization=self.org,
            name="Project Mobilize",
            status=Project.Status.PLANNING,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Pre-Construction",
            status=ProjectPhase.Status.IN_PROGRESS,
        )

        self.employee_user = user_model.objects.create_user(
            username="mobilization-worker",
            email="mobilization-worker@example.com",
            password="pass1234",
        )
        self.employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=self.employee_user,
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=self.phase,
            name="Mobilization prep assignment",
            assigned_user=self.employee_user,
        )

        self.vendor = Vendor.objects.create(
            organization=self.org,
            name="Mobilization Vendor",
        )
        self.po = PurchaseOrder.objects.create(
            organization=self.org,
            vendor=self.vendor,
            project=self.project,
            status=PurchaseOrder.Status.ISSUED,
            issue_date=timezone.localdate(),
        )
        GoodsReceipt.objects.create(
            organization=self.org,
            purchase_order=self.po,
            status=GoodsReceipt.Status.ACCEPTED,
            received_date=timezone.localdate(),
            received_by="Storekeeper",
        )
        EquipmentAllocation.objects.create(
            organization=self.org,
            employee=self.employee,
            item_name="Tower crane access kit",
            status=EquipmentAllocation.Status.ALLOCATED,
        )
        OrientationChecklistItem.objects.create(
            organization=self.org,
            employee=self.employee,
            title="Site safety induction",
            category=OrientationChecklistItem.Category.SAFETY_TRAINING,
            is_completed=True,
        )

    def test_site_mobilization_get_includes_linked_procurement_and_hr_fields(self):
        response = self.client.get(
            "/api/projects/construction/site-mobilization/",
            {"project": str(self.project.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        mobilization = payload["mobilization"]
        checklist = mobilization["checklist"]

        self.assertEqual(payload["filters"]["project"], self.project.id)
        self.assertEqual(mobilization["project"], self.project.id)
        self.assertTrue(checklist["contractors_mobilized"])
        self.assertTrue(checklist["equipment_delivered"])
        self.assertTrue(checklist["material_staging"])
        self.assertTrue(checklist["safety_induction"])
        self.assertEqual(
            mobilization["linked_sources"]["procurement"]["contractors_count"],
            1,
        )
        self.assertEqual(
            mobilization["linked_sources"]["procurement"]["material_staging_count"],
            1,
        )
        self.assertEqual(
            mobilization["linked_sources"]["hr"]["equipment_delivery_count"],
            1,
        )
        self.assertEqual(
            mobilization["linked_sources"]["hr"]["safety_induction_count"],
            1,
        )

    def test_site_mobilization_patch_updates_manual_fields(self):
        response = self.client.patch(
            "/api/projects/construction/site-mobilization/",
            {
                "project": self.project.id,
                "planned_start_date": "2026-03-10",
                "notes": "Mobilization sequence confirmed.",
                "site_preparation": {
                    "fencing": "completed",
                    "site_offices": "in_progress",
                    "temporary_roads": "blocked",
                },
                "checklist": {
                    "survey_control_established": True,
                    "permits_obtained": True,
                    "insurance_certificates": False,
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mobilization = response.json()["mobilization"]

        self.assertEqual(mobilization["site_preparation"]["fencing"], "completed")
        self.assertEqual(mobilization["site_preparation"]["site_offices"], "in_progress")
        self.assertEqual(mobilization["site_preparation"]["temporary_roads"], "blocked")
        self.assertTrue(mobilization["checklist"]["survey_control_established"])
        self.assertTrue(mobilization["checklist"]["permits_obtained"])
        self.assertFalse(mobilization["checklist"]["insurance_certificates"])
        self.assertTrue(mobilization["checklist"]["contractors_mobilized"])

    def test_procurement_field_change_persists_to_site_mobilization(self):
        self.po.status = PurchaseOrder.Status.CANCELLED
        self.po.save(update_fields=["status", "updated_at"])

        mobilization = ProjectSiteMobilization.objects.get(project=self.project)
        self.assertFalse(mobilization.contractors_mobilized)


class ProjectConstructionScheduleTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Construction Schedule Test Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="schedule-admin",
            email="schedule-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.admin)

        self.today = timezone.localdate()
        self.project = Project.objects.create(
            organization=self.org,
            name="Project Timeline",
            project_manager="Ada Manager",
            start_date=self.today - timedelta(days=30),
            target_end_date=self.today + timedelta(days=120),
            status=Project.Status.IN_PROGRESS,
        )
        self.phase_a = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Foundation",
            status=ProjectPhase.Status.IN_PROGRESS,
            sort_order=1,
            planned_start_date=self.today - timedelta(days=20),
            planned_end_date=self.today + timedelta(days=5),
            planned_budget=Decimal("450000.00"),
            actual_cost=Decimal("220000.00"),
        )
        self.phase_b = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Structure",
            status=ProjectPhase.Status.NOT_STARTED,
            sort_order=2,
            planned_start_date=self.today + timedelta(days=6),
            planned_end_date=self.today + timedelta(days=55),
            planned_budget=Decimal("780000.00"),
            actual_cost=Decimal("0.00"),
        )
        ProjectPhaseDependency.objects.create(
            organization=self.org,
            project=self.project,
            predecessor_phase=self.phase_a,
            successor_phase=self.phase_b,
            dependency_type=ProjectPhaseDependency.DependencyType.FINISH_TO_START,
            lag_days=2,
        )

        self.assignee_user = user_model.objects.create_user(
            username="schedule-user",
            email="schedule-user@example.com",
            password="pass1234",
        )
        self.employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=self.assignee_user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )

        ProjectTask.objects.create(
            organization=self.org,
            phase=self.phase_a,
            name="Rebar placement",
            status=ProjectTask.Status.IN_PROGRESS,
            priority=ProjectTask.Priority.HIGH,
            assigned_user=self.assignee_user,
            due_date=self.today + timedelta(days=3),
            predecessors=[{"task": "Formwork complete", "dependency_type": "fs", "lag_days": 0}],
        )
        ProjectTask.objects.create(
            organization=self.org,
            phase=self.phase_b,
            name="Column casting prep",
            status=ProjectTask.Status.PENDING,
            priority=ProjectTask.Priority.MEDIUM,
            due_date=self.today - timedelta(days=1),
        )

        ProjectWorkforceLog.objects.create(
            organization=self.org,
            project=self.project,
            report_date=self.today,
            laborers_count=8,
            skilled_count=4,
            supervisors_count=2,
            subcontractors_count=3,
            equipment_operators_count=1,
        )

        EquipmentAllocation.objects.create(
            organization=self.org,
            employee=self.employee,
            item_name="Tower crane controller",
            status=EquipmentAllocation.Status.ALLOCATED,
        )

        self.vendor = Vendor.objects.create(organization=self.org, name="Schedule Vendor")
        PurchaseOrder.objects.create(
            organization=self.org,
            vendor=self.vendor,
            project=self.project,
            status=PurchaseOrder.Status.APPROVED,
            issue_date=self.today - timedelta(days=2),
            expected_delivery_date=self.today + timedelta(days=4),
        )
        PurchaseOrder.objects.create(
            organization=self.org,
            vendor=self.vendor,
            project=self.project,
            status=PurchaseOrder.Status.ISSUED,
            issue_date=self.today - timedelta(days=7),
            expected_delivery_date=self.today - timedelta(days=1),
        )
        po_received = PurchaseOrder.objects.create(
            organization=self.org,
            vendor=self.vendor,
            project=self.project,
            status=PurchaseOrder.Status.RECEIVED,
            issue_date=self.today - timedelta(days=14),
            expected_delivery_date=self.today - timedelta(days=5),
        )
        GoodsReceipt.objects.create(
            organization=self.org,
            purchase_order=po_received,
            status=GoodsReceipt.Status.ACCEPTED,
            received_date=self.today - timedelta(days=1),
            received_by="Site Store",
        )

    def test_construction_schedule_get_returns_timeline_sections_and_links(self):
        response = self.client.get(
            "/api/projects/construction/schedule/",
            {"project": str(self.project.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        schedule = payload["schedule"]

        self.assertEqual(payload["filters"]["project"], self.project.id)
        self.assertEqual(schedule["project"], self.project.id)
        self.assertIn("master_schedule", schedule)
        self.assertIn("phase_schedules", schedule)
        self.assertIn("lookahead_schedules", schedule)
        self.assertIn("task_dependencies", schedule)
        self.assertIn("critical_path", schedule)
        self.assertIn("resource_assignments", schedule)
        self.assertIn("linked_sources", schedule)
        self.assertEqual(len(schedule["phase_schedules"]), 2)

        self.assertEqual(
            schedule["linked_sources"]["procurement_deliveries"]["upcoming"],
            1,
        )
        self.assertEqual(
            schedule["linked_sources"]["procurement_deliveries"]["overdue"],
            1,
        )
        self.assertEqual(
            schedule["linked_sources"]["procurement_deliveries"]["received"],
            1,
        )
        self.assertEqual(
            schedule["linked_sources"]["procurement_deliveries"]["goods_receipts_logged"],
            1,
        )
        self.assertGreaterEqual(schedule["lookahead_schedules"]["overdue_open_tasks"], 1)
        self.assertEqual(schedule["timeline_sections"]["project_manager"], "")
        self.assertEqual(schedule["resource_assignments"]["project_manager"], "Ada Manager")

    def test_construction_schedule_patch_updates_timeline_fields(self):
        response = self.client.patch(
            "/api/projects/construction/schedule/",
            {
                "project": self.project.id,
                "lookahead_window_days": 28,
                "notes": "Schedule baseline revised after kickoff.",
                "section_notes": {
                    "master_schedule": "Milestone dates reconfirmed.",
                    "critical_path": "Foundation to structure remains critical.",
                },
                "timeline_sections": {
                    "project_manager": "Approved revised sequencing.",
                    "task_assignees": "Need early MEP coordination drawings.",
                    "site_workers": "Night shift requested for concrete pours.",
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        schedule = response.json()["schedule"]

        self.assertEqual(schedule["lookahead_window_days"], 28)
        self.assertEqual(schedule["notes"], "Schedule baseline revised after kickoff.")
        self.assertEqual(
            schedule["section_notes"]["master_schedule"],
            "Milestone dates reconfirmed.",
        )
        self.assertEqual(
            schedule["section_notes"]["critical_path"],
            "Foundation to structure remains critical.",
        )
        self.assertEqual(
            schedule["timeline_sections"]["project_manager"],
            "Approved revised sequencing.",
        )
        self.assertEqual(
            schedule["timeline_sections"]["task_assignees"],
            "Need early MEP coordination drawings.",
        )
        self.assertEqual(
            schedule["timeline_sections"]["site_workers"],
            "Night shift requested for concrete pours.",
        )

        persisted = ProjectConstructionSchedule.objects.get(project=self.project)
        self.assertEqual(persisted.lookahead_window_days, 28)
        self.assertEqual(
            persisted.project_manager_updates,
            "Approved revised sequencing.",
        )


class ProjectWorkPackageWorkspaceTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Work Package Test Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="work-package-admin",
            email="work-package-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.admin)

        self.project = Project.objects.create(
            organization=self.org,
            name="Project Packages",
            status=Project.Status.IN_PROGRESS,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Structure",
            status=ProjectPhase.Status.IN_PROGRESS,
        )

        self.contractor = Vendor.objects.create(
            organization=self.org,
            name="Structure Contractor",
            category=Vendor.Category.CONTRACTOR,
        )
        self.additional_contractor = Vendor.objects.create(
            organization=self.org,
            name="Finishes Contractor",
            category=Vendor.Category.CONTRACTOR,
        )
        self.purchase_order = PurchaseOrder.objects.create(
            organization=self.org,
            vendor=self.contractor,
            project=self.project,
            status=PurchaseOrder.Status.ISSUED,
            issue_date=timezone.localdate(),
            expected_delivery_date=timezone.localdate() + timedelta(days=5),
        )
        self.cost_entry = ProjectCostEntry.objects.create(
            organization=self.org,
            phase=self.phase,
            description="Concrete placement",
            amount=Decimal("350000.00"),
            date=timezone.localdate(),
            category=ProjectCostEntry.Category.MATERIALS,
        )
        self.inspection = ProjectExecutionInspection.objects.create(
            organization=self.org,
            project=self.project,
            phase=self.phase,
            inspection_type=ProjectExecutionInspection.InspectionType.WORKMANSHIP,
            status=ProjectExecutionInspection.Status.PLANNED,
            inspected_on=timezone.localdate(),
            inspector_name="QA Inspector",
            work_package="Structural concrete",
        )

    def test_work_package_setup_options_returns_linked_sources(self):
        response = self.client.get(
            "/api/projects/work-packages/setup-options/",
            {"project": str(self.project.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()

        self.assertEqual(payload["projects"][0]["id"], self.project.id)
        self.assertEqual(payload["phases"][0]["id"], self.phase.id)
        self.assertEqual(payload["contractors"][0]["id"], self.contractor.id)
        self.assertEqual(payload["purchase_orders"][0]["id"], self.purchase_order.id)
        self.assertEqual(payload["cost_entries"][0]["id"], self.cost_entry.id)
        self.assertEqual(payload["inspections"][0]["id"], self.inspection.id)
        self.assertIn("Structural concrete", payload["examples"])

    def test_work_package_create_persists_cross_module_links(self):
        response = self.client.post(
            "/api/projects/work-packages/",
            {
                "project": self.project.id,
                "phase": self.phase.id,
                "name": "Structural concrete",
                "scope_description": "Columns, beams and suspended slab concrete works.",
                "contractor": self.contractor.id,
                "boq_items": [
                    "Reinforcement steel",
                    "C30 concrete supply",
                ],
                "budget": "1200000.00",
                "start_date": "2026-03-15",
                "end_date": "2026-05-30",
                "quality_requirements": "Cube test every 50m3 and slump test per pour.",
                "safety_requirements": "Edge protection, harness, and lifting permit controls.",
                "inspection_plan": "Weekly concrete quality inspections and hold-point signoffs.",
                "linked_purchase_orders": [self.purchase_order.id],
                "linked_cost_entries": [self.cost_entry.id],
                "linked_contractors": [self.additional_contractor.id],
                "linked_inspections": [self.inspection.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()

        self.assertTrue(payload["package_id"].startswith("WP-"))
        self.assertEqual(payload["project"], self.project.id)
        self.assertEqual(payload["phase"], self.phase.id)
        self.assertEqual(payload["contractor"], self.contractor.id)
        self.assertEqual(payload["linked_modules"]["procurement"]["purchase_orders"], 1)
        self.assertEqual(payload["linked_modules"]["finance"]["cost_entries"], 1)
        self.assertEqual(payload["linked_modules"]["contractors"]["count"], 2)
        self.assertEqual(payload["linked_modules"]["inspections"]["count"], 1)

        stored = ProjectWorkPackage.objects.get(id=payload["id"])
        self.assertEqual(stored.project_id, self.project.id)
        self.assertEqual(stored.phase_id, self.phase.id)
        self.assertEqual(stored.contractor_id, self.contractor.id)
        self.assertEqual(stored.linked_purchase_orders.count(), 1)
        self.assertEqual(stored.linked_cost_entries.count(), 1)
        self.assertEqual(stored.linked_contractors.count(), 1)
        self.assertEqual(stored.linked_inspections.count(), 1)


class ProjectContractorManagementWorkspaceTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Contractor Management Test Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="contractor-management-admin",
            email="contractor-management-admin@example.com",
            password="pass1234",
        )
        self.client.force_authenticate(user=self.admin)

        self.project = Project.objects.create(
            organization=self.org,
            name="Project Contractor Hub",
            status=Project.Status.IN_PROGRESS,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Structure",
            status=ProjectPhase.Status.IN_PROGRESS,
        )
        self.contractor = Vendor.objects.create(
            organization=self.org,
            name="Concrete Masters Ltd",
            category=Vendor.Category.CONTRACTOR,
            contact_person="Ada Mason",
            email="ops@concretemasters.test",
            phone="+234800000111",
            address="Yaba, Lagos",
        )
        self.work_package = ProjectWorkPackage.objects.create(
            organization=self.org,
            project=self.project,
            phase=self.phase,
            contractor=self.contractor,
            name="Structural concrete",
            scope_description="Columns and slab concrete execution.",
            budget=Decimal("1250000.00"),
        )
        self.rfi = ProjectFieldEscalation.objects.create(
            organization=self.org,
            project=self.project,
            issue_type=ProjectFieldEscalation.IssueType.RFI_PENDING,
            title="Clarify slab reinforcement spacing",
            status=ProjectFieldEscalation.Status.OPEN,
        )
        self.inspection = ProjectExecutionInspection.objects.create(
            organization=self.org,
            project=self.project,
            phase=self.phase,
            inspection_type=ProjectExecutionInspection.InspectionType.WORKMANSHIP,
            status=ProjectExecutionInspection.Status.PASSED,
            inspected_on=timezone.localdate(),
            inspector_name="QA Manager",
            overall_score=Decimal("92.00"),
            work_package="Structural concrete",
        )

    def test_setup_options_returns_contractors_work_packages_rfis_and_inspections(self):
        response = self.client.get(
            "/api/projects/contractor-management/setup-options/",
            {"project": str(self.project.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()

        self.assertEqual(payload["projects"][0]["id"], self.project.id)
        self.assertEqual(payload["contractors"][0]["id"], self.contractor.id)
        self.assertEqual(payload["work_packages"][0]["id"], self.work_package.id)
        self.assertEqual(payload["rfis"][0]["id"], self.rfi.id)
        self.assertEqual(payload["inspections"][0]["id"], self.inspection.id)

    def test_create_profile_persists_received_items_and_links(self):
        response = self.client.post(
            "/api/projects/contractor-management/",
            {
                "project": self.project.id,
                "contractor": self.contractor.id,
                "company_profile": "Regional reinforced concrete specialist.",
                "trade_specialization": "Structural concrete",
                "contract_value": "1450000.00",
                "insurance": "Contractors all-risk policy valid through Q4.",
                "licenses": "COREN, Lagos State Contractor Permit",
                "performance_rating": "4.30",
                "payment_history": "Mobilization paid, first valuation certified.",
                "safety_record": "2,100 safe man-hours with zero LTIs.",
                "quality_record": "All cube tests within target strength range.",
                "site_instructions": "Maintain pour sequence by zone.\nSubmit daily reinforcement checklists.",
                "work_packages": [self.work_package.id],
                "rfis": [self.rfi.id],
                "inspection_results": [self.inspection.id],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()

        self.assertEqual(payload["project"], self.project.id)
        self.assertEqual(payload["contractor"], self.contractor.id)
        self.assertEqual(payload["work_package_records"][0]["id"], self.work_package.id)
        self.assertEqual(payload["rfi_records"][0]["id"], self.rfi.id)
        self.assertEqual(payload["inspection_result_records"][0]["id"], self.inspection.id)
        self.assertEqual(payload["received_items"]["site_instructions"]["count"], 2)
        self.assertEqual(payload["received_items"]["rfis"]["count"], 1)
        self.assertEqual(payload["received_items"]["inspection_results"]["count"], 1)

        stored = ProjectContractorProfile.objects.get(id=payload["id"])
        self.assertEqual(stored.project_id, self.project.id)
        self.assertEqual(stored.contractor_id, self.contractor.id)
        self.assertEqual(stored.work_packages.count(), 1)
        self.assertEqual(stored.rfis.count(), 1)
        self.assertEqual(stored.inspection_results.count(), 1)


class ProjectFieldOperationsMirrorTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Field Ops Mirror Test Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="field-ops-mirror-admin",
            email="field-ops-mirror-admin@example.com",
            password="pass1234",
        )
        profile = getattr(self.admin, "profile", None)
        if profile is not None:
            profile.organization = self.org
            profile.save(update_fields=["organization"])
        self.client.force_authenticate(user=self.admin)

        self.project = Project.objects.create(
            organization=self.org,
            name="Project Mirror",
            status=Project.Status.IN_PROGRESS,
        )
        self.report_date = timezone.localdate()
        self.report_date_str = self.report_date.isoformat()

    def test_daily_site_report_create_and_update_mirrors_workforce_log_counts(self):
        create_response = self.client.post(
            "/api/projects/field-operations/reports/",
            {
                "project": self.project.id,
                "report_date": self.report_date_str,
                "shift": ProjectDailySiteReport.Shift.DAY,
                "laborers_count": 10,
                "skilled_count": 6,
                "supervisors_count": 2,
                "subcontractors_count": 3,
                "equipment_operators_count": 1,
                "equipment_used": "Tower crane and plate compactor",
                "materials_delivered": "Cement, rebar, plumbing fittings",
                "materials_consumed": "Cement and rebar",
                "visitors_log": "Client representative and structural consultant",
                "instructions_issued": "Proceed with slab pour only after rebar signoff",
                "work_completed": "Slab formwork completed",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        created_payload = create_response.json()
        self.assertEqual(created_payload["equipment_used"], "Tower crane and plate compactor")
        self.assertEqual(created_payload["materials_delivered"], "Cement, rebar, plumbing fittings")
        self.assertEqual(created_payload["materials_consumed"], "Cement and rebar")
        self.assertEqual(created_payload["visitors_log"], "Client representative and structural consultant")
        self.assertEqual(created_payload["instructions_issued"], "Proceed with slab pour only after rebar signoff")

        workforce_log = ProjectWorkforceLog.objects.get(
            project=self.project,
            report_date=self.report_date,
            shift=ProjectWorkforceLog.Shift.DAY,
        )
        self.assertEqual(workforce_log.laborers_count, 10)
        self.assertEqual(workforce_log.skilled_count, 6)
        self.assertEqual(workforce_log.supervisors_count, 2)
        self.assertEqual(workforce_log.subcontractors_count, 3)
        self.assertEqual(workforce_log.equipment_operators_count, 1)

        update_response = self.client.patch(
            f"/api/projects/field-operations/reports/{created_payload['id']}/",
            {
                "laborers_count": 14,
                "skilled_count": 8,
                "supervisors_count": 3,
                "subcontractors_count": 4,
                "equipment_operators_count": 2,
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        workforce_log.refresh_from_db()
        self.assertEqual(workforce_log.laborers_count, 14)
        self.assertEqual(workforce_log.skilled_count, 8)
        self.assertEqual(workforce_log.supervisors_count, 3)
        self.assertEqual(workforce_log.subcontractors_count, 4)
        self.assertEqual(workforce_log.equipment_operators_count, 2)
        self.assertEqual(
            ProjectWorkforceLog.objects.filter(
                project=self.project,
                report_date=self.report_date,
                shift=ProjectWorkforceLog.Shift.DAY,
            ).count(),
            1,
        )

    def test_workforce_log_create_and_update_mirrors_daily_site_report_counts(self):
        create_response = self.client.post(
            "/api/projects/field-operations/workforce/",
            {
                "project": self.project.id,
                "report_date": self.report_date_str,
                "shift": ProjectWorkforceLog.Shift.NIGHT,
                "laborers_count": 20,
                "skilled_count": 9,
                "supervisors_count": 4,
                "subcontractors_count": 5,
                "equipment_operators_count": 3,
                "notes": "Night shift concrete preparation team.",
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        created_payload = create_response.json()

        report = ProjectDailySiteReport.objects.get(
            project=self.project,
            report_date=self.report_date,
            shift=ProjectDailySiteReport.Shift.NIGHT,
        )
        self.assertEqual(report.laborers_count, 20)
        self.assertEqual(report.skilled_count, 9)
        self.assertEqual(report.supervisors_count, 4)
        self.assertEqual(report.subcontractors_count, 5)
        self.assertEqual(report.equipment_operators_count, 3)

        update_response = self.client.patch(
            f"/api/projects/field-operations/workforce/{created_payload['id']}/",
            {
                "laborers_count": 24,
                "skilled_count": 10,
                "supervisors_count": 5,
                "subcontractors_count": 6,
                "equipment_operators_count": 4,
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        report.refresh_from_db()
        self.assertEqual(report.laborers_count, 24)
        self.assertEqual(report.skilled_count, 10)
        self.assertEqual(report.supervisors_count, 5)
        self.assertEqual(report.subcontractors_count, 6)
        self.assertEqual(report.equipment_operators_count, 4)
        self.assertEqual(
            ProjectDailySiteReport.objects.filter(
                project=self.project,
                report_date=self.report_date,
                shift=ProjectDailySiteReport.Shift.NIGHT,
            ).count(),
            1,
        )


class ProjectWorkforceIntegrationFieldTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Field Workforce Integration Org")
        user_model = get_user_model()
        self.admin = user_model.objects.create_superuser(
            username="field-workforce-integration-admin",
            email="field-workforce-integration-admin@example.com",
            password="pass1234",
        )
        profile = getattr(self.admin, "profile", None)
        if profile is not None:
            profile.organization = self.org
            profile.save(update_fields=["organization"])
        self.client.force_authenticate(user=self.admin)

        self.project = Project.objects.create(
            organization=self.org,
            name="Project Workforce Integration",
            status=Project.Status.IN_PROGRESS,
        )
        self.phase = ProjectPhase.objects.create(
            organization=self.org,
            project=self.project,
            name="Structure",
            status=ProjectPhase.Status.IN_PROGRESS,
        )
        self.task = ProjectTask.objects.create(
            organization=self.org,
            phase=self.phase,
            name="Rebar fixing",
            status=ProjectTask.Status.IN_PROGRESS,
        )
        self.contractor = Vendor.objects.create(
            organization=self.org,
            name="Steel Crew Ltd",
            category=Vendor.Category.CONTRACTOR,
        )
        self.worker_user = user_model.objects.create_user(
            username="worker-integration-user",
            email="worker-integration-user@example.com",
            password="pass1234",
            first_name="Musa",
            last_name="Adebayo",
        )
        self.employee = EmployeeRecord.objects.create(
            organization=self.org,
            user=self.worker_user,
            employment_status=EmployeeRecord.EmploymentStatus.ACTIVE,
        )
        OrientationChecklistItem.objects.create(
            organization=self.org,
            employee=self.employee,
            title="Safety induction complete",
            category=OrientationChecklistItem.Category.SAFETY_TRAINING,
            is_completed=True,
            completed_date=timezone.localdate(),
        )
        Payslip.objects.create(
            organization=self.org,
            employee=self.employee,
            period_start=timezone.localdate() - timedelta(days=30),
            period_end=timezone.localdate(),
            basic_salary=Decimal("150000.00"),
            gross_salary=Decimal("165000.00"),
            net_salary=Decimal("155000.00"),
            status=Payslip.Status.GENERATED,
        )

    def test_workforce_log_supports_new_fields_and_returns_hr_payroll_safety_status(self):
        response = self.client.post(
            "/api/projects/field-operations/workforce/",
            {
                "project": self.project.id,
                "worker_id": "WK-442",
                "employee": self.employee.id,
                "trade": "Steel Fixing",
                "contractor": self.contractor.id,
                "report_date": timezone.localdate().isoformat(),
                "daily_attendance": "present",
                "shift": ProjectWorkforceLog.Shift.DAY,
                "task_assigned": self.task.id,
                "productivity": "88.50",
                "overtime_hours": "1.75",
                "laborers_count": 12,
                "skilled_count": 7,
                "supervisors_count": 2,
                "subcontractors_count": 3,
                "equipment_operators_count": 1,
                "notes": "Strong output on reinforcement works.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payload = response.json()

        self.assertEqual(payload["worker_id"], "WK-442")
        self.assertEqual(payload["trade"], "Steel Fixing")
        self.assertEqual(payload["contractor"], self.contractor.id)
        self.assertEqual(payload["contractor_name"], self.contractor.name)
        self.assertEqual(payload["task_assigned"], self.task.id)
        self.assertEqual(payload["task_assigned_name"], self.task.name)
        self.assertEqual(payload["daily_attendance"], "present")
        self.assertEqual(payload["productivity"], "88.50")
        self.assertEqual(payload["overtime_hours"], "1.75")
        self.assertEqual(payload["employee"], self.employee.id)
        self.assertEqual(payload["employee_name"], "Musa Adebayo")
        self.assertEqual(payload["hr_employment_status"], EmployeeRecord.EmploymentStatus.ACTIVE)
        self.assertEqual(payload["payroll_status"], "synced")
        self.assertEqual(payload["safety_training_status"], "compliant")
        self.assertIsNotNone(payload["latest_payslip_period_end"])
        self.assertEqual(payload["latest_payslip_net_salary"], "155000.00")

    def test_workforce_setup_options_exposes_employees_contractors_and_tasks(self):
        response = self.client.get(
            "/api/projects/field-operations/workforce/setup-options/",
            {"project": str(self.project.id)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()

        self.assertIn("employees", payload)
        self.assertIn("contractors", payload)
        self.assertIn("tasks", payload)

        self.assertTrue(any(row["id"] == self.employee.id for row in payload["employees"]))
        self.assertTrue(any(row["id"] == self.contractor.id for row in payload["contractors"]))
        self.assertTrue(any(row["id"] == self.task.id for row in payload["tasks"]))

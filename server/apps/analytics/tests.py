"""
Analytics test suite.

Covers computation correctness, snapshot task integrity, view behaviour
(snapshot-first, live fallback, org scoping), freshness health endpoint,
drilldown endpoints, and custom dashboard CRUD.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.finance.models import Account, Budget, BudgetLineItem
from apps.procurement.models import PurchaseOrder, PurchaseRequisition, Vendor
from apps.projects.models import Project, ProjectCostEntry, ProjectPhase, ProjectRiskRegisterEntry
from apps.properties.models import (
    Property,
    PropertyEncumbrance,
    PropertyValuation,
    Unit,
)
from apps.workflows.models import WorkflowInstance, WorkflowTemplate

from .computations import (
    compute_approval_time,
    compute_budget_overrun,
    compute_classification_breakdown,
    compute_cost_variance,
    compute_emergency_purchases,
    compute_encumbrance_summary,
    compute_full_board_kpis,
    compute_full_portfolio_snapshot,
    compute_portfolio_kpis,
    compute_procurement_cycle_time,
    compute_project_budget_summary,
    compute_top_properties,
    compute_type_distribution,
    compute_unit_occupancy,
    compute_valuation_history,
    compute_vendor_reliability,
)
from .models import BoardKpiSnapshot, CustomDashboard, PortfolioSnapshot

User = get_user_model()


class _AnalyticsTestDataMixin:
    """Shared seed data for analytics tests."""

    @classmethod
    def _create_test_data(cls):
        cls.org = Organization.objects.create(name="Analytics Test Org")
        cls.org_b = Organization.objects.create(name="Other Org")

        # Users
        cls.admin = User.objects.create_user(
            username="analytics-admin@test.com",
            email="analytics-admin@test.com",
            password="Pass123!",
            is_superuser=True,
            is_staff=True,
        )
        profile = cls.admin.profile
        profile.organization = cls.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.save(update_fields=["organization", "role", "user_status"])

        cls.member = User.objects.create_user(
            username="analytics-member@test.com",
            email="analytics-member@test.com",
            password="Pass123!",
        )
        m_profile = cls.member.profile
        m_profile.organization = cls.org
        m_profile.role = "admin"  # org admin: bypasses RBAC but still org-scoped
        m_profile.user_status = "active"
        m_profile.save(update_fields=["organization", "role", "user_status"])

        cls.member_b = User.objects.create_user(
            username="other-member@test.com",
            email="other-member@test.com",
            password="Pass123!",
        )
        m_b_profile = cls.member_b.profile
        m_b_profile.organization = cls.org_b
        m_b_profile.role = "admin"  # org admin: bypasses RBAC but still org-scoped
        m_b_profile.user_status = "active"
        m_b_profile.save(update_fields=["organization", "role", "user_status"])

        today = date.today()

        # Properties
        cls.prop_a = Property.objects.create(
            organization=cls.org,
            name="Tower A",
            property_type="building",
            classification="owned",
            address="1 Main St",
            current_value=Decimal("5000000"),
            acquisition_price=Decimal("4000000"),
            total_area_sqft=Decimal("10000"),
            is_active=True,
        )
        cls.prop_b = Property.objects.create(
            organization=cls.org,
            name="Land B",
            property_type="land",
            classification="lease",
            address="2 Side Rd",
            current_value=Decimal("2000000"),
            acquisition_price=Decimal("2500000"),
            total_area_sqft=Decimal("50000"),
            is_active=True,
        )
        # Property in other org (should not appear for org member)
        Property.objects.create(
            organization=cls.org_b,
            name="Other Prop",
            property_type="building",
            address="3 Other Ave",
            current_value=Decimal("1000000"),
            acquisition_price=Decimal("800000"),
            total_area_sqft=Decimal("5000"),
            is_active=True,
        )

        # Units
        Unit.objects.create(
            organization=cls.org,
            property=cls.prop_a,
            unit_number="A-101",
            status="occupied",
            area_sqft=Decimal("500"),
            asking_price=Decimal("100000"),
        )
        Unit.objects.create(
            organization=cls.org,
            property=cls.prop_a,
            unit_number="A-102",
            status="vacant",
            area_sqft=Decimal("600"),
            asking_price=Decimal("120000"),
        )

        # Valuations
        PropertyValuation.objects.create(
            organization=cls.org,
            property=cls.prop_a,
            valuation_date=today - timedelta(days=15),
            value=Decimal("5000000"),
        )

        # Encumbrances
        PropertyEncumbrance.objects.create(
            organization=cls.org,
            property=cls.prop_a,
            encumbrance_type="mortgage",
            title="Bank Mortgage",
            amount=Decimal("2000000"),
            status="active",
            date_filed=today - timedelta(days=365),
        )

        # Projects
        cls.project_a = Project.objects.create(
            organization=cls.org,
            name="Project Alpha",
            status="in_progress",
            budget=Decimal("500000"),
        )
        phase = ProjectPhase.objects.create(
            organization=cls.org,
            project=cls.project_a,
            name="Phase 1",
            planned_budget=Decimal("200000"),
        )
        ProjectCostEntry.objects.create(
            organization=cls.org,
            phase=phase,
            description="Labour",
            amount=Decimal("250000"),
            date=today,
        )

        # Vendors
        cls.vendor_good = Vendor.objects.create(
            name="Good Vendor",
            organization=cls.org,
            is_active=True,
            performance_rating=Decimal("4.50"),
            delivery_timeliness_score=Decimal("85.00"),
            compliance_status="compliant",
        )
        cls.vendor_poor = Vendor.objects.create(
            name="Poor Vendor",
            organization=cls.org,
            is_active=True,
            performance_rating=Decimal("1.50"),
            delivery_timeliness_score=Decimal("30.00"),
            compliance_status="non_compliant",
        )

        # Purchase Requisitions
        cls.pr_normal = PurchaseRequisition.objects.create(
            organization=cls.org,
            title="Normal PR",
            requester="John",
            required_date=today + timedelta(days=30),
            priority="medium",
        )
        cls.pr_urgent = PurchaseRequisition.objects.create(
            organization=cls.org,
            title="Urgent PR",
            requester="Jane",
            required_date=today + timedelta(days=5),
            priority="urgent",
            project=cls.project_a,
        )

        # Purchase Orders
        cls.po = PurchaseOrder.objects.create(
            organization=cls.org,
            vendor=cls.vendor_good,
            requisition=cls.pr_normal,
            issue_date=today - timedelta(days=5),
        )

        # Budgets
        cls.account = Account.objects.create(
            organization=cls.org,
            code="5001",
            name="Office Supplies",
            account_type="expense",
            sub_type="operating_expense",
        )
        cls.budget = Budget.objects.create(
            organization=cls.org,
            name="2025 OpEx",
            status="active",
            start_date=today - timedelta(days=180),
            end_date=today + timedelta(days=180),
            total_amount=Decimal("100000"),
        )
        BudgetLineItem.objects.create(
            budget=cls.budget,
            account=cls.account,
            budgeted_amount=Decimal("50000"),
        )

        # Workflow Templates + Instances
        cls.wf_template = WorkflowTemplate.objects.create(
            organization=cls.org,
            code="test-approval",
            name="Test Approval",
        )
        ct = ContentType.objects.get_for_model(Project)
        now = timezone.now()
        cls.wf_instance = WorkflowInstance.objects.create(
            template=cls.wf_template,
            content_type=ct,
            object_id=cls.project_a.id,
            state="approved",
            submitted_at=now - timedelta(hours=8),
            completed_at=now - timedelta(hours=2),
        )


# ── Computation Tests ──────────────────────────────────────────────────


class AnalyticsComputationTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()
        cls.active_qs = Property.objects.filter(
            is_active=True, organization=cls.org
        )

    def test_portfolio_kpis_aggregates(self):
        result = compute_portfolio_kpis(self.active_qs)
        self.assertEqual(result["property_count"], 2)
        self.assertEqual(Decimal(result["total_value"]), Decimal("7000000"))
        self.assertEqual(Decimal(result["total_acquisition"]), Decimal("6500000"))
        self.assertEqual(Decimal(result["total_area_sqft"]), Decimal("60000"))
        self.assertEqual(
            Decimal(result["unrealized_gain"]), Decimal("500000")
        )

    def test_type_distribution_groups(self):
        result = compute_type_distribution(self.active_qs)
        types = {r["type"] for r in result}
        self.assertIn("building", types)
        self.assertIn("land", types)

    def test_classification_breakdown_groups(self):
        result = compute_classification_breakdown(self.active_qs)
        classes = {r["classification"] for r in result}
        self.assertIn("owned", classes)
        self.assertIn("lease", classes)

    def test_valuation_history(self):
        result = compute_valuation_history(self.org.id)
        self.assertGreaterEqual(len(result), 1)
        self.assertIn("total_value", result[0])

    def test_unit_occupancy(self):
        result = compute_unit_occupancy(self.active_qs)
        statuses = {r["status"] for r in result}
        self.assertIn("occupied", statuses)
        self.assertIn("vacant", statuses)

    def test_project_budget_summary(self):
        result = compute_project_budget_summary(self.org.id)
        self.assertGreaterEqual(len(result), 1)
        proj = result[0]
        self.assertIn("variance", proj)

    def test_top_properties_appreciating(self):
        result = compute_top_properties(self.active_qs, ascending=False)
        self.assertGreaterEqual(len(result), 1)
        # Tower A appreciated (5M vs 4M)
        self.assertEqual(result[0]["name"], "Tower A")

    def test_top_properties_depreciating(self):
        result = compute_top_properties(self.active_qs, ascending=True)
        self.assertGreaterEqual(len(result), 1)
        # Land B depreciated (2M vs 2.5M)
        self.assertEqual(result[0]["name"], "Land B")

    def test_encumbrance_summary(self):
        result = compute_encumbrance_summary(self.active_qs)
        self.assertGreaterEqual(result["total_count"], 1)
        self.assertEqual(Decimal(result["total_amount"]), Decimal("2000000"))

    def test_full_portfolio_snapshot_shape(self):
        result = compute_full_portfolio_snapshot(self.org.id)
        expected_keys = {
            "total_value",
            "total_acquisition",
            "property_count",
            "total_area_sqft",
            "avg_price_per_sqft",
            "unrealized_gain",
            "type_distribution",
            "classification_breakdown",
            "valuation_history",
            "unit_occupancy",
            "project_budget_summary",
            "top_appreciating",
            "top_depreciating",
            "encumbrance_summary",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_procurement_cycle_time(self):
        today = date.today()
        result = compute_procurement_cycle_time(
            today - timedelta(days=30), today, self.org.id
        )
        self.assertIn("value", result)
        self.assertIn("sample_size", result)
        self.assertEqual(result["unit"], "days")

    def test_cost_variance(self):
        result = compute_cost_variance(self.org.id)
        self.assertIn("value", result)
        self.assertGreaterEqual(result["project_count"], 1)
        # Project Alpha: planned 200k, actual 250k → +25%
        self.assertGreater(result["value"], 0)
        self.assertGreaterEqual(result["over_budget_projects"], 1)

    def test_vendor_reliability(self):
        result = compute_vendor_reliability(self.org.id)
        self.assertIn("value", result)
        self.assertGreaterEqual(result["vendor_count"], 2)
        self.assertEqual(result["unit"], "score_0_100")

    def test_emergency_purchases(self):
        today = date.today()
        result = compute_emergency_purchases(
            today - timedelta(days=30), today + timedelta(days=1), self.org.id
        )
        self.assertIn("value", result)
        # 1 urgent out of 2 = 50%
        self.assertEqual(result["emergency_count"], 1)
        self.assertEqual(result["total_requisitions"], 2)
        self.assertAlmostEqual(result["value"], 50.0, places=0)

    def test_budget_overrun(self):
        result = compute_budget_overrun(self.org.id)
        self.assertIn("value", result)
        self.assertEqual(result["unit"], "percentage")

    def test_approval_time(self):
        today = date.today()
        result = compute_approval_time(
            today - timedelta(days=1), today + timedelta(days=1), self.org.id
        )
        self.assertIn("value", result)
        # Workflow took 6 hours (submitted -8h, completed -2h)
        self.assertAlmostEqual(result["value"], 6.0, delta=0.5)
        self.assertEqual(result["completed_workflows"], 1)

    def test_full_board_kpis_shape(self):
        today = date.today()
        result = compute_full_board_kpis(
            self.org.id, today - timedelta(days=180), today
        )
        expected_keys = {
            "procurement_cycle_time_days",
            "cost_variance_per_project_pct",
            "vendor_reliability_score",
            "emergency_purchases_pct",
            "budget_overrun_frequency_pct",
            "average_approval_time_hours",
            "period_start",
            "period_end",
        }
        self.assertEqual(set(result.keys()), expected_keys)


# ── Snapshot Task Tests ────────────────────────────────────────────────


class SnapshotTaskTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    def test_daily_portfolio_snapshot_creates_record(self):
        from .tasks import compute_daily_portfolio_snapshots

        result = compute_daily_portfolio_snapshots()
        self.assertGreaterEqual(result["orgs_processed"], 1)
        self.assertTrue(
            PortfolioSnapshot.objects.filter(organization=self.org).exists()
        )

    def test_daily_portfolio_snapshot_is_idempotent(self):
        from .tasks import compute_daily_portfolio_snapshots

        compute_daily_portfolio_snapshots()
        compute_daily_portfolio_snapshots()
        count = PortfolioSnapshot.objects.filter(
            organization=self.org,
            snapshot_date=date.today(),
        ).count()
        self.assertEqual(count, 1)

    def test_hourly_board_kpi_snapshot_creates_record(self):
        from .tasks import compute_hourly_board_kpi_snapshots

        result = compute_hourly_board_kpi_snapshots()
        self.assertGreaterEqual(result["orgs_processed"], 1)
        self.assertTrue(
            BoardKpiSnapshot.objects.filter(organization=self.org).exists()
        )

    def test_hourly_board_kpi_snapshot_is_idempotent(self):
        from .tasks import compute_hourly_board_kpi_snapshots

        compute_hourly_board_kpi_snapshots()
        compute_hourly_board_kpi_snapshots()
        now = timezone.now()
        snapshot_hour = now.replace(minute=0, second=0, microsecond=0)
        count = BoardKpiSnapshot.objects.filter(
            organization=self.org,
            snapshot_hour=snapshot_hour,
        ).count()
        self.assertEqual(count, 1)

    def test_snapshot_task_handles_computation_error(self):
        from .tasks import compute_daily_portfolio_snapshots

        with patch(
            "apps.analytics.tasks.compute_full_portfolio_snapshot",
            side_effect=Exception("boom"),
        ):
            result = compute_daily_portfolio_snapshots()
            self.assertGreaterEqual(result["errors"], 1)


# ── Portfolio View Tests ───────────────────────────────────────────────


class PortfolioAnalyticsViewTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_member_gets_portfolio_data(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("kpis", resp.data)

    def test_member_gets_cross_module_summaries(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("construction_summary", resp.data)
        self.assertIn("crm_summary", resp.data)
        self.assertIn("hr_summary", resp.data)
        self.assertIn("procurement_summary", resp.data)
        self.assertIn("facility_summary", resp.data)
        self.assertIn("tenant_summary", resp.data)

    def test_snapshot_first_serves_snapshot(self):
        from django.core.cache import cache as django_cache

        django_cache.clear()  # Avoid stale cache from prior tests
        now = timezone.now()
        PortfolioSnapshot.objects.create(
            organization=self.org,
            snapshot_date=date.today(),
            total_value=Decimal("9999"),
            computed_at=now,
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("_snapshot", resp.data)
        self.assertEqual(resp.data["kpis"]["total_value"], "9999.00")

    def test_live_fallback_when_no_snapshot(self):
        PortfolioSnapshot.objects.filter(organization=self.org).delete()
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("_snapshot", resp.data)

    def test_superuser_gets_data(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


# ── Board KPI View Tests ──────────────────────────────────────────────


class BoardKpiViewTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/analytics/board-kpis/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_member_gets_board_kpi_data(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/board-kpis/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("period", resp.data)
        self.assertIn("kpis", resp.data)

    def test_custom_date_range(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get(
            "/api/analytics/board-kpis/",
            {"start_date": "2024-01-01", "end_date": "2024-06-30"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["period"]["start_date"], "2024-01-01")

    def test_snapshot_first_for_default_period(self):
        now = timezone.now()
        today = now.date()
        snapshot_hour = now.replace(minute=0, second=0, microsecond=0)
        BoardKpiSnapshot.objects.create(
            organization=self.org,
            snapshot_hour=snapshot_hour,
            period_start=today - timedelta(days=180),
            period_end=today,
            procurement_cycle_time_days={"value": 5, "sample_size": 1, "unit": "days"},
            cost_variance_per_project_pct={"value": 0, "project_count": 0, "over_budget_projects": 0, "unit": "percentage"},
            vendor_reliability_score={"value": 0, "vendor_count": 0, "unit": "score_0_100"},
            emergency_purchases_pct={"value": 0, "emergency_count": 0, "total_requisitions": 0, "unit": "percentage"},
            budget_overrun_frequency_pct={"value": 0, "overrun_items": 0, "tracked_items": 0, "unit": "percentage"},
            average_approval_time_hours={"value": 0, "completed_workflows": 0, "unit": "hours"},
            computed_at=now,
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/board-kpis/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("_snapshot", resp.data)

    def test_org_scoping(self):
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/board-kpis/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Should not see org A's data in counts
        kpis = resp.data["kpis"]
        self.assertEqual(kpis["procurement_cycle_time_days"]["sample_size"], 0)


# ── Risk Alerts View Tests ─────────────────────────────────────────────


class RiskAlertsViewTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/analytics/risk-alerts/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_member_gets_risk_alert_payload_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/risk-alerts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("generated_at", resp.data)
        self.assertIn("overview", resp.data)
        self.assertIn("severity_distribution", resp.data)
        self.assertIn("module_totals", resp.data)
        self.assertIn("feeds", resp.data)
        self.assertIn("recent_alerts", resp.data)
        self.assertEqual(len(resp.data["module_totals"]), 6)
        self.assertIn("projects", resp.data["feeds"])
        self.assertIn("workflows", resp.data["feeds"])
        self.assertIn("finance", resp.data["feeds"])
        self.assertIn("procurement", resp.data["feeds"])
        self.assertIn("facilities", resp.data["feeds"])
        self.assertIn("crm", resp.data["feeds"])

    def test_org_scoping(self):
        ProjectRiskRegisterEntry.objects.create(
            organization=self.org,
            project=self.project_a,
            title="Org A risk",
            severity=ProjectRiskRegisterEntry.Severity.CRITICAL,
            status=ProjectRiskRegisterEntry.Status.OPEN,
            risk_score=20,
        )
        project_b = Project.objects.create(
            organization=self.org_b,
            name="Project Beta",
            status="in_progress",
            budget=Decimal("250000"),
        )
        ProjectRiskRegisterEntry.objects.create(
            organization=self.org_b,
            project=project_b,
            title="Org B risk",
            severity=ProjectRiskRegisterEntry.Severity.HIGH,
            status=ProjectRiskRegisterEntry.Status.OPEN,
            risk_score=16,
        )

        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/risk-alerts/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        projects_feed = resp.data["feeds"]["projects"]
        self.assertEqual(projects_feed["summary"]["open_risks"], 1)
        self.assertEqual(projects_feed["critical_alerts"], 0)
        self.assertEqual(projects_feed["high_alerts"], 1)


# ── Snapshot Health View Tests ─────────────────────────────────────────


class SnapshotHealthViewTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    def test_unauthenticated_returns_401(self):
        resp = self.client.get("/api/analytics/health/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_fresh_when_recent(self):
        now = timezone.now()
        PortfolioSnapshot.objects.create(
            organization=self.org,
            snapshot_date=date.today(),
            computed_at=now,
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/health/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["portfolio"]["status"], "fresh")
        self.assertFalse(resp.data["portfolio"]["is_stale"])

    def test_returns_stale_when_old(self):
        now = timezone.now()
        PortfolioSnapshot.objects.create(
            organization=self.org,
            snapshot_date=date.today() - timedelta(days=2),
            computed_at=now - timedelta(hours=26),
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/health/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["portfolio"]["status"], "stale")
        self.assertTrue(resp.data["portfolio"]["is_stale"])

    def test_returns_missing_when_no_snapshot(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/health/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["portfolio"]["status"], "missing")
        self.assertTrue(resp.data["portfolio"]["is_stale"])
        self.assertEqual(resp.data["board_kpis"]["status"], "missing")


# ── Drilldown View Tests ──────────────────────────────────────────────


class DrilldownViewTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    DRILLDOWN_URLS = [
        "/api/analytics/drilldowns/procurement-cycle/",
        "/api/analytics/drilldowns/cost-variance/",
        "/api/analytics/drilldowns/vendor-reliability/",
        "/api/analytics/drilldowns/emergency-purchases/",
        "/api/analytics/drilldowns/budget-overrun/",
        "/api/analytics/drilldowns/approval-time/",
    ]

    def test_all_drilldowns_require_auth(self):
        for url in self.DRILLDOWN_URLS:
            resp = self.client.get(url)
            self.assertEqual(
                resp.status_code, status.HTTP_401_UNAUTHORIZED, msg=url
            )

    def test_all_drilldowns_return_200_for_member(self):
        self.client.force_authenticate(user=self.member)
        for url in self.DRILLDOWN_URLS:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK, msg=url)

    def test_procurement_cycle_drilldown_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/drilldowns/procurement-cycle/")
        self.assertIn("histogram", resp.data)
        self.assertIn("slowest_pos", resp.data)
        self.assertIn("summary", resp.data)

    def test_cost_variance_drilldown_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/drilldowns/cost-variance/")
        self.assertIn("per_project", resp.data)
        self.assertIn("over_budget_projects", resp.data)
        self.assertIn("summary", resp.data)

    def test_vendor_reliability_drilldown_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/drilldowns/vendor-reliability/")
        self.assertIn("top_vendors", resp.data)
        self.assertIn("bottom_vendors", resp.data)
        self.assertIn("score_distribution", resp.data)

    def test_emergency_purchases_drilldown_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/drilldowns/emergency-purchases/")
        self.assertIn("trend", resp.data)
        self.assertIn("by_category", resp.data)
        self.assertIn("recent_emergencies", resp.data)

    def test_budget_overrun_drilldown_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/drilldowns/budget-overrun/")
        self.assertIn("per_budget", resp.data)
        self.assertIn("worst_line_items", resp.data)
        self.assertIn("summary", resp.data)

    def test_approval_time_drilldown_shape(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/drilldowns/approval-time/")
        self.assertIn("by_workflow_type", resp.data)
        self.assertIn("slowest_approvals", resp.data)
        self.assertIn("summary", resp.data)

    def test_drilldown_org_scoping(self):
        """Member of org_b should not see org A's drilldown data."""
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/drilldowns/cost-variance/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["per_project"]), 0)


# ── Custom Dashboard Tests ────────────────────────────────────────────


class CustomDashboardViewTests(_AnalyticsTestDataMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

    def _valid_layout(self):
        return [
            {
                "widget_type": "board_kpi_card",
                "kpi_key": "procurement_cycle_time_days",
                "position": {"x": 0, "y": 0, "w": 4, "h": 2},
                "config": {},
            },
        ]

    def test_create_dashboard(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.post(
            "/api/analytics/dashboards/",
            {"name": "My Dashboard", "layout": self._valid_layout()},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "My Dashboard")

    def test_list_shows_only_own(self):
        CustomDashboard.objects.create(
            user=self.member, name="Mine", layout=self._valid_layout()
        )
        CustomDashboard.objects.create(
            user=self.member_b, name="Theirs", layout=self._valid_layout()
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.get("/api/analytics/dashboards/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        names = [d["name"] for d in results]
        self.assertIn("Mine", names)
        self.assertNotIn("Theirs", names)

    def test_update_dashboard(self):
        dash = CustomDashboard.objects.create(
            user=self.member, name="Old Name", layout=self._valid_layout()
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.patch(
            f"/api/analytics/dashboards/{dash.id}/",
            {"name": "New Name"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["name"], "New Name")

    def test_delete_dashboard(self):
        dash = CustomDashboard.objects.create(
            user=self.member, name="Delete Me", layout=self._valid_layout()
        )
        self.client.force_authenticate(user=self.member)
        resp = self.client.delete(f"/api/analytics/dashboards/{dash.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomDashboard.objects.filter(id=dash.id).exists())

    def test_invalid_widget_type_rejected(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.post(
            "/api/analytics/dashboards/",
            {
                "name": "Bad",
                "layout": [
                    {
                        "widget_type": "nonexistent_widget",
                        "position": {"x": 0, "y": 0, "w": 4, "h": 2},
                        "config": {},
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_position_rejected(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.post(
            "/api/analytics/dashboards/",
            {
                "name": "Bad",
                "layout": [
                    {
                        "widget_type": "board_kpi_card",
                        "position": {"x": 0},  # missing y, w, h
                        "config": {},
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_portfolio_widget_type_accepted(self):
        self.client.force_authenticate(user=self.member)
        resp = self.client.post(
            "/api/analytics/dashboards/",
            {
                "name": "Portfolio Ops Dashboard",
                "layout": [
                    {
                        "widget_type": "portfolio_procurement_commitments",
                        "position": {"x": 0, "y": 0, "w": 6, "h": 3},
                        "config": {},
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


# ── Data Quality: Null Handling ──────────────────────────────────────


class NullHandlingTests(_AnalyticsTestDataMixin, APITestCase):
    """Verify computations handle null/missing field values gracefully."""

    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

        # Property with all nullable financial fields set to None
        cls.prop_null = Property.objects.create(
            organization=cls.org,
            name="Null Prop",
            property_type="building",
            classification="owned",
            address="99 Null Rd",
            current_value=None,
            acquisition_price=None,
            total_area_sqft=None,
            is_active=True,
        )

    def test_portfolio_kpis_with_null_values(self):
        qs = Property.objects.filter(is_active=True, organization=self.org)
        result = compute_portfolio_kpis(qs)
        # Should not crash; nulls are coalesced to 0
        self.assertEqual(result["property_count"], 3)
        self.assertIsNotNone(result["total_value"])

    def test_type_distribution_with_null_values(self):
        qs = Property.objects.filter(is_active=True, organization=self.org)
        result = compute_type_distribution(qs)
        self.assertGreaterEqual(len(result), 1)

    def test_top_properties_excludes_null_prices(self):
        qs = Property.objects.filter(is_active=True, organization=self.org)
        appreciating = compute_top_properties(qs, ascending=False)
        depreciating = compute_top_properties(qs, ascending=True)
        # Null Prop should be excluded (no current_value / acquisition_price)
        names_app = {p["name"] for p in appreciating}
        names_dep = {p["name"] for p in depreciating}
        self.assertNotIn("Null Prop", names_app)
        self.assertNotIn("Null Prop", names_dep)

    def test_encumbrance_summary_with_no_encumbrances(self):
        qs = Property.objects.filter(id=self.prop_null.id)
        result = compute_encumbrance_summary(qs)
        self.assertEqual(result["total_count"], 0)
        self.assertEqual(Decimal(result["total_amount"]), Decimal("0"))

    def test_vendor_reliability_with_zero_ratings(self):
        Vendor.objects.create(
            name="Zero Rating Vendor",
            organization=self.org,
            is_active=True,
            performance_rating=Decimal("0"),
            delivery_timeliness_score=Decimal("0"),
            compliance_status="pending_review",
        )
        result = compute_vendor_reliability(self.org.id)
        # Should not crash; zero ratings handled gracefully
        self.assertGreaterEqual(result["vendor_count"], 3)

    def test_procurement_cycle_with_no_matching_pos(self):
        today = date.today()
        # Far future range — no POs should match
        result = compute_procurement_cycle_time(
            today + timedelta(days=9000),
            today + timedelta(days=9001),
            self.org.id,
        )
        self.assertEqual(result["value"], 0.0)
        self.assertEqual(result["sample_size"], 0)

    def test_approval_time_with_no_workflows(self):
        result = compute_approval_time(
            date(2000, 1, 1), date(2000, 1, 2), self.org.id
        )
        self.assertEqual(result["value"], 0.0)
        self.assertEqual(result["completed_workflows"], 0)


# ── Data Quality: Balance / Consistency Checks ───────────────────────


class BalanceConsistencyTests(_AnalyticsTestDataMixin, APITestCase):
    """Verify sub-totals and breakdowns are internally consistent."""

    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()
        cls.active_qs = Property.objects.filter(
            is_active=True, organization=cls.org
        )

    def test_type_distribution_sums_to_portfolio_count(self):
        kpis = compute_portfolio_kpis(self.active_qs)
        distribution = compute_type_distribution(self.active_qs)
        dist_total = sum(r["count"] for r in distribution)
        self.assertEqual(dist_total, kpis["property_count"])

    def test_type_distribution_value_sums_to_total(self):
        kpis = compute_portfolio_kpis(self.active_qs)
        distribution = compute_type_distribution(self.active_qs)
        dist_value = sum(Decimal(r["total_value"]) for r in distribution)
        self.assertEqual(dist_value, Decimal(kpis["total_value"]))

    def test_classification_breakdown_sums_to_portfolio_count(self):
        kpis = compute_portfolio_kpis(self.active_qs)
        breakdown = compute_classification_breakdown(self.active_qs)
        breakdown_total = sum(r["count"] for r in breakdown)
        self.assertEqual(breakdown_total, kpis["property_count"])

    def test_unit_occupancy_counts_match_total_units(self):
        occupancy = compute_unit_occupancy(self.active_qs)
        occ_total = sum(r["count"] for r in occupancy)
        actual_units = Unit.objects.filter(
            property__in=self.active_qs
        ).count()
        self.assertEqual(occ_total, actual_units)

    def test_emergency_purchases_counts_are_consistent(self):
        today = date.today()
        result = compute_emergency_purchases(
            today - timedelta(days=30), today + timedelta(days=1), self.org.id
        )
        self.assertLessEqual(
            result["emergency_count"], result["total_requisitions"]
        )
        if result["total_requisitions"] > 0:
            expected_pct = round(
                (result["emergency_count"] / result["total_requisitions"]) * 100,
                2,
            )
            self.assertAlmostEqual(result["value"], expected_pct, places=2)

    def test_cost_variance_over_budget_count_consistent(self):
        result = compute_cost_variance(self.org.id)
        self.assertLessEqual(
            result["over_budget_projects"], result["project_count"]
        )

    def test_budget_overrun_counts_consistent(self):
        result = compute_budget_overrun(self.org.id)
        self.assertLessEqual(
            result["overrun_items"], result["tracked_items"]
        )

    def test_full_portfolio_snapshot_values_match_kpis(self):
        """Full snapshot dict must match individual KPI computation."""
        snapshot = compute_full_portfolio_snapshot(self.org.id)
        kpis = compute_portfolio_kpis(self.active_qs)
        self.assertEqual(snapshot["property_count"], kpis["property_count"])
        self.assertEqual(
            snapshot["total_value"], Decimal(kpis["total_value"])
        )

    def test_full_board_kpis_matches_individual_functions(self):
        today = date.today()
        start = today - timedelta(days=180)
        full = compute_full_board_kpis(self.org.id, start, today)
        individual = compute_procurement_cycle_time(start, today, self.org.id)
        self.assertEqual(
            full["procurement_cycle_time_days"]["value"],
            individual["value"],
        )
        self.assertEqual(
            full["procurement_cycle_time_days"]["sample_size"],
            individual["sample_size"],
        )


# ── Data Quality: Cross-Tenant Leakage Tests ────────────────────────


class CrossTenantLeakageTests(_AnalyticsTestDataMixin, APITestCase):
    """
    Verify strict tenant isolation: org_b member must NEVER see org_a data.
    Tests every analytics endpoint and computation path.
    """

    @classmethod
    def setUpTestData(cls):
        cls._create_test_data()

        # Seed richer data for org_b to prove isolation (not just "empty")
        cls.prop_b = Property.objects.create(
            organization=cls.org_b,
            name="Org B Tower",
            property_type="land",
            classification="lease",
            address="100 OrgB St",
            current_value=Decimal("3000000"),
            acquisition_price=Decimal("2800000"),
            total_area_sqft=Decimal("20000"),
            is_active=True,
        )
        cls.project_b = Project.objects.create(
            organization=cls.org_b,
            name="Project Beta",
            status="in_progress",
            budget=Decimal("300000"),
        )
        phase_b = ProjectPhase.objects.create(
            organization=cls.org_b,
            project=cls.project_b,
            name="Phase B1",
            planned_budget=Decimal("100000"),
        )
        ProjectCostEntry.objects.create(
            organization=cls.org_b,
            phase=phase_b,
            description="Materials",
            amount=Decimal("120000"),
            date=date.today(),
        )
        cls.vendor_b = Vendor.objects.create(
            name="OrgB Vendor",
            organization=cls.org_b,
            is_active=True,
            performance_rating=Decimal("3.00"),
            delivery_timeliness_score=Decimal("50.00"),
            compliance_status="compliant",
        )
        cls.pr_b = PurchaseRequisition.objects.create(
            organization=cls.org_b,
            title="OrgB PR",
            requester="Bob",
            required_date=date.today() + timedelta(days=30),
            priority="medium",
        )
        PurchaseOrder.objects.create(
            organization=cls.org_b,
            vendor=cls.vendor_b,
            requisition=cls.pr_b,
            issue_date=date.today() - timedelta(days=3),
        )
        cls.budget_b = Budget.objects.create(
            organization=cls.org_b,
            name="OrgB Budget",
            status="active",
            start_date=date.today() - timedelta(days=180),
            end_date=date.today() + timedelta(days=180),
            total_amount=Decimal("50000"),
        )

    # ── Computation-level isolation ──

    def test_portfolio_kpis_isolated(self):
        qs_a = Property.objects.filter(is_active=True, organization=self.org)
        qs_b = Property.objects.filter(is_active=True, organization=self.org_b)
        kpis_a = compute_portfolio_kpis(qs_a)
        kpis_b = compute_portfolio_kpis(qs_b)
        # Org A has 2 props, Org B has 2 props (seeded 1 in base + 1 here)
        self.assertEqual(kpis_a["property_count"], 2)
        self.assertEqual(kpis_b["property_count"], 2)  # Other Prop + Org B Tower
        # Values must differ
        self.assertNotEqual(kpis_a["total_value"], kpis_b["total_value"])

    def test_procurement_cycle_isolated(self):
        today = date.today()
        start = today - timedelta(days=30)
        result_a = compute_procurement_cycle_time(start, today, self.org.id)
        result_b = compute_procurement_cycle_time(start, today, self.org_b.id)
        # Each org has its own POs — sample sizes should match each org's data
        self.assertGreaterEqual(result_a["sample_size"], 0)
        self.assertGreaterEqual(result_b["sample_size"], 0)

    def test_vendor_reliability_isolated(self):
        result_a = compute_vendor_reliability(self.org.id)
        result_b = compute_vendor_reliability(self.org_b.id)
        # Org A has 2 vendors, Org B has 1
        self.assertEqual(result_a["vendor_count"], 2)
        self.assertEqual(result_b["vendor_count"], 1)

    def test_cost_variance_isolated(self):
        result_a = compute_cost_variance(self.org.id)
        result_b = compute_cost_variance(self.org_b.id)
        self.assertGreaterEqual(result_a["project_count"], 1)
        self.assertGreaterEqual(result_b["project_count"], 1)

    def test_emergency_purchases_isolated(self):
        today = date.today()
        result_a = compute_emergency_purchases(
            today - timedelta(days=30), today + timedelta(days=1), self.org.id
        )
        result_b = compute_emergency_purchases(
            today - timedelta(days=30), today + timedelta(days=1), self.org_b.id
        )
        # Org A has 1 urgent + 1 normal; Org B has 1 normal
        self.assertEqual(result_a["emergency_count"], 1)
        self.assertEqual(result_b["emergency_count"], 0)

    # ── View-level isolation ──

    def test_portfolio_view_isolated(self):
        """Org B member must not see Org A property data."""
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Org B has 2 properties, not Org A's 2
        self.assertEqual(resp.data["kpis"]["property_count"], 2)
        total = Decimal(resp.data["kpis"]["total_value"])
        # Org A total is 7M; Org B total is 4M — must not match Org A
        self.assertNotEqual(total, Decimal("7000000"))

    def test_board_kpis_view_isolated(self):
        """Org B member must not see Org A KPI data."""
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/board-kpis/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        kpis = resp.data["kpis"]
        # Org B has 0 urgent PRs
        self.assertEqual(kpis["emergency_purchases_pct"]["emergency_count"], 0)
        # Org B has 1 vendor, not Org A's 2
        self.assertEqual(kpis["vendor_reliability_score"]["vendor_count"], 1)

    def test_all_drilldowns_isolated(self):
        """Every drilldown endpoint must be scoped to org_b for member_b."""
        self.client.force_authenticate(user=self.member_b)

        # Cost variance — should see Org B project, not Org A's
        resp = self.client.get("/api/analytics/drilldowns/cost-variance/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        project_names = [p["name"] for p in resp.data["per_project"]]
        self.assertNotIn("Project Alpha", project_names)
        self.assertIn("Project Beta", project_names)

        # Vendor reliability — should see 1 vendor, not Org A's
        resp = self.client.get("/api/analytics/drilldowns/vendor-reliability/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        vendor_names = [v["name"] for v in resp.data["top_vendors"]]
        self.assertNotIn("Good Vendor", vendor_names)
        self.assertNotIn("Poor Vendor", vendor_names)

        # Emergency purchases — should see 0 emergencies
        resp = self.client.get("/api/analytics/drilldowns/emergency-purchases/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["recent_emergencies"]), 0)

    def test_snapshot_isolation(self):
        """Snapshots from org_a must not be served to org_b member."""
        now = timezone.now()
        PortfolioSnapshot.objects.create(
            organization=self.org,
            snapshot_date=date.today(),
            total_value=Decimal("9999999"),
            computed_at=now,
        )
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/portfolio/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Must NOT get org_a's snapshot
        total = Decimal(resp.data["kpis"]["total_value"])
        self.assertNotEqual(total, Decimal("9999999.00"))

    def test_health_endpoint_isolated(self):
        """Health endpoint must reflect org_b's snapshot state, not org_a's."""
        now = timezone.now()
        PortfolioSnapshot.objects.create(
            organization=self.org,
            snapshot_date=date.today(),
            computed_at=now,
        )
        # Org B has no snapshot
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get("/api/analytics/health/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["portfolio"]["status"], "missing")

    def test_dashboard_isolation(self):
        """User must not access another user's dashboards via direct ID."""
        dash_a = CustomDashboard.objects.create(
            user=self.member,
            name="Member A Dash",
            layout=[],
        )
        self.client.force_authenticate(user=self.member_b)
        resp = self.client.get(f"/api/analytics/dashboards/{dash_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        resp = self.client.patch(
            f"/api/analytics/dashboards/{dash_a.id}/",
            {"name": "Hijacked"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        resp = self.client.delete(f"/api/analytics/dashboards/{dash_a.id}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ── User organization invariant ──
    # Every created user profile must have a non-null organization.

    def test_new_user_profile_gets_organization(self):
        user = User.objects.create_user(
            username="orgbound@test.com",
            email="orgbound@test.com",
            password="Pass123!",
        )
        user.refresh_from_db()
        self.assertIsNotNone(user.profile.organization_id)

    def test_new_superuser_profile_gets_developeros_org(self):
        superuser = User.objects.create_superuser(
            username="rootbound@test.com",
            email="rootbound@test.com",
            password="Pass123!",
        )
        superuser.refresh_from_db()
        self.assertIsNotNone(superuser.profile.organization_id)
        self.assertEqual(superuser.profile.organization.name, "developerOS")

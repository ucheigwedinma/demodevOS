from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import Campaign, ContactAccount, ContactDealLink, Lead, LeadActivity, LeadSource
from apps.crm.tasks import (
    check_pipeline_drop_for_org,
    send_weekly_crm_analytics_report_for_org,
    sync_crm_procurement_demand_insights_for_org,
    sync_crm_project_demand_insights_for_org,
)
from apps.procurement.models import ProcurementDemandInsight
from apps.projects.models import ProjectPlanningInsight

User = get_user_model()


class CRMAnalyticsReportingTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="CRM Analytics Test Org")
        self.admin = User.objects.create_superuser(
            username="crm-analytics-admin@example.com",
            email="crm-analytics-admin@example.com",
            password="Pass123!",
        )
        self._configure_profile(self.admin, role="admin", job_title="Sales Director")
        self.client.force_authenticate(self.admin)

        self.sales_user = User.objects.create_user(
            username="crm-analytics-sales@example.com",
            email="crm-analytics-sales@example.com",
            password="Pass123!",
        )
        self._configure_profile(self.sales_user, role="member", job_title="Sales Executive")

        self.source_web = LeadSource.objects.create(
            organization=self.org,
            name="Website",
            code="WEB",
        )
        self.source_referral = LeadSource.objects.create(
            organization=self.org,
            name="Referral",
            code="REF",
        )

        today = timezone.now().date()
        self.lead_active = Lead.objects.create(
            organization=self.org,
            first_name="Ife",
            last_name="Ade",
            email="ife.ade@example.com",
            phone="+1-555-0101",
            status=Lead.Status.ACTIVE,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
            inquiry_date=today - timezone.timedelta(days=20),
            qualified_date=today - timezone.timedelta(days=18),
            assigned_to=self.sales_user,
            source=self.source_web,
            score=68,
        )
        self.lead_won = Lead.objects.create(
            organization=self.org,
            first_name="Nora",
            last_name="Cole",
            email="nora.cole@example.com",
            phone="+1-555-0102",
            status=Lead.Status.WON,
            pipeline_stage=Lead.PipelineStage.CLOSED,
            inquiry_date=today - timezone.timedelta(days=42),
            qualified_date=today - timezone.timedelta(days=39),
            site_visit_date=today - timezone.timedelta(days=31),
            offer_date=today - timezone.timedelta(days=24),
            reservation_date=today - timezone.timedelta(days=16),
            spa_issued_date=today - timezone.timedelta(days=10),
            closed_date=today - timezone.timedelta(days=4),
            assigned_to=self.sales_user,
            source=self.source_web,
            score=88,
        )
        self.lead_lost = Lead.objects.create(
            organization=self.org,
            first_name="Tolu",
            last_name="Grant",
            email="tolu.grant@example.com",
            phone="+1-555-0103",
            status=Lead.Status.LOST,
            pipeline_stage=Lead.PipelineStage.OFFER_MADE,
            inquiry_date=today - timezone.timedelta(days=27),
            qualified_date=today - timezone.timedelta(days=24),
            site_visit_date=today - timezone.timedelta(days=20),
            offer_date=today - timezone.timedelta(days=14),
            assigned_to=self.sales_user,
            source=self.source_referral,
            score=51,
        )

        contact_one = ContactAccount.objects.create(
            organization=self.org,
            first_name="Ife",
            last_name="Ade",
            email="ife.ade@example.com",
            phone="+1-555-0101",
        )
        contact_two = ContactAccount.objects.create(
            organization=self.org,
            first_name="Nora",
            last_name="Cole",
            email="nora.cole@example.com",
            phone="+1-555-0102",
        )

        self.deal_current = ContactDealLink.objects.create(
            contact=contact_one,
            lead=self.lead_active,
            deal_name="Ife - Block A",
            stage="Qualified",
            status=ContactDealLink.Status.ACTIVE,
            deal_value=Decimal("1800000.00"),
            close_probability=55,
        )
        self.deal_previous_one = ContactDealLink.objects.create(
            contact=contact_two,
            lead=self.lead_won,
            deal_name="Nora - Block C",
            stage="Closed Won",
            status=ContactDealLink.Status.ACTIVE,
            deal_value=Decimal("2600000.00"),
            close_probability=100,
        )
        self.deal_previous_two = ContactDealLink.objects.create(
            contact=contact_two,
            lead=self.lead_won,
            deal_name="Nora - Tower 2",
            stage="Qualified",
            status=ContactDealLink.Status.ACTIVE,
            deal_value=Decimal("2200000.00"),
            close_probability=40,
        )

        LeadActivity.objects.create(
            lead=self.lead_active,
            activity_type=LeadActivity.ActivityType.CALL,
            subject="Qualification call",
            is_completed=True,
            performed_by=self.sales_user,
        )
        Campaign.objects.create(
            organization=self.org,
            name="Q2 Website Retargeting",
            campaign_type=Campaign.CampaignType.EMAIL_BLAST,
            status=Campaign.Status.RUNNING,
            channel="email",
            total_recipients=120,
            sent_count=120,
            delivered_count=112,
            opened_count=76,
            clicked_count=31,
            spend_amount=Decimal("2500000.00"),
            revenue_attributed=Decimal("8750000.00"),
            auto_created_leads_count=14,
            target_lead_types=[Lead.LeadType.BUYER, Lead.LeadType.INVESTOR],
        )

    def _configure_profile(self, user, *, role: str, job_title: str):
        profile = user.profile
        profile.organization = self.org
        profile.role = role
        profile.job_title = job_title
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(
            update_fields=[
                "organization",
                "role",
                "job_title",
                "user_status",
                "mfa_enabled",
            ]
        )

    def test_overview_endpoint_returns_requested_metric_sections(self):
        res = self.client.get("/api/crm/analytics-reporting/overview/", {"window_days": "120"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("conversion_rates", res.data)
        self.assertIn("sales_velocity", res.data)
        self.assertIn("revenue_forecast", res.data)
        self.assertIn("lead_source_performance", res.data)
        self.assertIn("agent_performance", res.data)
        self.assertIn("pipeline_drop_monitor", res.data)
        self.assertIn("campaign_performance", res.data)
        self.assertIn("summary", res.data)
        self.assertGreaterEqual(res.data["summary"]["total_leads"], 1)
        self.assertGreaterEqual(res.data["campaign_performance"]["total_campaigns"], 1)

    @patch("apps.crm.tasks.dispatch_workflow_notification")
    def test_weekly_report_automation_dispatches_to_management(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 2,
            "emails_sent": 1,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }
        result = send_weekly_crm_analytics_report_for_org(
            organization_id=self.org.id,
            now=timezone.now(),
            window_days=90,
        )
        self.assertFalse(result["skipped"])
        self.assertGreaterEqual(result["recipients"], 1)
        self.assertEqual(result["notifications_sent"], 2)
        self.assertEqual(result["emails_sent"], 1)
        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(mock_dispatch.call_args.kwargs["event_key"], "crm_weekly_analytics_report")

    @patch("apps.crm.tasks.dispatch_workflow_notification")
    def test_pipeline_drop_alert_triggers_when_drop_is_detected(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 1,
            "emails_sent": 1,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }

        now = timezone.now()
        ContactDealLink.objects.filter(id=self.deal_current.id).update(
            linked_at=now - timezone.timedelta(days=2)
        )
        ContactDealLink.objects.filter(id=self.deal_previous_one.id).update(
            linked_at=now - timezone.timedelta(days=10)
        )
        ContactDealLink.objects.filter(id=self.deal_previous_two.id).update(
            linked_at=now - timezone.timedelta(days=11)
        )

        # Remove current-period addition to force a strong period-over-period drop.
        ContactDealLink.objects.filter(id=self.deal_current.id).delete()

        result = check_pipeline_drop_for_org(
            organization_id=self.org.id,
            now=now,
            lookback_days=7,
            force=True,
        )
        self.assertTrue(result["alert_triggered"], result)
        self.assertFalse(result["suppressed"], result)
        self.assertGreaterEqual(result["pipeline_drop"]["drop_percent"], 20.0)
        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(mock_dispatch.call_args.kwargs["event_key"], "crm_pipeline_drop_alert")

    @patch("apps.crm.tasks.dispatch_workflow_notification")
    def test_project_demand_sync_creates_projects_planning_insights(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 2,
            "emails_sent": 1,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }

        for index in range(6):
            Lead.objects.create(
                organization=self.org,
                first_name=f"Lekki{index}",
                last_name="Buyer",
                email=f"lekki-{index}@example.com",
                phone=f"+1-555-02{index:02d}",
                status=Lead.Status.ACTIVE,
                pipeline_stage=Lead.PipelineStage.QUALIFIED,
                preferred_locations=["Lekki"],
                assigned_to=self.sales_user,
                source=self.source_web,
                score=60,
            )

        result = sync_crm_project_demand_insights_for_org(
            organization_id=self.org.id,
            now=timezone.now(),
            window_days=90,
            threshold_percent=20.0,
            min_leads=3,
            top_areas=10,
            force=True,
        )

        self.assertFalse(result["skipped"], result)
        self.assertGreaterEqual(result["insights_upserted"], 1)
        self.assertGreaterEqual(result["high_demand_triggered"], 1)
        self.assertIn("Lekki", result["high_demand_areas"])

        demand_insight = ProjectPlanningInsight.objects.filter(
            organization=self.org,
            insight_type=ProjectPlanningInsight.InsightType.DEMAND_ANALYTICS,
            area_name="Lekki",
            is_active=True,
        ).first()
        self.assertIsNotNone(demand_insight)
        self.assertGreaterEqual(demand_insight.lead_count, 6)

        high_demand_insight = ProjectPlanningInsight.objects.filter(
            organization=self.org,
            insight_type=ProjectPlanningInsight.InsightType.NEW_DEVELOPMENT,
            area_name="Lekki",
            is_active=True,
        ).first()
        self.assertIsNotNone(high_demand_insight)

        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(
            mock_dispatch.call_args.kwargs["event_key"],
            "crm_projects_high_demand_insight",
        )

    def test_overview_includes_projects_integration_summary(self):
        for index in range(4):
            Lead.objects.create(
                organization=self.org,
                first_name=f"Abuja{index}",
                last_name="Buyer",
                email=f"abuja-{index}@example.com",
                phone=f"+1-555-03{index:02d}",
                status=Lead.Status.ACTIVE,
                pipeline_stage=Lead.PipelineStage.QUALIFIED,
                preferred_locations=["Abuja"],
                assigned_to=self.sales_user,
                source=self.source_referral,
                score=58,
            )

        with patch("apps.crm.tasks.dispatch_workflow_notification") as mock_dispatch:
            mock_dispatch.return_value = {
                "notifications_sent": 0,
                "emails_sent": 0,
                "templates_used": 0,
                "unsupported_channel_templates": 0,
            }
            sync_crm_project_demand_insights_for_org(
                organization_id=self.org.id,
                now=timezone.now(),
                window_days=90,
                threshold_percent=15.0,
                min_leads=2,
                top_areas=8,
                force=True,
            )

        cache.clear()
        res = self.client.get("/api/crm/analytics-reporting/overview/", {"window_days": "90"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("projects_integration", res.data)
        projects_integration = res.data["projects_integration"]
        self.assertIn("top_demand_areas", projects_integration)
        self.assertIn("high_demand_areas", projects_integration)
        self.assertGreaterEqual(projects_integration["demand_insight_count"], 1)

    @patch("apps.crm.tasks.dispatch_workflow_notification")
    def test_manual_project_demand_sync_endpoint(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 1,
            "emails_sent": 0,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }
        for index in range(3):
            Lead.objects.create(
                organization=self.org,
                first_name=f"Ikoyi{index}",
                last_name="Buyer",
                email=f"ikoyi-{index}@example.com",
                phone=f"+1-555-04{index:02d}",
                status=Lead.Status.ACTIVE,
                pipeline_stage=Lead.PipelineStage.QUALIFIED,
                preferred_locations=["Ikoyi"],
                assigned_to=self.sales_user,
                source=self.source_web,
            )

        res = self.client.post(
            "/api/crm/analytics-reporting/sync-project-demand-insights/",
            {
                "window_days": 90,
                "threshold_percent": 10.0,
                "min_leads": 2,
                "top_areas": 8,
                "force": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("insights_upserted", res.data)
        self.assertIn("high_demand_triggered", res.data)

    @patch("apps.crm.tasks.dispatch_workflow_notification")
    def test_procurement_demand_sync_creates_package_insights(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 2,
            "emails_sent": 1,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }

        for index in range(6):
            Lead.objects.create(
                organization=self.org,
                first_name=f"LekkiInvestor{index}",
                last_name="Buyer",
                email=f"lekki-investor-{index}@example.com",
                phone=f"+1-555-05{index:02d}",
                status=Lead.Status.ACTIVE,
                pipeline_stage=Lead.PipelineStage.QUALIFIED,
                lead_type=Lead.LeadType.INVESTOR,
                preferred_locations=["Lekki"],
                assigned_to=self.sales_user,
                source=self.source_web,
                score=72,
            )

        result = sync_crm_procurement_demand_insights_for_org(
            organization_id=self.org.id,
            now=timezone.now(),
            window_days=90,
            threshold_percent=20.0,
            min_leads=3,
            min_bulk_leads=2,
            top_areas=10,
            force=True,
        )

        self.assertFalse(result["skipped"], result)
        self.assertGreaterEqual(result["insights_upserted"], 3)
        self.assertGreaterEqual(result["package_triggers"], 1)
        self.assertIn("Lekki", result["triggered_areas"])

        bulk_insight = ProcurementDemandInsight.objects.filter(
            organization=self.org,
            insight_type=ProcurementDemandInsight.InsightType.BULK_BUYER_DEMAND,
            area_name="Lekki",
            is_active=True,
        ).first()
        self.assertIsNotNone(bulk_insight)
        self.assertGreaterEqual(bulk_insight.bulk_buyer_lead_count, 6)

        furnishing_insight = ProcurementDemandInsight.objects.filter(
            organization=self.org,
            insight_type=ProcurementDemandInsight.InsightType.FURNISHING_PACKAGE,
            area_name="Lekki",
            is_active=True,
        ).first()
        self.assertIsNotNone(furnishing_insight)

        add_on_insight = ProcurementDemandInsight.objects.filter(
            organization=self.org,
            insight_type=ProcurementDemandInsight.InsightType.ADD_ON_PACKAGE,
            area_name="Lekki",
            is_active=True,
        ).first()
        self.assertIsNotNone(add_on_insight)

        self.assertEqual(mock_dispatch.call_count, 1)
        self.assertEqual(
            mock_dispatch.call_args.kwargs["event_key"],
            "crm_procurement_bulk_buyer_demand",
        )

    def test_overview_includes_procurement_integration_summary(self):
        for index in range(4):
            Lead.objects.create(
                organization=self.org,
                first_name=f"AbujaInvestor{index}",
                last_name="Buyer",
                email=f"abuja-investor-{index}@example.com",
                phone=f"+1-555-06{index:02d}",
                status=Lead.Status.ACTIVE,
                pipeline_stage=Lead.PipelineStage.QUALIFIED,
                lead_type=Lead.LeadType.INVESTOR,
                preferred_locations=["Abuja"],
                assigned_to=self.sales_user,
                source=self.source_referral,
                score=70,
            )

        with patch("apps.crm.tasks.dispatch_workflow_notification") as mock_dispatch:
            mock_dispatch.return_value = {
                "notifications_sent": 0,
                "emails_sent": 0,
                "templates_used": 0,
                "unsupported_channel_templates": 0,
            }
            sync_crm_procurement_demand_insights_for_org(
                organization_id=self.org.id,
                now=timezone.now(),
                window_days=90,
                threshold_percent=20.0,
                min_leads=2,
                min_bulk_leads=2,
                top_areas=8,
                force=True,
            )

        cache.clear()
        res = self.client.get("/api/crm/analytics-reporting/overview/", {"window_days": "90"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("procurement_integration", res.data)
        procurement_integration = res.data["procurement_integration"]
        self.assertIn("package_recommendations", procurement_integration)
        self.assertGreaterEqual(procurement_integration["bulk_demand_insight_count"], 1)
        self.assertGreaterEqual(procurement_integration["furnishing_package_count"], 1)

    @patch("apps.crm.tasks.dispatch_workflow_notification")
    def test_manual_procurement_demand_sync_endpoint(self, mock_dispatch):
        mock_dispatch.return_value = {
            "notifications_sent": 1,
            "emails_sent": 0,
            "templates_used": 0,
            "unsupported_channel_templates": 0,
        }
        for index in range(3):
            Lead.objects.create(
                organization=self.org,
                first_name=f"IkoyiInvestor{index}",
                last_name="Buyer",
                email=f"ikoyi-investor-{index}@example.com",
                phone=f"+1-555-07{index:02d}",
                status=Lead.Status.ACTIVE,
                pipeline_stage=Lead.PipelineStage.QUALIFIED,
                lead_type=Lead.LeadType.INVESTOR,
                preferred_locations=["Ikoyi"],
                assigned_to=self.sales_user,
                source=self.source_web,
            )

        res = self.client.post(
            "/api/crm/analytics-reporting/sync-procurement-demand-insights/",
            {
                "window_days": 90,
                "threshold_percent": 20.0,
                "min_leads": 2,
                "min_bulk_leads": 2,
                "top_areas": 8,
                "force": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertIn("insights_upserted", res.data)
        self.assertIn("package_triggers", res.data)

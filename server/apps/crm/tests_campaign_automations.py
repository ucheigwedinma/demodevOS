from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import Campaign, CampaignRecipient, Lead, LeadSource

User = get_user_model()


class CampaignAutomationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Campaign Automation Org")
        self.admin = User.objects.create_superuser(
            username="campaign-admin@example.com",
            email="campaign-admin@example.com",
            password="Pass123!",
        )
        profile = self.admin.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(
            update_fields=[
                "organization",
                "role",
                "user_status",
                "mfa_enabled",
            ]
        )
        self.client.force_authenticate(self.admin)

        self.source = LeadSource.objects.create(
            organization=self.org,
            name="Digital Ads",
            code="DIGITAL",
        )

    def test_launch_auto_creates_leads_and_recipients(self):
        campaign = Campaign.objects.create(
            organization=self.org,
            name="Investor Demand Gen",
            campaign_type=Campaign.CampaignType.EMAIL_BLAST,
            status=Campaign.Status.DRAFT,
            channel="email",
            target_lead_sources=[self.source.id],
            target_lead_types=[Lead.LeadType.INVESTOR],
            auto_create_leads_on_launch=True,
            auto_create_leads_count=3,
            auto_create_lead_type=Lead.LeadType.INVESTOR,
        )

        res = self.client.post(f"/api/crm/campaigns/{campaign.id}/launch/", {})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        campaign.refresh_from_db()
        leads = Lead.objects.filter(organization=self.org, notes__icontains=campaign.name)
        recipients = CampaignRecipient.objects.filter(campaign=campaign)

        self.assertEqual(campaign.status, Campaign.Status.RUNNING)
        self.assertEqual(campaign.auto_created_leads_count, 3)
        self.assertEqual(campaign.total_recipients, 3)
        self.assertEqual(leads.count(), 3)
        self.assertEqual(recipients.count(), 3)
        self.assertEqual(leads.filter(lead_type=Lead.LeadType.INVESTOR).count(), 3)
        self.assertEqual(leads.filter(source=self.source).count(), 3)

    def test_launch_uses_segment_filters_to_pull_existing_leads(self):
        matching_lead = Lead.objects.create(
            organization=self.org,
            first_name="Ada",
            last_name="Investor",
            email="ada.investor@example.com",
            phone="+1-555-0300",
            lead_type=Lead.LeadType.INVESTOR,
            source=self.source,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
            status=Lead.Status.ACTIVE,
        )
        Lead.objects.create(
            organization=self.org,
            first_name="John",
            last_name="Buyer",
            email="john.buyer@example.com",
            phone="+1-555-0301",
            lead_type=Lead.LeadType.BUYER,
            source=self.source,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
            status=Lead.Status.ACTIVE,
        )

        campaign = Campaign.objects.create(
            organization=self.org,
            name="Investor Segment Launch",
            campaign_type=Campaign.CampaignType.EMAIL_BLAST,
            status=Campaign.Status.DRAFT,
            channel="email",
            target_pipeline_stages=[Lead.PipelineStage.QUALIFIED],
            target_lead_sources=[self.source.id],
            target_lead_types=[Lead.LeadType.INVESTOR],
            auto_create_leads_on_launch=False,
            auto_create_leads_count=0,
        )

        res = self.client.post(f"/api/crm/campaigns/{campaign.id}/launch/", {})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

        campaign.refresh_from_db()
        recipients = CampaignRecipient.objects.filter(campaign=campaign)
        self.assertEqual(campaign.total_recipients, 1)
        self.assertEqual(recipients.count(), 1)
        self.assertEqual(recipients.first().lead_id, matching_lead.id)

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.crm.models import ContactAccount, ContactDealLink, Lead

User = get_user_model()


class KYCStageGatingTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="CRM KYC Gate Test Org")
        self.user = User.objects.create_superuser(
            username="crm-kyc-gate-admin@example.com",
            email="crm-kyc-gate-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        self.client.force_authenticate(self.user)

        self.lead = Lead.objects.create(
            organization=self.org,
            first_name="Tobi",
            last_name="Aremu",
            email="tobi.aremu@example.com",
            phone="+1-555-1200",
            status=Lead.Status.ACTIVE,
            pipeline_stage=Lead.PipelineStage.QUALIFIED,
        )
        self.contact = ContactAccount.objects.create(
            organization=self.org,
            entity_type=ContactAccount.EntityType.INDIVIDUAL,
            first_name="Tobi",
            last_name="Aremu",
            email="tobi.aremu@example.com",
            phone="+1-555-1200",
            kyc_status=ContactAccount.KYCStatus.NOT_SUBMITTED,
        )
        ContactDealLink.objects.create(
            contact=self.contact,
            lead=self.lead,
            deal_name="Pearl Gardens Purchase",
            stage="Qualified",
            status=ContactDealLink.Status.ACTIVE,
        )

    def test_spa_stage_is_blocked_without_verified_kyc(self):
        blocked = self.client.post(
            f"/api/crm/leads/{self.lead.id}/change_stage/",
            {
                "stage": Lead.PipelineStage.SPA_ISSUED,
                "notes": "Attempting to issue SPA",
            },
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST, blocked.data)
        self.assertIn("KYC verification is required", str(blocked.data))

        self.contact.kyc_status = ContactAccount.KYCStatus.VERIFIED
        self.contact.save(update_fields=["kyc_status", "updated_at"])

        allowed = self.client.post(
            f"/api/crm/leads/{self.lead.id}/change_stage/",
            {
                "stage": Lead.PipelineStage.SPA_ISSUED,
                "notes": "KYC approved",
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK, allowed.data)

        self.lead.refresh_from_db()
        self.assertEqual(self.lead.pipeline_stage, Lead.PipelineStage.SPA_ISSUED)

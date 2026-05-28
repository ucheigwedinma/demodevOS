from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Organization
from apps.partners.models import (
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    OnboardingTemplateStage,
    PartnerType,
)

User = get_user_model()


class PartnerDocumentKycAutomationTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Partner KYC Gate Test Org")
        self.user = User.objects.create_superuser(
            username="partner-kyc-gate-admin@example.com",
            email="partner-kyc-gate-admin@example.com",
            password="Pass123!",
        )
        profile = self.user.profile
        profile.organization = self.org
        profile.role = "admin"
        profile.user_status = "active"
        profile.mfa_enabled = True
        profile.save(update_fields=["organization", "role", "user_status", "mfa_enabled"])
        self.client.force_authenticate(self.user)

        self.template = OnboardingTemplate.objects.create(
            organization=self.org,
            partner_type=PartnerType.CONTRACTOR,
            code="contractor_kyc_gate_test",
            name="Contractor KYC Gate Template",
            description="Test template for KYC-driven contract stage lock/unlock.",
            is_default=False,
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )
        self.stage_prequal = OnboardingTemplateStage.objects.create(
            template=self.template,
            sequence=1,
            code="prequalification",
            name="Prequalification",
            is_required=True,
            approval_required=False,
        )
        self.stage_contract = OnboardingTemplateStage.objects.create(
            template=self.template,
            sequence=2,
            code="contract_signed",
            name="Contract Signed",
            is_required=True,
            approval_required=True,
        )
        self.requirement = OnboardingTemplateDocumentRequirement.objects.create(
            template=self.template,
            sequence=1,
            code="contractor_kyc_pack",
            name="Contractor KYC Pack",
            is_required=True,
            applies_to_stage=self.stage_contract,
            accepted_sources=["email", "secure_upload_link"],
            allowed_extensions=["pdf"],
        )

        case_response = self.client.post(
            "/api/partners/cases/",
            {
                "partner_type": PartnerType.CONTRACTOR,
                "status": "in_progress",
                "template": self.template.id,
                "title": "Prime Build Ltd Onboarding",
                "contact_name": "Prime Build Ltd",
                "contact_email": "ops@primebuild.example.com",
            },
            format="json",
        )
        self.assertEqual(case_response.status_code, status.HTTP_201_CREATED, case_response.data)
        self.case_id = case_response.data["id"]

    def _fetch_case_detail(self):
        response = self.client.get(f"/api/partners/cases/{self.case_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    @staticmethod
    def _stage_status(case_payload: dict, stage_code: str) -> str:
        for stage in case_payload.get("stage_progress", []):
            if stage.get("stage_code") == stage_code:
                return stage.get("status")
        return ""

    def test_missing_kyc_blocks_contract_stage_and_verified_kyc_unlocks(self):
        create_doc = self.client.post(
            f"/api/partners/cases/{self.case_id}/intake-documents/",
            {
                "case": self.case_id,
                "requirement": self.requirement.id,
                "document_code": "contractor_kyc_pack",
                "document_name": "Contractor KYC Pack",
                "source_channel": "email",
                "status": "received",
                "external_reference_number": "KYC-REF-1001",
            },
            format="json",
        )
        self.assertEqual(create_doc.status_code, status.HTTP_201_CREATED, create_doc.data)
        intake_document_id = create_doc.data["id"]

        blocked_case = self._fetch_case_detail()
        self.assertEqual(
            self._stage_status(blocked_case, "contract_signed"),
            "blocked",
        )

        blocked_mark = self.client.post(
            f"/api/partners/cases/{self.case_id}/mark-stage/",
            {
                "stage_code": "contract_signed",
                "status": "completed",
                "notes": "Attempting to force complete",
            },
            format="json",
        )
        self.assertEqual(blocked_mark.status_code, status.HTTP_400_BAD_REQUEST, blocked_mark.data)
        self.assertIn("blocked until required intake documents are approved", str(blocked_mark.data))

        approve_doc = self.client.patch(
            f"/api/partners/intake-documents/{intake_document_id}/",
            {
                "status": "approved",
            },
            format="json",
        )
        self.assertEqual(approve_doc.status_code, status.HTTP_200_OK, approve_doc.data)

        unlocked_case = self._fetch_case_detail()
        self.assertEqual(
            self._stage_status(unlocked_case, "contract_signed"),
            "not_started",
        )

        allowed_mark = self.client.post(
            f"/api/partners/cases/{self.case_id}/mark-stage/",
            {
                "stage_code": "contract_signed",
                "status": "completed",
                "notes": "Required KYC approved",
            },
            format="json",
        )
        self.assertEqual(allowed_mark.status_code, status.HTTP_200_OK, allowed_mark.data)

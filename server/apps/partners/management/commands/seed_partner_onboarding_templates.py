from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Organization
from apps.partners.models import (
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    OnboardingTemplateStage,
    PartnerType,
)

TEMPLATE_DEFINITIONS = [
    {
        "partner_type": PartnerType.CLIENT,
        "code": "buyer_onboarding_v1",
        "name": "Buyer Onboarding",
        "description": "Lead-to-client onboarding flow for buyer portal activation.",
        "stages": [
            (1, "lead_capture", "Lead Capture (CRM)", False),
            (2, "qualification", "Qualification", False),
            (3, "unit_allocation", "Unit Allocation", False),
            (4, "reservation_fee", "Reservation Fee", True),
            (5, "spa_execution", "SPA Execution", True),
            (6, "erp_client_creation", "ERP Client Creation", True),
            (7, "portal_access_granted", "Portal Access Granted", True),
        ],
        "required_documents": [
            (1, "buyer_identity_kyc", "Buyer Identity / KYC", "qualification", ["physical_scan", "email", "secure_upload_link"]),
            (2, "reservation_receipt", "Reservation Fee Receipt", "reservation_fee", ["email", "secure_upload_link", "internal_generated"]),
            (3, "spa_signed_copy", "Signed SPA Copy", "spa_execution", ["physical_scan", "email", "secure_upload_link"]),
        ],
    },
    {
        "partner_type": PartnerType.CONTRACTOR,
        "code": "contractor_onboarding_v1",
        "name": "Contractor Onboarding",
        "description": "Prequalification-to-vendor onboarding flow for contractor portal activation.",
        "stages": [
            (1, "prequalification", "Prequalification (CRM)", False),
            (2, "tender_participation", "Tender Participation", False),
            (3, "technical_evaluation", "Technical Evaluation", True),
            (4, "award_decision", "Award Decision", True),
            (5, "contract_signed", "Contract Signed", True),
            (6, "erp_vendor_creation", "ERP Vendor Creation", True),
            (7, "portal_access_granted", "Portal Access Granted", True),
        ],
        "required_documents": [
            (1, "company_registration", "Company Registration Certificate", "prequalification", ["physical_scan", "email", "tender_portal", "secure_upload_link"]),
            (2, "tax_clearance", "Tax Clearance Certificate", "technical_evaluation", ["physical_scan", "email", "tender_portal"]),
            (3, "insurance_certificate", "Insurance Certificate", "contract_signed", ["physical_scan", "email", "secure_upload_link"]),
            (4, "performance_bond", "Performance Bond", "contract_signed", ["physical_scan", "email", "secure_upload_link"]),
            (5, "signed_contract", "Signed Contract", "contract_signed", ["physical_scan", "email", "internal_generated"]),
        ],
    },
    {
        "partner_type": PartnerType.INVESTOR,
        "code": "investor_onboarding_v1",
        "name": "Investor Onboarding",
        "description": "Prospect-to-investor onboarding flow for investor portal activation.",
        "stages": [
            (1, "investor_prospect", "Investor Prospect (CRM)", False),
            (2, "nda", "NDA", True),
            (3, "data_room", "Data Room", False),
            (4, "term_sheet", "Term Sheet", True),
            (5, "subscription_agreement", "Subscription Agreement", True),
            (6, "capital_call", "Capital Call", True),
            (7, "erp_investor_profile", "ERP Investor Profile", True),
            (8, "portal_access_granted", "Portal Access Granted", True),
        ],
        "required_documents": [
            (1, "executed_nda", "Executed NDA", "nda", ["physical_scan", "email", "secure_upload_link"]),
            (2, "investor_kyc_pack", "Investor KYC Pack", "term_sheet", ["physical_scan", "email", "secure_upload_link", "data_room"]),
            (3, "subscription_agreement_signed", "Signed Subscription Agreement", "subscription_agreement", ["physical_scan", "email", "secure_upload_link"]),
            (4, "capital_call_evidence", "Capital Call Evidence", "capital_call", ["email", "secure_upload_link", "internal_generated"]),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed partner onboarding templates for buyer, contractor, and investor flows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            default=None,
            help="Optional organization ID for org-scoped templates. If omitted, templates are global.",
        )
        parser.add_argument(
            "--set-default",
            action="store_true",
            help="Mark seeded templates as defaults.",
        )

    def handle(self, *args, **options):
        organization = None
        org_id = options.get("organization_id")
        if org_id is not None:
            try:
                organization = Organization.objects.get(pk=org_id)
            except Organization.DoesNotExist as exc:
                raise CommandError(f"Organization with id={org_id} not found.") from exc

        user = get_user_model().objects.filter(is_superuser=True).order_by("id").first()
        set_default = options.get("set_default", False)

        for template_def in TEMPLATE_DEFINITIONS:
            template, created = OnboardingTemplate.objects.update_or_create(
                organization=organization,
                partner_type=template_def["partner_type"],
                code=template_def["code"],
                version=1,
                defaults={
                    "name": template_def["name"],
                    "description": template_def["description"],
                    "is_active": True,
                    "is_default": set_default,
                    "created_by": user,
                    "updated_by": user,
                },
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} template: {template.name}")

            existing_stage_codes = set(
                OnboardingTemplateStage.objects.filter(template=template).values_list("code", flat=True)
            )
            target_stage_codes = set()

            for sequence, code, name, approval_required in template_def["stages"]:
                target_stage_codes.add(code)
                OnboardingTemplateStage.objects.update_or_create(
                    template=template,
                    code=code,
                    defaults={
                        "sequence": sequence,
                        "name": name,
                        "is_required": True,
                        "approval_required": approval_required,
                        "approval_role_label": "Governance" if approval_required else "",
                        "sla_hours": 48 if approval_required else None,
                        "auto_complete": False,
                    },
                )

            obsolete_codes = existing_stage_codes - target_stage_codes
            if obsolete_codes:
                OnboardingTemplateStage.objects.filter(template=template, code__in=obsolete_codes).delete()
                self.stdout.write(f"Removed obsolete stages: {', '.join(sorted(obsolete_codes))}")

            stage_map = {
                row.code: row
                for row in OnboardingTemplateStage.objects.filter(template=template)
            }
            existing_requirement_codes = set(
                OnboardingTemplateDocumentRequirement.objects.filter(template=template).values_list("code", flat=True)
            )
            target_requirement_codes = set()

            for sequence, code, name, stage_code, accepted_sources in template_def.get("required_documents", []):
                target_requirement_codes.add(code)
                OnboardingTemplateDocumentRequirement.objects.update_or_create(
                    template=template,
                    code=code,
                    defaults={
                        "sequence": sequence,
                        "name": name,
                        "description": "",
                        "is_required": True,
                        "applies_to_stage": stage_map.get(stage_code),
                        "accepted_sources": accepted_sources,
                        "allowed_extensions": ["pdf", "jpg", "jpeg", "png"],
                    },
                )

            obsolete_requirement_codes = existing_requirement_codes - target_requirement_codes
            if obsolete_requirement_codes:
                OnboardingTemplateDocumentRequirement.objects.filter(
                    template=template,
                    code__in=obsolete_requirement_codes,
                ).delete()
                self.stdout.write(
                    f"Removed obsolete document requirements: {', '.join(sorted(obsolete_requirement_codes))}"
                )

        scope = f"organization {organization.id}" if organization else "global"
        self.stdout.write(self.style.SUCCESS(f"Partner onboarding templates seeded for {scope}."))

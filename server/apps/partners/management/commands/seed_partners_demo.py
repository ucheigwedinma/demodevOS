"""
Seed realistic demo data for the Partners module.

Creates onboarding cases with stage progress, intake documents,
approvals, entitlements, and audit log entries.

Requires: seed_partner_onboarding_templates to have run first.

Usage:
    python manage.py seed_partners_demo
    python manage.py seed_partners_demo --flush
    python manage.py seed_partners_demo --organization-id 1
"""

from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Organization
from apps.partners.models import (
    OnboardingTemplate,
    PartnerEntitlement,
    PartnerOnboardingApproval,
    PartnerOnboardingAuditLog,
    PartnerOnboardingCase,
    PartnerOnboardingIntakeDocument,
    PartnerOnboardingStageProgress,
)

DEMO_MARKER = "[demo-seed]"

User = get_user_model()

# ---------------------------------------------------------------------------
# Hardcoded realistic data
# ---------------------------------------------------------------------------

CASE_DATA = [
    {
        "partner_type": "client",
        "title": "Apex Property Group — Lekki Phase 3 Buyer",
        "contact_name": "Chief Adewale Ogundimu",
        "contact_email": "adewale@apexgroup.com.ng",
        "contact_phone": "+234 803 123 4567",
        "status": "active",
    },
    {
        "partner_type": "client",
        "title": "Westbridge Holdings — Eko Atlantic Buyer",
        "contact_name": "Mrs. Olufunke Adeyemi",
        "contact_email": "funke@westbridge.ng",
        "contact_phone": "+234 812 345 6789",
        "status": "approved",
    },
    {
        "partner_type": "contractor",
        "title": "Julius Berger Nigeria — Main Contractor",
        "contact_name": "Dipl.-Ing. Klaus Weber",
        "contact_email": "k.weber@juliusberger.com.ng",
        "contact_phone": "+234 809 111 2233",
        "status": "active",
    },
    {
        "partner_type": "contractor",
        "title": "BuildMate Construction — Subcontractor",
        "contact_name": "Chukwuemeka Obi",
        "contact_email": "c.obi@buildmateng.com",
        "contact_phone": "+234 812 456 7890",
        "status": "in_progress",
    },
    {
        "partner_type": "investor",
        "title": "Northcourt Capital — Series A Investor",
        "contact_name": "Tunde Lawal",
        "contact_email": "tunde@northcourtcapital.com",
        "contact_phone": "+234 802 234 5678",
        "status": "active",
    },
    {
        "partner_type": "investor",
        "title": "LagosAngel Fund — Co-Investment Vehicle",
        "contact_name": "Dr. Ngozi Iweala-Smith",
        "contact_email": "ngozi@lagosangel.vc",
        "contact_phone": "+234 810 567 8901",
        "status": "under_review",
    },
    {
        "partner_type": "client",
        "title": "Cedarline Developments — Ikoyi Buyer",
        "contact_name": "Mr. Emeka Nwosu",
        "contact_email": "emeka@cedarline.ng",
        "contact_phone": "+234 803 678 9012",
        "status": "in_progress",
    },
    {
        "partner_type": "contractor",
        "title": "Arbico Construction — Finishing Works",
        "contact_name": "Tunde Bakare",
        "contact_email": "t.bakare@arbicoplc.com",
        "contact_phone": "+234 802 111 2233",
        "status": "approved",
    },
]

DOCUMENT_SOURCES = [
    "physical_scan",
    "email",
    "secure_upload_link",
    "tender_portal",
]

DOCUMENT_NAMES = {
    "client": [
        ("kyc_identity", "Government-Issued ID (National/Passport)"),
        ("proof_of_address", "Utility Bill / Proof of Address"),
        ("company_registration", "CAC Certificate of Incorporation"),
    ],
    "contractor": [
        ("company_registration", "CAC Certificate of Incorporation"),
        ("tax_clearance", "Tax Clearance Certificate"),
        ("insurance_certificate", "Professional Indemnity Insurance"),
        ("safety_certification", "HSE Certification"),
        ("past_projects", "Portfolio of Past Projects"),
    ],
    "investor": [
        ("kyc_identity", "Government-Issued ID (Director)"),
        ("company_registration", "Certificate of Incorporation"),
        ("source_of_funds", "Source of Funds Declaration"),
        ("investment_mandate", "Investment Mandate / Board Resolution"),
    ],
}

APPROVAL_COMMENTS = [
    "All documents verified and in order. Approved for onboarding.",
    "KYC check completed — no adverse findings. Proceeding.",
    "Financial due diligence cleared. Risk rating: Low.",
    "Technical evaluation satisfactory. Vendor meets minimum requirements.",
    "Board approval received. Partner can proceed to portal activation.",
    "Compliance check passed. Anti-money laundering screening clear.",
]


class Command(BaseCommand):
    help = "Seed realistic demo data for the Partners module (onboarding cases, documents, approvals)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            action="append",
            default=None,
            dest="org_ids",
            help="Seed only for specific organization(s). Omit to seed for all.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previous demo-seeded data before re-seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        org_ids = options.get("org_ids")
        flush = options.get("flush", False)

        if org_ids:
            orgs = Organization.objects.filter(id__in=org_ids)
        else:
            orgs = Organization.objects.all()

        if not orgs.exists():
            self.stderr.write(self.style.ERROR("No organizations found."))
            return

        for org in orgs:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Organization: {org.name} (id={org.id})")
            self.stdout.write(f"{'='*60}")

            random.seed(org.id + 9000)

            if flush:
                self._flush(org)

            templates = self._get_templates(org)
            if not templates:
                self.stdout.write(self.style.WARNING(
                    "  No onboarding templates found. Run seed_partner_onboarding_templates first."
                ))
                continue

            cases = self._seed_cases(org, templates)
            self._seed_stage_progress(org, cases)
            self._seed_intake_documents(org, cases)
            self._seed_approvals(org, cases)
            self._seed_entitlements(org, cases)
            self._seed_audit_logs(org, cases)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done! Partners module populated for {org.name}: "
                    f"{len(cases)} onboarding cases."
                )
            )

    def _flush(self, org):
        self.stdout.write("Flushing previous Partners demo data ...")
        PartnerOnboardingAuditLog.objects.filter(
            case__organization=org, message__icontains=DEMO_MARKER
        ).delete()
        PartnerEntitlement.objects.filter(
            organization=org, case__notes__icontains=DEMO_MARKER
        ).delete()
        PartnerOnboardingApproval.objects.filter(
            case__organization=org, comments__icontains=DEMO_MARKER
        ).delete()
        PartnerOnboardingIntakeDocument.objects.filter(
            case__organization=org, review_notes__icontains=DEMO_MARKER
        ).delete()
        PartnerOnboardingStageProgress.objects.filter(
            case__organization=org, notes__icontains=DEMO_MARKER
        ).delete()
        PartnerOnboardingCase.objects.filter(
            organization=org, notes__icontains=DEMO_MARKER
        ).delete()
        self.stdout.write("  Flushed.")

    def _get_templates(self, org):
        """Get templates — org-specific or global."""
        templates = {}
        for pt in ("client", "contractor", "investor"):
            tmpl = (
                OnboardingTemplate.objects.filter(
                    partner_type=pt, is_active=True
                )
                .filter(
                    models_Q_org_or_global(org)
                )
                .first()
            )
            if not tmpl:
                tmpl = OnboardingTemplate.objects.filter(
                    partner_type=pt, is_active=True
                ).first()
            if tmpl:
                templates[pt] = tmpl
        return templates

    # ----- Cases -----

    def _seed_cases(self, org, templates):
        now = timezone.now()
        cases = []

        for data in CASE_DATA:
            partner_type = data["partner_type"]
            template = templates.get(partner_type)
            if not template:
                continue

            is_active = data["status"] in ("active", "approved")

            case, created = PartnerOnboardingCase.objects.get_or_create(
                organization=org,
                title=data["title"],
                defaults={
                    "partner_type": partner_type,
                    "status": data["status"],
                    "template": template,
                    "contact_name": data["contact_name"],
                    "contact_email": data["contact_email"],
                    "contact_phone": data["contact_phone"],
                    "portal_access_granted": is_active,
                    "portal_access_granted_at": now - timedelta(days=random.randint(1, 30)) if is_active else None,
                    "notes": f"{DEMO_MARKER} Demo partner onboarding case",
                },
            )
            cases.append(case)

        self.stdout.write(f"  {len(cases)} onboarding cases ready.")
        return cases

    # ----- Stage Progress -----

    def _seed_stage_progress(self, org, cases):
        now = timezone.now()
        count = 0

        for case in cases:
            if not case.template:
                continue
            stages = list(case.template.stages.all().order_by("sequence"))
            if not stages:
                continue

            # Determine how many stages are completed based on case status
            if case.status in ("active",):
                completed_count = len(stages)
            elif case.status in ("approved",):
                completed_count = len(stages) - 1
            elif case.status in ("under_review",):
                completed_count = max(1, len(stages) - 2)
            elif case.status in ("in_progress",):
                completed_count = max(1, len(stages) // 2)
            else:
                completed_count = 0

            for idx, stage in enumerate(stages):
                if idx < completed_count:
                    status = "completed"
                    started = now - timedelta(days=random.randint(completed_count - idx + 5, 60))
                    completed_at = started + timedelta(hours=random.randint(4, 72))
                elif idx == completed_count:
                    status = "in_progress"
                    started = now - timedelta(days=random.randint(1, 5))
                    completed_at = None
                    case.current_stage = stage
                    case.save(update_fields=["current_stage"])
                else:
                    status = "not_started"
                    started = None
                    completed_at = None

                PartnerOnboardingStageProgress.objects.get_or_create(
                    case=case,
                    template_stage=stage,
                    defaults={
                        "status": status,
                        "is_required": stage.is_required,
                        "started_at": started,
                        "completed_at": completed_at,
                        "notes": f"{DEMO_MARKER} Stage progress record",
                    },
                )
                count += 1

        self.stdout.write(f"  {count} stage progress records ready.")

    # ----- Intake Documents -----

    def _seed_intake_documents(self, org, cases):
        now = timezone.now()
        count = 0

        for case in cases:
            doc_names = DOCUMENT_NAMES.get(case.partner_type, [])
            for code, name in doc_names:
                # Determine status based on case progress
                if case.status in ("active", "approved"):
                    doc_status = "approved"
                elif case.status in ("under_review",):
                    doc_status = random.choice(["approved", "under_review"])
                elif case.status in ("in_progress",):
                    doc_status = random.choice(["received", "under_review", "approved"])
                else:
                    doc_status = "received"

                PartnerOnboardingIntakeDocument.objects.get_or_create(
                    case=case,
                    document_code=code,
                    defaults={
                        "document_name": name,
                        "source_channel": random.choice(DOCUMENT_SOURCES),
                        "received_at": now - timedelta(days=random.randint(5, 45)),
                        "status": doc_status,
                        "reviewed_at": now - timedelta(days=random.randint(1, 10)) if doc_status in ("approved", "under_review") else None,
                        "review_notes": f"{DEMO_MARKER} Document reviewed and verified" if doc_status == "approved" else f"{DEMO_MARKER}",
                    },
                )
                count += 1

        self.stdout.write(f"  {count} intake documents ready.")

    # ----- Approvals -----

    def _seed_approvals(self, org, cases):
        count = 0

        for case in cases:
            if case.status not in ("approved", "active"):
                continue

            # Find completed stage progress records
            completed_stages = PartnerOnboardingStageProgress.objects.filter(
                case=case,
                status="completed",
                template_stage__approval_required=True,
            )

            for sp in completed_stages:
                PartnerOnboardingApproval.objects.get_or_create(
                    case=case,
                    stage_progress=sp,
                    defaults={
                        "decision": "approved",
                        "approver_role_label": sp.template_stage.approval_role_label or "Operations Manager",
                        "comments": f"{DEMO_MARKER} {random.choice(APPROVAL_COMMENTS)}",
                    },
                )
                count += 1

            # Also create a case-level approval if none linked to stage
            if not completed_stages.exists():
                PartnerOnboardingApproval.objects.get_or_create(
                    case=case,
                    stage_progress=None,
                    defaults={
                        "decision": "approved",
                        "approver_role_label": "Head of Operations",
                        "comments": f"{DEMO_MARKER} {random.choice(APPROVAL_COMMENTS)}",
                    },
                )
                count += 1

        self.stdout.write(f"  {count} approvals ready.")

    # ----- Entitlements -----

    def _seed_entitlements(self, org, cases):
        count = 0
        portal_role_map = {
            "client": "client",
            "contractor": "contractor",
            "investor": "investor",
        }

        for case in cases:
            if case.status not in ("approved", "active"):
                continue

            role = portal_role_map.get(case.partner_type, "client")

            PartnerEntitlement.objects.get_or_create(
                case=case,
                organization=org,
                portal_role=role,
                defaults={
                    "budget_scope": "aggregated" if role == "investor" else ("boq_only" if role == "contractor" else "none"),
                    "can_view_other_investors": role == "investor",
                    "can_edit": role == "contractor",
                    "can_approve": False,
                    "can_comment": True,
                    "can_download_documents": True,
                    "is_active": True,
                },
            )
            count += 1

        self.stdout.write(f"  {count} entitlements ready.")

    # ----- Audit Logs -----

    def _seed_audit_logs(self, org, cases):
        count = 0

        for case in cases:
            # Case created event
            PartnerOnboardingAuditLog.objects.get_or_create(
                case=case,
                event_type="case_created",
                message=f"{DEMO_MARKER} Onboarding case created for {case.contact_name}",
                defaults={
                    "actor_role_label": "System",
                    "payload": {"partner_type": case.partner_type, "title": case.title},
                },
            )
            count += 1

            # Stages initialized
            PartnerOnboardingAuditLog.objects.get_or_create(
                case=case,
                event_type="stages_initialized",
                message=f"{DEMO_MARKER} Onboarding stages initialized from template",
                defaults={
                    "actor_role_label": "System",
                    "payload": {"template": case.template.name if case.template else "N/A"},
                },
            )
            count += 1

            if case.status in ("approved", "active"):
                PartnerOnboardingAuditLog.objects.get_or_create(
                    case=case,
                    event_type="case_status_changed",
                    message=f"{DEMO_MARKER} Case status changed to {case.status}",
                    defaults={
                        "actor_role_label": "Operations Manager",
                        "payload": {"from": "under_review", "to": case.status},
                    },
                )
                count += 1

            if case.portal_access_granted:
                PartnerOnboardingAuditLog.objects.get_or_create(
                    case=case,
                    event_type="portal_access_granted",
                    message=f"{DEMO_MARKER} Portal access granted to {case.contact_email}",
                    defaults={
                        "actor_role_label": "System Administrator",
                        "payload": {"email": case.contact_email},
                    },
                )
                count += 1

        self.stdout.write(f"  {count} audit log entries ready.")


def models_Q_org_or_global(org):
    """Return Q for templates belonging to org or global (org=None)."""
    from django.db.models import Q
    return Q(organization=org) | Q(organization__isnull=True)

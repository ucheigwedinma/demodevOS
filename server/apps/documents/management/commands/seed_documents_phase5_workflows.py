from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.documents.models import (
    DocumentType,
    DocumentWorkflowRule,
    DocumentWorkflowTemplate,
    DocumentWorkflowTemplateStep,
)


class Command(BaseCommand):
    help = "Seed Phase 5 document workflow templates and conditional routing rules."

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            type=int,
            help="Seed for a specific organization ID. Defaults to first organization.",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Rebuild phase 5 default templates/rules from scratch.",
        )

    def handle(self, *args, **options):
        org_id = options.get("org")
        reset = options.get("reset", False)

        if org_id:
            organization = Organization.objects.filter(pk=org_id).first()
            if organization is None:
                self.stderr.write(self.style.ERROR(f"Organization {org_id} not found."))
                return
        else:
            organization = Organization.objects.order_by("id").first()
            if organization is None:
                self.stderr.write(self.style.ERROR("No organizations found."))
                return

        if reset:
            DocumentWorkflowRule.objects.filter(organization=organization).delete()
            DocumentWorkflowTemplateStep.objects.filter(organization=organization).delete()
            DocumentWorkflowTemplate.objects.filter(organization=organization).delete()
            self.stdout.write(
                f"Deleted existing workflow templates, steps, and rules for org={organization.id}."
            )

        default_template, _ = DocumentWorkflowTemplate.objects.update_or_create(
            code="default-document-approval",
            defaults={
                "organization": organization,
                "name": "Default Document Approval",
                "description": "Fallback approval chain when no conditional rule matches.",
                "is_default": True,
                "is_active": True,
            },
        )
        if default_template.organization_id is None:
            default_template.organization = organization
            default_template.save(update_fields=["organization"])
        self._sync_steps(
            default_template,
            [
                (1, "Governance", "governance-officer"),
            ],
        )

        high_value_contract_template, _ = DocumentWorkflowTemplate.objects.update_or_create(
            code="high-value-contract-approval",
            defaults={
                "organization": organization,
                "name": "High-Value Contract Approval",
                "description": (
                    "Conditional chain for contract documents above 100k: "
                    "Legal -> Finance -> COO"
                ),
                "is_default": False,
                "is_active": True,
            },
        )
        if high_value_contract_template.organization_id is None:
            high_value_contract_template.organization = organization
            high_value_contract_template.save(update_fields=["organization"])
        self._sync_steps(
            high_value_contract_template,
            [
                (1, "Legal", "legal"),
                (2, "Finance", "finance-controller"),
                (3, "COO", "developer-executive"),
            ],
        )

        contract_document_type = (
            DocumentType.objects
            .filter(organization=organization)
            .filter(name__iexact="Contract")
            .order_by("id")
            .first()
        )

        if contract_document_type:
            DocumentWorkflowRule.objects.update_or_create(
                organization=organization,
                name="Contract > 100k",
                defaults={
                    "template": high_value_contract_template,
                    "document_type": contract_document_type,
                    "min_contract_value": Decimal("100000.00"),
                    "max_contract_value": None,
                    "allowed_confidentiality_levels": [
                        "public",
                        "internal",
                        "confidential",
                        "restricted",
                    ],
                    "allowed_project_risk_ratings": ["low", "medium", "high", "critical"],
                    "priority": 10,
                    "is_active": True,
                },
            )
            self.stdout.write("Seeded rule: Contract > 100k -> Legal -> Finance -> COO")
        else:
            self.stdout.write(
                self.style.WARNING(
                    "No DocumentType named 'Contract' found; skipped conditional contract rule."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Phase 5 workflow templates and rules seeded (org={organization.id})."
            )
        )

    def _sync_steps(self, template, rows):
        existing = {step.sequence: step for step in template.steps.all()}
        keep_sequences = set()

        for sequence, approver_label, approver_role_slug in rows:
            keep_sequences.add(sequence)
            step = existing.get(sequence)
            if step is None:
                DocumentWorkflowTemplateStep.objects.create(
                    organization=template.organization,
                    template=template,
                    sequence=sequence,
                    approver_label=approver_label,
                    approver_role_slug=approver_role_slug,
                    is_active=True,
                )
                continue

            updates = []
            if step.approver_label != approver_label:
                step.approver_label = approver_label
                updates.append("approver_label")
            if step.approver_role_slug != approver_role_slug:
                step.approver_role_slug = approver_role_slug
                updates.append("approver_role_slug")
            if not step.is_active:
                step.is_active = True
                updates.append("is_active")
            if step.organization_id is None:
                step.organization = template.organization
                updates.append("organization")
            if updates:
                step.save(update_fields=updates)

        template.steps.exclude(sequence__in=keep_sequences).delete()

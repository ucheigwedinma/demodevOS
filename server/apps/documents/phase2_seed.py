from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    DocumentOwnerRole,
    DocumentRetentionPolicy,
    DocumentType,
    DocumentWorkflowPhase,
)

PHASE2_DOCUMENT_TYPES = [
    {
        "code": "deed_of_assignment",
        "name": "Deed of Assignment",
        "category_code": "LND",
        "description": "Transfer instrument assigning legal interest in land.",
        "is_active": True,
    },
    {
        "code": "certificate_of_occupancy",
        "name": "Certificate of Occupancy",
        "category_code": "LND",
        "description": "Government-issued title certificate confirming occupancy rights.",
        "is_active": True,
    },
    {
        "code": "survey_plan",
        "name": "Survey Plan",
        "category_code": "LND",
        "description": "Licensed survey defining coordinates and legal parcel boundaries.",
        "is_active": True,
    },
    {
        "code": "development_permit",
        "name": "Development Permit",
        "category_code": "REG",
        "description": "Authority approval permitting commencement of development work.",
        "is_active": True,
    },
    {
        "code": "environmental_impact_approval",
        "name": "Environmental Impact Approval",
        "category_code": "REG",
        "description": "Regulatory clearance for environmental impact obligations.",
        "is_active": True,
    },
    {
        "code": "compliance_certificate",
        "name": "Compliance Certificate",
        "category_code": "REG",
        "description": "Evidence that statutory and code obligations were satisfied.",
        "is_active": True,
    },
    {
        "code": "ifc_drawing",
        "name": "Issue for Construction Drawing",
        "category_code": "DES",
        "description": "Approved drawing set released for construction execution.",
        "is_active": True,
    },
    {
        "code": "as_built_drawing",
        "name": "As-Built Drawing",
        "category_code": "DES",
        "description": "Final drawing set reflecting actual built conditions.",
        "is_active": True,
    },
    {
        "code": "design_revision",
        "name": "Design Revision",
        "category_code": "DES",
        "description": "Formal change to previously issued design deliverables.",
        "is_active": True,
    },
    {
        "code": "contract_agreement",
        "name": "Contract Agreement",
        "category_code": "CON",
        "description": "Executed contract defining scope, obligations, and commercials.",
        "is_active": True,
    },
    {
        "code": "variation_order",
        "name": "Variation Order",
        "category_code": "CON",
        "description": "Approved scope or value change against baseline contract.",
        "is_active": True,
    },
    {
        "code": "material_approval",
        "name": "Material Approval",
        "category_code": "CON",
        "description": "Approval record for submitted materials and specifications.",
        "is_active": True,
    },
    {
        "code": "offer_letter",
        "name": "Offer Letter",
        "category_code": "SAL",
        "description": "Commercial offer to prospective buyer or tenant.",
        "is_active": True,
    },
    {
        "code": "sales_agreement",
        "name": "Sales Agreement",
        "category_code": "SAL",
        "description": "Binding sale and purchase agreement with client.",
        "is_active": True,
    },
    {
        "code": "allocation_letter",
        "name": "Allocation Letter",
        "category_code": "SAL",
        "description": "Allocation letter assigning a specific unit to a buyer.",
        "is_active": True,
    },
    {
        "code": "handover_pack",
        "name": "Handover Pack",
        "category_code": "SAL",
        "description": "Final bundle issued at unit/property handover.",
        "is_active": True,
    },
    {
        "code": "payment_certificate",
        "name": "Payment Certificate",
        "category_code": "FIN",
        "description": "Certified valuation authorizing payment release.",
        "is_active": True,
    },
    {
        "code": "invoice",
        "name": "Invoice",
        "category_code": "FIN",
        "description": "Tax-compliant commercial invoice.",
        "is_active": True,
    },
    {
        "code": "tax_clearance",
        "name": "Tax Clearance",
        "category_code": "FIN",
        "description": "Official certificate confirming tax compliance standing.",
        "is_active": True,
    },
    {
        "code": "other",
        "name": "Other",
        "category_code": "GEN",
        "description": "Controlled document type for exceptional records.",
        "is_active": True,
    },
]

PHASE2_OWNER_ROLES = [
    {
        "code": "document_controller",
        "name": "Document Controller",
        "description": "Owns repository integrity, numbering, and publication controls.",
        "is_active": True,
    },
    {
        "code": "legal",
        "name": "Legal",
        "description": "Owns legal validity and contractual compliance of records.",
        "is_active": True,
    },
    {
        "code": "compliance",
        "name": "Compliance",
        "description": "Owns statutory, regulatory, and policy adherence.",
        "is_active": True,
    },
    {
        "code": "engineering",
        "name": "Engineering",
        "description": "Owns technical quality and design/construction deliverables.",
        "is_active": True,
    },
    {
        "code": "project_management",
        "name": "Project Management",
        "description": "Owns project lifecycle document completeness and gating.",
        "is_active": True,
    },
    {
        "code": "procurement",
        "name": "Procurement",
        "description": "Owns vendor and contract procurement documentation.",
        "is_active": True,
    },
    {
        "code": "sales_admin",
        "name": "Sales Administration",
        "description": "Owns client commercial records from offer to handover.",
        "is_active": True,
    },
    {
        "code": "finance_control",
        "name": "Finance Control",
        "description": "Owns finance and commercial audit documentation.",
        "is_active": True,
    },
]

PHASE2_WORKFLOW_PHASES = [
    {
        "code": "land_acquisition",
        "name": "Land Acquisition",
        "numbering_code": "PH1",
        "description": "Land identification, due diligence, and title transfer stage.",
        "sort_order": 1,
        "is_active": True,
    },
    {
        "code": "design_approvals",
        "name": "Design & Approvals",
        "numbering_code": "PH2",
        "description": "Concept/design development and statutory approvals stage.",
        "sort_order": 2,
        "is_active": True,
    },
    {
        "code": "construction",
        "name": "Construction",
        "numbering_code": "PH3",
        "description": "Construction execution, supervision, and commercial administration stage.",
        "sort_order": 3,
        "is_active": True,
    },
    {
        "code": "sales_leasing",
        "name": "Sales & Leasing",
        "numbering_code": "PH4",
        "description": "Commercialization stage including offers, contracts, and collections.",
        "sort_order": 4,
        "is_active": True,
    },
    {
        "code": "handover_closeout",
        "name": "Handover & Closeout",
        "numbering_code": "PH5",
        "description": "Client handover, closeout certificates, and archive preparation stage.",
        "sort_order": 5,
        "is_active": True,
    },
]


@dataclass(frozen=True)
class RetentionPolicySeedRow:
    code: str
    name: str
    retention_years: int | None
    is_indefinite: bool
    description: str
    is_active: bool = True


PHASE2_RETENTION_POLICIES = [
    RetentionPolicySeedRow(
        code="permanent_title",
        name="Permanent - Title Records",
        retention_years=None,
        is_indefinite=True,
        description="Permanent retention for title, deed, and foundational ownership records.",
    ),
    RetentionPolicySeedRow(
        code="statutory_10_years",
        name="Statutory - 10 Years",
        retention_years=10,
        is_indefinite=False,
        description="Default statutory retention where regulations require 10 years.",
    ),
    RetentionPolicySeedRow(
        code="project_7_years",
        name="Project - 7 Years Post Completion",
        retention_years=7,
        is_indefinite=False,
        description="Project and engineering records retained for 7 years after completion.",
    ),
    RetentionPolicySeedRow(
        code="sales_10_years",
        name="Sales & Client - 10 Years",
        retention_years=10,
        is_indefinite=False,
        description="Sales and handover records retained for 10 years.",
    ),
    RetentionPolicySeedRow(
        code="finance_7_years",
        name="Finance - 7 Years",
        retention_years=7,
        is_indefinite=False,
        description="Finance/commercial records retained for minimum tax-audit cycle.",
    ),
]


def _resolve_seed_organization(organization=None):
    """Resolve target organization for document-control seed data."""
    if organization is not None:
        return organization

    from apps.accounts.models import Organization

    org = Organization.objects.order_by("id").first()
    if org is None:
        raise ValueError(
            "No organization found. Create an organization first, then seed documents."
        )
    return org


def _upsert_rows(
    model,
    rows: list[dict[str, Any]],
    *,
    organization,
    key_field: str = "code",
) -> dict[str, int]:
    created = 0
    updated = 0
    for row in rows:
        lookup = {key_field: row[key_field]}
        defaults = {**row, "organization": organization}
        _, was_created = model.objects.update_or_create(defaults=defaults, **lookup)
        if was_created:
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated, "total": len(rows)}


def seed_phase2_document_types(*, organization=None) -> dict[str, int]:
    org = _resolve_seed_organization(organization)
    return _upsert_rows(DocumentType, PHASE2_DOCUMENT_TYPES, organization=org)


def seed_phase2_owner_roles(*, organization=None) -> dict[str, int]:
    org = _resolve_seed_organization(organization)
    return _upsert_rows(DocumentOwnerRole, PHASE2_OWNER_ROLES, organization=org)


def seed_phase2_workflow_phases(*, organization=None) -> dict[str, int]:
    org = _resolve_seed_organization(organization)
    return _upsert_rows(
        DocumentWorkflowPhase,
        PHASE2_WORKFLOW_PHASES,
        organization=org,
    )


def seed_phase2_retention_policies(*, organization=None) -> dict[str, int]:
    org = _resolve_seed_organization(organization)
    rows = [
        {
            "code": row.code,
            "name": row.name,
            "retention_years": row.retention_years,
            "is_indefinite": row.is_indefinite,
            "description": row.description,
            "is_active": row.is_active,
        }
        for row in PHASE2_RETENTION_POLICIES
    ]
    return _upsert_rows(DocumentRetentionPolicy, rows, organization=org)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    ControlledVocabularyTerm,
    DocumentDomain,
    DocumentGovernanceCharter,
)

CHARTER_LOOKUP = {
    "title": "Document Governance Charter",
    "version": "v1.0",
}

CHARTER_DEFAULTS = {
    "status": DocumentGovernanceCharter.Status.ACTIVE,
    "purpose": (
        "Establish governance baseline for a centralized document repository "
        "covering land acquisition, development, sales, and handover workflows."
    ),
    "repository_scope": DocumentGovernanceCharter.RepositoryScope.FORMAL_ONLY,
    "external_portal_access": DocumentGovernanceCharter.ExternalPortalAccess.READ_ONLY,
    "includes_digital_signature_v1": False,
    "scope_notes": (
        "Phase 1 scope controls formal records only. Site photos remain in project "
        "evidence stores until future governance expansion."
    ),
    "approved_by": "Document Governance Working Group",
}

PHASE1_DOMAINS = [
    {
        "code": DocumentDomain.Code.LAND_TITLE,
        "name": "Land & Title",
        "description": "Core records that prove ownership, interests, and encumbrances.",
        "sort_order": 1,
        "is_active": True,
    },
    {
        "code": DocumentDomain.Code.REGULATORY_STATUTORY,
        "name": "Regulatory & Statutory",
        "description": "Approvals, permits, and statutory submissions required by regulators.",
        "sort_order": 2,
        "is_active": True,
    },
    {
        "code": DocumentDomain.Code.DESIGN_ENGINEERING,
        "name": "Design & Engineering",
        "description": "Design packages, calculations, revisions, and issue-for-construction artifacts.",
        "sort_order": 3,
        "is_active": True,
    },
    {
        "code": DocumentDomain.Code.CONSTRUCTION_VENDOR,
        "name": "Construction & Vendor",
        "description": "Commercial and execution documents governing contractor and supplier work.",
        "sort_order": 4,
        "is_active": True,
    },
    {
        "code": DocumentDomain.Code.SALES_CLIENT,
        "name": "Sales & Client",
        "description": "Sales contracts, customer-facing commitments, and handover records.",
        "sort_order": 5,
        "is_active": True,
    },
    {
        "code": DocumentDomain.Code.FINANCE_COMMERCIAL,
        "name": "Finance & Commercial",
        "description": "Financial and commercial records that support audit, payment, and due diligence.",
        "sort_order": 6,
        "is_active": True,
    },
]


@dataclass(frozen=True)
class VocabularySeedRow:
    domain_code: str
    term: str
    term_key: str
    definition: str
    usage_guidance: str
    synonyms: str
    is_required: bool
    sort_order: int


PHASE1_VOCABULARY_ROWS = [
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.LAND_TITLE,
        term="Deed of Assignment",
        term_key="deed_of_assignment",
        definition="Transfer instrument assigning legal interest in land.",
        usage_guidance="Upload signed and stamped executed copy as controlled master.",
        synonyms="Assignment Deed",
        is_required=True,
        sort_order=1,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.LAND_TITLE,
        term="Certificate of Occupancy",
        term_key="certificate_of_occupancy",
        definition="Government-issued title certificate confirming rights of occupancy.",
        usage_guidance="Track issuance date and linked parcel identifier.",
        synonyms="C of O",
        is_required=True,
        sort_order=2,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.LAND_TITLE,
        term="Survey Plan",
        term_key="survey_plan",
        definition="Licensed survey defining coordinates and physical boundaries.",
        usage_guidance="Store signed PDF plus source CAD where available.",
        synonyms="Survey",
        is_required=True,
        sort_order=3,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.REGULATORY_STATUTORY,
        term="Development Permit",
        term_key="development_permit",
        definition="Authority approval granting permission to commence development.",
        usage_guidance="Capture permit number, issuing authority, and expiry date.",
        synonyms="Building Approval",
        is_required=True,
        sort_order=1,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.REGULATORY_STATUTORY,
        term="Environmental Impact Approval",
        term_key="environmental_impact_approval",
        definition="Regulatory clearance for environmental impact obligations.",
        usage_guidance="Attach submission pack and final determination letter.",
        synonyms="EIA Approval",
        is_required=False,
        sort_order=2,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.REGULATORY_STATUTORY,
        term="Compliance Certificate",
        term_key="compliance_certificate",
        definition="Evidence that statutory or code compliance requirements were met.",
        usage_guidance="Document validity dates and inspection references.",
        synonyms="Statutory Certificate",
        is_required=False,
        sort_order=3,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.DESIGN_ENGINEERING,
        term="Issue for Construction Drawing",
        term_key="ifc_drawing",
        definition="Approved drawing set released for construction execution.",
        usage_guidance="Maintain revision history and superseded versions.",
        synonyms="IFC Drawing",
        is_required=True,
        sort_order=1,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.DESIGN_ENGINEERING,
        term="As-Built Drawing",
        term_key="as_built_drawing",
        definition="Final drawing reflecting actual built conditions.",
        usage_guidance="Link to completion milestone and handover package.",
        synonyms="Record Drawing",
        is_required=False,
        sort_order=2,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.DESIGN_ENGINEERING,
        term="Design Revision",
        term_key="design_revision",
        definition="Formal change to previously issued design documents.",
        usage_guidance="Reference prior revision and approval authority.",
        synonyms="Revision Notice",
        is_required=True,
        sort_order=3,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.CONSTRUCTION_VENDOR,
        term="Contract Agreement",
        term_key="contract_agreement",
        definition="Executed agreement defining scope, timelines, and obligations.",
        usage_guidance="Use signed final version as authoritative contract record.",
        synonyms="Works Contract",
        is_required=True,
        sort_order=1,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.CONSTRUCTION_VENDOR,
        term="Variation Order",
        term_key="variation_order",
        definition="Approved scope or value change against baseline contract.",
        usage_guidance="Include pricing rationale and impacted milestones.",
        synonyms="Change Order",
        is_required=False,
        sort_order=2,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.CONSTRUCTION_VENDOR,
        term="Material Approval",
        term_key="material_approval",
        definition="Approval record for submitted materials and specifications.",
        usage_guidance="Attach submittal, technical review, and final decision.",
        synonyms="Submittal Approval",
        is_required=False,
        sort_order=3,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.SALES_CLIENT,
        term="Offer Letter",
        term_key="offer_letter",
        definition="Commercial offer issued to prospective buyer.",
        usage_guidance="Track validity window and pricing assumptions.",
        synonyms="Sales Offer",
        is_required=True,
        sort_order=1,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.SALES_CLIENT,
        term="Sales Agreement",
        term_key="sales_agreement",
        definition="Binding purchase agreement with buyer and transaction terms.",
        usage_guidance="Control approved template and capture executed final copy.",
        synonyms="SPA",
        is_required=True,
        sort_order=2,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.SALES_CLIENT,
        term="Handover Pack",
        term_key="handover_pack",
        definition="Bundle of documents delivered at possession handover.",
        usage_guidance="Include snag closeout, warranties, and utility records.",
        synonyms="Closeout Pack",
        is_required=False,
        sort_order=3,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.FINANCE_COMMERCIAL,
        term="Payment Certificate",
        term_key="payment_certificate",
        definition="Certified valuation authorizing stage payment.",
        usage_guidance="Reference related contract, milestone, and valuation period.",
        synonyms="Interim Certificate",
        is_required=True,
        sort_order=1,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.FINANCE_COMMERCIAL,
        term="Invoice",
        term_key="invoice",
        definition="Commercial invoice requesting payment for goods or services.",
        usage_guidance="Store tax-compliant final issued version.",
        synonyms="Tax Invoice",
        is_required=True,
        sort_order=2,
    ),
    VocabularySeedRow(
        domain_code=DocumentDomain.Code.FINANCE_COMMERCIAL,
        term="Tax Clearance",
        term_key="tax_clearance",
        definition="Official confirmation of fulfilled tax obligations.",
        usage_guidance="Track validity date and issuing authority.",
        synonyms="Tax Certificate",
        is_required=False,
        sort_order=3,
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


def seed_phase1_charter(*, organization=None) -> tuple[DocumentGovernanceCharter, bool]:
    org = _resolve_seed_organization(organization)
    defaults = {**CHARTER_DEFAULTS, "organization": org}
    return DocumentGovernanceCharter.objects.update_or_create(
        organization=org,
        **CHARTER_LOOKUP,
        defaults=defaults,
    )


def seed_phase1_domains(*, organization=None) -> dict[str, int]:
    org = _resolve_seed_organization(organization)
    return _upsert_rows(DocumentDomain, PHASE1_DOMAINS, organization=org)


def seed_phase1_vocabulary(*, organization=None) -> dict[str, int]:
    org = _resolve_seed_organization(organization)
    domain_codes = sorted({row.domain_code for row in PHASE1_VOCABULARY_ROWS})
    domain_map = DocumentDomain.objects.in_bulk(domain_codes, field_name="code")

    missing_codes = [code for code in domain_codes if code not in domain_map]
    if missing_codes:
        raise ValueError(
            "Missing document domains required for vocabulary seed: "
            + ", ".join(missing_codes)
        )

    created = 0
    updated = 0
    for row in PHASE1_VOCABULARY_ROWS:
        _, was_created = ControlledVocabularyTerm.objects.update_or_create(
            domain=domain_map[row.domain_code],
            term_key=row.term_key,
            defaults={
                "organization": org,
                "term": row.term,
                "definition": row.definition,
                "usage_guidance": row.usage_guidance,
                "synonyms": row.synonyms,
                "status": ControlledVocabularyTerm.Status.ACTIVE,
                "is_required": row.is_required,
                "sort_order": row.sort_order,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "created": created,
        "updated": updated,
        "total": len(PHASE1_VOCABULARY_ROWS),
    }

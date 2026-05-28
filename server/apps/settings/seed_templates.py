"""
Global system project templates seeded once for the entire platform.

Templates with organization=NULL are visible to every organisation.
Invoke via: python manage.py seed_project_templates
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_TEMPLATES = [
    {
        "name": "Residential Tower Development",
        "template_type": "residential",
        "description": "Standard template for residential high-rise and mid-rise tower projects, covering land acquisition through unit handover.",
        "phases": [
            {
                "name": "Pre-Development",
                "description": "Feasibility studies, land acquisition, and initial concept design.",
                "sort_order": 0,
                "duration_days": 90,
                "weight": 10,
                "milestones": [
                    {"name": "Site Identified", "sort_order": 0, "days_from_phase_start": 14},
                    {"name": "Feasibility Report Approved", "sort_order": 1, "days_from_phase_start": 45},
                    {"name": "Land Acquisition Complete", "sort_order": 2, "days_from_phase_start": 90},
                ],
                "required_documents": [
                    {"name": "Site Survey Report", "category": "report", "is_mandatory": True},
                    {"name": "Feasibility Study", "category": "report", "is_mandatory": True},
                    {"name": "Title Deed", "category": "certificate", "is_mandatory": True},
                    {"name": "Environmental Impact Assessment", "category": "report", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Environmental Clearance", "regulatory_reference": "EPA Regulations", "is_mandatory": True},
                    {"name": "Zoning Compliance Verified", "regulatory_reference": "Municipal Zoning Code", "is_mandatory": True},
                ],
            },
            {
                "name": "Design & Approvals",
                "description": "Architectural design, engineering, and statutory approvals.",
                "sort_order": 1,
                "duration_days": 120,
                "weight": 15,
                "milestones": [
                    {"name": "Concept Design Approved", "sort_order": 0, "days_from_phase_start": 30},
                    {"name": "Detailed Design Complete", "sort_order": 1, "days_from_phase_start": 75},
                    {"name": "Building Permit Issued", "sort_order": 2, "days_from_phase_start": 120},
                ],
                "required_documents": [
                    {"name": "Architectural Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "Structural Engineering Report", "category": "report", "is_mandatory": True},
                    {"name": "MEP Design Package", "category": "plan", "is_mandatory": True},
                    {"name": "Building Permit Application", "category": "permit", "is_mandatory": True},
                    {"name": "Traffic Impact Study", "category": "report", "is_mandatory": False},
                ],
                "compliance_checkpoints": [
                    {"name": "Building Code Compliance", "regulatory_reference": "National Building Code", "is_mandatory": True},
                    {"name": "Fire Safety Review", "regulatory_reference": "Fire Safety Standards", "is_mandatory": True},
                    {"name": "Accessibility Compliance", "regulatory_reference": "ADA / Accessibility Standards", "is_mandatory": True},
                ],
            },
            {
                "name": "Construction",
                "description": "Main construction phase from foundation to structure completion.",
                "sort_order": 2,
                "duration_days": 540,
                "weight": 55,
                "milestones": [
                    {"name": "Groundbreaking", "sort_order": 0, "days_from_phase_start": 1},
                    {"name": "Foundation Complete", "sort_order": 1, "days_from_phase_start": 90},
                    {"name": "Structural Topping Out", "sort_order": 2, "days_from_phase_start": 360},
                    {"name": "MEP Rough-In Complete", "sort_order": 3, "days_from_phase_start": 420},
                    {"name": "Exterior Envelope Complete", "sort_order": 4, "days_from_phase_start": 480},
                ],
                "required_documents": [
                    {"name": "Construction Contract", "category": "contract", "is_mandatory": True},
                    {"name": "Insurance Certificates", "category": "certificate", "is_mandatory": True},
                    {"name": "Health & Safety Plan", "category": "plan", "is_mandatory": True},
                    {"name": "Quality Assurance Plan", "category": "plan", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Foundation Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                    {"name": "Structural Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                    {"name": "Health & Safety Audit", "regulatory_reference": "OSHA / Local H&S Regulations", "is_mandatory": True},
                ],
            },
            {
                "name": "Finishing & Handover",
                "description": "Interior finishing, snagging, and unit handover to buyers.",
                "sort_order": 3,
                "duration_days": 120,
                "weight": 20,
                "milestones": [
                    {"name": "Interior Finishing Complete", "sort_order": 0, "days_from_phase_start": 60},
                    {"name": "Snagging & Defects Rectified", "sort_order": 1, "days_from_phase_start": 90},
                    {"name": "Occupancy Certificate Issued", "sort_order": 2, "days_from_phase_start": 100},
                    {"name": "Unit Handover Complete", "sort_order": 3, "days_from_phase_start": 120},
                ],
                "required_documents": [
                    {"name": "Completion Certificate", "category": "certificate", "is_mandatory": True},
                    {"name": "Occupancy Certificate", "category": "permit", "is_mandatory": True},
                    {"name": "As-Built Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "Warranty Documents", "category": "certificate", "is_mandatory": True},
                    {"name": "Owner's Manual", "category": "other", "is_mandatory": False},
                ],
                "compliance_checkpoints": [
                    {"name": "Final Building Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                    {"name": "Fire Safety Certificate", "regulatory_reference": "Fire Department", "is_mandatory": True},
                    {"name": "Utility Connections Approved", "regulatory_reference": "Utility Providers", "is_mandatory": True},
                ],
            },
        ],
    },
    {
        "name": "Commercial Office Complex",
        "template_type": "commercial",
        "description": "Template for commercial office buildings and business parks, including tenant fit-out coordination.",
        "phases": [
            {
                "name": "Concept & Feasibility",
                "description": "Market analysis, site selection, and financial feasibility.",
                "sort_order": 0,
                "duration_days": 60,
                "weight": 10,
                "milestones": [
                    {"name": "Market Study Complete", "sort_order": 0, "days_from_phase_start": 21},
                    {"name": "Financial Model Approved", "sort_order": 1, "days_from_phase_start": 45},
                    {"name": "Investment Decision", "sort_order": 2, "days_from_phase_start": 60},
                ],
                "required_documents": [
                    {"name": "Market Feasibility Study", "category": "report", "is_mandatory": True},
                    {"name": "Financial Pro Forma", "category": "report", "is_mandatory": True},
                    {"name": "Site Due Diligence Report", "category": "report", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Zoning Verification", "regulatory_reference": "Municipal Zoning Code", "is_mandatory": True},
                ],
            },
            {
                "name": "Design Development",
                "description": "Architectural design, tenant specification, and permit applications.",
                "sort_order": 1,
                "duration_days": 150,
                "weight": 15,
                "milestones": [
                    {"name": "Schematic Design Approved", "sort_order": 0, "days_from_phase_start": 45},
                    {"name": "Design Development Complete", "sort_order": 1, "days_from_phase_start": 90},
                    {"name": "Construction Documents Issued", "sort_order": 2, "days_from_phase_start": 130},
                    {"name": "Building Permit Obtained", "sort_order": 3, "days_from_phase_start": 150},
                ],
                "required_documents": [
                    {"name": "Architectural Design Package", "category": "plan", "is_mandatory": True},
                    {"name": "Structural Calculations", "category": "report", "is_mandatory": True},
                    {"name": "MEP Engineering Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "Landscape Design", "category": "plan", "is_mandatory": False},
                    {"name": "Building Permit", "category": "permit", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Energy Efficiency Standards", "regulatory_reference": "Green Building Code", "is_mandatory": True},
                    {"name": "Fire Safety Design Review", "regulatory_reference": "Fire Safety Standards", "is_mandatory": True},
                ],
            },
            {
                "name": "Procurement & Construction",
                "description": "Contractor selection, construction execution, and quality management.",
                "sort_order": 2,
                "duration_days": 480,
                "weight": 55,
                "milestones": [
                    {"name": "Main Contractor Appointed", "sort_order": 0, "days_from_phase_start": 30},
                    {"name": "Foundation Complete", "sort_order": 1, "days_from_phase_start": 120},
                    {"name": "Structure Complete", "sort_order": 2, "days_from_phase_start": 300},
                    {"name": "Facade Complete", "sort_order": 3, "days_from_phase_start": 390},
                    {"name": "Practical Completion", "sort_order": 4, "days_from_phase_start": 480},
                ],
                "required_documents": [
                    {"name": "Main Construction Contract", "category": "contract", "is_mandatory": True},
                    {"name": "Performance Bond", "category": "certificate", "is_mandatory": True},
                    {"name": "Construction Programme", "category": "plan", "is_mandatory": True},
                    {"name": "Quality Management Plan", "category": "plan", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Foundation Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                    {"name": "Structural Frame Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                    {"name": "Site Safety Compliance", "regulatory_reference": "OSHA / Local H&S Regulations", "is_mandatory": True},
                ],
            },
            {
                "name": "Commissioning & Handover",
                "description": "Systems commissioning, tenant fit-out, and building handover.",
                "sort_order": 3,
                "duration_days": 90,
                "weight": 20,
                "milestones": [
                    {"name": "MEP Commissioning Complete", "sort_order": 0, "days_from_phase_start": 30},
                    {"name": "BMS Integration Tested", "sort_order": 1, "days_from_phase_start": 45},
                    {"name": "Defects Liability Period Starts", "sort_order": 2, "days_from_phase_start": 75},
                    {"name": "Building Handover", "sort_order": 3, "days_from_phase_start": 90},
                ],
                "required_documents": [
                    {"name": "Commissioning Report", "category": "report", "is_mandatory": True},
                    {"name": "Occupancy Certificate", "category": "permit", "is_mandatory": True},
                    {"name": "As-Built Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "O&M Manuals", "category": "other", "is_mandatory": True},
                    {"name": "Warranty Schedule", "category": "certificate", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Final Inspection Certificate", "regulatory_reference": "Building Department", "is_mandatory": True},
                    {"name": "Fire Safety Compliance Certificate", "regulatory_reference": "Fire Department", "is_mandatory": True},
                    {"name": "Environmental Compliance Sign-off", "regulatory_reference": "EPA Regulations", "is_mandatory": False},
                ],
            },
        ],
    },
    {
        "name": "Mixed-Use Development",
        "template_type": "mixed_use",
        "description": "Template for mixed-use developments combining residential, retail, and commercial spaces with phased delivery.",
        "phases": [
            {
                "name": "Master Planning",
                "description": "Overall site master plan, phasing strategy, and regulatory approvals.",
                "sort_order": 0,
                "duration_days": 120,
                "weight": 10,
                "milestones": [
                    {"name": "Master Plan Concept Approved", "sort_order": 0, "days_from_phase_start": 30},
                    {"name": "Phasing Strategy Defined", "sort_order": 1, "days_from_phase_start": 60},
                    {"name": "Master Plan Permit Issued", "sort_order": 2, "days_from_phase_start": 120},
                ],
                "required_documents": [
                    {"name": "Master Plan Document", "category": "plan", "is_mandatory": True},
                    {"name": "Environmental Impact Assessment", "category": "report", "is_mandatory": True},
                    {"name": "Traffic & Infrastructure Study", "category": "report", "is_mandatory": True},
                    {"name": "Phasing Strategy Report", "category": "plan", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Master Plan Zoning Approval", "regulatory_reference": "Planning Authority", "is_mandatory": True},
                    {"name": "Environmental Clearance", "regulatory_reference": "EPA Regulations", "is_mandatory": True},
                ],
            },
            {
                "name": "Design & Approvals",
                "description": "Detailed design for all components and building permit applications.",
                "sort_order": 1,
                "duration_days": 150,
                "weight": 15,
                "milestones": [
                    {"name": "Retail Component Design Approved", "sort_order": 0, "days_from_phase_start": 50},
                    {"name": "Residential Component Design Approved", "sort_order": 1, "days_from_phase_start": 80},
                    {"name": "Integrated Design Complete", "sort_order": 2, "days_from_phase_start": 120},
                    {"name": "Building Permits Obtained", "sort_order": 3, "days_from_phase_start": 150},
                ],
                "required_documents": [
                    {"name": "Integrated Architectural Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "Structural Engineering Package", "category": "plan", "is_mandatory": True},
                    {"name": "MEP Design for All Components", "category": "plan", "is_mandatory": True},
                    {"name": "Parking & Access Design", "category": "plan", "is_mandatory": True},
                    {"name": "Building Permits", "category": "permit", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Mixed-Use Zoning Compliance", "regulatory_reference": "Municipal Planning Code", "is_mandatory": True},
                    {"name": "Fire Separation Standards", "regulatory_reference": "Fire Safety Standards", "is_mandatory": True},
                    {"name": "Accessibility Review", "regulatory_reference": "ADA / Accessibility Standards", "is_mandatory": True},
                ],
            },
            {
                "name": "Construction — Podium & Retail",
                "description": "Construction of podium levels including retail and common areas.",
                "sort_order": 2,
                "duration_days": 360,
                "weight": 30,
                "milestones": [
                    {"name": "Groundbreaking", "sort_order": 0, "days_from_phase_start": 1},
                    {"name": "Basement & Foundation Complete", "sort_order": 1, "days_from_phase_start": 120},
                    {"name": "Podium Structure Complete", "sort_order": 2, "days_from_phase_start": 240},
                    {"name": "Retail Fit-Out Start", "sort_order": 3, "days_from_phase_start": 300},
                    {"name": "Podium Practical Completion", "sort_order": 4, "days_from_phase_start": 360},
                ],
                "required_documents": [
                    {"name": "Construction Contract — Podium", "category": "contract", "is_mandatory": True},
                    {"name": "Health & Safety Plan", "category": "plan", "is_mandatory": True},
                    {"name": "Excavation & Shoring Report", "category": "report", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Excavation Safety Inspection", "regulatory_reference": "OSHA / Local H&S Regulations", "is_mandatory": True},
                    {"name": "Foundation Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                ],
            },
            {
                "name": "Construction — Tower",
                "description": "Residential/office tower construction above podium.",
                "sort_order": 3,
                "duration_days": 420,
                "weight": 30,
                "milestones": [
                    {"name": "Tower Construction Start", "sort_order": 0, "days_from_phase_start": 1},
                    {"name": "Structural Topping Out", "sort_order": 1, "days_from_phase_start": 280},
                    {"name": "Facade Complete", "sort_order": 2, "days_from_phase_start": 340},
                    {"name": "Interior Finishing Complete", "sort_order": 3, "days_from_phase_start": 400},
                    {"name": "Tower Practical Completion", "sort_order": 4, "days_from_phase_start": 420},
                ],
                "required_documents": [
                    {"name": "Tower Construction Contract", "category": "contract", "is_mandatory": True},
                    {"name": "Wind Load Analysis", "category": "report", "is_mandatory": True},
                    {"name": "Elevator Installation Contract", "category": "contract", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Structural Integrity Inspection", "regulatory_reference": "Building Inspection Code", "is_mandatory": True},
                    {"name": "Elevator Safety Certification", "regulatory_reference": "Elevator Safety Standards", "is_mandatory": True},
                ],
            },
            {
                "name": "Completion & Handover",
                "description": "Final commissioning, snagging, and phased handover of all components.",
                "sort_order": 4,
                "duration_days": 90,
                "weight": 15,
                "milestones": [
                    {"name": "Retail Handover", "sort_order": 0, "days_from_phase_start": 30},
                    {"name": "Residential Unit Handover Start", "sort_order": 1, "days_from_phase_start": 45},
                    {"name": "Common Areas Handover", "sort_order": 2, "days_from_phase_start": 60},
                    {"name": "Full Project Handover", "sort_order": 3, "days_from_phase_start": 90},
                ],
                "required_documents": [
                    {"name": "Occupancy Certificates — All Components", "category": "permit", "is_mandatory": True},
                    {"name": "As-Built Drawings Package", "category": "plan", "is_mandatory": True},
                    {"name": "Warranty & Maintenance Agreements", "category": "certificate", "is_mandatory": True},
                    {"name": "Strata / Body Corporate Documentation", "category": "other", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Final Building Inspection — All Components", "regulatory_reference": "Building Department", "is_mandatory": True},
                    {"name": "Fire Safety Certificate", "regulatory_reference": "Fire Department", "is_mandatory": True},
                ],
            },
        ],
    },
    {
        "name": "Infrastructure Development",
        "template_type": "infrastructure",
        "description": "Template for infrastructure projects such as roads, utilities, site preparation, and community facilities.",
        "phases": [
            {
                "name": "Planning & Feasibility",
                "description": "Needs assessment, route/site selection, and environmental approvals.",
                "sort_order": 0,
                "duration_days": 90,
                "weight": 15,
                "milestones": [
                    {"name": "Needs Assessment Complete", "sort_order": 0, "days_from_phase_start": 21},
                    {"name": "Route/Site Selection Finalized", "sort_order": 1, "days_from_phase_start": 45},
                    {"name": "Environmental Approval Granted", "sort_order": 2, "days_from_phase_start": 90},
                ],
                "required_documents": [
                    {"name": "Needs Assessment Report", "category": "report", "is_mandatory": True},
                    {"name": "Environmental Impact Assessment", "category": "report", "is_mandatory": True},
                    {"name": "Geotechnical Investigation", "category": "report", "is_mandatory": True},
                    {"name": "Stakeholder Consultation Report", "category": "report", "is_mandatory": False},
                ],
                "compliance_checkpoints": [
                    {"name": "Environmental Clearance", "regulatory_reference": "EPA Regulations", "is_mandatory": True},
                    {"name": "Land Use Approval", "regulatory_reference": "Planning Authority", "is_mandatory": True},
                ],
            },
            {
                "name": "Detailed Engineering Design",
                "description": "Detailed design, specifications, and cost estimation.",
                "sort_order": 1,
                "duration_days": 120,
                "weight": 15,
                "milestones": [
                    {"name": "Preliminary Design Complete", "sort_order": 0, "days_from_phase_start": 40},
                    {"name": "Detailed Design Complete", "sort_order": 1, "days_from_phase_start": 90},
                    {"name": "Cost Estimate & BoQ Finalized", "sort_order": 2, "days_from_phase_start": 110},
                    {"name": "Design Approval", "sort_order": 3, "days_from_phase_start": 120},
                ],
                "required_documents": [
                    {"name": "Engineering Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "Technical Specifications", "category": "report", "is_mandatory": True},
                    {"name": "Bill of Quantities", "category": "report", "is_mandatory": True},
                    {"name": "Design Approval Certificate", "category": "permit", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Design Standards Compliance", "regulatory_reference": "Infrastructure Design Standards", "is_mandatory": True},
                    {"name": "Utility Coordination Sign-off", "regulatory_reference": "Utility Authorities", "is_mandatory": True},
                ],
            },
            {
                "name": "Procurement",
                "description": "Tendering, contractor selection, and contract award.",
                "sort_order": 2,
                "duration_days": 60,
                "weight": 10,
                "milestones": [
                    {"name": "Tender Documents Issued", "sort_order": 0, "days_from_phase_start": 7},
                    {"name": "Tender Evaluation Complete", "sort_order": 1, "days_from_phase_start": 40},
                    {"name": "Contract Awarded", "sort_order": 2, "days_from_phase_start": 60},
                ],
                "required_documents": [
                    {"name": "Tender Documents", "category": "contract", "is_mandatory": True},
                    {"name": "Tender Evaluation Report", "category": "report", "is_mandatory": True},
                    {"name": "Letter of Award", "category": "contract", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Procurement Process Compliance", "regulatory_reference": "Procurement Regulations", "is_mandatory": True},
                ],
            },
            {
                "name": "Construction & Installation",
                "description": "Physical construction and installation of infrastructure.",
                "sort_order": 3,
                "duration_days": 360,
                "weight": 45,
                "milestones": [
                    {"name": "Site Mobilization", "sort_order": 0, "days_from_phase_start": 14},
                    {"name": "Earthworks Complete", "sort_order": 1, "days_from_phase_start": 90},
                    {"name": "Primary Structure / Installation 50%", "sort_order": 2, "days_from_phase_start": 180},
                    {"name": "Primary Works Complete", "sort_order": 3, "days_from_phase_start": 300},
                    {"name": "Reinstatement & Landscaping", "sort_order": 4, "days_from_phase_start": 360},
                ],
                "required_documents": [
                    {"name": "Construction Contract", "category": "contract", "is_mandatory": True},
                    {"name": "Health & Safety Plan", "category": "plan", "is_mandatory": True},
                    {"name": "Traffic Management Plan", "category": "plan", "is_mandatory": True},
                    {"name": "Environmental Management Plan", "category": "plan", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Site Safety Audit", "regulatory_reference": "OSHA / Local H&S Regulations", "is_mandatory": True},
                    {"name": "Environmental Monitoring", "regulatory_reference": "EPA Regulations", "is_mandatory": True},
                    {"name": "Quality Inspection — Materials", "regulatory_reference": "Material Standards", "is_mandatory": True},
                ],
            },
            {
                "name": "Testing & Commissioning",
                "description": "Performance testing, snagging, and formal handover.",
                "sort_order": 4,
                "duration_days": 60,
                "weight": 15,
                "milestones": [
                    {"name": "System Testing Complete", "sort_order": 0, "days_from_phase_start": 21},
                    {"name": "Snagging & Defects Cleared", "sort_order": 1, "days_from_phase_start": 40},
                    {"name": "Practical Completion Certificate", "sort_order": 2, "days_from_phase_start": 50},
                    {"name": "Formal Handover", "sort_order": 3, "days_from_phase_start": 60},
                ],
                "required_documents": [
                    {"name": "Test Certificates", "category": "certificate", "is_mandatory": True},
                    {"name": "Practical Completion Certificate", "category": "certificate", "is_mandatory": True},
                    {"name": "As-Built Drawings", "category": "plan", "is_mandatory": True},
                    {"name": "Operation & Maintenance Manuals", "category": "other", "is_mandatory": True},
                    {"name": "Defects Liability Agreement", "category": "contract", "is_mandatory": True},
                ],
                "compliance_checkpoints": [
                    {"name": "Final Inspection Certificate", "regulatory_reference": "Relevant Authority", "is_mandatory": True},
                    {"name": "Performance Standards Verification", "regulatory_reference": "Infrastructure Standards", "is_mandatory": True},
                ],
            },
        ],
    },
]


def seed_global_project_templates() -> int:
    """
    Create the default system project templates as global entries (organization=NULL).

    Global templates are visible to every organisation.
    Skips any template whose name already exists globally (idempotent).
    Returns the number of templates created.
    """
    from .models import (
        ProjectTemplate,
        TemplateComplianceCheckpoint,
        TemplateMilestone,
        TemplatePhase,
        TemplateRequiredDocument,
    )

    created_count = 0

    for tpl_data in DEFAULT_TEMPLATES:
        if ProjectTemplate.objects.filter(
            organization__isnull=True, name=tpl_data["name"]
        ).exists():
            continue

        template = ProjectTemplate.objects.create(
            organization=None,
            name=tpl_data["name"],
            template_type=tpl_data["template_type"],
            description=tpl_data["description"],
            is_active=True,
            is_system=True,
        )

        for phase_data in tpl_data.get("phases", []):
            phase = TemplatePhase.objects.create(
                template=template,
                name=phase_data["name"],
                description=phase_data.get("description", ""),
                sort_order=phase_data.get("sort_order", 0),
                duration_days=phase_data.get("duration_days"),
                weight=phase_data.get("weight", 1),
            )

            for ms_data in phase_data.get("milestones", []):
                TemplateMilestone.objects.create(
                    phase=phase,
                    name=ms_data["name"],
                    sort_order=ms_data.get("sort_order", 0),
                    days_from_phase_start=ms_data.get("days_from_phase_start"),
                )

            for doc_data in phase_data.get("required_documents", []):
                TemplateRequiredDocument.objects.create(
                    phase=phase,
                    name=doc_data["name"],
                    category=doc_data.get("category", "other"),
                    is_mandatory=doc_data.get("is_mandatory", True),
                )

            for cp_data in phase_data.get("compliance_checkpoints", []):
                TemplateComplianceCheckpoint.objects.create(
                    phase=phase,
                    name=cp_data["name"],
                    regulatory_reference=cp_data.get("regulatory_reference", ""),
                    is_mandatory=cp_data.get("is_mandatory", True),
                )

        created_count += 1
        logger.info("Seeded global project template '%s'", tpl_data["name"])

    return created_count

"""
Seed realistic demo data for the Projects module.

Usage:
    python manage.py seed_projects_demo
    python manage.py seed_projects_demo --flush
    python manage.py seed_projects_demo --organization-id 1
    python manage.py seed_projects_demo --organization-id 1 --flush
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone as tz

from apps.accounts.models import Organization
from apps.projects.models import (
    Project,
    ProjectCostEntry,
    ProjectDailySiteReport,
    ProjectFieldEscalation,
    ProjectMilestone,
    ProjectPhase,
    ProjectRiskRegisterEntry,
    ProjectTask,
    ProjectVariationOrder,
    ProjectWorkforceLog,
)
from apps.properties.models import Property

DEMO_MARKER = "[demo-seed]"

# ---------------------------------------------------------------------------
# Hardcoded realistic data
# ---------------------------------------------------------------------------

PROJECT_DATA = [
    {
        "name": "Lekki Waterfront Residences Phase II",
        "project_type": "residential",
        "status": "in_progress",
        "location": "Plot 1265, Admiralty Road, Lekki Phase 1, Lagos",
        "land_status": "freehold",
        "budget": Decimal("4850000000.00"),
        "target_irr": Decimal("22.50"),
        "risk_rating": "medium",
        "project_manager": "Engr. Tunde Fashola",
        "spv_entity": "Lekki Waterfront Development Co. Ltd",
    },
    {
        "name": "Maitama Corporate Plaza",
        "project_type": "commercial",
        "status": "in_progress",
        "location": "Plot 289, Aguiyi Ironsi Street, Maitama, Abuja",
        "land_status": "freehold",
        "budget": Decimal("3200000000.00"),
        "target_irr": Decimal("18.75"),
        "risk_rating": "low",
        "project_manager": "Arch. Amara Obi",
        "spv_entity": "Maitama Plaza Investments Ltd",
    },
    {
        "name": "Victoria Island Mixed-Use Tower",
        "project_type": "mixed_use",
        "status": "planning",
        "location": "Plot 42, Ozumba Mbadiwe Avenue, Victoria Island, Lagos",
        "land_status": "leasehold",
        "budget": Decimal("8900000000.00"),
        "target_irr": Decimal("25.00"),
        "risk_rating": "high",
        "project_manager": "Engr. Chika Nnoli",
        "spv_entity": "VI Tower Development SPV",
    },
    {
        "name": "Port Harcourt Garden Estate",
        "project_type": "residential",
        "status": "on_hold",
        "location": "KM 14, East-West Road, Rumuokwurushi, Port Harcourt",
        "land_status": "under_contract",
        "budget": Decimal("2100000000.00"),
        "target_irr": Decimal("19.00"),
        "risk_rating": "high",
        "project_manager": "Engr. Boma Wike",
        "spv_entity": "Garden Estate Rivers SPV Ltd",
    },
    {
        "name": "Abuja Ring Road Upgrade",
        "project_type": "infrastructure",
        "status": "completed",
        "location": "Northern Ring Road, Phase 3 Extension, Abuja FCT",
        "land_status": "joint_venture",
        "budget": Decimal("6500000000.00"),
        "target_irr": Decimal("12.50"),
        "risk_rating": "medium",
        "project_manager": "Engr. Musa Danladi",
        "spv_entity": "FCT Infrastructure Partners JV",
    },
]

# Phase templates per project type
PHASE_TEMPLATES = {
    "residential": [
        ("Land Acquisition & Due Diligence", 1, 15),
        ("Design & Regulatory Approvals", 2, 20),
        ("Foundation & Substructure", 3, 20),
        ("Superstructure & Envelope", 4, 25),
        ("MEP Installation & Finishing", 5, 15),
        ("Handover & Defects Liability", 6, 5),
    ],
    "commercial": [
        ("Site Assembly & Due Diligence", 1, 10),
        ("Concept Design & Permits", 2, 15),
        ("Piling & Foundation Works", 3, 20),
        ("Structural Frame & Core", 4, 25),
        ("Facade, MEP & Fit-Out", 5, 20),
        ("Commissioning & Handover", 6, 10),
    ],
    "mixed_use": [
        ("Land Acquisition & Planning", 1, 10),
        ("Architecture & Engineering Design", 2, 15),
        ("Enabling Works & Foundation", 3, 15),
        ("Superstructure Construction", 4, 25),
        ("MEP, Finishing & Landscaping", 5, 25),
        ("Testing, Commissioning & Handover", 6, 10),
    ],
    "infrastructure": [
        ("Feasibility Study & Approvals", 1, 10),
        ("Detailed Engineering Design", 2, 15),
        ("Mobilization & Earthworks", 3, 20),
        ("Road & Drainage Construction", 4, 30),
        ("Utilities & Street Furniture", 5, 15),
        ("Testing & Commissioning", 6, 10),
    ],
}

MILESTONE_TEMPLATES = {
    "residential": [
        (0, "Land Title Verified", False),
        (0, "Governor's Consent Obtained", True),
        (1, "Building Permit Approved", True),
        (1, "Architectural Drawings Signed Off", False),
        (2, "Piling Completed", False),
        (2, "Ground Floor Slab Cast", False),
        (3, "Roof Slab Cast", False),
        (3, "Block Work Completed", False),
        (4, "MEP Rough-In Signed Off", True),
        (4, "Internal Plastering Complete", False),
        (5, "Practical Completion Certificate", True),
        (5, "Defects Liability Period Ends", False),
    ],
    "commercial": [
        (0, "Site Acquisition Complete", False),
        (0, "Environmental Impact Assessment Approved", True),
        (1, "Design Development Approved", True),
        (1, "Construction Permit Issued", True),
        (2, "Piling Works Complete", False),
        (2, "Raft Foundation Poured", False),
        (3, "Steel Frame Erected", False),
        (3, "Core & Shell Topped Out", True),
        (4, "Curtain Wall Installation Complete", False),
        (4, "MEP Systems Tested", True),
        (5, "Fire Safety Certificate Issued", True),
        (5, "Occupancy Certificate Obtained", True),
    ],
    "mixed_use": [
        (0, "Land Acquisition Completed", False),
        (0, "Zoning Approval Secured", True),
        (1, "Schematic Design Approved", True),
        (1, "Structural Engineering Report Signed", False),
        (2, "Shoring & Excavation Complete", False),
        (2, "Foundation Mat Poured", False),
        (3, "Podium Level Complete", False),
        (3, "Tower Topped Out", True),
        (4, "Elevator Installation Complete", False),
        (4, "Landscape Design Implemented", False),
        (5, "Building Systems Commissioned", True),
        (5, "Certificate of Occupancy Issued", True),
    ],
    "infrastructure": [
        (0, "Feasibility Report Accepted", True),
        (0, "Environmental Clearance Obtained", True),
        (1, "Detailed Design Drawings Approved", True),
        (1, "Bill of Quantities Finalized", False),
        (2, "Site Mobilization Complete", False),
        (2, "Cut & Fill Earthworks Done", False),
        (3, "Sub-Base Layer Completed", False),
        (3, "Asphalt Wearing Course Laid", True),
        (4, "Storm Drainage System Installed", False),
        (4, "Street Lighting Energized", False),
        (5, "Load Testing Complete", True),
        (5, "Final Handover to Client", True),
    ],
}

TASK_TEMPLATES = {
    "residential": [
        (0, "Conduct title search at Land Registry", "medium"),
        (0, "Commission survey & beacon verification", "high"),
        (1, "Prepare & submit building plan", "high"),
        (1, "Obtain LASBCA approval", "critical"),
        (1, "Procure soil investigation report", "medium"),
        (2, "Mobilize piling contractor", "high"),
        (2, "Cast pile caps & ground beams", "high"),
        (2, "Pour ground floor slab", "medium"),
        (3, "Erect block walls — all floors", "medium"),
        (3, "Install roof trusses & sheeting", "high"),
        (3, "External rendering & painting", "low"),
        (4, "Rough-in electrical conduits", "medium"),
        (4, "Install plumbing & sanitary ware", "medium"),
        (4, "Tile flooring — all units", "low"),
        (4, "Install doors, windows & ironmongery", "medium"),
        (5, "Punch list walkthrough", "high"),
        (5, "Final cleaning & landscaping", "low"),
    ],
    "commercial": [
        (0, "Engage solicitors for site acquisition", "high"),
        (0, "Commission EIA study", "critical"),
        (1, "Finalize concept design", "high"),
        (1, "Submit permit application", "high"),
        (2, "Award piling contract", "high"),
        (2, "Monitor piling integrity tests", "medium"),
        (3, "Erect steel frame — levels 1-5", "critical"),
        (3, "Pour concrete core walls", "high"),
        (3, "Install MEP risers in core", "medium"),
        (4, "Install curtain wall panels", "high"),
        (4, "Commission HVAC plant", "high"),
        (4, "Fit-out common areas", "medium"),
        (5, "Fire safety inspection", "critical"),
        (5, "Obtain occupancy permit", "high"),
    ],
    "mixed_use": [
        (0, "Secure land option agreement", "high"),
        (0, "Apply for zoning variance", "critical"),
        (1, "Complete schematic design", "high"),
        (1, "Engage structural engineer", "medium"),
        (2, "Install shoring & dewater", "high"),
        (2, "Pour foundation mat", "high"),
        (3, "Construct podium parking levels", "medium"),
        (3, "Build tower floors 1-20", "critical"),
        (3, "Install elevator guide rails", "high"),
        (4, "Complete MEP fit-out", "high"),
        (4, "Install landscape & hardscape", "medium"),
        (4, "External facade cladding", "high"),
        (5, "Commission building systems", "critical"),
        (5, "Obtain C of O from LASG", "high"),
    ],
    "infrastructure": [
        (0, "Conduct traffic impact study", "high"),
        (0, "Prepare feasibility report", "medium"),
        (1, "Complete detailed engineering drawings", "critical"),
        (1, "Finalize BOQ & cost estimate", "high"),
        (2, "Clear right of way", "high"),
        (2, "Mobilize heavy equipment", "medium"),
        (2, "Execute cut & fill earthworks", "high"),
        (3, "Lay sub-base & base course", "critical"),
        (3, "Construct storm drainage channels", "high"),
        (3, "Lay asphalt binder & wearing course", "critical"),
        (4, "Install road markings & signage", "medium"),
        (4, "Erect street lighting poles", "medium"),
        (4, "Connect utility crossings", "high"),
        (5, "Conduct load test on pavement", "high"),
        (5, "Prepare as-built drawings", "medium"),
    ],
}

COST_ENTRY_DATA = [
    ("Reinforcement steel — 16mm TMT bars", "materials", "Dangote Steel Ltd", 45000000),
    ("Concrete supply — Grade 35", "materials", "Lafarge Africa Plc", 28000000),
    ("Formwork timber & plywood", "materials", "Wemabod Timber", 8500000),
    ("Piling works — CFA piles", "subcontractor", "Julius Berger Foundations", 95000000),
    ("Structural steel fabrication", "materials", "Honeywell Steel", 62000000),
    ("Electrical installation — Phase 1", "subcontractor", "MBH Power Systems", 18000000),
    ("Plumbing & sanitary fittings", "materials", "Franke Nigeria", 12000000),
    ("HVAC equipment procurement", "equipment", "CoolTech HVAC Services", 35000000),
    ("Building permit fees", "permits", "Lagos State Government", 4500000),
    ("Environmental impact assessment", "permits", "Federal Ministry of Environment", 2800000),
    ("Skilled labor — masonry crew", "labor", "Direct hire", 15000000),
    ("Skilled labor — MEP team", "labor", "Direct hire", 22000000),
    ("Tower crane rental — 3 months", "equipment", "Mantrac Nigeria", 18000000),
    ("Excavation & earthworks", "subcontractor", "Reynolds Construction", 32000000),
    ("Facade glazing & curtain wall", "subcontractor", "Aluminium City Ltd", 48000000),
    ("Fire detection & suppression system", "equipment", "Securifire Nigeria", 9500000),
    ("External painting & waterproofing", "materials", "Dulux Nigeria", 6800000),
    ("Road asphalt & bitumen", "materials", "Setraco Nigeria", 75000000),
    ("Survey & geotechnical investigation", "permits", "Geoprobe Nigeria", 3200000),
    ("Elevator procurement & installation", "equipment", "Otis Elevator Nigeria", 85000000),
    ("Generator — 500kVA Mikano", "equipment", "Mikano International", 42000000),
    ("Landscaping & hardscape", "subcontractor", "Eden Garden Services", 7500000),
    ("Security infrastructure", "equipment", "SecureNet Systems", 5200000),
    ("Temporary site facilities", "other", "Portakabin Nigeria", 4800000),
    ("Insurance — CAR policy", "other", "Leadway Assurance", 8900000),
    ("Quality testing — concrete cubes", "other", "COREN Labs", 1200000),
    ("Drainage & culvert works", "subcontractor", "Dredging Associates", 28000000),
    ("Water treatment plant", "equipment", "WTP Nigeria", 11000000),
    ("Tiling & flooring — all units", "materials", "Porcelanosa Nigeria", 14500000),
    ("Doors, windows & ironmongery", "materials", "Tower Aluminium", 19000000),
]

RISK_DATA = [
    {
        "title": "Building Permit Delays",
        "description": "Extended processing times at LASBCA may delay construction start by 2-4 months",
        "severity": "high",
        "likelihood_key": "high",
        "likelihood_score": 4,
        "impact_key": "high",
        "impact_score": 4,
        "risk_score": 16,
        "treatment": "mitigate",
        "mitigation_plan": "Engage experienced permit consultant; submit early; maintain relationships with regulatory bodies",
    },
    {
        "title": "Construction Material Cost Escalation",
        "description": "Naira depreciation and import restrictions may increase steel and cement costs by 15-25%",
        "severity": "high",
        "likelihood_key": "high",
        "likelihood_score": 4,
        "impact_key": "medium",
        "impact_score": 3,
        "risk_score": 12,
        "treatment": "mitigate",
        "mitigation_plan": "Lock in prices with advance purchase agreements; source locally where possible; maintain 10% contingency",
    },
    {
        "title": "Rainy Season Construction Delays",
        "description": "Peak rainfall June-September may halt earthworks and foundation activities",
        "severity": "medium",
        "likelihood_key": "high",
        "likelihood_score": 4,
        "impact_key": "medium",
        "impact_score": 3,
        "risk_score": 12,
        "treatment": "accept",
        "mitigation_plan": "Schedule earthworks for dry season; plan indoor activities during rain periods",
    },
    {
        "title": "Title Dispute / Omo-Onile Interference",
        "description": "Community land claims or youth group disruptions at project site",
        "severity": "critical",
        "likelihood_key": "medium",
        "likelihood_score": 3,
        "impact_key": "critical",
        "impact_score": 5,
        "risk_score": 15,
        "treatment": "mitigate",
        "mitigation_plan": "Verify title with Governor's Consent; engage community liaison; secure site perimeter early",
    },
    {
        "title": "Foreign Exchange Volatility",
        "description": "Naira/USD fluctuation impacting imported equipment costs",
        "severity": "medium",
        "likelihood_key": "medium",
        "likelihood_score": 3,
        "impact_key": "medium",
        "impact_score": 3,
        "risk_score": 9,
        "treatment": "transfer",
        "mitigation_plan": "Use forward contracts for major FX exposures; negotiate NGN-denominated supplier contracts",
    },
    {
        "title": "Workforce Shortage — Skilled Trades",
        "description": "Shortage of certified welders, electricians, and plumbers in project locality",
        "severity": "medium",
        "likelihood_key": "medium",
        "likelihood_score": 3,
        "impact_key": "medium",
        "impact_score": 3,
        "risk_score": 9,
        "treatment": "mitigate",
        "mitigation_plan": "Partner with TVET institutions; offer competitive rates; pre-qualify subcontractors",
    },
    {
        "title": "Power Supply Interruptions",
        "description": "Unreliable grid power affecting site operations and concrete curing",
        "severity": "low",
        "likelihood_key": "high",
        "likelihood_score": 4,
        "impact_key": "low",
        "impact_score": 2,
        "risk_score": 8,
        "treatment": "mitigate",
        "mitigation_plan": "Procure dedicated site generators; install solar backup for critical operations",
    },
    {
        "title": "Regulatory Change — Building Codes",
        "description": "New Lagos State building regulations may require design modifications",
        "severity": "low",
        "likelihood_key": "low",
        "likelihood_score": 2,
        "impact_key": "medium",
        "impact_score": 3,
        "risk_score": 6,
        "treatment": "accept",
        "mitigation_plan": "Monitor regulatory developments; design to exceed current minimums",
    },
    {
        "title": "Environmental Compliance Issues",
        "description": "Waste disposal and erosion control non-compliance may trigger stop-work order",
        "severity": "high",
        "likelihood_key": "medium",
        "likelihood_score": 3,
        "impact_key": "high",
        "impact_score": 4,
        "risk_score": 12,
        "treatment": "avoid",
        "mitigation_plan": "Appoint dedicated EHS officer; implement waste management plan; conduct monthly audits",
    },
    {
        "title": "Subcontractor Default",
        "description": "Key subcontractor fails to deliver or abandons site mid-project",
        "severity": "high",
        "likelihood_key": "low",
        "likelihood_score": 2,
        "impact_key": "high",
        "impact_score": 4,
        "risk_score": 8,
        "treatment": "transfer",
        "mitigation_plan": "Require performance bonds; maintain pre-qualified backup subcontractor list",
    },
    {
        "title": "Site Access Road Deterioration",
        "description": "Heavy construction traffic may damage access roads, delaying material delivery",
        "severity": "low",
        "likelihood_key": "medium",
        "likelihood_score": 3,
        "impact_key": "low",
        "impact_score": 2,
        "risk_score": 6,
        "treatment": "mitigate",
        "mitigation_plan": "Maintain temporary access road; coordinate with local government for road repairs",
    },
    {
        "title": "Client Scope Change Requests",
        "description": "Late design changes from client affecting schedule and budget",
        "severity": "medium",
        "likelihood_key": "medium",
        "likelihood_score": 3,
        "impact_key": "medium",
        "impact_score": 3,
        "risk_score": 9,
        "treatment": "mitigate",
        "mitigation_plan": "Establish design freeze milestones; process changes through variation order system",
    },
]

VARIATION_ORDER_DATA = [
    {
        "title": "Additional Basement Parking Level",
        "change_summary": "Client requested additional basement level to increase parking from 120 to 200 spaces",
        "reason": "Market demand analysis showed higher parking ratio needed for premium pricing",
        "status": "approved",
        "contract_value": Decimal("185000000.00"),
    },
    {
        "title": "Upgraded Facade Specification",
        "change_summary": "Change from aluminium composite panel to unitized curtain wall system",
        "reason": "Design review identified thermal performance shortfall; upgraded to double-glazed system",
        "status": "approved",
        "contract_value": Decimal("92000000.00"),
    },
    {
        "title": "Smart Building Systems Integration",
        "change_summary": "Add BMS, access control, and IoT sensors throughout the building",
        "reason": "Client decision to market as smart building for premium tenants",
        "status": "under_review",
        "contract_value": Decimal("145000000.00"),
    },
    {
        "title": "Foundation Design Revision",
        "change_summary": "Redesign from pad foundations to raft foundation due to soil conditions",
        "reason": "Geotechnical investigation revealed weaker soil bearing capacity than assumed",
        "status": "approved",
        "contract_value": Decimal("68000000.00"),
    },
    {
        "title": "Landscape Redesign — Rooftop Garden",
        "change_summary": "Add rooftop garden with irrigation system and recreational deck",
        "reason": "Competitive differentiation requested by marketing team",
        "status": "submitted",
        "contract_value": Decimal("42000000.00"),
    },
    {
        "title": "MEP Scope Reduction — Phase 2 Deferral",
        "change_summary": "Defer 3rd floor MEP fit-out to Phase 2 to manage cash flow",
        "reason": "Budget pressure due to FX movements; defer non-critical scope",
        "status": "draft",
        "contract_value": Decimal("-28000000.00"),
    },
    {
        "title": "Road Width Increase — Dual Carriageway",
        "change_summary": "Widen road from single to dual carriageway with central median",
        "reason": "Federal Ministry directive for arterial road classification upgrade",
        "status": "approved",
        "contract_value": Decimal("320000000.00"),
    },
    {
        "title": "Additional Fire Escape Staircase",
        "change_summary": "Add second fire escape staircase per updated fire safety code requirements",
        "reason": "Lagos State Fire Service review mandated additional escape route for buildings above 8 floors",
        "status": "approved",
        "contract_value": Decimal("56000000.00"),
    },
]

ESCALATION_DATA = [
    {
        "title": "Heavy Rainfall Flooding at Foundation Level",
        "issue_category": "weather",
        "issue_type": "extreme_rain_flooding",
        "severity": "escalation",
        "status": "resolved",
        "location": "Basement excavation area",
        "impact_summary": "3-day work stoppage; dewatering pumps deployed; 2 days lost on foundation schedule",
        "root_cause": "Unexpected heavy rainfall exceeded drainage capacity",
        "immediate_action": "Deployed 3 dewatering pumps; diverted surface water with temporary berms",
    },
    {
        "title": "Cement Supply Shortage — BUA Cement",
        "issue_category": "procurement",
        "issue_type": "material_shortage",
        "severity": "action_required",
        "status": "in_progress",
        "location": "Site stores",
        "impact_summary": "Block work halted for 5 days; switched to Dangote Cement at higher cost",
        "root_cause": "BUA Cement plant shutdown for maintenance; no advance notice",
        "immediate_action": "Procured from alternative supplier; adjusted budget for price differential",
    },
    {
        "title": "Scaffold Collapse — Near Miss Incident",
        "issue_category": "safety",
        "issue_type": "near_miss",
        "severity": "escalation",
        "status": "closed",
        "location": "Block A, Level 3 external face",
        "impact_summary": "No injuries; 1-day work stoppage for safety review; all scaffolding re-inspected",
        "root_cause": "Improper bracing on cantilever section; subcontractor non-compliance",
        "immediate_action": "Evacuated area immediately; engaged certified scaffolding inspector",
    },
    {
        "title": "Subcontractor Workforce No-Show",
        "issue_category": "workforce",
        "issue_type": "workforce_shortage",
        "severity": "action_required",
        "status": "resolved",
        "location": "Tower block floors 6-8",
        "impact_summary": "Plastering works delayed 4 days; alternative crew mobilized from sister project",
        "root_cause": "Subcontractor diverted crew to another project without notice",
        "immediate_action": "Issued formal warning; mobilized backup crew; deducted penalty from subcontractor payment",
    },
    {
        "title": "LASBCA Stop-Work Notice — Permit Issue",
        "issue_category": "compliance",
        "issue_type": "regulatory_stop_notice",
        "severity": "escalation",
        "status": "resolved",
        "location": "Entire project site",
        "impact_summary": "7-day full work stoppage; additional permit fees of ₦1.2M; legal engagement required",
        "root_cause": "Discrepancy between approved plans and as-built floor area ratio",
        "immediate_action": "Engaged architect to prepare amended drawings; met with LASBCA officials",
    },
    {
        "title": "Generator Breakdown During Concrete Pour",
        "issue_category": "equipment",
        "issue_type": "equipment_breakdown",
        "severity": "action_required",
        "status": "closed",
        "location": "Concrete batching area",
        "impact_summary": "Concrete pour delayed 6 hours; hired emergency standby generator",
        "root_cause": "Fuel pump failure on primary 500kVA generator; overdue for service",
        "immediate_action": "Activated emergency generator hire; expedited fuel pump replacement",
    },
    {
        "title": "Community Youth Protest — Access Blocked",
        "issue_category": "community",
        "issue_type": "community_complaint",
        "severity": "escalation",
        "status": "resolved",
        "location": "Main site access gate",
        "impact_summary": "2-day access disruption; negotiated employment of 15 local youth; ₦500K community fund",
        "root_cause": "Community youth demanded local employment and CSR contributions",
        "immediate_action": "Engaged community liaison; held stakeholder meeting with youth leaders",
    },
    {
        "title": "Quality Defect — Misaligned Column Reinforcement",
        "issue_category": "quality",
        "issue_type": "rework_required",
        "severity": "action_required",
        "status": "in_progress",
        "location": "Block B, Ground Floor Column C7",
        "impact_summary": "Column rebar cage 50mm off centre; rework and re-pour required; 3-day delay",
        "root_cause": "Inadequate formwork bracing; setting-out error by subcontractor",
        "immediate_action": "Broke out defective column; re-set formwork with independent survey check",
    },
]

NIGERIAN_SITE_ENGINEERS = [
    "Engr. Adebayo Oluwatobi",
    "Engr. Chioma Nwosu",
    "Engr. Ibrahim Musa",
    "Engr. Ngozi Okeke",
    "Engr. Yusuf Abdullahi",
    "Engr. Boma Briggs",
    "Engr. Fatima Bello",
    "Engr. Emeka Obiora",
]


class Command(BaseCommand):
    help = "Seed realistic demo data for the Projects module."

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

            random.seed(org.id + 8000)

            if flush:
                self._flush(org)

            projects = self._seed_projects(org)
            phases = self._seed_phases(org, projects)
            self._seed_milestones(org, projects, phases)
            self._seed_tasks(org, projects, phases)
            self._seed_cost_entries(org, projects, phases)
            self._seed_risks(org, projects)
            self._seed_variation_orders(org, projects)
            self._seed_workforce_logs(org, projects)
            self._seed_daily_site_reports(org, projects)
            self._seed_escalations(org, projects)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done! Projects module populated for {org.name}: "
                    f"{len(projects)} projects, {sum(len(v) for v in phases.values())} phases."
                )
            )

    def _flush(self, org):
        self.stdout.write("Flushing previous Projects demo data ...")
        ProjectFieldEscalation.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        ProjectDailySiteReport.objects.filter(
            organization=org, work_completed__icontains=DEMO_MARKER
        ).delete()
        ProjectWorkforceLog.objects.filter(
            organization=org, notes__icontains=DEMO_MARKER
        ).delete()
        ProjectVariationOrder.objects.filter(
            organization=org, change_summary__icontains=DEMO_MARKER
        ).delete()
        ProjectRiskRegisterEntry.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        ProjectCostEntry.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        ProjectTask.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        ProjectMilestone.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        ProjectPhase.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        Project.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        self.stdout.write("  Flushed.")

    # ----- Projects -----

    def _seed_projects(self, org):
        today = date.today()
        projects = []

        # Try to link projects to existing properties from seed_properties_demo
        properties = list(Property.objects.filter(organization=org).order_by("id"))

        for idx, p in enumerate(PROJECT_DATA):
            linked_property = None
            if properties:
                # Link some projects to matching properties
                if idx == 0 and len(properties) > 0:
                    linked_property = properties[0]  # Admiralty Towers
                elif idx == 1 and len(properties) > 3:
                    linked_property = properties[3]  # Maitama Business Hub
                elif idx == 2 and len(properties) > 2:
                    linked_property = properties[2]  # Victoria Heights

            status = p["status"]
            if status == "completed":
                start = today - timedelta(days=random.randint(900, 1200))
                target_end = start + timedelta(days=random.randint(540, 720))
                actual_end = target_end + timedelta(days=random.randint(-30, 60))
            elif status == "in_progress":
                start = today - timedelta(days=random.randint(180, 540))
                target_end = today + timedelta(days=random.randint(180, 540))
                actual_end = None
            elif status == "on_hold":
                start = today - timedelta(days=random.randint(120, 365))
                target_end = today + timedelta(days=random.randint(365, 730))
                actual_end = None
            else:  # planning
                start = today + timedelta(days=random.randint(30, 180))
                target_end = start + timedelta(days=random.randint(720, 1080))
                actual_end = None

            project, _ = Project.objects.get_or_create(
                organization=org,
                name=p["name"],
                defaults={
                    "description": f"{DEMO_MARKER} Demo project for platform testing",
                    "project_type": p["project_type"],
                    "status": status,
                    "location": p["location"],
                    "land_status": p["land_status"],
                    "budget": p["budget"],
                    "target_irr": p["target_irr"],
                    "risk_rating": p["risk_rating"],
                    "project_manager": p["project_manager"],
                    "spv_entity": p["spv_entity"],
                    "start_date": start,
                    "target_end_date": target_end,
                    "actual_end_date": actual_end,
                    "property": linked_property,
                },
            )
            projects.append(project)

        self.stdout.write(f"  {len(projects)} projects ready.")
        return projects

    # ----- Phases -----

    def _seed_phases(self, org, projects):
        today = date.today()
        phases_map: dict[int, list[ProjectPhase]] = {}

        for project in projects:
            template = PHASE_TEMPLATES.get(project.project_type, PHASE_TEMPLATES["residential"])
            project_phases = []

            total_duration = (
                (project.target_end_date - project.start_date).days
                if project.start_date and project.target_end_date
                else 720
            )

            cursor_date = project.start_date or today

            for phase_name, sort_order, weight in template:
                phase_days = int(total_duration * weight / 100)
                planned_start = cursor_date
                planned_end = cursor_date + timedelta(days=phase_days)

                # Determine status based on project status and phase position
                if project.status == "completed":
                    phase_status = "completed"
                    actual_start = planned_start + timedelta(days=random.randint(-5, 10))
                    actual_end = planned_end + timedelta(days=random.randint(-10, 20))
                elif project.status == "planning":
                    phase_status = "not_started"
                    actual_start = None
                    actual_end = None
                elif project.status == "on_hold":
                    if sort_order <= 2:
                        phase_status = "completed"
                        actual_start = planned_start + timedelta(days=random.randint(0, 7))
                        actual_end = planned_end + timedelta(days=random.randint(-5, 15))
                    elif sort_order == 3:
                        phase_status = "in_progress"
                        actual_start = planned_start + timedelta(days=random.randint(0, 10))
                        actual_end = None
                    else:
                        phase_status = "not_started"
                        actual_start = None
                        actual_end = None
                else:  # in_progress
                    if planned_end < today - timedelta(days=30):
                        phase_status = "completed"
                        actual_start = planned_start + timedelta(days=random.randint(0, 7))
                        actual_end = planned_end + timedelta(days=random.randint(-5, 15))
                    elif planned_start < today:
                        phase_status = "in_progress"
                        actual_start = planned_start + timedelta(days=random.randint(0, 7))
                        actual_end = None
                    else:
                        phase_status = "not_started"
                        actual_start = None
                        actual_end = None

                phase_budget = Decimal(str(int(float(project.budget or 1000000000) * weight / 100)))
                actual_cost = (
                    phase_budget * Decimal(str(random.uniform(0.85, 1.15)))
                    if phase_status == "completed"
                    else phase_budget * Decimal(str(random.uniform(0.3, 0.7)))
                    if phase_status == "in_progress"
                    else Decimal("0")
                )

                phase, _ = ProjectPhase.objects.get_or_create(
                    organization=org,
                    project=project,
                    name=phase_name,
                    defaults={
                        "description": f"{DEMO_MARKER} {phase_name}",
                        "sort_order": sort_order,
                        "status": phase_status,
                        "planned_start_date": planned_start,
                        "planned_end_date": planned_end,
                        "actual_start_date": actual_start,
                        "actual_end_date": actual_end,
                        "planned_budget": phase_budget,
                        "actual_cost": int(actual_cost),
                        "weight": weight,
                    },
                )
                project_phases.append(phase)
                cursor_date = planned_end

            phases_map[project.id] = project_phases

        total = sum(len(v) for v in phases_map.values())
        self.stdout.write(f"  {total} phases ready.")
        return phases_map

    # ----- Milestones -----

    def _seed_milestones(self, org, projects, phases_map):
        today = date.today()
        count = 0

        for project in projects:
            project_phases = phases_map.get(project.id, [])
            if not project_phases:
                continue

            template = MILESTONE_TEMPLATES.get(project.project_type, MILESTONE_TEMPLATES["residential"])

            for phase_idx, ms_name, approval_required in template:
                if phase_idx >= len(project_phases):
                    continue

                phase = project_phases[phase_idx]
                start = phase.planned_start_date or today
                end = phase.planned_end_date or (today + timedelta(days=90))
                target = start + timedelta(days=int((end - start).days * random.uniform(0.3, 0.9)))

                is_completed = phase.status == "completed"
                completed_dt = target + timedelta(days=random.randint(-5, 10)) if is_completed else None

                if approval_required and is_completed:
                    approval_status = "approved"
                elif approval_required and phase.status == "in_progress":
                    approval_status = random.choice(["pending", "approved"])
                elif approval_required:
                    approval_status = "pending"
                else:
                    approval_status = "not_required"

                ProjectMilestone.objects.get_or_create(
                    organization=org,
                    phase=phase,
                    name=ms_name,
                    defaults={
                        "description": f"{DEMO_MARKER} {ms_name}",
                        "target_date": target,
                        "is_completed": is_completed,
                        "completed_date": completed_dt,
                        "approval_required": approval_required,
                        "approval_status": approval_status,
                    },
                )
                count += 1

        self.stdout.write(f"  {count} milestones ready.")

    # ----- Tasks -----

    def _seed_tasks(self, org, projects, phases_map):
        today = date.today()
        count = 0

        for project in projects:
            project_phases = phases_map.get(project.id, [])
            if not project_phases:
                continue

            template = TASK_TEMPLATES.get(project.project_type, TASK_TEMPLATES["residential"])

            for phase_idx, task_name, priority in template:
                if phase_idx >= len(project_phases):
                    continue

                phase = project_phases[phase_idx]
                start = phase.planned_start_date or today
                end = phase.planned_end_date or (today + timedelta(days=90))
                due = start + timedelta(days=int((end - start).days * random.uniform(0.4, 0.95)))

                if phase.status == "completed":
                    task_status = "completed"
                    completed_dt = due + timedelta(days=random.randint(-5, 8))
                elif phase.status == "in_progress":
                    task_status = random.choice(["pending", "in_progress", "in_progress", "completed"])
                    completed_dt = due - timedelta(days=random.randint(0, 10)) if task_status == "completed" else None
                else:
                    task_status = "pending"
                    completed_dt = None

                ProjectTask.objects.get_or_create(
                    organization=org,
                    phase=phase,
                    name=task_name,
                    defaults={
                        "description": f"{DEMO_MARKER} {task_name}",
                        "priority": priority,
                        "status": task_status,
                        "assigned_to": random.choice(NIGERIAN_SITE_ENGINEERS),
                        "due_date": due,
                        "completed_date": completed_dt,
                        "sort_order": count,
                    },
                )
                count += 1

        self.stdout.write(f"  {count} tasks ready.")

    # ----- Cost Entries -----

    def _seed_cost_entries(self, org, projects, phases_map):
        today = date.today()
        count = 0
        cost_pool = list(COST_ENTRY_DATA)
        random.shuffle(cost_pool)

        for project in projects:
            project_phases = phases_map.get(project.id, [])
            active_phases = [p for p in project_phases if p.status in ("completed", "in_progress")]
            if not active_phases:
                continue

            # Assign 4-8 cost entries per project
            num_entries = random.randint(4, 8)
            for _ in range(num_entries):
                if not cost_pool:
                    cost_pool = list(COST_ENTRY_DATA)
                    random.shuffle(cost_pool)

                desc, category, vendor, base_amount = cost_pool.pop(0)
                phase = random.choice(active_phases)
                cost_date = (phase.actual_start_date or phase.planned_start_date or today) + timedelta(
                    days=random.randint(0, 90)
                )
                # Scale amount by project budget relative to baseline 5B
                scale = float(project.budget or 5000000000) / 5000000000
                amount = Decimal(str(int(base_amount * scale * random.uniform(0.8, 1.2))))
                ref = f"INV-{project.id:02d}-{count+1:04d}"

                ProjectCostEntry.objects.get_or_create(
                    organization=org,
                    phase=phase,
                    description=f"{DEMO_MARKER} {desc}",
                    defaults={
                        "amount": amount,
                        "date": cost_date,
                        "category": category,
                        "vendor": vendor,
                        "reference_number": ref,
                    },
                )
                count += 1

        self.stdout.write(f"  {count} cost entries ready.")

    # ----- Risk Register -----

    def _seed_risks(self, org, projects):
        today = date.today()
        count = 0
        risk_pool = list(RISK_DATA)
        random.shuffle(risk_pool)

        for project in projects:
            num_risks = random.randint(2, 4)
            for _ in range(num_risks):
                if not risk_pool:
                    risk_pool = list(RISK_DATA)
                    random.shuffle(risk_pool)

                r = risk_pool.pop(0)

                # Determine status
                if project.status == "completed":
                    status = random.choice(["mitigated", "closed", "accepted"])
                    resolved = today - timedelta(days=random.randint(30, 180))
                elif project.status == "on_hold":
                    status = random.choice(["open", "in_progress"])
                    resolved = None
                else:
                    status = random.choice(["open", "open", "in_progress", "mitigated"])
                    resolved = today - timedelta(days=random.randint(5, 30)) if status == "mitigated" else None

                identified = today - timedelta(days=random.randint(30, 365))

                ProjectRiskRegisterEntry.objects.get_or_create(
                    organization=org,
                    project=project,
                    title=r["title"],
                    defaults={
                        "description": f"{DEMO_MARKER} {r['description']}",
                        "severity": r["severity"],
                        "likelihood_key": r["likelihood_key"],
                        "likelihood_score": r["likelihood_score"],
                        "impact_key": r["impact_key"],
                        "impact_score": r["impact_score"],
                        "risk_score": r["risk_score"],
                        "status": status,
                        "treatment": r["treatment"],
                        "mitigation_plan": r["mitigation_plan"],
                        "identified_on": identified,
                        "resolved_on": resolved,
                        "target_resolution_date": identified + timedelta(days=random.randint(30, 120)),
                        "last_reviewed_on": today - timedelta(days=random.randint(1, 30)),
                    },
                )
                count += 1

        self.stdout.write(f"  {count} risk register entries ready.")

    # ----- Variation Orders -----

    def _seed_variation_orders(self, org, projects):
        today = date.today()
        count = 0
        vo_pool = list(VARIATION_ORDER_DATA)
        random.shuffle(vo_pool)

        existing_vo_nums = set(
            ProjectVariationOrder.objects.values_list("variation_number", flat=True)
        )

        for project in projects:
            if project.status == "planning":
                continue

            num_vos = random.randint(1, 2)
            for _ in range(num_vos):
                if not vo_pool:
                    vo_pool = list(VARIATION_ORDER_DATA)
                    random.shuffle(vo_pool)

                v = vo_pool.pop(0)
                vo_num = f"VO-{org.id:02d}-{project.id:03d}-{count+1:03d}"
                while vo_num in existing_vo_nums:
                    count += 1
                    vo_num = f"VO-{org.id:02d}-{project.id:03d}-{count+1:03d}"

                requested = today - timedelta(days=random.randint(14, 180))
                due = requested + timedelta(days=random.randint(14, 60))

                ProjectVariationOrder.objects.get_or_create(
                    organization=org,
                    project=project,
                    variation_number=vo_num,
                    defaults={
                        "title": v["title"],
                        "change_summary": f"{DEMO_MARKER} {v['change_summary']}",
                        "reason": v["reason"],
                        "status": v["status"],
                        "contract_value": v["contract_value"],
                        "requested_date": requested,
                        "due_date": due,
                    },
                )
                existing_vo_nums.add(vo_num)
                count += 1

        self.stdout.write(f"  {count} variation orders ready.")

    # ----- Workforce Logs -----

    def _seed_workforce_logs(self, org, projects):
        today = date.today()
        count = 0

        active_projects = [p for p in projects if p.status in ("in_progress", "completed")]

        for project in active_projects:
            num_logs = random.randint(4, 6)
            used_dates = set()

            for i in range(num_logs):
                log_date = today - timedelta(days=i + random.randint(0, 3))
                if project.status == "completed":
                    log_date = (project.actual_end_date or today) - timedelta(days=i * 2 + random.randint(0, 5))

                # Avoid duplicate (project, date, shift)
                while log_date in used_dates:
                    log_date -= timedelta(days=1)
                used_dates.add(log_date)

                ProjectWorkforceLog.objects.get_or_create(
                    organization=org,
                    project=project,
                    report_date=log_date,
                    shift="day",
                    defaults={
                        "laborers_count": random.randint(15, 45),
                        "skilled_count": random.randint(8, 25),
                        "supervisors_count": random.randint(2, 6),
                        "subcontractors_count": random.randint(5, 20),
                        "equipment_operators_count": random.randint(2, 8),
                        "notes": f"{DEMO_MARKER} Daily workforce deployment log",
                    },
                )
                count += 1

        self.stdout.write(f"  {count} workforce logs ready.")

    # ----- Daily Site Reports -----

    def _seed_daily_site_reports(self, org, projects):
        today = date.today()
        count = 0

        active_projects = [p for p in projects if p.status in ("in_progress", "completed")]
        weather_choices = ["clear", "clear", "clear", "cloudy", "cloudy", "rain"]

        work_completed_samples = [
            "Completed block work on Level 3 east wing. Poured column bases C12-C16.",
            "Installed electrical conduits on Level 2. Completed plumbing rough-in for units 201-204.",
            "Steel reinforcement placed for Level 4 slab. Formwork 80% complete.",
            "External plastering completed on south facade. Scaffolding partially struck.",
            "MEP duct installation on Level 5. Fire detection wiring 60% complete.",
            "Asphalt wearing course laid on Section A (KM 0+000 to KM 1+500).",
            "Foundation raft pour completed — 450m³ concrete placed in continuous pour.",
            "Curtain wall panel installation — Levels 1-3 complete. Level 4 in progress.",
            "Elevator guide rails installed in Shaft A. Car assembly started in Shaft B.",
            "Landscape grading and topsoil spreading. Irrigation pipe laying 50% complete.",
            "Roof waterproofing membrane applied. Screed pour for terraces in progress.",
            "Generator room block work and slab. Transformer pad foundation completed.",
        ]

        planned_next_samples = [
            "Continue block work Level 4. Begin roof slab reinforcement.",
            "Complete plumbing rough-in. Start tiling on Level 1.",
            "Cast Level 4 slab. Strike formwork Level 3.",
            "Begin internal plastering. Install window frames south wing.",
            "Continue MEP installation. Begin fire suppression piping.",
            "Lay sub-base on Section B. Begin drainage culvert works.",
            "Begin column casting from foundation raft. Set out ground floor walls.",
            "Continue curtain wall Level 4-5. Begin internal glazing Level 1.",
            "Complete elevator installation Shaft A. Begin Shaft B car assembly.",
            "Continue landscape planting. Install perimeter fence Section C.",
            "Apply final roof coating. Begin terrace tiling.",
            "Complete generator room. Begin cable tray installation.",
        ]

        for project in active_projects:
            num_reports = random.randint(3, 5)
            used_dates = set()

            for i in range(num_reports):
                report_date = today - timedelta(days=i + random.randint(0, 2))
                if project.status == "completed":
                    report_date = (project.actual_end_date or today) - timedelta(days=i * 2 + random.randint(0, 3))

                while report_date in used_dates:
                    report_date -= timedelta(days=1)
                used_dates.add(report_date)

                weather = random.choice(weather_choices)
                weather_delay = Decimal(str(random.choice([0, 0, 0, 0, 1.5, 2.0, 3.5]))) if weather == "rain" else Decimal("0.00")

                statuses = ["submitted", "submitted", "reviewed", "draft"]

                ProjectDailySiteReport.objects.get_or_create(
                    organization=org,
                    project=project,
                    report_date=report_date,
                    shift="day",
                    defaults={
                        "weather": weather,
                        "weather_notes": f"{'Light showers in afternoon' if weather == 'rain' else 'Good working conditions'}",
                        "weather_delay_hours": weather_delay,
                        "progress_percent": Decimal(str(round(random.uniform(0.5, 3.0), 2))),
                        "workforce_summary": f"Total crew: {random.randint(30, 80)} workers on site",
                        "work_completed": f"{DEMO_MARKER} {random.choice(work_completed_samples)}",
                        "planned_next_day": random.choice(planned_next_samples),
                        "safety_observations": "All workers in PPE. Toolbox talk conducted at 7:00 AM.",
                        "quality_observations": "Concrete cube samples taken for testing. Slump test passed.",
                        "status": random.choice(statuses),
                    },
                )
                count += 1

        self.stdout.write(f"  {count} daily site reports ready.")

    # ----- Field Escalations -----

    def _seed_escalations(self, org, projects):
        today = date.today()
        count = 0
        esc_pool = list(ESCALATION_DATA)
        random.shuffle(esc_pool)

        active_projects = [p for p in projects if p.status in ("in_progress", "on_hold", "completed")]

        for project in active_projects:
            num_esc = random.randint(1, 3)
            for _ in range(num_esc):
                if not esc_pool:
                    esc_pool = list(ESCALATION_DATA)
                    random.shuffle(esc_pool)

                e = esc_pool.pop(0)
                issue_date = today - timedelta(days=random.randint(5, 120))

                if e["status"] in ("resolved", "closed"):
                    resolved_at = tz.now() - timedelta(days=random.randint(1, 30))
                    resolution = "Issue resolved through corrective action and management intervention."
                else:
                    resolved_at = None
                    resolution = ""

                weather_cond = "rain" if e["issue_category"] == "weather" else ""
                weather_delay = (
                    Decimal(str(random.choice([4.0, 6.0, 8.0, 12.0])))
                    if e["issue_category"] == "weather"
                    else Decimal("0.00")
                )

                ProjectFieldEscalation.objects.get_or_create(
                    organization=org,
                    project=project,
                    title=e["title"],
                    defaults={
                        "description": f"{DEMO_MARKER} {e['title']}",
                        "issue_date": issue_date,
                        "issue_category": e["issue_category"],
                        "issue_type": e["issue_type"],
                        "severity": e["severity"],
                        "status": e["status"],
                        "location": e["location"],
                        "weather_condition": weather_cond,
                        "weather_delay_hours": weather_delay,
                        "estimated_schedule_impact_days": Decimal(str(random.randint(1, 7))),
                        "estimated_cost_impact": Decimal(str(random.randint(500000, 5000000))),
                        "impact_summary": e["impact_summary"],
                        "root_cause": e["root_cause"],
                        "immediate_action": e["immediate_action"],
                        "owner_name": random.choice(NIGERIAN_SITE_ENGINEERS),
                        "due_date": issue_date + timedelta(days=random.randint(3, 14)),
                        "resolved_at": resolved_at,
                        "resolution_notes": resolution,
                    },
                )
                count += 1

        self.stdout.write(f"  {count} field escalations ready.")

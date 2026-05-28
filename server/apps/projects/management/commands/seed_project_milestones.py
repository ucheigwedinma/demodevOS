"""
Seed the 12 standard construction milestone templates.

Usage:
    python manage.py seed_project_milestones
    python manage.py seed_project_milestones --flush
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.settings.models import MilestoneTemplate

MILESTONE_TEMPLATES = [
    # ── 0  Pre-Construction ──────────────────────────────────────────────
    {
        "name": "Site clearance complete",
        "description": "All vegetation, debris, and obstructions removed; site levelled and ready for setting out. Geotechnical survey results confirmed.",
        "phase_sort_order": 0,
        "reference_code": "MS-001",
        "typical_offset_days": 14,
        "success_criteria": [
            {"criterion": "Site fully cleared and levelled to formation", "verification_method": "Site inspection report signed by project manager"},
            {"criterion": "Geotechnical survey results reviewed and approved", "verification_method": "Geotechnical report sign-off by structural engineer"},
        ],
        "key_deliverables": [
            {"name": "Site clearance completion report", "description": "Photographic evidence and surveyor confirmation of cleared site", "is_mandatory": True},
            {"name": "Geotechnical survey report", "description": "Bearing capacity and soil classification results", "is_mandatory": True},
        ],
        "predecessors": [],
        "successors": [
            {"milestone": "Piling works complete", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "owner_role": "Site Manager",
        "approver_role": "Project Manager",
        "stakeholders_to_notify": [
            {"role": "Client Representative", "notification_trigger": "on_completion"},
            {"role": "Structural Engineer", "notification_trigger": "on_completion"},
        ],
    },
    {
        "name": "Piling works complete",
        "description": "All load-bearing piles driven or bored to design depth. Pile integrity tests passed and as-built pile layout approved by structural engineer.",
        "phase_sort_order": 0,
        "reference_code": "MS-002",
        "typical_offset_days": 35,
        "success_criteria": [
            {"criterion": "All piles installed to design depth per structural drawings", "verification_method": "Pile installation log and depth records"},
            {"criterion": "Pile integrity tests (PIT) passed for 100% of piles", "verification_method": "PIT test certificates from specialist contractor"},
        ],
        "key_deliverables": [
            {"name": "Pile integrity test report", "description": "PIT results for all piles confirming structural adequacy", "is_mandatory": True},
            {"name": "As-built pile layout", "description": "Survey of actual pile positions vs design positions", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Site clearance complete", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"milestone": "Foundation slab poured", "dependency_type": "finish_to_start", "lag_days": 2},
        ],
        "owner_role": "Piling Contractor Lead",
        "approver_role": "Structural Engineer",
        "stakeholders_to_notify": [
            {"role": "Project Manager", "notification_trigger": "on_completion"},
            {"role": "Client Representative", "notification_trigger": "on_completion"},
        ],
    },
    # ── 1  Foundation & Substructure ─────────────────────────────────────
    {
        "name": "Foundation slab poured",
        "description": "Raft or strip foundations cast, cured to design strength, and waterproofing membrane applied. Foundation inspection certificate obtained.",
        "phase_sort_order": 1,
        "reference_code": "MS-003",
        "typical_offset_days": 21,
        "success_criteria": [
            {"criterion": "Concrete achieves minimum 28-day design strength", "verification_method": "Cube test results from accredited lab"},
            {"criterion": "Waterproofing membrane correctly applied with no defects", "verification_method": "Waterproofing inspection certificate"},
        ],
        "key_deliverables": [
            {"name": "Foundation inspection certificate", "description": "Local authority or building control sign-off on foundations", "is_mandatory": True},
            {"name": "Concrete cube test results", "description": "Lab-certified strength test results at 7 and 28 days", "is_mandatory": True},
            {"name": "Waterproofing warranty", "description": "Manufacturer warranty for applied membrane system", "is_mandatory": False},
        ],
        "predecessors": [
            {"milestone": "Piling works complete", "dependency_type": "finish_to_start", "lag_days": 2},
        ],
        "successors": [
            {"milestone": "Ground floor structural frame complete", "dependency_type": "finish_to_start", "lag_days": 7},
        ],
        "owner_role": "Concrete Foreman",
        "approver_role": "Structural Engineer",
        "stakeholders_to_notify": [
            {"role": "Building Control Inspector", "notification_trigger": "on_completion"},
            {"role": "Project Manager", "notification_trigger": "on_completion"},
        ],
    },
    {
        "name": "Ground floor structural frame complete",
        "description": "All ground-floor columns, beams, and slab erected per structural drawings. Alignment and level surveys verified by site engineer.",
        "phase_sort_order": 1,
        "reference_code": "MS-004",
        "typical_offset_days": 42,
        "success_criteria": [
            {"criterion": "All columns and beams erected per structural GA drawings", "verification_method": "Site engineer alignment and level survey report"},
            {"criterion": "Concrete strength verified for all poured elements", "verification_method": "Cube test results at 7 and 28 days"},
        ],
        "key_deliverables": [
            {"name": "Structural frame survey report", "description": "As-built survey confirming alignment, level, and plumb of all elements", "is_mandatory": True},
            {"name": "Concrete test certificates", "description": "Cube test results confirming design strength achieved", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Foundation slab poured", "dependency_type": "finish_to_start", "lag_days": 7},
        ],
        "successors": [
            {"milestone": "Roof slab cast", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "owner_role": "Structural Engineer",
        "approver_role": "Project Manager",
        "stakeholders_to_notify": [
            {"role": "Client Representative", "notification_trigger": "on_completion"},
            {"role": "Architect", "notification_trigger": "on_completion"},
        ],
    },
    # ── 2  Superstructure ────────────────────────────────────────────────
    {
        "name": "Roof slab cast",
        "description": "Final roof-level slab poured and cured. Temporary props scheduled for striking after 28-day strength test confirmation.",
        "phase_sort_order": 2,
        "reference_code": "MS-005",
        "typical_offset_days": 30,
        "success_criteria": [
            {"criterion": "Roof slab poured to specification and levels", "verification_method": "Site engineer level survey and pour records"},
            {"criterion": "28-day cube test confirms design strength", "verification_method": "Lab-certified cube test results"},
        ],
        "key_deliverables": [
            {"name": "Roof slab pour record", "description": "Concrete delivery tickets, pour sequence, and vibration records", "is_mandatory": True},
            {"name": "Temporary works striking schedule", "description": "Programme for prop removal after strength confirmation", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Ground floor structural frame complete", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"milestone": "Building envelope watertight", "dependency_type": "finish_to_start", "lag_days": 14},
        ],
        "owner_role": "Concrete Foreman",
        "approver_role": "Structural Engineer",
        "stakeholders_to_notify": [
            {"role": "Temporary Works Coordinator", "notification_trigger": "on_completion"},
            {"role": "Project Manager", "notification_trigger": "on_completion"},
        ],
    },
    {
        "name": "Building envelope watertight",
        "description": "External walls, cladding, glazing, and roof covering installed. Building is weather-tight; internal trades can commence without weather risk.",
        "phase_sort_order": 2,
        "reference_code": "MS-006",
        "typical_offset_days": 60,
        "success_criteria": [
            {"criterion": "All external openings fitted with glazing or permanent closures", "verification_method": "Visual inspection and weather-tightness test report"},
            {"criterion": "Roof covering installed with no reported leaks after 48-hour rain test", "verification_method": "Roof inspection certificate and leak test results"},
        ],
        "key_deliverables": [
            {"name": "Weather-tightness certificate", "description": "Confirmation that building is sealed against weather ingress", "is_mandatory": True},
            {"name": "Cladding installation sign-off", "description": "Cladding contractor completion certificate with warranty", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Roof slab cast", "dependency_type": "finish_to_start", "lag_days": 14},
        ],
        "successors": [
            {"milestone": "MEP rough-in signed off", "dependency_type": "finish_to_start", "lag_days": 0},
            {"milestone": "Internal partitions complete", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "owner_role": "Envelope Subcontractor Lead",
        "approver_role": "Project Manager",
        "stakeholders_to_notify": [
            {"role": "MEP Coordinator", "notification_trigger": "on_completion"},
            {"role": "Client Representative", "notification_trigger": "on_completion"},
        ],
    },
    # ── 3  Building Envelope / Enclosure ─────────────────────────────────
    {
        "name": "MEP rough-in signed off",
        "description": "First-fix mechanical, electrical, and plumbing installations complete. Pressure tests, continuity checks, and conduit inspections passed.",
        "phase_sort_order": 3,
        "reference_code": "MS-007",
        "typical_offset_days": 30,
        "success_criteria": [
            {"criterion": "Plumbing pressure tested to 1.5x working pressure for 30 mins with no drop", "verification_method": "Pressure test certificate signed by plumbing lead"},
            {"criterion": "Electrical continuity and insulation resistance tests passed", "verification_method": "Electrical test certificates per BS 7671"},
            {"criterion": "HVAC ductwork installed and leak-tested", "verification_method": "Ductwork pressure test results"},
        ],
        "key_deliverables": [
            {"name": "MEP first-fix completion report", "description": "Combined sign-off from mechanical, electrical, and plumbing leads", "is_mandatory": True},
            {"name": "Pressure test certificates", "description": "Individual test results for plumbing, HVAC, and fire suppression systems", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Building envelope watertight", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"milestone": "Internal partitions complete", "dependency_type": "start_to_start", "lag_days": 7},
        ],
        "owner_role": "MEP Coordinator",
        "approver_role": "Project Manager",
        "stakeholders_to_notify": [
            {"role": "Building Control Inspector", "notification_trigger": "on_completion"},
            {"role": "Fire Safety Officer", "notification_trigger": "on_completion"},
        ],
    },
    # ── 4  Interior Fit-Out ──────────────────────────────────────────────
    {
        "name": "Internal partitions complete",
        "description": "All internal block, stud, and drywall partitions erected, taped, and skimmed. Door frames fitted and ready for second-fix trades.",
        "phase_sort_order": 4,
        "reference_code": "MS-008",
        "typical_offset_days": 21,
        "success_criteria": [
            {"criterion": "All partitions erected per architectural layout drawings", "verification_method": "Architect inspection and sign-off"},
            {"criterion": "Door frames installed plumb and level, ready for hanging", "verification_method": "Joinery lead inspection report"},
        ],
        "key_deliverables": [
            {"name": "Partition completion report", "description": "Room-by-room checklist confirming all partitions erected and finished", "is_mandatory": True},
            {"name": "Door frame schedule sign-off", "description": "Confirmation all frames installed per door schedule", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Building envelope watertight", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"milestone": "Final fit-out inspection", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "owner_role": "Finishing Foreman",
        "approver_role": "Architect",
        "stakeholders_to_notify": [
            {"role": "MEP Coordinator", "notification_trigger": "on_completion"},
            {"role": "Project Manager", "notification_trigger": "on_completion"},
        ],
    },
    # ── 5  Finishing & Services ───────────────────────────────────────────
    {
        "name": "Final fit-out inspection",
        "description": "Flooring, painting, joinery, sanitary ware, and kitchen fit-out inspected. Snagging list compiled and items under rectification.",
        "phase_sort_order": 5,
        "reference_code": "MS-009",
        "typical_offset_days": 28,
        "success_criteria": [
            {"criterion": "All finish trades complete per specification", "verification_method": "Room-by-room snagging inspection by QA manager"},
            {"criterion": "Snagging list compiled with fewer than 5 Category A defects per unit", "verification_method": "Snagging report with defect categorisation"},
        ],
        "key_deliverables": [
            {"name": "Snagging report", "description": "Comprehensive defect list categorised by severity and assigned to responsible subcontractors", "is_mandatory": True},
            {"name": "Fit-out completion photographs", "description": "Photographic record of each room and common area", "is_mandatory": False},
        ],
        "predecessors": [
            {"milestone": "Internal partitions complete", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"milestone": "Practical completion certificate issued", "dependency_type": "finish_to_start", "lag_days": 7},
        ],
        "owner_role": "QA Manager",
        "approver_role": "Project Manager",
        "stakeholders_to_notify": [
            {"role": "Client Representative", "notification_trigger": "on_completion"},
            {"role": "Architect", "notification_trigger": "on_completion"},
        ],
    },
    # ── 6  Handover & Close-out ──────────────────────────────────────────
    {
        "name": "Practical completion certificate issued",
        "description": "Building substantially complete per contract specification. Practical Completion Certificate signed by contract administrator; defects liability period begins.",
        "phase_sort_order": 6,
        "reference_code": "MS-010",
        "typical_offset_days": 7,
        "success_criteria": [
            {"criterion": "All Category A snagging items rectified", "verification_method": "Snag reinspection report with zero Category A items"},
            {"criterion": "All statutory inspections and certificates obtained", "verification_method": "Compliance certificate bundle (fire, electrical, gas, lift)"},
            {"criterion": "O&M manuals and as-built drawings submitted", "verification_method": "Document transmittal receipt signed by client"},
        ],
        "key_deliverables": [
            {"name": "Practical Completion Certificate", "description": "Formal certificate signed by contract administrator", "is_mandatory": True},
            {"name": "Compliance certificate bundle", "description": "Fire, electrical, gas safety, and lift certificates", "is_mandatory": True},
            {"name": "O&M manuals and as-built drawings", "description": "Full set of operation manuals, maintenance schedules, and as-built documentation", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Final fit-out inspection", "dependency_type": "finish_to_start", "lag_days": 7},
        ],
        "successors": [
            {"milestone": "Defects liability period start", "dependency_type": "finish_to_start", "lag_days": 0},
            {"milestone": "Client handover", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "owner_role": "Project Manager",
        "approver_role": "Contract Administrator",
        "stakeholders_to_notify": [
            {"role": "Client Representative", "notification_trigger": "on_completion"},
            {"role": "Quantity Surveyor", "notification_trigger": "on_completion"},
            {"role": "All Subcontractors", "notification_trigger": "on_completion"},
        ],
    },
    {
        "name": "Defects liability period start",
        "description": "12-month defects liability period commenced. Contractor obligated to remedy any defects reported during this window at own cost.",
        "phase_sort_order": 6,
        "reference_code": "MS-011",
        "typical_offset_days": 0,
        "success_criteria": [
            {"criterion": "Defect reporting mechanism established and communicated to client", "verification_method": "Client acknowledgement of defect reporting procedure"},
            {"criterion": "Retention sum terms confirmed with quantity surveyor", "verification_method": "Retention schedule signed by both parties"},
        ],
        "key_deliverables": [
            {"name": "Defect reporting procedure", "description": "Document outlining how client reports defects and expected response times", "is_mandatory": True},
            {"name": "Retention schedule", "description": "Financial retention terms and release milestones", "is_mandatory": True},
        ],
        "predecessors": [
            {"milestone": "Practical completion certificate issued", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [],
        "owner_role": "Project Manager",
        "approver_role": "Contract Administrator",
        "stakeholders_to_notify": [
            {"role": "Client Representative", "notification_trigger": "on_completion"},
            {"role": "Quantity Surveyor", "notification_trigger": "on_completion"},
        ],
    },
    {
        "name": "Client handover",
        "description": "Keys, O&M manuals, as-built drawings, warranties, and compliance certificates handed to client. Building officially in client's possession.",
        "phase_sort_order": 6,
        "reference_code": "MS-012",
        "typical_offset_days": 1,
        "success_criteria": [
            {"criterion": "All keys handed over and inventoried", "verification_method": "Key schedule signed by client representative"},
            {"criterion": "Client acknowledges receipt of all documentation", "verification_method": "Signed handover receipt form"},
            {"criterion": "Building security systems commissioned and codes transferred", "verification_method": "Security system commissioning certificate"},
        ],
        "key_deliverables": [
            {"name": "Handover certificate", "description": "Formal document transferring building possession to client", "is_mandatory": True},
            {"name": "Key schedule", "description": "Inventory of all keys, access cards, and security codes", "is_mandatory": True},
            {"name": "Warranty bundle", "description": "Compiled warranties from all subcontractors and product manufacturers", "is_mandatory": True},
            {"name": "Building user guide", "description": "Simplified guide for day-to-day building operation and emergency procedures", "is_mandatory": False},
        ],
        "predecessors": [
            {"milestone": "Practical completion certificate issued", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [],
        "owner_role": "Project Manager",
        "approver_role": "Client Representative",
        "stakeholders_to_notify": [
            {"role": "Facilities Manager", "notification_trigger": "on_completion"},
            {"role": "Contract Administrator", "notification_trigger": "on_completion"},
            {"role": "Insurance Provider", "notification_trigger": "on_completion"},
        ],
    },
]


class Command(BaseCommand):
    help = "Seed 12 standard construction milestone templates. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete all milestone templates before re-seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = MilestoneTemplate.objects.all().delete()
            self.stdout.write(f"Flushed {deleted} milestone templates.")

        created = 0
        for idx, tmpl in enumerate(MILESTONE_TEMPLATES):
            _, was_created = MilestoneTemplate.objects.update_or_create(
                name=tmpl["name"],
                defaults={
                    "description": tmpl["description"],
                    "sort_order": idx,
                    "phase_sort_order": tmpl["phase_sort_order"],
                    "reference_code": tmpl.get("reference_code", ""),
                    "typical_offset_days": tmpl.get("typical_offset_days"),
                    "success_criteria": tmpl.get("success_criteria", []),
                    "key_deliverables": tmpl.get("key_deliverables", []),
                    "predecessors": tmpl.get("predecessors", []),
                    "successors": tmpl.get("successors", []),
                    "owner_role": tmpl.get("owner_role", ""),
                    "approver_role": tmpl.get("approver_role", ""),
                    "stakeholders_to_notify": tmpl.get("stakeholders_to_notify", []),
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Milestone templates: {created} created, {len(MILESTONE_TEMPLATES) - created} updated.")
        )

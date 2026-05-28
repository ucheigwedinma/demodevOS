"""
Seed the 15 standard construction task templates.

Usage:
    python manage.py seed_project_tasks
    python manage.py seed_project_tasks --flush
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.settings.models import TaskTemplate

TASK_TEMPLATES = [
    # ── 0  Pre-Construction ──────────────────────────────────────────────
    {
        "name": "Mobilise site team and secure perimeter",
        "description": "Deploy site manager and crew; erect hoarding, signage, and temporary fencing. Establish welfare facilities, site office, and material laydown areas.",
        "assigned_role": "Site Manager",
        "priority": "high",
        "phase_sort_order": 0,
        "reference_code": "TASK-001",
        "reviewer_role": "Project Manager",
        "collaborators": [
            {"role": "Health & Safety Officer", "responsibility": "Approve site welfare and safety plan"},
            {"role": "Security Contractor", "responsibility": "Install perimeter fencing and CCTV"},
        ],
        "estimated_effort_hours": 40,
        "predecessors": [],
        "successors": [
            {"task": "Survey and set out foundation grid lines", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "definition_of_done": [
            {"criterion": "Hoarding erected around full site perimeter", "is_required": True},
            {"criterion": "Welfare facilities operational (toilets, drying room, canteen)", "is_required": True},
            {"criterion": "Site office set up with power and internet", "is_required": True},
            {"criterion": "H&S file opened and site induction materials posted", "is_required": False},
        ],
        "tools_required": [
            {"name": "Hoarding panels and fixings", "description": "Timber or steel hoarding system for site perimeter"},
            {"name": "Welfare cabin", "description": "Portable cabin with toilet, kitchen, and drying facilities"},
        ],
        "reference_links": [
            {"title": "CDM Regulations 2015 guidance", "url": "https://www.hse.gov.uk/construction/cdm/2015/"},
        ],
    },
    {
        "name": "Survey and set out foundation grid lines",
        "description": "Conduct topographic survey and transfer design grid to site using total station. Install permanent benchmarks and reference pegs for all trades.",
        "assigned_role": "Land Surveyor",
        "priority": "high",
        "phase_sort_order": 0,
        "reference_code": "TASK-002",
        "reviewer_role": "Structural Engineer",
        "collaborators": [
            {"role": "Site Engineer", "responsibility": "Verify grid line positions against structural drawings"},
        ],
        "estimated_effort_hours": 24,
        "predecessors": [
            {"task": "Mobilise site team and secure perimeter", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"task": "Excavate to formation level", "dependency_type": "finish_to_start", "lag_days": 1},
        ],
        "definition_of_done": [
            {"criterion": "All grid lines set out and marked with permanent pegs", "is_required": True},
            {"criterion": "Benchmark installed and coordinates recorded", "is_required": True},
            {"criterion": "Setting-out report signed by site engineer", "is_required": True},
        ],
        "tools_required": [
            {"name": "Total station", "description": "Electronic surveying instrument for angular and distance measurement"},
            {"name": "GPS rover", "description": "GNSS receiver for position verification"},
        ],
        "reference_links": [],
    },
    # ── 1  Foundation & Substructure ─────────────────────────────────────
    {
        "name": "Excavate to formation level",
        "description": "Bulk excavation to designed formation level. Dispose of spoil off-site or stockpile for backfill. Confirm bearing capacity with plate load tests.",
        "assigned_role": "Earthworks Foreman",
        "priority": "high",
        "phase_sort_order": 1,
        "reference_code": "TASK-003",
        "reviewer_role": "Geotechnical Engineer",
        "collaborators": [
            {"role": "Plant Operator", "responsibility": "Operate excavator and dumper trucks"},
            {"role": "Banksman", "responsibility": "Guide plant movements and ensure safety"},
        ],
        "estimated_effort_hours": 80,
        "predecessors": [
            {"task": "Survey and set out foundation grid lines", "dependency_type": "finish_to_start", "lag_days": 1},
        ],
        "successors": [
            {"task": "Install reinforcement cages for pile caps", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "definition_of_done": [
            {"criterion": "Excavation to correct formation level confirmed by survey", "is_required": True},
            {"criterion": "Plate load test results meet minimum bearing capacity", "is_required": True},
            {"criterion": "Spoil disposed or stockpiled per waste management plan", "is_required": True},
        ],
        "tools_required": [
            {"name": "Tracked excavator (20T+)", "description": "Main excavation plant"},
            {"name": "Plate load test kit", "description": "Equipment for in-situ bearing capacity testing"},
        ],
        "reference_links": [],
    },
    {
        "name": "Install reinforcement cages for pile caps",
        "description": "Cut, bend, and fix steel reinforcement cages per structural schedule. Ensure correct cover, lap lengths, and spacer placement before concrete pour.",
        "assigned_role": "Steel Fixer Lead",
        "priority": "critical",
        "phase_sort_order": 1,
        "reference_code": "TASK-004",
        "reviewer_role": "Structural Engineer",
        "collaborators": [
            {"role": "Steel Fixers (x4)", "responsibility": "Cut, bend, and tie reinforcement bars"},
        ],
        "estimated_effort_hours": 120,
        "predecessors": [
            {"task": "Excavate to formation level", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [
            {"task": "Pour and cure ground floor slab", "dependency_type": "finish_to_start", "lag_days": 1},
        ],
        "definition_of_done": [
            {"criterion": "All cages fabricated per bar bending schedule", "is_required": True},
            {"criterion": "Correct cover maintained with spacers", "is_required": True},
            {"criterion": "Lap lengths comply with structural specification", "is_required": True},
            {"criterion": "Reinforcement inspection signed off before pour", "is_required": True},
        ],
        "tools_required": [
            {"name": "Bar bending machine", "description": "Hydraulic rebar bending equipment"},
            {"name": "Bar cutting machine", "description": "Rebar cutting shears"},
            {"name": "Cover spacers", "description": "Plastic/concrete spacers for maintaining cover"},
        ],
        "reference_links": [],
    },
    {
        "name": "Pour and cure ground floor slab",
        "description": "Place ready-mix concrete to ground floor slab specification. Vibrate, level, and power-float finish. Maintain wet curing for minimum 7 days.",
        "assigned_role": "Concrete Foreman",
        "priority": "critical",
        "phase_sort_order": 1,
        "reference_code": "TASK-005",
        "reviewer_role": "Structural Engineer",
        "collaborators": [
            {"role": "Concrete Gang (x6)", "responsibility": "Place, vibrate, and finish concrete"},
            {"role": "Ready-Mix Supplier", "responsibility": "Deliver concrete to site per call-off schedule"},
        ],
        "estimated_effort_hours": 48,
        "predecessors": [
            {"task": "Install reinforcement cages for pile caps", "dependency_type": "finish_to_start", "lag_days": 1},
        ],
        "successors": [
            {"task": "Erect structural columns to first floor", "dependency_type": "finish_to_start", "lag_days": 7},
        ],
        "definition_of_done": [
            {"criterion": "Concrete placed to correct levels and specification", "is_required": True},
            {"criterion": "Power-float finish achieved to flatness tolerance", "is_required": True},
            {"criterion": "Wet curing maintained for minimum 7 days", "is_required": True},
            {"criterion": "Cube samples taken and sent to lab", "is_required": True},
        ],
        "tools_required": [
            {"name": "Concrete pump", "description": "Boom pump for placing concrete"},
            {"name": "Poker vibrator", "description": "Internal vibrator for compaction"},
            {"name": "Power float", "description": "Ride-on or walk-behind power trowel"},
        ],
        "reference_links": [],
    },
    # ── 2  Superstructure ────────────────────────────────────────────────
    {
        "name": "Erect structural columns to first floor",
        "description": "Lift and fix precast or in-situ RC columns to first-floor level. Check verticality with plumb bob and optical level. Grout base plates where applicable.",
        "assigned_role": "Structural Engineer",
        "priority": "critical",
        "phase_sort_order": 2,
        "reference_code": "TASK-006",
        "reviewer_role": "Project Manager",
        "collaborators": [
            {"role": "Crane Operator", "responsibility": "Lift and position precast columns"},
            {"role": "Steel Fixers", "responsibility": "Fix in-situ column reinforcement"},
        ],
        "estimated_effort_hours": 96,
        "predecessors": [
            {"task": "Pour and cure ground floor slab", "dependency_type": "finish_to_start", "lag_days": 7},
        ],
        "successors": [
            {"task": "Install formwork for upper floor slabs", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "definition_of_done": [
            {"criterion": "All columns erected to correct position and height", "is_required": True},
            {"criterion": "Verticality within tolerance (1:500)", "is_required": True},
            {"criterion": "Base plates grouted and cured", "is_required": True},
        ],
        "tools_required": [
            {"name": "Tower crane", "description": "Main lifting equipment for column placement"},
            {"name": "Optical level", "description": "For verticality and alignment checks"},
        ],
        "reference_links": [],
    },
    {
        "name": "Install formwork for upper floor slabs",
        "description": "Erect proprietary table-form or traditional plywood formwork for upper-floor slabs. Ensure propping design checked by temporary-works coordinator.",
        "assigned_role": "Carpentry Foreman",
        "priority": "high",
        "phase_sort_order": 2,
        "reference_code": "TASK-007",
        "reviewer_role": "Temporary Works Coordinator",
        "collaborators": [
            {"role": "Carpenters (x4)", "responsibility": "Erect and strike formwork"},
        ],
        "estimated_effort_hours": 64,
        "predecessors": [
            {"task": "Erect structural columns to first floor", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [],
        "definition_of_done": [
            {"criterion": "Formwork erected to correct levels and dimensions", "is_required": True},
            {"criterion": "Propping design approved by temporary-works coordinator", "is_required": True},
            {"criterion": "Edge protection installed around open edges", "is_required": True},
        ],
        "tools_required": [
            {"name": "Table-form system", "description": "Proprietary aluminium formwork system"},
            {"name": "Acrow props", "description": "Adjustable steel props for slab support"},
        ],
        "reference_links": [],
    },
    # ── 3  Building Envelope / Enclosure ─────────────────────────────────
    {
        "name": "Lay external block walls and cavity insulation",
        "description": "Construct outer-leaf blockwork, install cavity insulation boards, and tie to inner leaf. Include cavity trays, weep holes, and DPC at required positions.",
        "assigned_role": "Masonry Foreman",
        "priority": "high",
        "phase_sort_order": 3,
        "reference_code": "TASK-008",
        "reviewer_role": "Architect",
        "collaborators": [
            {"role": "Bricklayers (x4)", "responsibility": "Lay blockwork and brickwork"},
            {"role": "Labourer", "responsibility": "Mix mortar and supply materials to bricklayers"},
        ],
        "estimated_effort_hours": 160,
        "predecessors": [],
        "successors": [
            {"task": "Fit window and door frames", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "definition_of_done": [
            {"criterion": "All external walls constructed to correct height and coursing", "is_required": True},
            {"criterion": "Cavity insulation installed with no gaps or compression", "is_required": True},
            {"criterion": "Wall ties, cavity trays, weep holes, and DPC correctly positioned", "is_required": True},
        ],
        "tools_required": [
            {"name": "Mortar mixer", "description": "Drum mixer for mortar preparation"},
            {"name": "Scaffold", "description": "External scaffolding for access above 2m"},
        ],
        "reference_links": [],
    },
    # ── 4  Interior Fit-Out ──────────────────────────────────────────────
    {
        "name": "Run first-fix electrical conduits and back-boxes",
        "description": "Route PVC conduits and trunking through walls and slabs per electrical layout. Fix back-boxes at specified heights. Pull draw wires for second-fix cabling.",
        "assigned_role": "Electrical Lead",
        "priority": "medium",
        "phase_sort_order": 4,
        "reference_code": "TASK-009",
        "reviewer_role": "MEP Coordinator",
        "collaborators": [
            {"role": "Electricians (x3)", "responsibility": "Install conduits, trunking, and back-boxes"},
        ],
        "estimated_effort_hours": 80,
        "predecessors": [],
        "successors": [],
        "definition_of_done": [
            {"criterion": "All conduits routed per approved electrical layout", "is_required": True},
            {"criterion": "Back-boxes fixed at specified heights (BS 7671)", "is_required": True},
            {"criterion": "Draw wires pulled through all conduits", "is_required": True},
            {"criterion": "Continuity test passed on all circuits", "is_required": False},
        ],
        "tools_required": [
            {"name": "PVC conduit bender", "description": "Spring bender for PVC conduit"},
            {"name": "SDS drill", "description": "Rotary hammer drill for masonry chasing"},
        ],
        "reference_links": [
            {"title": "BS 7671 Wiring Regulations", "url": "https://www.theiet.org/standards/bs-7671/"},
        ],
    },
    {
        "name": "Install first-fix plumbing and soil stacks",
        "description": "Fit hot/cold water pipes, soil and waste stacks, and above-ground drainage. Pressure test pipework to 1.5\u00d7 working pressure for 30 minutes.",
        "assigned_role": "Plumbing Lead",
        "priority": "medium",
        "phase_sort_order": 4,
        "reference_code": "TASK-010",
        "reviewer_role": "MEP Coordinator",
        "collaborators": [
            {"role": "Plumbers (x3)", "responsibility": "Install pipework and soil stacks"},
        ],
        "estimated_effort_hours": 80,
        "predecessors": [],
        "successors": [],
        "definition_of_done": [
            {"criterion": "All pipework installed per approved plumbing layout", "is_required": True},
            {"criterion": "Pressure test passed at 1.5x working pressure for 30 mins", "is_required": True},
            {"criterion": "Soil stacks installed with correct falls and connections", "is_required": True},
        ],
        "tools_required": [
            {"name": "Pipe press tool", "description": "Hydraulic press-fit tool for copper/plastic pipe"},
            {"name": "Pressure test pump", "description": "Manual or electric pump for hydrostatic testing"},
        ],
        "reference_links": [],
    },
    # ── 5  Finishing & Services ───────────────────────────────────────────
    {
        "name": "Fit window and door frames",
        "description": "Install aluminium or uPVC window frames and external door assemblies. Seal with expanding foam and silicone. Check operation and weather-tightness.",
        "assigned_role": "Joinery Lead",
        "priority": "medium",
        "phase_sort_order": 5,
        "reference_code": "TASK-011",
        "reviewer_role": "Architect",
        "collaborators": [
            {"role": "Joiners (x2)", "responsibility": "Install frames and check operation"},
        ],
        "estimated_effort_hours": 48,
        "predecessors": [
            {"task": "Lay external block walls and cavity insulation", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [],
        "definition_of_done": [
            {"criterion": "All frames installed plumb, level, and square", "is_required": True},
            {"criterion": "Foam and silicone seals applied with no gaps", "is_required": True},
            {"criterion": "All opening lights operate correctly and lock", "is_required": True},
        ],
        "tools_required": [
            {"name": "Expanding foam gun", "description": "Applicator for PU expanding foam"},
            {"name": "Silicone gun", "description": "Caulking gun for silicone sealant"},
        ],
        "reference_links": [],
    },
    {
        "name": "Apply screed to all floor areas",
        "description": "Lay sand-cement or liquid screed to required thickness and falls. Allow drying time per specification before tiling or flooring installation.",
        "assigned_role": "Finishing Foreman",
        "priority": "medium",
        "phase_sort_order": 5,
        "reference_code": "TASK-012",
        "reviewer_role": "Project Manager",
        "collaborators": [
            {"role": "Screed Gang (x3)", "responsibility": "Lay and level screed"},
        ],
        "estimated_effort_hours": 40,
        "predecessors": [],
        "successors": [
            {"task": "Paint internal walls and ceilings", "dependency_type": "start_to_start", "lag_days": 7},
        ],
        "definition_of_done": [
            {"criterion": "Screed laid to correct thickness and levels", "is_required": True},
            {"criterion": "Falls correct in wet areas (1:40 minimum)", "is_required": True},
            {"criterion": "Drying time observed per manufacturer specification", "is_required": True},
        ],
        "tools_required": [
            {"name": "Laser level", "description": "Rotary laser for setting screed levels"},
            {"name": "Screed pump", "description": "Pump for liquid screed application"},
        ],
        "reference_links": [],
    },
    {
        "name": "Paint internal walls and ceilings",
        "description": "Apply mist coat to new plaster, followed by two coats of emulsion to walls and ceilings. Use satinwood on woodwork. Protect floors and joinery.",
        "assigned_role": "Painting Contractor",
        "priority": "low",
        "phase_sort_order": 5,
        "reference_code": "TASK-013",
        "reviewer_role": "QA Manager",
        "collaborators": [
            {"role": "Painters (x4)", "responsibility": "Apply paint to walls, ceilings, and woodwork"},
        ],
        "estimated_effort_hours": 120,
        "predecessors": [
            {"task": "Apply screed to all floor areas", "dependency_type": "start_to_start", "lag_days": 7},
        ],
        "successors": [],
        "definition_of_done": [
            {"criterion": "Mist coat applied to all new plaster surfaces", "is_required": True},
            {"criterion": "Two full coats of emulsion applied with even coverage", "is_required": True},
            {"criterion": "Satinwood applied to all woodwork (two coats)", "is_required": True},
            {"criterion": "Floor and joinery protection maintained throughout", "is_required": False},
        ],
        "tools_required": [
            {"name": "Airless sprayer", "description": "For mist coat application to large areas"},
            {"name": "Roller kit and brushes", "description": "Standard painting equipment"},
        ],
        "reference_links": [],
    },
    # ── 6  Handover & Close-out ──────────────────────────────────────────
    {
        "name": "Commission fire alarm and sprinkler systems",
        "description": "Test all fire alarm call points, detectors, sounders, and panel. Witness sprinkler flow and pressure tests. Issue commissioning certificates.",
        "assigned_role": "Fire Safety Officer",
        "priority": "critical",
        "phase_sort_order": 6,
        "reference_code": "TASK-014",
        "reviewer_role": "Building Control Inspector",
        "collaborators": [
            {"role": "Fire Alarm Engineer", "responsibility": "Programme and test fire alarm panel and devices"},
            {"role": "Sprinkler Engineer", "responsibility": "Conduct flow and pressure tests"},
        ],
        "estimated_effort_hours": 32,
        "predecessors": [],
        "successors": [
            {"task": "Complete snagging list and final inspection", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "definition_of_done": [
            {"criterion": "All call points, detectors, and sounders tested and operational", "is_required": True},
            {"criterion": "Fire alarm panel programmed with correct zones", "is_required": True},
            {"criterion": "Sprinkler flow test passed", "is_required": True},
            {"criterion": "Commissioning certificates issued", "is_required": True},
        ],
        "tools_required": [
            {"name": "Call point test key", "description": "Key for activating manual call points"},
            {"name": "Smoke detector tester", "description": "Aerosol-based detector test device"},
        ],
        "reference_links": [
            {"title": "BS 5839-1 Fire detection and alarm systems", "url": "https://www.bsigroup.com/en-GB/bs-5839-1/"},
        ],
    },
    {
        "name": "Complete snagging list and final inspection",
        "description": "Walk every unit and common area to compile defect/snagging schedule. Categorise items by severity and assign to responsible subcontractors for rectification.",
        "assigned_role": "QA Manager",
        "priority": "high",
        "phase_sort_order": 6,
        "reference_code": "TASK-015",
        "reviewer_role": "Project Manager",
        "collaborators": [
            {"role": "Architect", "responsibility": "Review finish quality and specification compliance"},
            {"role": "Client Representative", "responsibility": "Attend final walkthrough"},
        ],
        "estimated_effort_hours": 40,
        "predecessors": [
            {"task": "Commission fire alarm and sprinkler systems", "dependency_type": "finish_to_start", "lag_days": 0},
        ],
        "successors": [],
        "definition_of_done": [
            {"criterion": "Every room and common area inspected", "is_required": True},
            {"criterion": "Snagging list compiled with severity categories", "is_required": True},
            {"criterion": "All items assigned to responsible subcontractors", "is_required": True},
            {"criterion": "Rectification deadline agreed with each subcontractor", "is_required": True},
        ],
        "tools_required": [
            {"name": "Snagging app/tablet", "description": "Digital tool for recording and photographing defects"},
            {"name": "Laser measure", "description": "For checking dimensions and tolerances"},
        ],
        "reference_links": [],
    },
]


class Command(BaseCommand):
    help = "Seed 15 standard construction task templates. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete all task templates before re-seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = TaskTemplate.objects.all().delete()
            self.stdout.write(f"Flushed {deleted} task templates.")

        created = 0
        for idx, tmpl in enumerate(TASK_TEMPLATES):
            _, was_created = TaskTemplate.objects.update_or_create(
                name=tmpl["name"],
                defaults={
                    "description": tmpl["description"],
                    "assigned_role": tmpl["assigned_role"],
                    "priority": tmpl["priority"],
                    "sort_order": idx,
                    "phase_sort_order": tmpl["phase_sort_order"],
                    "reference_code": tmpl.get("reference_code", ""),
                    "reviewer_role": tmpl.get("reviewer_role", ""),
                    "collaborators": tmpl.get("collaborators", []),
                    "estimated_effort_hours": tmpl.get("estimated_effort_hours"),
                    "predecessors": tmpl.get("predecessors", []),
                    "successors": tmpl.get("successors", []),
                    "definition_of_done": tmpl.get("definition_of_done", []),
                    "tools_required": tmpl.get("tools_required", []),
                    "reference_links": tmpl.get("reference_links", []),
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Task templates: {created} created, {len(TASK_TEMPLATES) - created} updated.")
        )

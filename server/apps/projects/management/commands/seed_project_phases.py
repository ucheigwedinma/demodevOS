"""
Seed the 7 standard construction phase templates with full 5-section data.

Usage:
    python manage.py seed_project_phases
    python manage.py seed_project_phases --flush
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.settings.models import PhaseTemplate

PHASE_TEMPLATES = [
    # ── 0  Pre-Construction ─────────────────────────────────────────────
    {
        "name": "Pre-Construction",
        "description": "Site surveys, soil tests, EIA, permits, and regulatory approvals.",
        "weight": 1,
        "budget_pct": "0.05",
        # Section A
        "objective": "Complete all preparatory studies, obtain regulatory approvals, and establish the project baseline before any physical construction begins.",
        "estimated_duration_days": 90,
        "phase_owner_role": "Project Manager",
        # Section B
        "raci_matrix": [
            {"task": "Topographical & boundary survey", "responsible": "Land Surveyor", "accountable": "Project Manager", "consulted": "Client", "informed": "Design Team"},
            {"task": "Geotechnical investigation", "responsible": "Geotechnical Consultant", "accountable": "Project Manager", "consulted": "Structural Engineer", "informed": "Client"},
            {"task": "Environmental Impact Assessment", "responsible": "Environmental Consultant", "accountable": "Project Manager", "consulted": "Regulatory Authority", "informed": "Client, Legal"},
            {"task": "Building permit application", "responsible": "Permits Coordinator", "accountable": "Project Manager", "consulted": "Legal Counsel", "informed": "Client"},
            {"task": "Utility survey & diversion plan", "responsible": "Site Engineer", "accountable": "Project Manager", "consulted": "Utility Providers", "informed": "Design Team"},
        ],
        "approval_authority": "Project Director or Client Representative must approve all regulatory submissions and EIA findings before proceeding to Foundation phase.",
        # Section C
        "key_tasks": [
            {"name": "Topographical survey", "description": "Complete land survey including contour mapping, boundary verification, and existing feature recording."},
            {"name": "Geotechnical investigation", "description": "Soil boring, SPT tests, and bearing capacity analysis at designated grid points."},
            {"name": "Environmental Impact Assessment", "description": "Full EIA study per local regulatory requirements, including public consultation where mandated."},
            {"name": "Building permit application", "description": "Prepare and submit all required permit documentation to the local planning authority."},
            {"name": "Utility mapping & diversion", "description": "Identify all existing underground utilities and agree diversion routes with providers."},
            {"name": "Design coordination review", "description": "Final review of architectural, structural, and MEP drawings for constructability and clash detection."},
        ],
        "deliverables": [
            {"name": "Site Survey Report", "description": "Topographical and boundary survey documentation with coordinates.", "is_mandatory": True},
            {"name": "Geotechnical Report", "description": "Soil investigation findings and foundation type recommendations.", "is_mandatory": True},
            {"name": "EIA Report & Approval", "description": "Environmental impact assessment with mitigation measures and regulatory approval letter.", "is_mandatory": True},
            {"name": "Building Permit", "description": "Approved building permit from local authority.", "is_mandatory": True},
            {"name": "Utility Survey Report", "description": "Mapping of existing underground services with agreed diversion plan.", "is_mandatory": False},
            {"name": "Design Coordination Report", "description": "Clash detection results and resolved coordination issues.", "is_mandatory": False},
        ],
        "out_of_scope": "Demolition of existing structures, detailed architectural design revisions, procurement of construction materials, and contractor mobilisation.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "Project Manager (full-time)", "quantity": "1"},
            {"type": "human", "description": "Site Engineer", "quantity": "1"},
            {"type": "human", "description": "Environmental Consultant (external)", "quantity": "1"},
            {"type": "human", "description": "Geotechnical Consultant (external)", "quantity": "1"},
            {"type": "human", "description": "Permits Coordinator", "quantity": "1"},
            {"type": "financial", "description": "Survey and testing budget", "quantity": "2-3% of project budget"},
            {"type": "technical", "description": "Total station and GPS survey equipment", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "Unexpected soil conditions requiring foundation redesign", "likelihood": "medium", "impact": "high", "mitigation": "Conduct comprehensive geotechnical investigation with adequate bore points across the site footprint."},
            {"risk": "Permit delays from regulatory authority", "likelihood": "high", "impact": "high", "mitigation": "Submit applications early, maintain regular follow-up schedule, and engage a local government liaison."},
            {"risk": "Environmental objections delaying EIA approval", "likelihood": "medium", "impact": "medium", "mitigation": "Engage community stakeholders early and prepare a thorough mitigation plan."},
            {"risk": "Undiscovered underground utilities", "likelihood": "medium", "impact": "medium", "mitigation": "Commission GPR (ground-penetrating radar) survey in addition to utility provider records."},
        ],
        "budget_notes": "Pre-construction typically represents 3-5% of total project cost. Major items: geotechnical investigation, environmental studies, permit fees, and professional consultant fees.",
        # Section E
        "success_metrics": [
            {"metric": "All permits obtained", "target": "100% of required permits issued", "measurement_method": "Permit tracker log"},
            {"metric": "Geotechnical report delivery", "target": "Within 30 days of investigation start", "measurement_method": "Deliverable sign-off date"},
            {"metric": "EIA approval obtained", "target": "Before foundation phase start date", "measurement_method": "Regulatory approval letter on file"},
        ],
        "exit_criteria": [
            {"criterion": "Building permit issued and valid", "verification_method": "Copy of approved permit on file"},
            {"criterion": "Geotechnical report reviewed and accepted by structural engineer", "verification_method": "Signed engineer's acceptance note"},
            {"criterion": "EIA approved with conditions documented", "verification_method": "Regulatory approval letter on file"},
            {"criterion": "Site survey complete and boundary verified", "verification_method": "Surveyor's certificate issued"},
            {"criterion": "Design coordination complete with zero critical clashes", "verification_method": "BIM clash report showing zero critical issues"},
        ],
        "lessons_learned_prompt": "What regulatory hurdles were encountered? Were geotechnical findings within expectations? How can the permit application timeline be shortened on future projects?",
    },

    # ── 1  Foundation & Substructure ────────────────────────────────────
    {
        "name": "Foundation & Substructure",
        "description": "Excavation, piling, foundation slabs, and waterproofing.",
        "weight": 2,
        "budget_pct": "0.15",
        # Section A
        "objective": "Construct all below-ground structural elements to design specification, ensuring adequate load-bearing capacity and waterproofing before superstructure works commence.",
        "estimated_duration_days": 60,
        "phase_owner_role": "Site Engineer",
        # Section B
        "raci_matrix": [
            {"task": "Excavation to formation level", "responsible": "Earthworks Foreman", "accountable": "Site Engineer", "consulted": "Geotechnical Consultant", "informed": "Project Manager"},
            {"task": "Piling works", "responsible": "Piling Subcontractor", "accountable": "Structural Engineer", "consulted": "Geotechnical Consultant", "informed": "Site Engineer"},
            {"task": "Reinforcement fixing", "responsible": "Steel Fixer Lead", "accountable": "Structural Engineer", "consulted": "QA Manager", "informed": "Site Engineer"},
            {"task": "Concrete pouring & curing", "responsible": "Concrete Foreman", "accountable": "Site Engineer", "consulted": "Structural Engineer", "informed": "QA Manager"},
            {"task": "Below-grade waterproofing", "responsible": "Waterproofing Subcontractor", "accountable": "Site Engineer", "consulted": "Architect", "informed": "QA Manager"},
        ],
        "approval_authority": "Structural Engineer must sign off on pile integrity tests, reinforcement inspections, and concrete cube test results before backfilling.",
        # Section C
        "key_tasks": [
            {"name": "Bulk excavation", "description": "Excavate to designed formation level, dispose of spoil, and confirm bearing capacity with plate load tests."},
            {"name": "Piling works", "description": "Drive or bore all load-bearing piles to design depth per structural drawings. Conduct pile integrity tests."},
            {"name": "Pile cap construction", "description": "Form, reinforce, and cast pile caps and ground beams connecting pile groups."},
            {"name": "Foundation slab", "description": "Place blinding, DPM, reinforcement, and pour raft or strip foundation slab to specification."},
            {"name": "Below-grade waterproofing", "description": "Apply tanking membrane or crystalline waterproofing system to all below-ground elements."},
            {"name": "Backfill and compaction", "description": "Backfill around foundations with approved material in layers, compacting to specification."},
        ],
        "deliverables": [
            {"name": "Pile Integrity Test Results", "description": "PIT and/or static load test reports for all piles.", "is_mandatory": True},
            {"name": "Foundation Inspection Certificate", "description": "Structural engineer sign-off on formation level and reinforcement.", "is_mandatory": True},
            {"name": "Concrete Cube Test Results", "description": "7-day and 28-day cube crush test certificates.", "is_mandatory": True},
            {"name": "Waterproofing Warranty", "description": "Manufacturer warranty certificate for below-grade waterproofing system.", "is_mandatory": True},
            {"name": "As-Built Foundation Drawings", "description": "Surveyed as-built drawings showing actual pile and foundation positions.", "is_mandatory": False},
        ],
        "out_of_scope": "Superstructure works above ground level, utility connections beyond the site boundary, and landscaping.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "Site Engineer (full-time)", "quantity": "1"},
            {"type": "human", "description": "Earthworks Foreman", "quantity": "1"},
            {"type": "human", "description": "Steel Fixer team", "quantity": "6-10"},
            {"type": "human", "description": "Concrete crew", "quantity": "4-6"},
            {"type": "human", "description": "Piling Subcontractor team", "quantity": "As per contract"},
            {"type": "financial", "description": "Foundation works budget", "quantity": "12-18% of project budget"},
            {"type": "technical", "description": "Excavator, piling rig, concrete pump, vibrating compactor", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "Encountering rock or hard strata during excavation", "likelihood": "medium", "impact": "high", "mitigation": "Review geotechnical report and allow contingency budget for rock-breaking equipment."},
            {"risk": "High water table affecting excavation stability", "likelihood": "medium", "impact": "high", "mitigation": "Pre-install dewatering wells and monitor water levels daily."},
            {"risk": "Pile refusal before design depth", "likelihood": "low", "impact": "high", "mitigation": "Have alternative pile design pre-approved by structural engineer."},
            {"risk": "Concrete supply delays during critical pours", "likelihood": "medium", "impact": "medium", "mitigation": "Pre-book concrete batching capacity and maintain two approved suppliers."},
        ],
        "budget_notes": "Foundation works typically account for 12-18% of total project cost. Major variables are ground conditions, pile type/depth, and dewatering requirements.",
        # Section E
        "success_metrics": [
            {"metric": "Pile integrity pass rate", "target": ">95% of piles pass on first test", "measurement_method": "PIT reports and logs"},
            {"metric": "Concrete strength compliance", "target": "100% of cubes meet design strength at 28 days", "measurement_method": "Cube test certificates"},
            {"metric": "Waterproofing inspection", "target": "Zero defects on flood test", "measurement_method": "Flood test report"},
        ],
        "exit_criteria": [
            {"criterion": "All pile integrity tests passed and approved", "verification_method": "Structural engineer signed test summary"},
            {"criterion": "Foundation slab poured and cured to design strength", "verification_method": "28-day cube test certificate"},
            {"criterion": "Waterproofing complete and tested", "verification_method": "Flood test report with zero leaks"},
            {"criterion": "As-built survey completed and approved", "verification_method": "Surveyor's as-built certificate"},
        ],
        "lessons_learned_prompt": "Were ground conditions as predicted by the geotechnical report? What dewatering challenges arose? Were concrete pours completed without cold joints?",
    },

    # ── 2  Superstructure ───────────────────────────────────────────────
    {
        "name": "Superstructure",
        "description": "Structural frame, columns, beams, floor slabs, and stairwells.",
        "weight": 3,
        "budget_pct": "0.25",
        # Section A
        "objective": "Erect the complete structural frame from ground floor to roof level, achieving design strength and alignment tolerances at every level.",
        "estimated_duration_days": 120,
        "phase_owner_role": "Structural Engineer",
        # Section B
        "raci_matrix": [
            {"task": "Column erection", "responsible": "Structural Foreman", "accountable": "Structural Engineer", "consulted": "QA Manager", "informed": "Project Manager"},
            {"task": "Formwork installation", "responsible": "Carpentry Foreman", "accountable": "Temporary Works Coordinator", "consulted": "Structural Engineer", "informed": "Safety Officer"},
            {"task": "Reinforcement fixing (upper floors)", "responsible": "Steel Fixer Lead", "accountable": "Structural Engineer", "consulted": "QA Manager", "informed": "Site Engineer"},
            {"task": "Floor slab concrete pours", "responsible": "Concrete Foreman", "accountable": "Site Engineer", "consulted": "Structural Engineer", "informed": "QA Manager"},
            {"task": "Stairwell and lift core construction", "responsible": "Structural Foreman", "accountable": "Structural Engineer", "consulted": "Architect", "informed": "MEP Coordinator"},
        ],
        "approval_authority": "Structural Engineer must approve each floor level before the next is commenced. Temporary Works Coordinator must approve all formwork and propping designs.",
        # Section C
        "key_tasks": [
            {"name": "Column erection per floor", "description": "Erect RC or steel columns to each floor level, checking verticality within ±5mm tolerance."},
            {"name": "Beam and slab formwork", "description": "Install proprietary or traditional formwork systems for beams and slabs at each level."},
            {"name": "Reinforcement fixing", "description": "Fix reinforcement cages for beams, slabs, and columns per structural schedule with inspections before pour."},
            {"name": "Floor slab pours", "description": "Pour and finish each floor slab, maintaining construction joints where specified."},
            {"name": "Stairwell construction", "description": "Form, reinforce, and pour stairwells and landing slabs in sequence with floor progression."},
            {"name": "Lift core walls", "description": "Construct lift shaft walls using slip-form or traditional methods, maintaining plumb tolerance."},
        ],
        "deliverables": [
            {"name": "Floor-Level Sign-Off Certificates", "description": "Structural engineer approval per floor before proceeding.", "is_mandatory": True},
            {"name": "Concrete Cube Test Results (per pour)", "description": "7-day and 28-day strength test certificates for every pour.", "is_mandatory": True},
            {"name": "Formwork & Propping Design Approval", "description": "Temporary works coordinator sign-off on formwork design.", "is_mandatory": True},
            {"name": "Survey Alignment Reports", "description": "Level and verticality survey at each completed floor.", "is_mandatory": True},
            {"name": "Reinforcement Inspection Records", "description": "Photo and checklist records of rebar inspections before each pour.", "is_mandatory": False},
        ],
        "out_of_scope": "External envelope works (cladding, glazing), internal partitions, MEP installations, and finishes.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "Structural Engineer (part-time inspections)", "quantity": "1"},
            {"type": "human", "description": "Structural Foreman", "quantity": "1"},
            {"type": "human", "description": "Steel fixer team", "quantity": "10-15"},
            {"type": "human", "description": "Carpentry/formwork team", "quantity": "8-12"},
            {"type": "human", "description": "Concrete crew", "quantity": "6-8"},
            {"type": "financial", "description": "Superstructure budget", "quantity": "20-28% of project budget"},
            {"type": "technical", "description": "Tower crane, concrete pump, formwork system, rebar bending machine", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "Tower crane breakdown halting floor-cycle progress", "likelihood": "low", "impact": "high", "mitigation": "Maintain crane service contract with 24-hour response guarantee."},
            {"risk": "Concrete strength below specification", "likelihood": "low", "impact": "high", "mitigation": "Pre-qualify batching plants and test every truck for slump and temperature."},
            {"risk": "Formwork failure or excessive deflection", "likelihood": "low", "impact": "high", "mitigation": "Independent check of temporary works design by qualified engineer."},
            {"risk": "Adverse weather delaying concrete pours", "likelihood": "high", "impact": "medium", "mitigation": "Build weather contingency into programme, procure cold/hot weather concreting additives."},
        ],
        "budget_notes": "Superstructure is the largest cost phase at 20-28% of total budget. Key cost drivers: concrete volume, reinforcement tonnage, crane hire, and formwork system rental.",
        # Section E
        "success_metrics": [
            {"metric": "Floor cycle time", "target": "7-10 working days per floor", "measurement_method": "Weekly progress tracker"},
            {"metric": "Concrete compliance", "target": "100% of cubes meeting design strength", "measurement_method": "Cube test certificates"},
            {"metric": "Verticality tolerance", "target": "Within ±5mm per floor, ±25mm overall", "measurement_method": "Survey reports"},
        ],
        "exit_criteria": [
            {"criterion": "Roof slab poured and cured to design strength", "verification_method": "28-day cube test certificate for roof slab"},
            {"criterion": "All floor-level sign-offs obtained", "verification_method": "Structural engineer certificates on file for every level"},
            {"criterion": "Lift core and stairwells complete to roof level", "verification_method": "Structural completion certificate"},
            {"criterion": "Temporary works striking schedule approved", "verification_method": "TWC sign-off on prop removal sequence"},
        ],
        "lessons_learned_prompt": "Was the floor cycle time achieved consistently? Were there any concrete placement issues (cold joints, honeycombing)? How effective was the formwork system choice?",
    },

    # ── 3  Envelope & Roofing ───────────────────────────────────────────
    {
        "name": "Envelope & Roofing",
        "description": "External walls, cladding, glazing, and roof installation.",
        "weight": 2,
        "budget_pct": "0.15",
        # Section A
        "objective": "Make the building weather-tight by completing all external wall systems, cladding, glazing, and roof covering, enabling internal trades to commence without weather risk.",
        "estimated_duration_days": 75,
        "phase_owner_role": "Facade Coordinator",
        # Section B
        "raci_matrix": [
            {"task": "External blockwork & cavity walls", "responsible": "Masonry Foreman", "accountable": "Site Engineer", "consulted": "Architect", "informed": "QA Manager"},
            {"task": "Cladding installation", "responsible": "Cladding Subcontractor", "accountable": "Facade Coordinator", "consulted": "Architect", "informed": "Structural Engineer"},
            {"task": "Window & door installation", "responsible": "Glazing Subcontractor", "accountable": "Facade Coordinator", "consulted": "Architect", "informed": "Site Engineer"},
            {"task": "Roof waterproofing & covering", "responsible": "Roofing Subcontractor", "accountable": "Site Engineer", "consulted": "Architect", "informed": "QA Manager"},
            {"task": "Sealant & weatherproofing", "responsible": "Specialist Applicator", "accountable": "Facade Coordinator", "consulted": "Material Supplier", "informed": "QA Manager"},
        ],
        "approval_authority": "Architect must approve facade mock-up and material samples before full installation. Building Control must inspect fire-rated elements.",
        # Section C
        "key_tasks": [
            {"name": "External blockwork", "description": "Lay external block walls with cavity insulation, DPC, cavity trays, and weep holes per design."},
            {"name": "Cladding system installation", "description": "Install specified cladding system (curtain wall, rain-screen, or render) including fixings and insulation."},
            {"name": "Window and door frames", "description": "Install all external window and door assemblies, seal with foam and silicone, and test for weather-tightness."},
            {"name": "Roof structure and covering", "description": "Complete roof structure (steel or timber), install insulation, vapour barrier, and waterproof membrane or tiles."},
            {"name": "Rainwater goods", "description": "Install gutters, downpipes, and rainwater drainage connections to below-ground system."},
        ],
        "deliverables": [
            {"name": "Facade Mock-Up Approval", "description": "Architect-approved full-scale facade sample panel.", "is_mandatory": True},
            {"name": "Air Tightness Test Report", "description": "Blower-door test confirming air permeability within specification.", "is_mandatory": True},
            {"name": "Roof Warranty Certificate", "description": "Manufacturer warranty for roofing membrane or tile system.", "is_mandatory": True},
            {"name": "Window Schedule Compliance", "description": "Confirmation that all windows meet U-value and acoustic specification.", "is_mandatory": True},
        ],
        "out_of_scope": "Internal partitions, MEP second-fix, interior finishes, and external landscaping.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "Facade Coordinator", "quantity": "1"},
            {"type": "human", "description": "Masonry team", "quantity": "8-12"},
            {"type": "human", "description": "Cladding Subcontractor team", "quantity": "Per subcontract"},
            {"type": "human", "description": "Glazing Subcontractor team", "quantity": "Per subcontract"},
            {"type": "human", "description": "Roofing Subcontractor team", "quantity": "Per subcontract"},
            {"type": "financial", "description": "Envelope and roofing budget", "quantity": "12-18% of project budget"},
            {"type": "technical", "description": "Scaffolding, mast climbers, roof access equipment", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "Cladding supply lead-time delays", "likelihood": "high", "impact": "high", "mitigation": "Place orders during superstructure phase, confirm delivery schedule monthly."},
            {"risk": "Wind conditions preventing high-level glazing installation", "likelihood": "medium", "impact": "medium", "mitigation": "Programme glazing for calmer weather periods, use wind-speed monitoring."},
            {"risk": "Water ingress before building is fully sealed", "likelihood": "medium", "impact": "medium", "mitigation": "Prioritise weathering at top floors down, use temporary protection where needed."},
        ],
        "budget_notes": "Envelope works represent 12-18% of project cost. Cladding system choice is the primary cost driver — curtain wall can be 3-5x the cost of render systems.",
        # Section E
        "success_metrics": [
            {"metric": "Building weather-tight date", "target": "Achieved within programme tolerance", "measurement_method": "Weather-tight certificate signed by site manager"},
            {"metric": "Air tightness result", "target": "≤5 m³/(h·m²) at 50 Pa or per specification", "measurement_method": "Blower door test report"},
            {"metric": "Zero water ingress incidents post-sealing", "target": "No internal water damage reported", "measurement_method": "Defect log review"},
        ],
        "exit_criteria": [
            {"criterion": "All external walls, cladding, and glazing installed", "verification_method": "Facade completion certificate"},
            {"criterion": "Roof covering complete and tested", "verification_method": "Roof flood test or inspection certificate"},
            {"criterion": "Air tightness test passed", "verification_method": "Test report within specification"},
            {"criterion": "Building declared weather-tight", "verification_method": "Site manager weather-tight declaration"},
        ],
        "lessons_learned_prompt": "Were cladding lead times managed effectively? Did the facade mock-up process reveal design issues early enough? Were there any water ingress events before the building was sealed?",
    },

    # ── 4  MEP Rough-In ─────────────────────────────────────────────────
    {
        "name": "MEP Rough-In",
        "description": "Mechanical, electrical, and plumbing first-fix installations.",
        "weight": 2,
        "budget_pct": "0.18",
        # Section A
        "objective": "Complete all first-fix mechanical, electrical, and plumbing installations within walls, floors, and ceilings before they are closed up by finishing trades.",
        "estimated_duration_days": 90,
        "phase_owner_role": "MEP Coordinator",
        # Section B
        "raci_matrix": [
            {"task": "Electrical conduits and back-boxes", "responsible": "Electrical Lead", "accountable": "MEP Coordinator", "consulted": "Electrical Engineer", "informed": "Site Engineer"},
            {"task": "Plumbing and soil stacks", "responsible": "Plumbing Lead", "accountable": "MEP Coordinator", "consulted": "Mechanical Engineer", "informed": "Site Engineer"},
            {"task": "HVAC ductwork and pipework", "responsible": "HVAC Subcontractor", "accountable": "MEP Coordinator", "consulted": "Mechanical Engineer", "informed": "Architect"},
            {"task": "Fire sprinkler pipework", "responsible": "Fire Protection Subcontractor", "accountable": "Fire Safety Officer", "consulted": "MEP Coordinator", "informed": "Building Control"},
            {"task": "Data and communications cabling", "responsible": "IT Cabling Contractor", "accountable": "MEP Coordinator", "consulted": "IT Consultant", "informed": "Client"},
        ],
        "approval_authority": "MEP Coordinator must sign off all first-fix installations before walls are closed. Fire Safety Officer approves sprinkler layout. Building Control must inspect fire-rated penetrations.",
        # Section C
        "key_tasks": [
            {"name": "Electrical first-fix", "description": "Route conduits, install back-boxes, distribution boards, and pull draw wires for second-fix cabling."},
            {"name": "Plumbing first-fix", "description": "Install hot/cold water pipes, soil and waste stacks, and above-ground drainage. Pressure test all pipework."},
            {"name": "HVAC rough-in", "description": "Install ductwork, chilled water pipework, fan coil unit brackets, and refrigerant piping."},
            {"name": "Fire sprinkler installation", "description": "Install sprinkler pipework, heads (capped for now), and zone valves per fire engineer design."},
            {"name": "Structured cabling", "description": "Route Cat6A/fibre cabling pathways, install containment trays, and data cabinet back-boxes."},
            {"name": "Fire-stopping and penetration sealing", "description": "Seal all service penetrations through fire-rated walls and floors with approved intumescent systems."},
        ],
        "deliverables": [
            {"name": "Pressure Test Certificates", "description": "Plumbing and sprinkler pressure test reports for all zones.", "is_mandatory": True},
            {"name": "Electrical Continuity Test Report", "description": "Insulation resistance and continuity tests for all circuits.", "is_mandatory": True},
            {"name": "Fire Stopping Inspection Report", "description": "Photographic record and certification of all fire-rated penetrations.", "is_mandatory": True},
            {"name": "MEP Coordination Drawings (as-installed)", "description": "Updated coordination drawings reflecting actual installation routes.", "is_mandatory": True},
            {"name": "HVAC Ductwork Leak Test Report", "description": "Air leakage test results for ductwork systems.", "is_mandatory": False},
        ],
        "out_of_scope": "Second-fix MEP (final connections, face plates, fixtures), commissioning of systems, and external utility connections beyond the building footprint.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "MEP Coordinator (full-time)", "quantity": "1"},
            {"type": "human", "description": "Electrical team", "quantity": "8-12"},
            {"type": "human", "description": "Plumbing team", "quantity": "6-8"},
            {"type": "human", "description": "HVAC Subcontractor team", "quantity": "Per subcontract"},
            {"type": "human", "description": "Fire Sprinkler Subcontractor team", "quantity": "Per subcontract"},
            {"type": "financial", "description": "MEP rough-in budget", "quantity": "15-20% of project budget"},
            {"type": "technical", "description": "Pipe threading machine, conduit bender, pressure test equipment", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "MEP coordination clashes discovered during installation", "likelihood": "high", "impact": "medium", "mitigation": "Complete 3D BIM coordination before start; hold weekly MEP coordination meetings."},
            {"risk": "Pressure test failures requiring rework", "likelihood": "medium", "impact": "medium", "mitigation": "Test in zones as work progresses rather than at final completion."},
            {"risk": "Fire stopping missed or incomplete", "likelihood": "medium", "impact": "high", "mitigation": "Dedicated fire-stop inspector with photographic records for every penetration."},
            {"risk": "Late design changes affecting routing", "likelihood": "medium", "impact": "high", "mitigation": "Design freeze deadline enforced before MEP rough-in starts."},
        ],
        "budget_notes": "MEP services represent 15-20% of project cost for first-fix. HVAC is typically the largest single trade. Fire sprinklers are often mandated by regulation regardless of cost.",
        # Section E
        "success_metrics": [
            {"metric": "First-time pressure test pass rate", "target": ">90% of zones pass on first attempt", "measurement_method": "Pressure test log"},
            {"metric": "Fire-stopping completion", "target": "100% of penetrations sealed and certified before wall close-up", "measurement_method": "Fire-stop inspection log"},
            {"metric": "Zero critical BIM clashes during installation", "target": "No field clashes requiring structural modification", "measurement_method": "Site RFI log"},
        ],
        "exit_criteria": [
            {"criterion": "All first-fix MEP installations complete", "verification_method": "MEP Coordinator sign-off per zone"},
            {"criterion": "Pressure tests passed for all plumbing and sprinkler zones", "verification_method": "Test certificates on file"},
            {"criterion": "Electrical continuity tests passed", "verification_method": "Electrical test certificates"},
            {"criterion": "All fire-rated penetrations sealed and inspected", "verification_method": "Fire-stop inspection report"},
        ],
        "lessons_learned_prompt": "Were BIM coordination drawings accurate? How many site RFIs were raised? Were there any fire-stopping omissions? Did the MEP subcontractors coordinate effectively?",
    },

    # ── 5  Interior Fit-Out ─────────────────────────────────────────────
    {
        "name": "Interior Fit-Out",
        "description": "Partitions, flooring, painting, joinery, and finishes.",
        "weight": 3,
        "budget_pct": "0.17",
        # Section A
        "objective": "Complete all internal finishing works to achieve a move-in ready standard, including partitions, flooring, painting, joinery, and MEP second-fix.",
        "estimated_duration_days": 90,
        "phase_owner_role": "Finishing Manager",
        # Section B
        "raci_matrix": [
            {"task": "Internal partitions (block/stud/drywall)", "responsible": "Partition Subcontractor", "accountable": "Finishing Manager", "consulted": "Architect", "informed": "MEP Coordinator"},
            {"task": "Floor screeding and tiling", "responsible": "Finishing Foreman", "accountable": "Finishing Manager", "consulted": "Architect", "informed": "QA Manager"},
            {"task": "Painting and decorating", "responsible": "Painting Contractor", "accountable": "Finishing Manager", "consulted": "Architect", "informed": "Client"},
            {"task": "Joinery and door hanging", "responsible": "Joinery Lead", "accountable": "Finishing Manager", "consulted": "Architect", "informed": "QA Manager"},
            {"task": "MEP second-fix (face plates, fixtures)", "responsible": "Electrical Lead / Plumbing Lead", "accountable": "MEP Coordinator", "consulted": "Finishing Manager", "informed": "QA Manager"},
            {"task": "Kitchen and bathroom fit-out", "responsible": "Fit-Out Subcontractor", "accountable": "Finishing Manager", "consulted": "Architect", "informed": "Client"},
        ],
        "approval_authority": "Architect must approve material samples and mock-up units before roll-out. Client approval required for any specification changes.",
        # Section C
        "key_tasks": [
            {"name": "Internal partitions", "description": "Erect all internal block, stud, and drywall partitions. Tape, joint, and skim to receive finishes."},
            {"name": "Floor screeding", "description": "Apply sand-cement or liquid screed to required thickness and falls. Allow drying before floor finishes."},
            {"name": "Tiling and floor finishes", "description": "Lay floor tiles, hardwood, laminate, or carpet per room schedule."},
            {"name": "Painting and decorating", "description": "Mist coat new plaster, two coats emulsion to walls/ceilings, satinwood to woodwork."},
            {"name": "Joinery installation", "description": "Hang internal doors, install skirting, architraves, built-in wardrobes, and shelving."},
            {"name": "Kitchen and bathroom installation", "description": "Install kitchen units, worktops, sanitary ware, taps, mirrors, and accessories."},
            {"name": "MEP second-fix", "description": "Install light fittings, switch plates, sockets, radiators/FCUs, and sanitary connections."},
        ],
        "deliverables": [
            {"name": "Mock-Up Unit Approval", "description": "Architect and client approved show-unit before mass roll-out.", "is_mandatory": True},
            {"name": "Material Sample Approvals", "description": "Signed approval sheets for all finish materials, colours, and textures.", "is_mandatory": True},
            {"name": "Floor Flatness/Levelness Report", "description": "SR (straightness) and FF/FL measurements for screeded floors.", "is_mandatory": False},
            {"name": "Snagging Schedule", "description": "Room-by-room defect list compiled during QA walk-through.", "is_mandatory": True},
        ],
        "out_of_scope": "External landscaping, final cleaning, furniture procurement, and tenant-specific customisation.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "Finishing Manager (full-time)", "quantity": "1"},
            {"type": "human", "description": "Partition team", "quantity": "6-10"},
            {"type": "human", "description": "Painting crew", "quantity": "8-12"},
            {"type": "human", "description": "Tiling team", "quantity": "4-8"},
            {"type": "human", "description": "Joinery team", "quantity": "4-6"},
            {"type": "human", "description": "Kitchen/bathroom fit-out team", "quantity": "Per subcontract"},
            {"type": "financial", "description": "Fit-out budget", "quantity": "15-20% of project budget"},
            {"type": "technical", "description": "Plaster pump, tile cutter, spray painting equipment", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "Finish material supply delays or discontinuation", "likelihood": "medium", "impact": "high", "mitigation": "Order all finish materials at project start; keep 10% contingency stock on-site."},
            {"risk": "Damage to completed finishes by following trades", "likelihood": "high", "impact": "medium", "mitigation": "Enforce strict trade sequencing and protect completed surfaces with coverings."},
            {"risk": "Screed drying time exceeding allowance", "likelihood": "medium", "impact": "medium", "mitigation": "Use accelerated screed systems or dehumidifiers to speed drying."},
            {"risk": "Client-requested changes delaying programme", "likelihood": "medium", "impact": "medium", "mitigation": "Enforce change-order process with cost and time impact assessment."},
        ],
        "budget_notes": "Interior fit-out is 15-20% of budget. Kitchen and bathroom specifications are the primary cost variables. Labour-intensive phase with many overlapping trades.",
        # Section E
        "success_metrics": [
            {"metric": "Snagging items per unit", "target": "<20 items per residential unit", "measurement_method": "Snagging list count at first inspection"},
            {"metric": "Trade damage incidents", "target": "Zero damage to completed surfaces", "measurement_method": "Damage log"},
            {"metric": "Client satisfaction on show-unit", "target": "Approval on first or second review", "measurement_method": "Mock-up sign-off date"},
        ],
        "exit_criteria": [
            {"criterion": "All internal finishes complete per room schedule", "verification_method": "Room-by-room QA checklist signed"},
            {"criterion": "MEP second-fix complete and functional", "verification_method": "MEP Coordinator sign-off"},
            {"criterion": "Snagging list compiled and items under rectification", "verification_method": "Snagging tracker showing all items assigned"},
            {"criterion": "Mock-up unit approved by architect and client", "verification_method": "Signed mock-up approval form"},
        ],
        "lessons_learned_prompt": "How effectively were trades sequenced to avoid damage? Were finish material orders placed early enough? What snagging patterns were most common?",
    },

    # ── 6  Commissioning & Handover ─────────────────────────────────────
    {
        "name": "Commissioning & Handover",
        "description": "Testing, snagging, compliance certification, and client handover.",
        "weight": 1,
        "budget_pct": "0.05",
        # Section A
        "objective": "Commission all building systems, rectify all snagging items, obtain statutory compliance certificates, and formally hand over the completed building to the client.",
        "estimated_duration_days": 45,
        "phase_owner_role": "Commissioning Manager",
        # Section B
        "raci_matrix": [
            {"task": "Fire alarm and sprinkler commissioning", "responsible": "Fire Safety Officer", "accountable": "Commissioning Manager", "consulted": "Building Control", "informed": "Client"},
            {"task": "Electrical installation testing", "responsible": "Electrical Lead", "accountable": "Commissioning Manager", "consulted": "Electrical Engineer", "informed": "Building Control"},
            {"task": "HVAC commissioning and balancing", "responsible": "HVAC Subcontractor", "accountable": "Commissioning Manager", "consulted": "Mechanical Engineer", "informed": "Facilities Manager"},
            {"task": "Lift commissioning", "responsible": "Lift Manufacturer", "accountable": "Commissioning Manager", "consulted": "Building Control", "informed": "Client"},
            {"task": "Snagging rectification", "responsible": "All Subcontractors", "accountable": "QA Manager", "consulted": "Architect", "informed": "Client"},
            {"task": "O&M manual compilation", "responsible": "Document Controller", "accountable": "Project Manager", "consulted": "All Subcontractors", "informed": "Client, Facilities Manager"},
        ],
        "approval_authority": "Building Control Officer must issue the Completion Certificate. Client must sign the Practical Completion Certificate. Contract Administrator certifies financial final account.",
        # Section C
        "key_tasks": [
            {"name": "Fire alarm and sprinkler commissioning", "description": "Test all call points, detectors, sounders, and panel. Witness sprinkler flow and pressure tests. Issue commissioning certificates."},
            {"name": "Electrical installation testing", "description": "Complete EICR (Electrical Installation Condition Report) testing of all circuits, distribution boards, and protective devices."},
            {"name": "HVAC commissioning", "description": "Balance air and water systems, set control sequences, and verify temperature and humidity performance."},
            {"name": "Lift commissioning and certification", "description": "Manufacturer commissioning of all lifts with independent insurance inspection."},
            {"name": "Snagging walk-through", "description": "Systematic walk of every unit and common area. Compile defect schedule, categorise by severity, and track rectification."},
            {"name": "O&M manual assembly", "description": "Compile operation and maintenance manuals, as-built drawings, warranties, and equipment data sheets."},
            {"name": "Building Control final inspection", "description": "Arrange and pass final Building Control inspection for Completion Certificate."},
            {"name": "Client handover meeting", "description": "Formal handover of keys, manuals, certificates, and training of facilities management team."},
        ],
        "deliverables": [
            {"name": "Fire Alarm Commissioning Certificate", "description": "Approved fire alarm and detection system commissioning report.", "is_mandatory": True},
            {"name": "EICR Certificate", "description": "Electrical Installation Condition Report with satisfactory rating.", "is_mandatory": True},
            {"name": "HVAC Commissioning Report", "description": "Air and water balancing results with design vs. actual comparison.", "is_mandatory": True},
            {"name": "Lift Commissioning Certificate", "description": "Manufacturer commissioning certificate and insurance inspection report.", "is_mandatory": True},
            {"name": "Building Completion Certificate", "description": "Final Building Control Completion Certificate.", "is_mandatory": True},
            {"name": "Practical Completion Certificate", "description": "Contract administrator signed PCC.", "is_mandatory": True},
            {"name": "O&M Manuals (full set)", "description": "Hard and digital copies of all operation and maintenance documentation.", "is_mandatory": True},
            {"name": "As-Built Drawings", "description": "Final as-built architectural, structural, and MEP drawings.", "is_mandatory": True},
            {"name": "Warranty Schedule", "description": "Consolidated schedule of all product and workmanship warranties.", "is_mandatory": True},
        ],
        "out_of_scope": "Post-occupancy tenant fit-out, furniture and equipment procurement, external site works beyond building footprint, and long-term maintenance contracts.",
        # Section D
        "resource_requirements": [
            {"type": "human", "description": "Commissioning Manager (full-time)", "quantity": "1"},
            {"type": "human", "description": "QA Manager / Snagging Inspector", "quantity": "1-2"},
            {"type": "human", "description": "Document Controller", "quantity": "1"},
            {"type": "human", "description": "All trade subcontractors (for rectification)", "quantity": "As needed"},
            {"type": "financial", "description": "Commissioning and handover budget", "quantity": "3-5% of project budget"},
            {"type": "technical", "description": "Commissioning test equipment (provided by subcontractors)", "quantity": "As needed"},
        ],
        "phase_risks": [
            {"risk": "Building Control inspection failure requiring rework", "likelihood": "medium", "impact": "high", "mitigation": "Conduct pre-inspection walkthrough with independent building control consultant."},
            {"risk": "Snagging volume exceeding programme allowance", "likelihood": "high", "impact": "medium", "mitigation": "Start snagging floor-by-floor as fit-out completes rather than waiting until the end."},
            {"risk": "Missing warranties or O&M documentation", "likelihood": "medium", "impact": "medium", "mitigation": "Maintain live O&M tracker throughout project, withhold retention until documents received."},
            {"risk": "System commissioning failures", "likelihood": "medium", "impact": "high", "mitigation": "Require subcontractor pre-commissioning before formal witnessing."},
        ],
        "budget_notes": "Commissioning and handover is 3-5% of total budget. Under-budgeting this phase is a common mistake that delays occupancy. Allow adequate snagging rectification time.",
        # Section E
        "success_metrics": [
            {"metric": "Snagging closure rate", "target": ">95% of items closed before handover", "measurement_method": "Snagging tracker percentage"},
            {"metric": "Commissioning first-pass rate", "target": ">80% of systems pass on first test", "measurement_method": "Commissioning tracker"},
            {"metric": "Handover date achievement", "target": "Within 5 working days of programme date", "measurement_method": "Practical completion certificate date vs. programme"},
        ],
        "exit_criteria": [
            {"criterion": "All commissioning certificates obtained", "verification_method": "Complete set of certificates filed in project document system"},
            {"criterion": "Building Completion Certificate issued", "verification_method": "Building Control certificate on file"},
            {"criterion": "Practical Completion Certificate signed", "verification_method": "Signed PCC with conditions (if any) documented"},
            {"criterion": "O&M manuals and as-built drawings handed over", "verification_method": "Client signed receipt for documentation"},
            {"criterion": "Keys and access devices handed to client", "verification_method": "Key register signed by client"},
            {"criterion": ">95% of snagging items resolved", "verification_method": "Snagging tracker showing <5% outstanding"},
        ],
        "lessons_learned_prompt": "Were commissioning resources mobilised early enough? What snagging patterns indicate quality issues in earlier phases? Was the O&M documentation collected proactively or was it a last-minute scramble?",
    },
]


# All section fields to persist via update_or_create defaults
SECTION_FIELDS = [
    "objective", "estimated_duration_days", "phase_owner_role",
    "raci_matrix", "approval_authority",
    "key_tasks", "deliverables", "out_of_scope",
    "resource_requirements", "phase_risks", "budget_notes",
    "success_metrics", "exit_criteria", "lessons_learned_prompt",
]


class Command(BaseCommand):
    help = "Seed 7 standard construction phase templates. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Delete all phase templates before re-seeding.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = PhaseTemplate.objects.all().delete()
            self.stdout.write(f"Flushed {deleted} phase templates.")

        created = 0
        for idx, tmpl in enumerate(PHASE_TEMPLATES):
            defaults = {
                "description": tmpl["description"],
                "sort_order": idx,
                "weight": tmpl["weight"],
                "budget_pct": tmpl["budget_pct"],
            }
            for field in SECTION_FIELDS:
                if field in tmpl:
                    defaults[field] = tmpl[field]

            _, was_created = PhaseTemplate.objects.update_or_create(
                name=tmpl["name"],
                defaults=defaults,
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Phase templates: {created} created, {len(PHASE_TEMPLATES) - created} updated.")
        )

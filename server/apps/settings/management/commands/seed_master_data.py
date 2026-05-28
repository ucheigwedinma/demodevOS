from django.core.management.base import BaseCommand

from apps.settings.models import MasterDataEntry

C = MasterDataEntry.Category

SEED_DATA = {
    # -----------------------------------------------------------------------
    # Identity & Access
    # -----------------------------------------------------------------------
    C.IDENTITY_TYPE: [
        ("user", "User", "Standard platform user with login credentials"),
        ("employee", "Employee", "Internal employee of the organization"),
        ("partner", "Partner", "External partner — contractor, vendor, client, or investor"),
        ("system_account", "System Account", "Non-human system or service account"),
    ],
    C.PARTNER_TYPE: [
        ("contractor", "Contractor", "Construction or service contractor"),
        ("vendor", "Vendor", "Goods or services vendor / supplier"),
        ("client", "Client", "Client or buyer entity"),
        ("investor", "Investor", "Investment partner or stakeholder"),
    ],

    # -----------------------------------------------------------------------
    # People & Organizations
    # -----------------------------------------------------------------------
    C.VENDOR_TYPE: [
        ("general_supplier", "General Supplier", "Broad-range goods and services provider"),
        ("subcontractor", "Subcontractor", "Specialist trade subcontractor"),
        ("equipment_rental", "Equipment Rental", "Construction equipment and machinery rental"),
        ("professional_services", "Professional Services", "Consulting, legal, and advisory services"),
        ("raw_materials", "Raw Materials", "Bulk raw material supplier"),
        ("logistics_transport", "Logistics & Transport", "Freight, haulage, and logistics provider"),
        ("it_technology", "IT & Technology", "Software, hardware, and IT services"),
        ("cleaning_janitorial", "Cleaning & Janitorial", "Cleaning and janitorial services"),
        ("security_services", "Security Services", "Security personnel and systems provider"),
        ("catering_hospitality", "Catering & Hospitality", "Catering and hospitality services"),
    ],
    C.CLIENT_TYPE: [
        ("individual", "Individual", "Private individual buyer"),
        ("corporate", "Corporate", "Corporate entity or company"),
        ("investor", "Investor", "Investment-focused buyer"),
        ("government", "Government", "Government or public sector entity"),
        ("institutional", "Institutional", "Institutional buyer (pension fund, endowment, etc.)"),
        ("developer", "Developer", "Real estate developer"),
        ("joint_venture", "Joint Venture", "Joint venture partnership"),
        ("trust_estate", "Trust / Estate", "Trust or estate entity"),
    ],
    C.CONSULTANT_SPECIALIZATION: [
        ("architecture", "Architecture", "Architectural design and planning"),
        ("structural_engineering", "Structural Engineering", "Structural analysis and design"),
        ("mep_engineering", "MEP Engineering", "Mechanical, electrical, and plumbing engineering"),
        ("quantity_surveying", "Quantity Surveying", "Cost estimation and quantity take-off"),
        ("project_management", "Project Management", "Project planning and execution oversight"),
        ("environmental", "Environmental", "Environmental impact assessment and compliance"),
        ("legal", "Legal", "Legal advisory and contract review"),
        ("financial_advisory", "Financial Advisory", "Financial planning, valuation, and advisory"),
        ("interior_design", "Interior Design", "Interior space design and fit-out"),
        ("landscape_architecture", "Landscape Architecture", "Landscape design and planning"),
    ],
    C.CONTRACTOR_CLASSIFICATION: [
        ("general_contractor", "General Contractor", "Main contractor for overall project delivery"),
        ("civil_works", "Civil Works", "Earthworks, foundations, and civil infrastructure"),
        ("mechanical", "Mechanical", "Mechanical installations and HVAC systems"),
        ("electrical", "Electrical", "Electrical wiring, panels, and systems"),
        ("plumbing", "Plumbing", "Plumbing and drainage systems"),
        ("finishing", "Finishing", "Plastering, painting, tiling, and interior finishing"),
        ("landscaping", "Landscaping", "External landscaping and hardscaping"),
        ("demolition", "Demolition", "Demolition and site clearance"),
        ("specialist_subcontractor", "Specialist Subcontractor", "Niche trades (piling, waterproofing, curtain wall, etc.)"),
    ],
    C.INVESTOR_TYPE: [
        ("individual", "Individual", "Private individual investor"),
        ("institutional", "Institutional", "Pension funds, sovereign wealth, endowments"),
        ("family_office", "Family Office", "Family office or private wealth manager"),
        ("fund", "Fund", "Real estate investment fund"),
        ("corporate", "Corporate", "Corporate investor entity"),
        ("jv_partner", "JV Partner", "Joint venture partner or co-investor"),
    ],

    # -----------------------------------------------------------------------
    # Property & Assets
    # -----------------------------------------------------------------------
    C.PROPERTY_TYPE: [
        ("land", "Land", "Undeveloped land parcel"),
        ("building", "Building", "Completed building structure"),
        ("mixed", "Mixed Use", "Combined residential and commercial property"),
        ("estate", "Estate", "Multi-unit residential or mixed estate"),
        ("warehouse", "Warehouse", "Warehouse or storage facility"),
        ("industrial", "Industrial", "Industrial facility or plant"),
    ],
    C.PROPERTY_CLASSIFICATION: [
        ("owned", "Owned", "Fully owned freehold property"),
        ("lease", "Lease", "Leasehold interest"),
        ("concession", "Concession", "Government or authority concession"),
        ("under_development", "Under Development", "Property currently under active development"),
    ],
    C.UNIT_TYPOLOGY: [
        ("studio", "Studio", "Studio / efficiency apartment"),
        ("1br", "1 Bedroom", "One-bedroom apartment"),
        ("2br", "2 Bedrooms", "Two-bedroom apartment"),
        ("3br", "3 Bedrooms", "Three-bedroom apartment"),
        ("4br_plus", "4+ Bedrooms", "Four or more bedrooms"),
        ("penthouse", "Penthouse", "Top-floor premium unit"),
        ("duplex", "Duplex", "Two-level unit"),
        ("townhouse", "Townhouse", "Attached multi-story dwelling"),
        ("commercial_space", "Commercial Space", "Office or commercial unit"),
        ("retail_unit", "Retail Unit", "Ground-floor retail or shop unit"),
    ],
    C.ASSET_CATEGORY: [
        ("structural", "Structural", "Load-bearing elements — columns, beams, slabs"),
        ("electrical", "Electrical", "Electrical systems — panels, wiring, transformers"),
        ("mechanical", "Mechanical", "Mechanical systems — motors, pumps, conveyors"),
        ("plumbing", "Plumbing", "Plumbing and drainage systems"),
        ("hvac", "HVAC", "Heating, ventilation, and air conditioning"),
        ("fire_safety", "Fire Safety", "Fire alarms, sprinklers, extinguishers"),
        ("elevator", "Elevator", "Passenger and freight elevators"),
        ("generator", "Generator", "Standby and emergency generators"),
        ("water_systems", "Water Systems", "Water tanks, pumps, treatment systems"),
        ("security", "Security", "CCTV, access control, alarm systems"),
    ],
    C.OWNERSHIP_STRUCTURE: [
        ("individual", "Individual", "Sole individual ownership"),
        ("corporate", "Corporate", "Owned by a corporate entity"),
        ("trust", "Trust", "Held in a trust structure"),
        ("joint_venture", "Joint Venture", "Shared ownership via joint venture"),
    ],

    # -----------------------------------------------------------------------
    # Maintenance & Operations
    # -----------------------------------------------------------------------
    C.MAINTENANCE_CATEGORY: [
        ("plumbing", "Plumbing", "Pipes, fixtures, drainage repairs"),
        ("electrical", "Electrical", "Wiring, panels, lighting repairs"),
        ("hvac", "HVAC", "Heating, ventilation, AC maintenance"),
        ("structural", "Structural", "Walls, floors, ceilings, foundations"),
        ("mechanical", "Mechanical", "Pumps, motors, mechanical equipment"),
        ("cleaning", "Cleaning", "Routine cleaning and sanitation"),
        ("landscaping", "Landscaping", "Grounds, gardens, external areas"),
        ("security", "Security", "Security systems and patrol"),
        ("painting", "Painting", "Interior and exterior painting"),
        ("fire_safety", "Fire & Safety", "Fire systems inspection and maintenance"),
        ("elevator", "Elevators", "Elevator maintenance and servicing"),
        ("generator", "Generators", "Generator servicing and fuel management"),
        ("water_systems", "Water Systems", "Water treatment and tank maintenance"),
        ("general", "General", "General maintenance and miscellaneous"),
    ],
    C.INSPECTION_TYPE: [
        ("routine", "Routine", "Scheduled periodic inspection"),
        ("safety", "Safety", "Occupational safety and hazard inspection"),
        ("compliance", "Compliance", "Regulatory compliance check"),
        ("pre_handover", "Pre-Handover", "Inspection before unit/building handover"),
        ("post_incident", "Post-Incident", "Inspection following a safety or structural incident"),
        ("condition_survey", "Condition Survey", "Comprehensive condition assessment"),
        ("fire_safety", "Fire Safety", "Fire safety systems and egress inspection"),
        ("electrical", "Electrical Inspection", "Electrical systems and wiring inspection"),
        ("structural_integrity", "Structural Integrity", "Structural load-bearing and foundation check"),
        ("elevator_certification", "Elevator Certification", "Elevator safety and certification inspection"),
        ("environmental_audit", "Environmental Audit", "Environmental impact and compliance audit"),
        ("health_safety", "Health & Safety", "Occupational health and safety audit"),
    ],

    # -----------------------------------------------------------------------
    # Finance & Costs
    # -----------------------------------------------------------------------
    C.COST_CODE: [
        ("prelims", "Preliminaries", "Site setup, temporary works, and project preliminaries"),
        ("substructure", "Substructure", "Foundations, piling, and below-ground works"),
        ("superstructure", "Superstructure", "Frame, upper floors, roof, and structural envelope"),
        ("finishes", "Finishes", "Internal finishes — flooring, plastering, painting"),
        ("mep_services", "MEP Services", "Mechanical, electrical, and plumbing installations"),
        ("external_works", "External Works", "Landscaping, roads, drainage, external infrastructure"),
        ("contingency", "Contingency", "Risk contingency and unforeseen cost allowance"),
        ("professional_fees", "Professional Fees", "Consultant and professional service fees"),
        ("permits_approvals", "Permits & Approvals", "Statutory fees, permits, and approval costs"),
        ("overheads", "Overheads", "Project management and administrative overhead"),
    ],
    C.MATERIAL_CATEGORY: [
        ("cement_concrete", "Cement & Concrete", "Cement, ready-mix concrete, and admixtures"),
        ("steel_rebar", "Reinforcement Steel", "Reinforcement steel, structural steel, and mesh"),
        ("aggregates", "Aggregates", "Building sand, gravel, crushed stone, and fill materials"),
        ("bricks_blocks", "Blocks", "Clay bricks, concrete blocks, and masonry units"),
        ("timber_wood", "Timber & Wood", "Structural and finishing timber products"),
        ("electrical_materials", "Electrical Materials", "Cables, switches, sockets, distribution boards, and wiring accessories"),
        ("plumbing_materials", "Plumbing Materials", "Pipes, valves, taps, sanitary ware, and drainage fittings"),
        ("finishing_materials", "Finishing Materials", "Tiles, flooring, paint, coatings, glass, glazing, and surface finishes"),
        ("hvac_materials", "HVAC Materials", "Ductwork, air handling units, refrigerant piping, and climate control components"),
        ("doors_windows", "Doors & Windows", "Internal and external doors, window frames, hardware, and glazing units"),
        ("roofing", "Roofing Materials", "Roofing sheets, tiles, membranes, and flashing"),
        ("waterproofing", "Waterproofing", "Waterproof membranes, sealants, damp-proofing, and tanking systems"),
        ("mechanical_equipment", "Mechanical Equipment", "Pumps, generators, lifts, hoists, and mechanical plant"),
        ("fixtures_fittings", "Fixtures & Fittings", "Bathroom fixtures, kitchen fittings, ironmongery, and built-in furniture"),
        ("insulation", "Insulation", "Thermal and acoustic insulation materials"),
        ("consumables", "Consumables", "Nails, screws, adhesives, tapes, PPE, and general site consumables"),
    ],
    C.PAYMENT_METHOD: [
        ("bank_transfer", "Bank Transfer", "Direct bank wire or electronic transfer"),
        ("check", "Check", "Paper or electronic check"),
        ("cash", "Cash", "Cash payment"),
        ("credit_card", "Credit Card", "Credit or debit card payment"),
        ("other", "Other", "Other payment method"),
    ],
    C.CURRENCY: [
        ("ngn", "NGN", "Nigerian Naira"),
        ("usd", "USD", "United States Dollar"),
        ("eur", "EUR", "Euro"),
        ("gbp", "GBP", "British Pound Sterling"),
        ("aed", "AED", "United Arab Emirates Dirham"),
        ("zar", "ZAR", "South African Rand"),
        ("kes", "KES", "Kenyan Shilling"),
        ("ghs", "GHS", "Ghanaian Cedi"),
    ],

    # -----------------------------------------------------------------------
    # Compliance & Risk
    # -----------------------------------------------------------------------
    C.RISK_CATEGORY: [
        ("market_risk", "Market Risk", "Demand fluctuations, pricing, and absorption risk"),
        ("construction_risk", "Construction Risk", "Schedule overruns, contractor delays, defects"),
        ("financial_risk", "Financial Risk", "Budget overruns, cash flow gaps, financing risk"),
        ("regulatory_risk", "Regulatory Risk", "Changes in regulations, permits, and zoning"),
        ("environmental_risk", "Environmental Risk", "Environmental contamination and compliance"),
        ("safety_risk", "Safety Risk", "Worker and public safety hazards"),
        ("legal_risk", "Legal Risk", "Contractual disputes, litigation, and liability"),
        ("design_risk", "Design Risk", "Design errors, scope changes, and rework"),
        ("supply_chain_risk", "Supply Chain Risk", "Material shortages, logistics delays"),
        ("reputational_risk", "Reputational Risk", "Brand damage, stakeholder perception"),
    ],
    C.ISSUE_CATEGORY: [
        ("safety_hazard", "Safety Hazard", "On-site safety hazard or near-miss"),
        ("quality_defect", "Quality Defect", "Construction or material quality issue"),
        ("schedule_delay", "Schedule Delay", "Activity or milestone delay"),
        ("budget_overrun", "Budget Overrun", "Cost exceeding approved budget"),
        ("design_conflict", "Design Conflict", "Clash or inconsistency in design drawings"),
        ("permit_issue", "Permit Issue", "Permit delay, rejection, or non-compliance"),
        ("environmental_violation", "Environmental Violation", "Environmental regulation breach"),
        ("labor_dispute", "Labor Dispute", "Worker grievance or labor action"),
        ("material_shortage", "Material Shortage", "Critical material supply gap"),
        ("client_complaint", "Client Complaint", "Buyer or stakeholder complaint"),
    ],
    C.COMPLIANCE_CATEGORY: [
        ("regulatory", "Regulatory", "Government and statutory regulatory requirements"),
        ("environmental", "Environmental", "Environmental protection and impact requirements"),
        ("safety", "Safety", "Occupational health and safety standards"),
        ("building_code", "Building Code", "Structural and building code compliance"),
        ("zoning", "Zoning", "Land use and zoning ordinance compliance"),
        ("accessibility", "Accessibility", "Disability access and universal design requirements"),
        ("fire_safety", "Fire Safety", "Fire prevention and life safety codes"),
        ("occupational_health", "Occupational Health", "Workplace health standards and regulations"),
    ],

    # -----------------------------------------------------------------------
    # Projects
    # -----------------------------------------------------------------------
    C.PROJECT_TYPE: [
        ("residential", "Residential", "Residential housing development"),
        ("mixed_use", "Mixed Use", "Combined residential, commercial, and retail"),
        ("commercial", "Commercial", "Office and commercial development"),
        ("infrastructure", "Infrastructure", "Roads, utilities, and infrastructure projects"),
    ],
    C.LAND_STATUS: [
        ("freehold", "Freehold", "Outright freehold ownership"),
        ("leasehold", "Leasehold", "Long-term leasehold interest"),
        ("under_contract", "Under Contract", "Purchase contract in progress"),
        ("to_acquire", "To Acquire", "Identified for future acquisition"),
        ("joint_venture", "Joint Venture", "Land held via joint venture arrangement"),
    ],

    # -----------------------------------------------------------------------
    # Documents
    # -----------------------------------------------------------------------
    C.DOCUMENT_TYPE: [
        ("deed", "Deed", "Title deed and ownership documents"),
        ("contract", "Contract", "Contractual agreements and amendments"),
        ("survey", "Survey", "Land and topographic survey documents"),
        ("permit", "Permit", "Building permits and government approvals"),
        ("inspection", "Inspection", "Inspection reports and certificates"),
        ("appraisal", "Appraisal", "Property valuation and appraisal reports"),
        ("insurance", "Insurance", "Insurance policies and certificates"),
        ("tax", "Tax", "Tax assessment and payment documents"),
        ("certificate_of_occupancy", "Certificate of Occupancy", "Occupancy permits and completion certificates"),
        ("lease_agreement", "Lease Agreement", "Lease contracts and tenancy agreements"),
        ("drawing", "Drawing", "Architectural and engineering drawings"),
        ("specification", "Specification", "Technical specifications and scope documents"),
        ("report", "Report", "Progress reports, studies, and assessments"),
        ("correspondence", "Correspondence", "Letters, emails, and official communications"),
    ],

    # -----------------------------------------------------------------------
    # CRM & Communications
    # -----------------------------------------------------------------------
    C.LEAD_TYPE: [
        ("buyer", "Buyer", "Prospective property buyer"),
        ("tenant", "Tenant", "Prospective tenant or lessee"),
        ("investor", "Investor", "Investment-focused lead"),
    ],
    C.LEAD_ARCHIVED_REASON: [
        ("duplicate", "Duplicate", "Lead is a duplicate of an existing record"),
        ("unqualified", "Unqualified", "Lead does not meet qualification criteria"),
        ("no_contact", "No Contact", "Unable to reach lead after multiple attempts"),
        ("lost", "Lost", "Lead chose a competitor or withdrew interest"),
        ("converted", "Converted", "Lead was converted to a customer or reservation"),
        ("inactive", "Inactive", "Lead has been inactive beyond retention threshold"),
        ("budget_mismatch", "Budget Mismatch", "Lead's budget does not match available inventory"),
        ("spam", "Spam", "Lead was identified as spam or fraudulent"),
        ("other", "Other", "Other reason for archival"),
    ],
    C.COMMUNICATION_CHANNEL: [
        ("email", "Email", "Email correspondence"),
        ("whatsapp", "WhatsApp", "WhatsApp messaging"),
        ("sms", "SMS", "Short message service"),
        ("phone", "Phone Call", "Voice phone call"),
        ("video_call", "Video Call", "Video conferencing (Zoom, Teams, Meet)"),
        ("in_person", "In-Person", "Face-to-face interaction"),
        ("social_media", "Social Media", "Social media direct messages"),
        ("live_chat", "Live Chat", "Website or app live chat"),
    ],
    C.CAMPAIGN_TYPE: [
        ("email_blast", "Email Blast", "Single bulk email to a lead segment"),
        ("whatsapp_campaign", "WhatsApp Campaign", "Bulk WhatsApp message campaign"),
        ("sms_blast", "SMS Blast", "Bulk SMS message campaign"),
        ("drip", "Drip Campaign", "Automated multi-step email/message sequence"),
        ("follow_up", "Follow-Up Sequence", "Automated follow-up reminders"),
        ("event_invitation", "Event Invitation", "Event or launch invitation campaign"),
        ("newsletter", "Newsletter", "Periodic newsletter distribution"),
    ],
    C.CALL_DISPOSITION: [
        ("answered", "Answered", "Call was answered and conversation held"),
        ("no_answer", "No Answer", "No answer after ringing"),
        ("voicemail", "Voicemail", "Went to voicemail, message left"),
        ("busy", "Busy", "Line was busy"),
        ("wrong_number", "Wrong Number", "Wrong number or disconnected"),
        ("dropped", "Dropped", "Call dropped or connection lost"),
        ("callback_requested", "Callback Requested", "Lead requested a callback"),
    ],
    C.MEETING_TYPE: [
        ("in_person", "In-Person", "Face-to-face meeting at office or location"),
        ("video_call", "Video Call", "Virtual meeting via video conferencing"),
        ("phone_conference", "Phone Conference", "Audio-only conference call"),
        ("site_visit", "Site Visit", "On-site property or project visit"),
        ("open_house", "Open House", "Open house or showroom event"),
        ("roadshow", "Roadshow", "Off-site marketing or sales event"),
    ],
    C.FOLLOW_UP_REASON: [
        ("initial_contact", "Initial Contact", "First outreach to new lead"),
        ("document_follow_up", "Document Follow-Up", "Follow up on sent documents"),
        ("price_discussion", "Price Discussion", "Pricing or payment plan discussion"),
        ("site_visit_scheduling", "Site Visit Scheduling", "Arrange property viewing"),
        ("offer_negotiation", "Offer Negotiation", "Negotiate terms or counter-offer"),
        ("reservation_confirmation", "Reservation Confirmation", "Confirm reservation details"),
        ("spa_execution", "SPA Execution", "Follow up on SPA signing"),
        ("payment_reminder", "Payment Reminder", "Remind about pending payment"),
        ("post_sale_check_in", "Post-Sale Check-In", "Post-purchase relationship follow-up"),
        ("re_engagement", "Re-Engagement", "Re-engage dormant or cold lead"),
    ],
    C.LEAD_SOURCE_CHANNEL: [
        ("website", "Website", "Company website inquiry form"),
        ("social_media", "Social Media", "Facebook, Instagram, LinkedIn, etc."),
        ("referral", "Referral", "Referred by existing client or broker"),
        ("walk_in", "Walk-In", "Walk-in to sales office or showroom"),
        ("exhibition", "Exhibition", "Property exhibition or expo"),
        ("cold_call", "Cold Call", "Outbound cold calling"),
        ("print_media", "Print Media", "Newspaper, magazine, or billboard"),
        ("digital_ads", "Digital Ads", "Google, Meta, or other digital ads"),
        ("broker_network", "Broker Network", "Broker or agent network"),
        ("portal_listing", "Portal Listing", "Property portal (Bayut, Property Finder, etc.)"),
    ],
    C.COMMISSION_TYPE: [
        ("percentage", "Percentage", "Percentage of deal value"),
        ("fixed", "Fixed Amount", "Fixed monetary amount per deal"),
        ("tiered", "Tiered", "Tiered rates based on deal value brackets"),
    ],
    C.COMMISSION_TRIGGER: [
        ("reservation", "On Reservation", "Commission triggered at reservation stage"),
        ("spa_issued", "On SPA Issuance", "Commission triggered on Sale & Purchase Agreement issuance"),
        ("closed", "On Deal Close", "Commission triggered at deal close"),
        ("milestone", "Milestone-Based", "Commission triggered at specific project milestones"),
    ],

    # -----------------------------------------------------------------------
    # Finance — Extended
    # -----------------------------------------------------------------------
    C.SPV_ENTITY_TYPE: [
        ("company", "Company", "Standard registered company"),
        ("llc", "LLC", "Limited liability company"),
        ("llp", "LLP", "Limited liability partnership"),
        ("trust", "Trust", "Trust structure"),
        ("fund", "Fund", "Investment fund vehicle"),
        ("other", "Other", "Other legal entity type"),
    ],
    C.PAYMENT_PLAN_TYPE: [
        ("fixed_installment", "Fixed Installment", "Equal recurring installment payments"),
        ("milestone_based", "Milestone-Based", "Payments tied to project milestones"),
        ("percentage_based", "Percentage-Based", "Payments as percentage of total value"),
        ("custom", "Custom Schedule", "Custom payment schedule"),
    ],
    C.PAYMENT_FREQUENCY: [
        ("weekly", "Weekly", "Once per week"),
        ("biweekly", "Bi-Weekly", "Once every two weeks"),
        ("monthly", "Monthly", "Once per month"),
        ("quarterly", "Quarterly", "Once every three months"),
        ("semi_annual", "Semi-Annual", "Once every six months"),
        ("annual", "Annual", "Once per year"),
    ],
    C.BUDGET_PERIOD: [
        ("annual", "Annual", "Yearly budget period"),
        ("quarterly", "Quarterly", "Three-month budget period"),
        ("monthly", "Monthly", "Monthly budget period"),
    ],

    # -----------------------------------------------------------------------
    # HR
    # -----------------------------------------------------------------------
    C.EMPLOYMENT_TYPE: [
        ("full_time", "Full-Time", "Permanent full-time employment"),
        ("part_time", "Part-Time", "Permanent part-time employment"),
        ("contract", "Contract", "Fixed-term contract engagement"),
        ("temporary", "Temporary", "Short-term temporary assignment"),
        ("intern", "Intern", "Internship or work-experience placement"),
        ("secondment", "Secondment", "Temporary transfer from another organization"),
    ],
    C.POSITION_LEVEL: [
        ("intern", "Intern", "Entry-level intern or trainee"),
        ("junior", "Junior", "Junior-level individual contributor"),
        ("mid", "Mid-Level", "Mid-level individual contributor"),
        ("senior", "Senior", "Senior individual contributor"),
        ("lead", "Lead", "Technical or functional team lead"),
        ("manager", "Manager", "People or project manager"),
        ("director", "Director", "Department or function director"),
        ("vp", "Vice President", "Vice president or senior director"),
        ("c_suite", "C-Suite", "Chief officer (CEO, CFO, COO, CTO, etc.)"),
    ],

    # -----------------------------------------------------------------------
    # HR — Employee Directory
    # -----------------------------------------------------------------------
    C.EMERGENCY_CONTACT_RELATIONSHIP: [
        ("parent", "Parent", "Mother or father"),
        ("spouse", "Spouse", "Husband, wife, or life partner"),
        ("sibling", "Sibling", "Brother or sister"),
        ("child", "Child", "Son or daughter"),
        ("friend", "Friend", "Close friend or companion"),
        ("other", "Other", "Other relationship"),
    ],
    C.ID_DOCUMENT_TYPE: [
        ("national_id", "National ID", "Government-issued national identification card"),
        ("passport", "Passport", "International travel passport"),
        ("driving_license", "Driving License", "Motor vehicle driving license"),
        ("residence_visa", "Residence Visa", "Residence permit or visa"),
        ("work_permit", "Work Permit", "Employment or work permit"),
        ("tax_id", "Tax ID", "Tax identification number or certificate"),
    ],
    C.HR_DOCUMENT_CATEGORY: [
        ("employment_contract", "Employment Contract", "Original employment contract"),
        ("contract_amendment", "Contract Amendment", "Amendment to existing employment contract"),
        ("contract_renewal", "Contract Renewal", "Renewal of employment contract"),
        ("nda", "NDA", "Non-disclosure agreement"),
        ("non_compete", "Non-Compete", "Non-compete agreement"),
        ("offer_letter", "Offer Letter", "Job offer letter"),
        ("termination_letter", "Termination Letter", "Employment termination notice"),
        ("warning_letter", "Warning Letter", "Disciplinary warning letter"),
        ("certificate", "Certificate", "Employment or experience certificate"),
        ("training_certificate", "Training Certificate", "Training completion certificate"),
        ("policy_acknowledgement", "Policy Acknowledgement", "Company policy acknowledgement form"),
        ("other", "Other", "Other HR document"),
    ],
    C.COMPENSATION_PAY_FREQUENCY: [
        ("monthly", "Monthly", "Paid once per month"),
        ("bi_weekly", "Bi-Weekly", "Paid every two weeks"),
        ("weekly", "Weekly", "Paid once per week"),
        ("annual", "Annual", "Paid once per year"),
    ],
    C.EMPLOYMENT_STATUS: [
        ("active", "Active", "Currently employed and active"),
        ("on_leave", "On Leave", "On approved leave of absence"),
        ("probation", "Probation", "Serving probationary period"),
        ("notice_period", "Notice Period", "Serving notice period"),
        ("terminated", "Terminated", "Employment terminated"),
        ("resigned", "Resigned", "Voluntarily resigned"),
    ],
    C.CONTRACT_TYPE: [
        ("permanent", "Permanent", "Permanent or indefinite employment contract"),
        ("fixed_term", "Fixed-Term", "Contract with a defined end date"),
        ("temporary", "Temporary", "Short-term temporary engagement"),
        ("freelance", "Freelance", "Freelance or independent contractor"),
        ("internship", "Internship", "Internship or work-experience contract"),
        ("secondment", "Secondment", "Temporary transfer from another organization"),
    ],

    # -----------------------------------------------------------------------
    # HR — Recruitment & Hiring
    # -----------------------------------------------------------------------
    C.REQUISITION_TYPE: [
        ("new_position", "New Position", "Request for a newly created role"),
        ("replacement", "Replacement", "Backfill for an existing vacancy"),
        ("expansion", "Expansion", "Additional headcount for team growth"),
        ("temp_to_perm", "Temp-to-Perm", "Convert temporary role to permanent"),
        ("intern_conversion", "Intern Conversion", "Convert internship to full-time"),
    ],
    C.CANDIDATE_SOURCE: [
        ("referral", "Referral", "Employee or external referral"),
        ("job_board", "Job Board", "Online job board posting"),
        ("company_website", "Company Website", "Direct application via company careers page"),
        ("recruiter", "Recruiter", "External recruitment agency"),
        ("social_media", "Social Media", "LinkedIn, Twitter, or other social platforms"),
        ("walk_in", "Walk-In", "Walk-in or direct approach"),
        ("career_fair", "Career Fair", "University or industry career fair"),
    ],
    C.INTERVIEW_TYPE: [
        ("phone_screen", "Phone Screen", "Initial phone screening call"),
        ("video_call", "Video Call", "Remote video interview"),
        ("technical", "Technical", "Technical skills assessment interview"),
        ("behavioral", "Behavioral", "Behavioral and situational interview"),
        ("panel", "Panel", "Multi-interviewer panel session"),
        ("final_round", "Final Round", "Final decision-making interview"),
        ("hr_screening", "HR Screening", "HR-led culture and logistics screening"),
    ],
    C.REJECTION_REASON: [
        ("not_qualified", "Not Qualified", "Does not meet minimum qualifications"),
        ("overqualified", "Overqualified", "Exceeds role requirements significantly"),
        ("salary_mismatch", "Salary Mismatch", "Compensation expectations do not align"),
        ("poor_culture_fit", "Poor Culture Fit", "Not aligned with company culture or values"),
        ("position_filled", "Position Filled", "Role has already been filled"),
        ("candidate_withdrew", "Candidate Withdrew", "Candidate withdrew from the process"),
        ("failed_background_check", "Failed Background Check", "Did not pass background or reference check"),
    ],
}


class Command(BaseCommand):
    help = "Seed master data entries for all MDM categories (~200 entries). Idempotent."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for category, entries in SEED_DATA.items():
            for idx, (code, label, description) in enumerate(entries):
                _, was_created = MasterDataEntry.objects.update_or_create(
                    category=category,
                    code=code,
                    defaults={
                        "label": label,
                        "description": description,
                        "sort_order": idx * 10,
                        "is_system": True,
                        "is_active": True,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        total = created + updated
        self.stdout.write(
            self.style.SUCCESS(
                f"Master data seeded: {total} entries ({created} created, {updated} updated) "
                f"across {len(SEED_DATA)} categories."
            )
        )

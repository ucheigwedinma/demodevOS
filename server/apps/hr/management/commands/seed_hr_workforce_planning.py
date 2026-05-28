"""
Seed demo data for HR Workforce Planning.

Usage:
    python manage.py seed_hr_workforce_planning
    python manage.py seed_hr_workforce_planning --flush

Creates:
    - PositionRoles (functional role templates with skills & KPIs)
    - Positions (across departments)
    - PositionAssignments (user ↔ position links)
    - EmployeeRecords (HR employment data per user)
    - CompensationRecords (salary packages)
    - PositionBudgets (FY headcount & budget)
    - Vacancies (open, on-hold, filled, cancelled)
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Organization
from apps.hr.models import (
    CompensationRecord,
    EmployeeRecord,
    Position,
    PositionAssignment,
    PositionBudget,
    PositionRole,
    Vacancy,
)
from apps.settings.models import Department, Division

User = get_user_model()

SEED_TAG = "[demo-seed]"
CURRENT_YEAR = date.today().year

# ---------------------------------------------------------------------------
# Org structure
# ---------------------------------------------------------------------------

ORG_STRUCTURE = {
    "Operations": [
        "Construction",
        "Project Management",
        "Quality Assurance",
    ],
    "Corporate": [
        "Finance & Accounting",
        "Human Resources",
        "Legal & Compliance",
        "IT & Systems",
    ],
    "Commercial": [
        "Sales & Marketing",
        "Customer Relations",
        "Procurement",
    ],
}

# ---------------------------------------------------------------------------
# Position Roles: code, name, grade, level, employment_type, sal_min, sal_max,
#   key_responsibilities, hard_skills, soft_skills, kpi_metrics
# ---------------------------------------------------------------------------

ROLE_TEMPLATES = [
    # -- Operations --
    (
        "PM-SR", "Senior Project Manager", "G7", "senior", "full_time", 180_000, 240_000,
        "Lead end-to-end delivery of large-scale real estate projects. Manage budgets, schedules, and stakeholder relationships. Oversee team of PMs and engineers.",
        ["PMP/PRINCE2", "Primavera P6", "MS Project", "Contract administration", "Risk management"],
        ["Leadership", "Negotiation", "Strategic thinking", "Conflict resolution"],
        ["Project delivery on-time %", "Budget variance %", "Client satisfaction score", "Team retention rate"],
    ),
    (
        "PM-MID", "Project Manager", "G6", "mid", "full_time", 130_000, 175_000,
        "Manage day-to-day project execution including scheduling, cost tracking, and subcontractor coordination.",
        ["Primavera P6", "AutoCAD", "Cost control", "Procurement planning"],
        ["Communication", "Time management", "Problem-solving"],
        ["Milestone completion rate", "RFI turnaround time", "Change order volume"],
    ),
    (
        "SE-SR", "Senior Site Engineer", "G6", "senior", "full_time", 120_000, 160_000,
        "Supervise on-site construction activities, ensure quality standards, coordinate with design consultants.",
        ["Structural engineering", "AutoCAD", "Revit", "Quality control", "Surveying"],
        ["Attention to detail", "Decision-making", "Team coordination"],
        ["Defect rate", "Safety incident count", "Daily progress vs plan"],
    ),
    (
        "SE-MID", "Site Engineer", "G5", "mid", "full_time", 85_000, 115_000,
        "Execute construction works per drawings and specs. Conduct material testing and daily site reporting.",
        ["AutoCAD", "Concrete technology", "Surveying", "Material testing"],
        ["Reliability", "Technical communication"],
        ["Inspection pass rate", "Report submission timeliness"],
    ),
    (
        "QS-SR", "Senior Quantity Surveyor", "G6", "senior", "full_time", 125_000, 165_000,
        "Prepare BOQs, manage cost estimates, evaluate variation claims, and produce monthly cost reports.",
        ["CostX", "FIDIC contracts", "BOQ preparation", "Tendering", "Final account settlement"],
        ["Analytical thinking", "Negotiation", "Precision"],
        ["Cost forecast accuracy", "Claim settlement turnaround", "Procurement savings %"],
    ),
    (
        "QS-MID", "Quantity Surveyor", "G5", "mid", "full_time", 80_000, 110_000,
        "Assist with cost estimation, measurement, and interim payment certifications.",
        ["BOQ take-off", "Excel", "Measurement standards"],
        ["Numerical accuracy", "Organization"],
        ["IPC processing time", "Measurement accuracy"],
    ),
    (
        "HSE-MGR", "HSE Manager", "G6", "manager", "full_time", 130_000, 170_000,
        "Develop and enforce HSE policies. Conduct audits, investigate incidents, and drive safety culture.",
        ["NEBOSH", "IOSH", "ISO 45001", "Incident investigation", "Risk assessment"],
        ["Leadership", "Assertiveness", "Training delivery"],
        ["LTIR", "Near-miss reporting rate", "Audit compliance score"],
    ),
    (
        "HSE-OFF", "HSE Officer", "G4", "mid", "full_time", 60_000, 85_000,
        "Conduct daily safety inspections, toolbox talks, and maintain safety documentation.",
        ["First aid", "Fire safety", "Permit to work systems"],
        ["Vigilance", "Communication"],
        ["Inspection completion rate", "Toolbox talk attendance"],
    ),
    (
        "FOREMAN", "Site Foreman", "G4", "mid", "full_time", 55_000, 75_000,
        "Directly supervise labor crews on specific trade activities. Ensure work quality and productivity.",
        ["Trade supervision", "Blueprint reading", "Material management"],
        ["Hands-on leadership", "Crew management"],
        ["Daily output vs target", "Material wastage %"],
    ),
    (
        "QA-INSP", "QA Inspector", "G4", "mid", "full_time", 65_000, 90_000,
        "Perform material and workmanship inspections. Document non-conformances and verify corrective actions.",
        ["NDT basics", "ISO 9001", "Inspection checklists", "Concrete & steel testing"],
        ["Thoroughness", "Objectivity"],
        ["NCR closure rate", "Inspection coverage %"],
    ),
    # -- Corporate --
    (
        "FIN-MGR", "Finance Manager", "G6", "manager", "full_time", 140_000, 185_000,
        "Oversee financial reporting, budgeting, and cash flow management. Ensure regulatory compliance.",
        ["IFRS", "Financial modelling", "ERP systems", "Tax compliance", "Audit coordination"],
        ["Analytical thinking", "Strategic planning", "Stakeholder management"],
        ["Reporting deadline adherence", "Audit findings count", "Budget accuracy"],
    ),
    (
        "ACCT-SR", "Senior Accountant", "G5", "senior", "full_time", 90_000, 125_000,
        "Manage general ledger, prepare financial statements, and oversee accounts payable/receivable.",
        ["ACCA/CPA", "SAP/ERP", "Reconciliation", "Tax filing"],
        ["Accuracy", "Deadline orientation"],
        ["Reconciliation accuracy", "Month-end close time"],
    ),
    (
        "ACCT-MID", "Accountant", "G4", "mid", "full_time", 60_000, 85_000,
        "Process transactions, maintain ledger entries, and assist with monthly close.",
        ["Bookkeeping", "Excel", "ERP data entry"],
        ["Attention to detail", "Reliability"],
        ["Transaction processing time", "Error rate"],
    ),
    (
        "HR-MGR", "HR Manager", "G6", "manager", "full_time", 130_000, 170_000,
        "Lead HR operations including recruitment, employee relations, performance management, and compliance.",
        ["Employment law", "HRIS", "Talent management", "Compensation & benefits", "L&D"],
        ["Empathy", "Conflict resolution", "Strategic thinking"],
        ["Time to hire", "Employee engagement score", "Turnover rate", "Training hours per employee"],
    ),
    (
        "HR-OFF", "HR Officer", "G4", "mid", "full_time", 55_000, 80_000,
        "Handle day-to-day HR administration: onboarding, leave management, and employee queries.",
        ["HRIS", "Payroll processing", "Onboarding checklists"],
        ["Approachability", "Organization", "Discretion"],
        ["Onboarding completion rate", "Query resolution time"],
    ),
    (
        "LEGAL-SR", "Senior Legal Counsel", "G7", "senior", "full_time", 170_000, 220_000,
        "Draft and review contracts, advise on regulatory compliance, manage disputes and litigation.",
        ["Contract law", "Real estate law", "Corporate governance", "Dispute resolution"],
        ["Analytical reasoning", "Persuasion", "Attention to detail"],
        ["Contract review turnaround", "Dispute resolution rate", "Compliance incident count"],
    ),
    (
        "IT-MGR", "IT Manager", "G6", "manager", "full_time", 140_000, 185_000,
        "Manage IT infrastructure, cybersecurity, and software systems supporting business operations.",
        ["Cloud infrastructure", "Cybersecurity", "ERP administration", "IT governance"],
        ["Problem-solving", "Vendor management", "Strategic planning"],
        ["System uptime %", "Security incident count", "IT ticket resolution time"],
    ),
    (
        "IT-ADMIN", "Systems Administrator", "G4", "mid", "full_time", 65_000, 95_000,
        "Maintain servers, networks, and end-user systems. Handle backups and security patching.",
        ["Linux/Windows server", "Networking", "Docker", "Backup systems"],
        ["Responsiveness", "Methodical approach"],
        ["Patch compliance %", "Backup success rate", "Ticket SLA adherence"],
    ),
    # -- Commercial --
    (
        "SALES-MGR", "Sales Manager", "G6", "manager", "full_time", 130_000, 175_000,
        "Lead the sales team, develop sales strategies, manage pipeline, and hit revenue targets.",
        ["CRM platforms", "Sales forecasting", "Negotiation", "Market analysis"],
        ["Persuasion", "Target orientation", "Team motivation"],
        ["Revenue vs target", "Conversion rate", "Pipeline value", "Team quota attainment"],
    ),
    (
        "SALES-EXEC", "Sales Executive", "G4", "mid", "full_time", 55_000, 80_000,
        "Engage with leads, conduct property viewings, negotiate deals, and close sales.",
        ["CRM data entry", "Property presentation", "Payment plan structuring"],
        ["Relationship building", "Persistence", "Product knowledge"],
        ["Units sold", "Lead response time", "Client satisfaction"],
    ),
    (
        "MKT-COORD", "Marketing Coordinator", "G3", "junior", "full_time", 45_000, 65_000,
        "Coordinate marketing campaigns, manage social media, and produce marketing collateral.",
        ["Digital marketing", "Adobe Creative Suite", "Social media management", "Content writing"],
        ["Creativity", "Organization", "Multitasking"],
        ["Campaign reach", "Lead generation count", "Content publishing cadence"],
    ),
    (
        "PROC-MGR", "Procurement Manager", "G6", "manager", "full_time", 125_000, 165_000,
        "Manage procurement strategy, supplier relationships, and purchasing compliance.",
        ["Strategic sourcing", "Contract negotiation", "Vendor management", "ERP procurement modules"],
        ["Negotiation", "Analytical thinking", "Integrity"],
        ["Cost savings %", "Supplier on-time delivery", "PO cycle time"],
    ),
    (
        "PROC-OFF", "Procurement Officer", "G4", "mid", "full_time", 60_000, 85_000,
        "Process purchase requisitions, solicit quotes, and manage purchase orders.",
        ["RFQ processing", "Vendor evaluation", "ERP data entry"],
        ["Organization", "Follow-through"],
        ["PO processing time", "Quote comparison accuracy"],
    ),
    (
        "CRM-EXEC", "CRM Executive", "G3", "junior", "full_time", 45_000, 60_000,
        "Manage customer relationships post-sale, handle complaints, and drive retention.",
        ["CRM platforms", "Customer service", "Data entry", "Reporting"],
        ["Patience", "Empathy", "Communication"],
        ["Customer retention rate", "Complaint resolution time", "NPS score"],
    ),
]

# Role code → departments
ROLE_DEPT_MAP = {
    "PM-SR": ["Project Management"],
    "PM-MID": ["Project Management"],
    "SE-SR": ["Construction"],
    "SE-MID": ["Construction"],
    "QS-SR": ["Construction", "Finance & Accounting"],
    "QS-MID": ["Construction"],
    "HSE-MGR": ["Quality Assurance"],
    "HSE-OFF": ["Quality Assurance", "Construction"],
    "FOREMAN": ["Construction"],
    "QA-INSP": ["Quality Assurance"],
    "FIN-MGR": ["Finance & Accounting"],
    "ACCT-SR": ["Finance & Accounting"],
    "ACCT-MID": ["Finance & Accounting"],
    "HR-MGR": ["Human Resources"],
    "HR-OFF": ["Human Resources"],
    "LEGAL-SR": ["Legal & Compliance"],
    "IT-MGR": ["IT & Systems"],
    "IT-ADMIN": ["IT & Systems"],
    "SALES-MGR": ["Sales & Marketing"],
    "SALES-EXEC": ["Sales & Marketing"],
    "MKT-COORD": ["Sales & Marketing"],
    "PROC-MGR": ["Procurement"],
    "PROC-OFF": ["Procurement"],
    "CRM-EXEC": ["Customer Relations"],
}

VACANCY_REASONS = [
    "New position approved in FY budget",
    "Replacement — previous holder relocated",
    "Replacement — previous holder promoted",
    "Replacement — previous holder resigned",
    "Team expansion to support new project pipeline",
    "Critical role — succession gap identified",
    "Restructuring — new department created",
]

CONTRACT_TYPES = ["permanent", "fixed_term", "temporary"]


class Command(BaseCommand):
    help = "Seed demo data for HR Workforce Planning (positions, budgets, employees, vacancies)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            dest="organization_ids",
            action="append",
            type=int,
            help=(
                "Target a specific organization id. "
                "Repeat the flag to seed multiple organizations. "
                "If omitted, all organizations are seeded."
            ),
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data before inserting.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        organization_ids = options.get("organization_ids") or []
        org_qs = Organization.objects.order_by("id")
        if organization_ids:
            org_qs = org_qs.filter(id__in=organization_ids)
        orgs = list(org_qs)

        if not orgs:
            self.stderr.write(self.style.ERROR("No Organization found. Create one first."))
            return

        if organization_ids:
            found_ids = {org.id for org in orgs}
            missing_ids = [org_id for org_id in organization_ids if org_id not in found_ids]
            if missing_ids:
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping unknown organization ids: {', '.join(str(value) for value in missing_ids)}"
                    )
                )

        for org in orgs:
            users = list(User.objects.filter(profile__organization=org, is_active=True)[:20])
            if not users:
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping org {org.id} ({org}) because it has no active users."
                    )
                )
                continue

            if options["flush"]:
                self._flush(org)

            self.stdout.write(f"Seeding workforce planning data for: {org} ...")

            depts = self._ensure_departments(org)
            roles = self._seed_position_roles(org)
            positions = self._seed_positions(org, depts, roles)
            self._seed_employee_records(org, users)
            self._seed_position_assignments(org, positions, users)
            self._seed_compensation_records(org, users)
            self._seed_position_budgets(org, depts, positions, users)
            self._seed_vacancies(org, positions, users)

        self.stdout.write(self.style.SUCCESS("Done! Workforce planning data seeded."))

    # ── Flush ──────────────────────────────────────────────────────────────

    def _flush(self, org):
        self.stdout.write("Flushing previous workforce planning demo data ...")
        Vacancy.objects.filter(organization=org, notes__startswith=SEED_TAG).delete()
        PositionBudget.objects.filter(organization=org, notes__startswith=SEED_TAG).delete()
        CompensationRecord.objects.filter(organization=org, notes__startswith=SEED_TAG).delete()
        PositionAssignment.objects.filter(organization=org, notes__startswith=SEED_TAG).delete()
        EmployeeRecord.objects.filter(organization=org, notes__startswith=SEED_TAG).delete()
        Position.objects.filter(organization=org, description__startswith=SEED_TAG).delete()
        PositionRole.objects.filter(organization=org, description__startswith=SEED_TAG).delete()
        self.stdout.write("  Flushed.")

    # ── Departments ────────────────────────────────────────────────────────

    def _ensure_departments(self, org):
        dept_map = {}
        for div_name, dept_names in ORG_STRUCTURE.items():
            division, _ = Division.objects.get_or_create(
                organization=org,
                name=div_name,
                defaults={"code": div_name[:3].upper(), "is_active": True},
            )
            for dept_name in dept_names:
                dept, _ = Department.objects.get_or_create(
                    division=division,
                    name=dept_name,
                    defaults={
                        "code": dept_name[:4].upper().replace(" ", ""),
                        "is_active": True,
                    },
                )
                dept_map[dept_name] = dept
        return dept_map

    # ── Position Roles (enriched) ─────────────────────────────────────────

    def _seed_position_roles(self, org):
        role_map = {}
        for tpl in ROLE_TEMPLATES:
            code, name, grade = tpl[0], tpl[1], tpl[2]
            responsibilities = tpl[7]
            hard_skills = tpl[8]
            soft_skills = tpl[9]
            kpi_metrics = tpl[10]

            role, created = PositionRole.objects.update_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "grade": grade,
                    "description": f"{SEED_TAG} Auto-seeded role template",
                    "key_responsibilities": responsibilities,
                    "hard_skills": hard_skills,
                    "soft_skills": soft_skills,
                    "kpi_metrics": kpi_metrics,
                    "is_active": True,
                },
            )
            role_map[code] = role
            if created:
                self.stdout.write(f"  + PositionRole: {code} — {name}")
        self.stdout.write(f"  {len(role_map)} position roles ready")
        return role_map

    # ── Positions ──────────────────────────────────────────────────────────

    def _seed_positions(self, org, depts, roles):
        positions = []
        pos_counter = 0

        for tpl in ROLE_TEMPLATES:
            code, name, _grade, level, etype = tpl[0], tpl[1], tpl[2], tpl[3], tpl[4]
            role = roles[code]
            dept_names = ROLE_DEPT_MAP.get(code, [])

            for dept_name in dept_names:
                dept = depts.get(dept_name)
                if not dept:
                    continue

                pos_counter += 1
                pos_code = f"POS-{pos_counter:03d}"

                # ~60% filled, ~30% vacant, ~10% proposed
                rand = random.random()
                if rand < 0.60:
                    slot_status = Position.SlotStatus.FILLED
                    vacant_since = None
                elif rand < 0.90:
                    slot_status = Position.SlotStatus.VACANT
                    vacant_since = date.today() - timedelta(days=random.randint(7, 120))
                else:
                    slot_status = Position.SlotStatus.PROPOSED
                    vacant_since = None

                position, created = Position.objects.get_or_create(
                    organization=org,
                    code=pos_code,
                    defaults={
                        "title": name,
                        "role": role,
                        "department": dept,
                        "employment_type": etype,
                        "level": level,
                        "status": Position.Status.ACTIVE,
                        "slot_status": slot_status,
                        "vacant_since": vacant_since,
                        "headcount_budget": 1,
                        "criticality_score": random.randint(20, 95),
                        "description": f"{SEED_TAG} {name} in {dept_name}",
                        "is_active": True,
                    },
                )
                positions.append(position)
                if created:
                    self.stdout.write(f"  + Position: {pos_code} — {name} ({dept_name}) [{slot_status}]")

        self.stdout.write(f"  {len(positions)} positions total")
        return positions

    # ── Employee Records ───────────────────────────────────────────────────

    def _seed_employee_records(self, org, users):
        created_count = 0
        for user in users:
            hire_offset = random.randint(90, 1800)
            hire_date = date.today() - timedelta(days=hire_offset)
            probation_end = hire_date + timedelta(days=90)

            # Most are active, a few on probation or leave
            rand = random.random()
            if rand < 0.70:
                status = EmployeeRecord.EmploymentStatus.ACTIVE
            elif rand < 0.85:
                status = EmployeeRecord.EmploymentStatus.PROBATION
                hire_date = date.today() - timedelta(days=random.randint(10, 80))
                probation_end = hire_date + timedelta(days=90)
            elif rand < 0.95:
                status = EmployeeRecord.EmploymentStatus.ON_LEAVE
            else:
                status = EmployeeRecord.EmploymentStatus.NOTICE_PERIOD

            contract_type = random.choice(CONTRACT_TYPES)
            contract_start = hire_date
            contract_end = None
            if contract_type == "fixed_term":
                contract_end = hire_date + timedelta(days=random.choice([365, 730, 1095]))
            elif contract_type == "temporary":
                contract_end = hire_date + timedelta(days=random.choice([90, 180]))

            _, was_created = EmployeeRecord.objects.get_or_create(
                organization=org,
                user=user,
                defaults={
                    "hire_date": hire_date,
                    "probation_end_date": probation_end,
                    "contract_start_date": contract_start,
                    "contract_end_date": contract_end,
                    "contract_type": contract_type,
                    "employment_status": status,
                    "notes": f"{SEED_TAG} Auto-seeded employee record",
                },
            )
            if was_created:
                created_count += 1

        self.stdout.write(f"  {created_count} employee records created")

    # ── Position Assignments ───────────────────────────────────────────────

    def _seed_position_assignments(self, org, positions, users):
        created_count = 0
        filled_positions = [p for p in positions if p.slot_status == Position.SlotStatus.FILLED]
        available_users = list(users)
        random.shuffle(available_users)

        for i, pos in enumerate(filled_positions):
            if i >= len(available_users):
                break

            user = available_users[i]
            # Hire date from employee record if available
            try:
                emp = EmployeeRecord.objects.get(organization=org, user=user)
                start_date = emp.hire_date or (date.today() - timedelta(days=random.randint(90, 730)))
            except EmployeeRecord.DoesNotExist:
                start_date = date.today() - timedelta(days=random.randint(90, 730))

            _, was_created = PositionAssignment.objects.get_or_create(
                organization=org,
                user=user,
                position=pos,
                defaults={
                    "start_date": start_date,
                    "is_primary": True,
                    "is_active": True,
                    "notes": f"{SEED_TAG} Auto-assigned to {pos.title}",
                },
            )
            if was_created:
                created_count += 1

        self.stdout.write(f"  {created_count} position assignments created")

    # ── Compensation Records ───────────────────────────────────────────────

    def _seed_compensation_records(self, org, users):
        created_count = 0
        approver = users[0] if users else None

        # Build a user → position lookup from assignments
        user_positions = {}
        for assignment in PositionAssignment.objects.filter(
            organization=org, is_active=True
        ).select_related("position__role"):
            user_positions[assignment.user_id] = assignment.position

        # Build a role code → salary range lookup
        salary_ranges = {}
        for tpl in ROLE_TEMPLATES:
            salary_ranges[tpl[0]] = (tpl[5], tpl[6])

        for user in users:
            pos = user_positions.get(user.id)
            if pos and pos.role:
                sal_min, sal_max = salary_ranges.get(pos.role.code, (50_000, 80_000))
            else:
                sal_min, sal_max = 50_000, 80_000

            base_salary = Decimal(str(random.randint(sal_min, sal_max)))
            allowances = Decimal(str(round(float(base_salary) * random.uniform(0.05, 0.15), 2)))
            bonus = Decimal(str(round(float(base_salary) * random.uniform(0, 0.10), 2)))
            total = base_salary + allowances + bonus

            try:
                emp = EmployeeRecord.objects.get(organization=org, user=user)
                effective = emp.hire_date or date(CURRENT_YEAR, 1, 1)
            except EmployeeRecord.DoesNotExist:
                effective = date(CURRENT_YEAR, 1, 1)

            _, was_created = CompensationRecord.objects.get_or_create(
                organization=org,
                user=user,
                effective_date=effective,
                defaults={
                    "base_salary": base_salary,
                    "currency": "USD",
                    "pay_frequency": "monthly",
                    "allowances": allowances,
                    "bonus": bonus,
                    "total_package": total,
                    "status": CompensationRecord.Status.ACTIVE,
                    "approved_by": approver,
                    "approved_at": timezone.now(),
                    "notes": f"{SEED_TAG} Initial compensation package",
                },
            )
            if was_created:
                created_count += 1

        self.stdout.write(f"  {created_count} compensation records created")

    # ── Position Budgets ───────────────────────────────────────────────────

    def _seed_position_budgets(self, org, depts, positions, users):
        created_count = 0
        approver = users[0] if users else None

        for dept_name, dept in depts.items():
            dept_positions = [p for p in positions if p.department_id == dept.id]
            if not dept_positions:
                continue

            filled = sum(1 for p in dept_positions if p.slot_status == Position.SlotStatus.FILLED)
            total = len(dept_positions)

            for year in [CURRENT_YEAR, CURRENT_YEAR + 1]:
                growth = random.randint(0, 3) if year == CURRENT_YEAR + 1 else 0
                approved_hc = total + growth
                avg_salary = sum(
                    r[5] + r[6]
                    for r in ROLE_TEMPLATES
                    if any(d == dept_name for d in ROLE_DEPT_MAP.get(r[0], []))
                ) / max(
                    2 * sum(
                        1 for r in ROLE_TEMPLATES
                        if any(d == dept_name for d in ROLE_DEPT_MAP.get(r[0], []))
                    ),
                    1,
                )
                budget_amt = Decimal(str(round(approved_hc * avg_salary * random.uniform(0.95, 1.10), 2)))

                if year == CURRENT_YEAR:
                    status = PositionBudget.Status.APPROVED
                else:
                    status = random.choice([PositionBudget.Status.DRAFT, PositionBudget.Status.APPROVED])

                _, was_created = PositionBudget.objects.get_or_create(
                    organization=org,
                    department=dept,
                    position=None,
                    fiscal_year=year,
                    defaults={
                        "approved_headcount": approved_hc,
                        "filled_headcount": filled if year == CURRENT_YEAR else 0,
                        "budget_amount": budget_amt,
                        "status": status,
                        "approved_by": approver if status == PositionBudget.Status.APPROVED else None,
                        "approved_at": timezone.now() if status == PositionBudget.Status.APPROVED else None,
                        "notes": f"{SEED_TAG} FY{year} headcount plan for {dept_name}",
                    },
                )
                if was_created:
                    created_count += 1

        self.stdout.write(f"  {created_count} position budgets created")

    # ── Vacancies ──────────────────────────────────────────────────────────

    def _seed_vacancies(self, org, positions, users):
        created_count = 0
        hiring_managers = users[:5] if len(users) >= 5 else users

        # Active vacancies for open slots
        vacant_positions = [
            p for p in positions
            if p.slot_status in (Position.SlotStatus.VACANT, Position.SlotStatus.PROPOSED)
        ]

        for pos in vacant_positions:
            rand = random.random()
            if rand < 0.40:
                priority = Vacancy.Priority.MEDIUM
            elif rand < 0.70:
                priority = Vacancy.Priority.HIGH
            elif rand < 0.90:
                priority = Vacancy.Priority.LOW
            else:
                priority = Vacancy.Priority.URGENT

            status = Vacancy.Status.ON_HOLD if random.random() < 0.15 else Vacancy.Status.OPEN
            hm = random.choice(hiring_managers)

            _, was_created = Vacancy.objects.get_or_create(
                organization=org,
                position=pos,
                status__in=[Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD],
                defaults={
                    "title": pos.title,
                    "status": status,
                    "priority": priority,
                    "hiring_manager": hm,
                    "target_fill_date": date.today() + timedelta(days=random.randint(14, 90)),
                    "reason": random.choice(VACANCY_REASONS),
                    "notes": f"{SEED_TAG} Auto-generated vacancy",
                },
            )
            if was_created:
                created_count += 1

        # Historical filled/cancelled vacancies
        filled_positions = [p for p in positions if p.slot_status == Position.SlotStatus.FILLED]
        for pos in random.sample(filled_positions, min(8, len(filled_positions))):
            days_ago = random.randint(30, 365)
            opened = date.today() - timedelta(days=days_ago)
            filled_dt = opened + timedelta(days=random.randint(14, 60))
            hm = random.choice(hiring_managers)

            is_cancelled = random.random() < 0.2
            status = Vacancy.Status.CANCELLED if is_cancelled else Vacancy.Status.FILLED

            _, was_created = Vacancy.objects.get_or_create(
                organization=org,
                position=pos,
                status=status,
                defaults={
                    "title": pos.title,
                    "priority": Vacancy.Priority.MEDIUM,
                    "hiring_manager": hm,
                    "target_fill_date": opened + timedelta(days=45),
                    "filled_date": filled_dt if not is_cancelled else None,
                    "filled_by": random.choice(users) if not is_cancelled else None,
                    "reason": random.choice(VACANCY_REASONS),
                    "notes": f"{SEED_TAG} Historical {'cancelled' if is_cancelled else 'filled'} vacancy",
                },
            )
            if was_created:
                created_count += 1

        self.stdout.write(f"  {created_count} vacancies created")

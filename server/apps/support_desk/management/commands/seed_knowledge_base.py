"""
Seed realistic knowledge-base articles for the Support Knowledge Center.

Usage:
    python manage.py seed_knowledge_base
    python manage.py seed_knowledge_base --flush
    python manage.py seed_knowledge_base --organization-id 2
    python manage.py seed_knowledge_base --organization-id 1 --organization-id 2 --flush
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Organization

DEMO_MARKER = "[demo-seed]"

ARTICLES = [
    # ── Account & Login ──────────────────────────────────────────────
    {
        "title": "How to Reset Your Password",
        "category": "Account & Login",
        "summary": "Step-by-step guide for resetting your account password via the login page or user settings.",
        "body": (
            "1. Navigate to the login screen and click 'Forgot Password'.\n"
            "2. Enter the email address associated with your account.\n"
            "3. Check your inbox for the password-reset link (valid for 30 minutes).\n"
            "4. Click the link and choose a new password (minimum 10 characters, at least one number and one special character).\n"
            "5. Log in with your new credentials.\n\n"
            "If you are already logged in, go to User Settings > Account & Login > Change Password.\n\n"
            "Tip: If you do not receive the email within 5 minutes, check your spam/junk folder or contact IT Support."
        ),
        "visibility": "internal",
    },
    {
        "title": "Setting Up Multi-Factor Authentication (MFA)",
        "category": "Account & Login",
        "summary": "Enable TOTP-based two-factor authentication to secure your account.",
        "body": (
            "Multi-factor authentication adds an extra layer of security beyond your password.\n\n"
            "Setup steps:\n"
            "1. Go to User Settings > Account & Login > Security.\n"
            "2. Click 'Enable MFA' and scan the QR code with an authenticator app (Google Authenticator, Authy, etc.).\n"
            "3. Enter the 6-digit verification code displayed in your app.\n"
            "4. Save the backup codes in a secure location.\n\n"
            "After enabling MFA you will be prompted for a code on every login.\n\n"
            "To disable MFA, return to the same settings page and click 'Disable MFA'. "
            "You will need to enter a valid code to confirm the change."
        ),
        "visibility": "internal",
    },
    # ── System Usage ─────────────────────────────────────────────────
    {
        "title": "Navigating the Dashboard",
        "category": "System Usage",
        "summary": "Overview of the main dashboard layout, widgets, and quick-action shortcuts.",
        "body": (
            "The dashboard is the first screen you see after logging in.\n\n"
            "Key sections:\n"
            "- **Quick Stats**: Organization-level KPIs at the top (revenue, active projects, open tickets).\n"
            "- **Activity Feed**: Recent actions across all modules — filterable by module.\n"
            "- **Shortcuts Bar**: Pin frequently-used pages for one-click access.\n"
            "- **Notifications Bell**: In-app notifications; click to view or manage preferences.\n\n"
            "Customization:\n"
            "- Drag widgets to reorder them.\n"
            "- Click the gear icon on any widget to configure its data source or time range.\n"
            "- Use Settings > Workspace Preferences to set your default landing page."
        ),
        "visibility": "internal",
    },
    {
        "title": "Using the Global Search",
        "category": "System Usage",
        "summary": "How to use the platform-wide search bar to find records, documents, and people.",
        "body": (
            "Press Ctrl+K (or Cmd+K on macOS) to open global search from any page.\n\n"
            "Search tips:\n"
            "- Type a record reference (e.g., INV-0042) to jump directly to it.\n"
            "- Use module prefixes to narrow results: 'bill:', 'lead:', 'project:'.\n"
            "- Search supports partial matches — 'Ade' will match 'Adebayo Holdings'.\n\n"
            "Results are grouped by module and sorted by relevance. "
            "Click any result to navigate to its detail page."
        ),
        "visibility": "internal",
    },
    # ── HR Policies ──────────────────────────────────────────────────
    {
        "title": "Annual Leave Policy",
        "category": "HR Policies",
        "summary": "Company policy on annual leave entitlement, accrual, carry-over, and request procedures.",
        "body": (
            "Entitlement:\n"
            "- Full-time employees: 20 working days per calendar year.\n"
            "- Part-time employees: pro-rated based on contracted hours.\n\n"
            "Accrual:\n"
            "- Leave accrues monthly (1.67 days/month for full-time).\n"
            "- New hires accrue from their start date.\n\n"
            "Carry-Over:\n"
            "- A maximum of 5 unused days may be carried into the next calendar year.\n"
            "- Carried-over days must be used by March 31.\n\n"
            "Request Process:\n"
            "1. Submit a leave request via HR > Leave Requests > New Request.\n"
            "2. Your reporting manager will receive a notification for approval.\n"
            "3. You will be notified once the request is approved or declined.\n\n"
            "Blackout periods may apply during month-end close or project milestones — "
            "check with your department head."
        ),
        "visibility": "internal",
    },
    {
        "title": "Employee Onboarding Checklist",
        "category": "HR Policies",
        "summary": "Standard onboarding checklist for new hires covering IT setup, compliance, and orientation.",
        "body": (
            "This checklist applies to all new employees from their first day.\n\n"
            "Day 1:\n"
            "- Collect employee ID badge from reception.\n"
            "- IT setup: laptop, email account, system access (IAM > Users > Invite).\n"
            "- Complete mandatory compliance training modules.\n"
            "- Meet reporting manager and team introductions.\n\n"
            "Week 1:\n"
            "- Review department objectives and current projects.\n"
            "- Complete HR paperwork (tax forms, bank details, emergency contacts).\n"
            "- Attend platform walkthrough session with IT.\n\n"
            "Month 1:\n"
            "- 30-day check-in with HR and reporting manager.\n"
            "- Complete all assigned onboarding tasks in HR > Onboarding.\n"
            "- Set personal KPIs with manager."
        ),
        "visibility": "internal",
    },
    # ── Finance Procedures ───────────────────────────────────────────
    {
        "title": "Invoice Submission Guidelines",
        "category": "Finance Procedures",
        "summary": "How to create and submit invoices for approval, including required fields and supporting documents.",
        "body": (
            "All invoices must be submitted through Finance > Invoices > New Invoice.\n\n"
            "Required fields:\n"
            "- Customer (select from CRM contacts)\n"
            "- Invoice date and due date\n"
            "- At least one line item with description, quantity, and unit price\n"
            "- Tax configuration (VAT rate auto-applied based on organization settings)\n\n"
            "Supporting documents:\n"
            "- Attach signed contracts or purchase orders where applicable.\n"
            "- For milestone-based billing, reference the project phase.\n\n"
            "Approval flow:\n"
            "1. Submit the invoice — status moves to 'Pending Approval'.\n"
            "2. Finance manager reviews and approves or returns with comments.\n"
            "3. Once approved, the invoice is sent to the customer.\n\n"
            "Payment tracking is automatic — the system matches incoming payments to open invoices."
        ),
        "visibility": "internal",
    },
    {
        "title": "Expense Reimbursement Process",
        "category": "Finance Procedures",
        "summary": "How to submit expense claims for reimbursement, including receipt requirements and approval timelines.",
        "body": (
            "Eligible expenses include travel, accommodation, meals (within per-diem limits), "
            "and pre-approved business purchases.\n\n"
            "Submission:\n"
            "1. Go to Finance > Expenses > New Claim.\n"
            "2. Enter expense details: date, category, amount, and description.\n"
            "3. Upload a photo or scan of the receipt (JPEG, PNG, or PDF).\n"
            "4. Submit for approval.\n\n"
            "Approval & Payment:\n"
            "- Your reporting manager approves the claim.\n"
            "- Finance processes approved claims within 5 business days.\n"
            "- Reimbursement is paid to your registered bank account.\n\n"
            "Claims must be submitted within 30 days of the expense date. "
            "Late submissions require written justification and CFO approval."
        ),
        "visibility": "internal",
    },
    # ── IT Support ───────────────────────────────────────────────────
    {
        "title": "VPN Access and Remote Work Setup",
        "category": "IT Support",
        "summary": "How to configure VPN access for secure remote work, including supported clients and troubleshooting.",
        "body": (
            "All remote access to internal systems must go through the company VPN.\n\n"
            "Setup:\n"
            "1. Download the approved VPN client (OpenVPN or WireGuard) from IT > Downloads.\n"
            "2. Import the configuration file emailed to you by IT.\n"
            "3. Enter your system credentials (same as your platform login).\n"
            "4. Connect to the VPN before accessing internal tools.\n\n"
            "Troubleshooting:\n"
            "- 'Authentication failed': Ensure MFA is enabled and enter the latest code.\n"
            "- 'Connection timed out': Check your internet connection; try a different network.\n"
            "- 'Certificate expired': Re-download the config file from IT > Downloads.\n\n"
            "If issues persist, raise a support ticket under IT Support > Network Access."
        ),
        "visibility": "internal",
    },
    {
        "title": "Requesting New Software or Hardware",
        "category": "IT Support",
        "summary": "Procedure for requesting new software licenses, hardware, or peripherals through IT procurement.",
        "body": (
            "All software and hardware requests must be submitted through the IT request process.\n\n"
            "Software:\n"
            "1. Check the approved software catalog in IT > Software Library.\n"
            "2. If the software is listed, click 'Request Access' — auto-approved within 24 hours.\n"
            "3. For unlisted software, submit a request with business justification.\n"
            "   IT Security will evaluate within 5 business days.\n\n"
            "Hardware:\n"
            "1. Submit a hardware request via Support Desk > Requests > New > IT Hardware.\n"
            "2. Include specifications, business justification, and budget code.\n"
            "3. Department head and IT manager must both approve.\n"
            "4. Procurement lead time is typically 7-14 business days.\n\n"
            "Emergency requests (e.g., broken laptop) should be flagged as 'Urgent' "
            "and will be processed within 24 hours."
        ),
        "visibility": "internal",
    },
    # ── Facilities ───────────────────────────────────────────────────
    {
        "title": "Meeting Room Booking Guidelines",
        "category": "Facilities",
        "summary": "How to book meeting rooms, check availability, and manage recurring reservations.",
        "body": (
            "Meeting rooms can be booked through the Calendar module or directly from the room display panels.\n\n"
            "Booking rules:\n"
            "- Maximum advance booking: 4 weeks.\n"
            "- Maximum single booking duration: 3 hours.\n"
            "- Recurring bookings (daily/weekly) require manager approval.\n"
            "- No-shows: rooms are automatically released 15 minutes after the scheduled start.\n\n"
            "Room types:\n"
            "- Huddle rooms (2-4 people): no AV equipment, whiteboard only.\n"
            "- Conference rooms (6-12 people): projector, video conferencing, whiteboard.\n"
            "- Board room (16+ people): full AV suite, recording capability.\n\n"
            "To request catering or special setup, add a note when booking or contact Facilities directly."
        ),
        "visibility": "internal",
    },
    {
        "title": "Office Access and Security Protocols",
        "category": "Facilities",
        "summary": "Building access procedures, visitor management, and after-hours entry policies.",
        "body": (
            "Standard office hours: 7:30 AM - 7:00 PM, Monday to Friday.\n\n"
            "Access:\n"
            "- Use your employee ID badge to tap in/out at building entry points.\n"
            "- After-hours access requires prior approval from your department head.\n"
            "- Lost badges: report immediately to Security and request a replacement from HR.\n\n"
            "Visitors:\n"
            "- All visitors must be pre-registered through the Visitor Management system.\n"
            "- Visitors receive a temporary badge at reception and must be escorted at all times.\n"
            "- Visitor badges must be returned upon departure.\n\n"
            "Emergency procedures:\n"
            "- Fire assembly points are marked on floor plans near each exit.\n"
            "- Fire drills are conducted quarterly — participation is mandatory.\n"
            "- Report any security concerns to the facilities team or dial the internal emergency line."
        ),
        "visibility": "internal",
    },
    # ── Investment Portfolio ──────────────────────────────────────────
    {
        "title": "Understanding Portfolio Performance Reports",
        "category": "Investment Portfolio",
        "summary": "How to read and interpret the portfolio analysis dashboards and performance metrics.",
        "body": (
            "The Portfolio Analysis module provides real-time performance metrics for all managed assets.\n\n"
            "Key metrics:\n"
            "- **Total Portfolio Value**: Sum of current market values across all properties.\n"
            "- **Occupancy Rate**: Percentage of leasable units currently occupied.\n"
            "- **Net Operating Income (NOI)**: Revenue minus operating expenses.\n"
            "- **Cap Rate**: NOI divided by current market value — measures return on investment.\n"
            "- **Cash-on-Cash Return**: Annual pre-tax cash flow divided by total cash invested.\n\n"
            "Dashboard views:\n"
            "- Overview: High-level summary with trend charts.\n"
            "- By Property: Drill down into individual property performance.\n"
            "- By Asset Class: Compare residential, commercial, and mixed-use segments.\n\n"
            "Reports can be exported as PDF or CSV from the Reports module."
        ),
        "visibility": "internal",
    },
    {
        "title": "Property Valuation Methodology",
        "category": "Investment Portfolio",
        "summary": "Overview of the valuation approaches used for property assets in the platform.",
        "body": (
            "The platform supports three standard valuation approaches:\n\n"
            "1. Income Approach (Capitalization):\n"
            "   - Estimates value based on expected income streams.\n"
            "   - Uses Net Operating Income (NOI) and market-derived cap rates.\n"
            "   - Best suited for income-producing commercial properties.\n\n"
            "2. Sales Comparison Approach:\n"
            "   - Values property based on recent sales of comparable properties.\n"
            "   - Adjustments made for location, size, condition, and amenities.\n"
            "   - Commonly used for residential properties.\n\n"
            "3. Cost Approach:\n"
            "   - Estimates the cost to replace the property minus depreciation.\n"
            "   - Used for new developments or special-purpose properties.\n\n"
            "Valuations can be entered manually or imported from external appraisals. "
            "The system tracks valuation history for trend analysis."
        ),
        "visibility": "internal",
    },
    # ── Partner Portal ───────────────────────────────────────────────
    {
        "title": "Partner Onboarding Process Overview",
        "category": "Partner Portal",
        "summary": "End-to-end overview of the partner onboarding workflow from application to activation.",
        "body": (
            "The Partner Gateway manages the full onboarding lifecycle for new partners.\n\n"
            "Stages:\n"
            "1. Application: Partner submits an onboarding case with company details and documents.\n"
            "2. Document Review: Internal team verifies submitted documents (tax certificates, licenses, etc.).\n"
            "3. Due Diligence: Background checks and reference verification.\n"
            "4. Commercial Terms: Negotiate and agree on commission structures and SLAs.\n"
            "5. System Setup: Create partner portal access and configure entitlements.\n"
            "6. Activation: Partner is marked as active and can begin operations.\n\n"
            "Each stage has configurable approval requirements set in Settings > Partner Gateway > Templates.\n\n"
            "Partners can track their onboarding progress through the portal at any time."
        ),
        "visibility": "portal",
    },
    {
        "title": "Submitting Documents Through the Partner Portal",
        "category": "Partner Portal",
        "summary": "How partners upload required documents during the onboarding and compliance renewal processes.",
        "body": (
            "Partners submit documents through the Partner Portal document upload interface.\n\n"
            "Steps:\n"
            "1. Log in to the Partner Portal.\n"
            "2. Navigate to 'My Onboarding' or 'Compliance Documents'.\n"
            "3. Click 'Upload Document' next to the required document type.\n"
            "4. Select the file (PDF, JPEG, or PNG, max 10 MB).\n"
            "5. Add an optional description and click 'Submit'.\n\n"
            "Document types commonly required:\n"
            "- Certificate of Incorporation\n"
            "- Tax Identification Number (TIN)\n"
            "- Professional licenses and certifications\n"
            "- Insurance certificates\n"
            "- Bank account verification letter\n\n"
            "Uploaded documents are reviewed by the onboarding team within 2 business days. "
            "You will receive a notification when each document is approved or if re-submission is needed."
        ),
        "visibility": "portal",
    },
]


class Command(BaseCommand):
    help = "Seed demo knowledge-base articles for the Support Knowledge Center."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded articles before re-seeding.",
        )
        parser.add_argument(
            "--organization-id",
            dest="organization_ids",
            action="append",
            type=int,
            help=(
                "Target a specific organization. "
                "Repeat the flag for multiple orgs. "
                "If omitted, all organizations are seeded."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.support_desk.models import SupportKnowledgeArticle

        organization_ids = options.get("organization_ids") or []
        flush = options["flush"]

        org_qs = Organization.objects.order_by("id")
        if organization_ids:
            org_qs = org_qs.filter(id__in=organization_ids)
        orgs = list(org_qs)

        if not orgs:
            self.stderr.write(self.style.ERROR("No organizations found. Create one first."))
            return

        if organization_ids:
            found = {o.id for o in orgs}
            missing = [oid for oid in organization_ids if oid not in found]
            if missing:
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping unknown organization ids: {', '.join(str(v) for v in missing)}"
                    )
                )

        now = timezone.now()

        for org in orgs:
            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(self.style.HTTP_INFO(f"Organization: {org.name} (id={org.id})"))

            if flush:
                deleted, _ = SupportKnowledgeArticle.objects.filter(
                    organization=org,
                    summary__icontains=DEMO_MARKER,
                ).delete()
                self.stdout.write(self.style.WARNING(f"  Flushed {deleted} previously seeded articles."))

            # Find an admin user to set as owner
            from apps.accounts.models import UserProfile

            admin_profile = (
                UserProfile.objects.filter(organization=org, role="admin", user__is_active=True)
                .select_related("user")
                .first()
            )
            owner = admin_profile.user if admin_profile else None
            if not owner:
                self.stderr.write(self.style.WARNING(f"  No active admin user found for org {org.id}; skipping."))
                continue

            created_count = 0
            for idx, article_data in enumerate(ARTICLES):
                slug_base = article_data["title"].lower().replace(" ", "-").replace("(", "").replace(")", "")
                # Check if already exists (by slug prefix)
                if SupportKnowledgeArticle.objects.filter(
                    organization=org,
                    slug__startswith=slug_base[:40],
                    summary__icontains=DEMO_MARKER,
                ).exists():
                    continue

                is_published = idx < 12  # First 12 are published, rest are drafts
                status = "published" if is_published else "draft"

                SupportKnowledgeArticle.objects.create(
                    organization=org,
                    title=article_data["title"],
                    summary=f"{article_data['summary']} {DEMO_MARKER}",
                    body=article_data["body"],
                    category=article_data["category"],
                    status=status,
                    visibility=article_data.get("visibility", "internal"),
                    owner=owner,
                    reviewer=owner if is_published else None,
                    published_at=now if is_published else None,
                    last_reviewed_at=now if is_published else None,
                    view_count=idx * 7 + 3 if is_published else 0,
                    helpful_votes=max(0, (12 - idx) * 2) if is_published else 0,
                    not_helpful_votes=max(0, idx - 4) if is_published else 0,
                )
                created_count += 1

            self.stdout.write(self.style.SUCCESS(f"  Created {created_count} knowledge articles."))

        self.stdout.write(self.style.SUCCESS("\nDone."))

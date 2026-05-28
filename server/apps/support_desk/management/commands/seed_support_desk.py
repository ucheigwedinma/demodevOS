"""
Seed realistic support-desk demo data: SLA policies, automation rules,
tickets (with comments & communication logs), and automation runs.

Knowledge-base articles are handled by the separate ``seed_knowledge_base``
command and are NOT duplicated here.

Usage:
    python manage.py seed_support_desk
    python manage.py seed_support_desk --flush
    python manage.py seed_support_desk --organization-id 2
    python manage.py seed_support_desk --tickets 120
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Organization

DEMO_MARKER = "[demo-seed]"
DEFAULT_TICKET_COUNT = 64

# ── SLA Policies ─────────────────────────────────────────────────────────

SLA_POLICIES = [
    {
        "name": "Critical — All Categories",
        "description": "Fastest response and resolution targets for critical-priority tickets.",
        "category": "",
        "priority": "critical",
        "response_target_hours": Decimal("0.50"),
        "resolution_target_hours": Decimal("4.00"),
        "escalate_after_hours": 1,
        "escalation_path": ["team_lead", "director"],
        "agent_notify_threshold_percent": 30,
        "manager_notify_threshold_percent": 60,
        "breach_escalation_role": "director",
    },
    {
        "name": "High — Technical Issues",
        "description": "Elevated targets for high-priority technical tickets.",
        "category": "technical",
        "priority": "high",
        "response_target_hours": Decimal("2.00"),
        "resolution_target_hours": Decimal("24.00"),
        "escalate_after_hours": 4,
        "escalation_path": ["team_lead"],
        "agent_notify_threshold_percent": 50,
        "manager_notify_threshold_percent": 80,
        "breach_escalation_role": "team_lead",
    },
    {
        "name": "High — Access & Account",
        "description": "Quick turnaround for access and account issues at high priority.",
        "category": "access",
        "priority": "high",
        "response_target_hours": Decimal("1.00"),
        "resolution_target_hours": Decimal("12.00"),
        "escalate_after_hours": 3,
        "escalation_path": ["team_lead", "security_admin"],
        "agent_notify_threshold_percent": 40,
        "manager_notify_threshold_percent": 70,
        "breach_escalation_role": "security_admin",
    },
    {
        "name": "Medium — General",
        "description": "Standard response and resolution targets for medium-priority tickets.",
        "category": "",
        "priority": "medium",
        "response_target_hours": Decimal("8.00"),
        "resolution_target_hours": Decimal("48.00"),
        "escalate_after_hours": 12,
        "escalation_path": ["team_lead"],
        "agent_notify_threshold_percent": 50,
        "manager_notify_threshold_percent": 80,
        "breach_escalation_role": "team_lead",
    },
    {
        "name": "Low — General Enquiries",
        "description": "Relaxed targets for low-priority enquiries and general requests.",
        "category": "",
        "priority": "low",
        "response_target_hours": Decimal("24.00"),
        "resolution_target_hours": Decimal("72.00"),
        "escalate_after_hours": 48,
        "escalation_path": [],
        "agent_notify_threshold_percent": 60,
        "manager_notify_threshold_percent": 90,
        "breach_escalation_role": "team_lead",
    },
    {
        "name": "Billing — All Priorities",
        "description": "Finance-specific SLA targets for billing-related tickets regardless of priority.",
        "category": "billing",
        "priority": "",
        "response_target_hours": Decimal("4.00"),
        "resolution_target_hours": Decimal("36.00"),
        "escalate_after_hours": 8,
        "escalation_path": ["finance_lead"],
        "agent_notify_threshold_percent": 40,
        "manager_notify_threshold_percent": 75,
        "breach_escalation_role": "finance_lead",
    },
]

# ── Automation Rules ─────────────────────────────────────────────────────

AUTOMATION_RULES = [
    {
        "name": "Auto-assign critical tickets to senior agents",
        "description": "Automatically assign critical-priority tickets to a senior support agent.",
        "trigger_type": "ticket_created",
        "conditions": {"priority": "critical"},
        "actions": {"assign_to_role": "senior_agent", "notify": ["team_lead"]},
        "priority": 10,
        "run_once_per_ticket": True,
    },
    {
        "name": "Escalate tickets approaching SLA breach",
        "description": "When an open ticket reaches 80% of its SLA deadline, auto-escalate.",
        "trigger_type": "sla_threshold",
        "conditions": {"threshold_percent": 80, "status__in": ["open", "in_progress"]},
        "actions": {"set_status": "escalated", "notify": ["assigned_agent", "team_lead"]},
        "priority": 20,
        "run_once_per_ticket": True,
    },
    {
        "name": "Notify requester on status change",
        "description": "Send an email notification to the requester whenever ticket status changes.",
        "trigger_type": "status_changed",
        "conditions": {},
        "actions": {"email_requester": True, "template": "ticket_status_update"},
        "priority": 50,
        "run_once_per_ticket": False,
    },
    {
        "name": "Tag billing tickets for finance review",
        "description": "Automatically tag billing-category tickets for finance team visibility.",
        "trigger_type": "ticket_created",
        "conditions": {"category": "billing"},
        "actions": {"add_tag": "finance-review", "notify": ["finance_lead"]},
        "priority": 30,
        "run_once_per_ticket": True,
    },
    {
        "name": "Auto-close resolved tickets after 48 hours",
        "description": "Close tickets that have been in resolved state for more than 48 hours without requester response.",
        "trigger_type": "ticket_updated",
        "conditions": {"status": "resolved", "no_reply_hours": 48},
        "actions": {"set_status": "closed", "email_requester": True},
        "priority": 90,
        "run_once_per_ticket": True,
    },
    {
        "name": "Assign access tickets to IAM team",
        "description": "Route all access-category tickets to the IAM support group.",
        "trigger_type": "ticket_created",
        "conditions": {"category": "access"},
        "actions": {"assign_to_group": "iam_support", "add_tag": "identity-access"},
        "priority": 15,
        "run_once_per_ticket": True,
    },
]

# ── Ticket Templates ─────────────────────────────────────────────────────

TICKET_SUBJECTS = [
    # Access
    ("access", "Cannot log in after password change"),
    ("access", "MFA token not generating codes"),
    ("access", "Need access to the Finance module"),
    ("access", "Account locked after failed login attempts"),
    ("access", "SSO redirect failing for partner portal"),
    ("access", "New hire needs system credentials"),
    # Billing
    ("billing", "Invoice INV-0042 shows incorrect tax rate"),
    ("billing", "Duplicate charge on last billing cycle"),
    ("billing", "Payment not reflected after bank transfer"),
    ("billing", "Need credit note for returned goods"),
    ("billing", "Subscription renewal not processing"),
    # Technical
    ("technical", "Dashboard charts not loading"),
    ("technical", "Report export stuck at 0%"),
    ("technical", "Slow page load on Projects module"),
    ("technical", "File upload fails for documents over 5 MB"),
    ("technical", "Search returns no results for existing records"),
    ("technical", "Mobile view layout broken on Safari"),
    ("technical", "API timeout when fetching large datasets"),
    ("technical", "Notification emails arriving with 2-hour delay"),
    # Workflow
    ("workflow", "Approval chain not advancing to next approver"),
    ("workflow", "Leave request stuck in pending state"),
    ("workflow", "Procurement requisition auto-rejected incorrectly"),
    ("workflow", "Cannot reassign task to another team member"),
    ("workflow", "Automated reminder not sending for overdue tasks"),
    # Account
    ("account", "Update company address in organization settings"),
    ("account", "Change primary contact email"),
    ("account", "Deactivate departed employee account"),
    ("account", "Merge duplicate contact records"),
    # Request
    ("request", "Request for additional user licenses"),
    ("request", "Custom report for quarterly board meeting"),
    ("request", "Bulk import of historical invoice data"),
    ("request", "Enable WhatsApp integration for support channel"),
    ("request", "Add new cost center to chart of accounts"),
    # Other
    ("other", "Feedback on new dashboard redesign"),
    ("other", "Training session request for procurement module"),
    ("other", "Suggestion: add dark mode to user preferences"),
]

TICKET_DESCRIPTIONS = {
    "access": (
        "I am experiencing an access-related issue. I have tried the standard troubleshooting "
        "steps (clearing cache, resetting browser, verifying credentials) without success. "
        "Please investigate and restore access as soon as possible."
    ),
    "billing": (
        "There appears to be a discrepancy in the billing/invoice details. "
        "I have attached the relevant documentation for reference. "
        "Kindly review and confirm the correct figures or issue a correction."
    ),
    "technical": (
        "I am encountering a technical issue that impacts my ability to complete my work. "
        "The problem started earlier today and persists across different browsers. "
        "Screenshots or error messages are described above."
    ),
    "workflow": (
        "A workflow/automation is not behaving as expected. The process appears to be "
        "stuck or has produced an incorrect outcome. I have verified the input data "
        "and configuration. Please review the workflow engine logs."
    ),
    "account": (
        "I need an update to our account/organization configuration. "
        "The change details are described in the subject. Please process at your earliest convenience."
    ),
    "request": (
        "I would like to submit a request for a new feature, configuration change, "
        "or additional resources as described above. "
        "Happy to provide further details if needed."
    ),
    "other": (
        "This is a general inquiry or feedback item. No immediate action is required "
        "but I would appreciate a response when convenient."
    ),
}

COMMENT_TEMPLATES = {
    "internal_note": [
        "Reviewed ticket details. Root cause appears to be a configuration mismatch. Investigating further.",
        "Escalated to L2 support for deeper analysis. Will update the requester once we have findings.",
        "Confirmed the issue is reproducible in staging. Coordinating with the engineering team for a fix.",
        "Awaiting response from the requester for additional information. SLA clock paused.",
        "Similar issue was reported last month (ref: SD-000032). Applying the same resolution approach.",
        "Checked server logs — no errors found. Likely a client-side caching issue. Advising cache clear.",
        "Spoke with the requester over phone. Clarified requirements. Proceeding with the resolution.",
    ],
    "requester_reply": [
        "Thank you for looking into this. I have attached the screenshot showing the error message.",
        "The issue is still occurring after following the suggested steps. Can we schedule a call?",
        "This has been resolved — thank you for the quick turnaround!",
        "I can confirm the fix is working now. Please close this ticket.",
        "The problem happens intermittently, usually between 2 PM and 4 PM. Let me know if you need more details.",
        "I have added two more team members who are experiencing the same issue.",
    ],
}

COMMUNICATION_DATA = [
    {
        "interaction_type": "ticket_conversation",
        "direction": "inbound",
        "channel": "portal",
        "subject": "Initial ticket submission",
        "message": "Ticket submitted through the support portal by the requester.",
    },
    {
        "interaction_type": "email_reply",
        "direction": "outbound",
        "channel": "email",
        "subject": "Acknowledgement: Your support request has been received",
        "message": "Thank you for contacting support. Your ticket has been assigned and our team will respond shortly.",
    },
    {
        "interaction_type": "internal_note",
        "direction": "internal",
        "channel": "portal",
        "subject": "Internal triage note",
        "message": "Triaged and assigned based on category and priority. SLA deadline calculated.",
    },
    {
        "interaction_type": "call_log",
        "direction": "outbound",
        "channel": "phone",
        "subject": "Follow-up call with requester",
        "message": "Called the requester to clarify the issue details and gather additional context.",
    },
    {
        "interaction_type": "email_reply",
        "direction": "inbound",
        "channel": "email",
        "subject": "RE: Your support request",
        "message": "Requester replied with additional screenshots and logs as requested.",
    },
    {
        "interaction_type": "chat_transcript",
        "direction": "inbound",
        "channel": "chat",
        "subject": "Live chat session",
        "message": "Quick chat session to walk the requester through the resolution steps.",
    },
    {
        "interaction_type": "whatsapp",
        "direction": "inbound",
        "channel": "whatsapp",
        "subject": "WhatsApp follow-up",
        "message": "Requester confirmed via WhatsApp that the issue has been resolved.",
    },
    {
        "interaction_type": "ticket_conversation",
        "direction": "outbound",
        "channel": "portal",
        "subject": "Resolution summary posted",
        "message": "Final resolution summary and next steps posted to the ticket thread.",
    },
]


class Command(BaseCommand):
    help = (
        "Seed comprehensive support-desk demo data: SLA policies, automation "
        "rules, tickets (with comments and communication logs), and automation runs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded support-desk rows before re-seeding.",
        )
        parser.add_argument(
            "--organization-id",
            dest="organization_ids",
            action="append",
            type=int,
            help="Target specific organization(s). Repeat for multiple. Omit for all.",
        )
        parser.add_argument(
            "--tickets",
            type=int,
            default=DEFAULT_TICKET_COUNT,
            help=f"Number of tickets to seed per organization (default {DEFAULT_TICKET_COUNT}).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        organization_ids = options.get("organization_ids") or []
        flush = options["flush"]
        ticket_count = options["tickets"]

        org_qs = Organization.objects.order_by("id")
        if organization_ids:
            org_qs = org_qs.filter(id__in=organization_ids)
        orgs = list(org_qs)

        if not orgs:
            self.stderr.write(self.style.ERROR("No organizations found."))
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

        for org in orgs:
            self.stdout.write(f"\n{'=' * 60}")
            self.stdout.write(self.style.HTTP_INFO(f"Organization: {org.name} (id={org.id})"))
            self._seed_org(org, flush=flush, ticket_count=ticket_count)

        self.stdout.write(self.style.SUCCESS("\nDone."))

    # ── Per-organization seeding ──────────────────────────────────────

    def _seed_org(self, org, *, flush, ticket_count):
        from apps.accounts.models import UserProfile

        if flush:
            self._flush(org)

        # Gather users
        profiles = list(
            UserProfile.objects.filter(
                organization=org, user__is_active=True
            ).select_related("user")
        )
        if not profiles:
            self.stderr.write(self.style.WARNING(f"  No active users for org {org.id}; skipping."))
            return

        admin_profiles = [p for p in profiles if p.role == "admin"]
        admin_user = admin_profiles[0].user if admin_profiles else profiles[0].user
        all_users = [p.user for p in profiles]

        random.seed(42 + org.id)

        # 1. SLA Policies
        sla_count = self._seed_sla_policies(org)

        # 2. Automation Rules
        rules = self._seed_automation_rules(org, admin_user)

        # 3. Tickets + Comments + Communication Logs
        tickets = self._seed_tickets(org, all_users, ticket_count)

        # 4. Automation Runs
        run_count = self._seed_automation_runs(org, rules, tickets)

        self.stdout.write(
            self.style.SUCCESS(
                f"  Summary: {sla_count} SLA policies, {len(rules)} rules, "
                f"{len(tickets)} tickets, {run_count} automation runs."
            )
        )

    def _flush(self, org):
        from apps.support_desk.models import (
            SupportAutomationRule,
            SupportAutomationRun,
            SupportCommunicationLog,
            SupportSlaPolicy,
            SupportTicket,
            SupportTicketComment,
        )

        # Delete in dependency order
        SupportAutomationRun.objects.filter(
            organization=org, summary__icontains=DEMO_MARKER
        ).delete()
        SupportCommunicationLog.objects.filter(
            organization=org, subject__icontains=DEMO_MARKER
        ).delete()
        SupportTicketComment.objects.filter(
            ticket__organization=org, body__icontains=DEMO_MARKER
        ).delete()
        SupportTicket.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        SupportAutomationRule.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()
        SupportSlaPolicy.objects.filter(
            organization=org, description__icontains=DEMO_MARKER
        ).delete()

        self.stdout.write(self.style.WARNING("  Flushed previously seeded support-desk data."))

    # ── SLA Policies ─────────────────────────────────────────────────

    def _seed_sla_policies(self, org):
        from apps.support_desk.models import SupportSlaPolicy

        created = 0
        for row in SLA_POLICIES:
            _, was_created = SupportSlaPolicy.objects.get_or_create(
                organization=org,
                name=row["name"],
                defaults={
                    "description": f'{row["description"]} {DEMO_MARKER}',
                    "category": row["category"],
                    "priority": row["priority"],
                    "response_target_hours": row["response_target_hours"],
                    "resolution_target_hours": row["resolution_target_hours"],
                    "escalate_after_hours": row["escalate_after_hours"],
                    "escalation_path": row["escalation_path"],
                    "agent_notify_threshold_percent": row["agent_notify_threshold_percent"],
                    "manager_notify_threshold_percent": row["manager_notify_threshold_percent"],
                    "breach_escalation_role": row["breach_escalation_role"],
                    "notify_assigned_agent": True,
                    "notify_manager": True,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f"  {created} SLA policies created.")
        return created

    # ── Automation Rules ─────────────────────────────────────────────

    def _seed_automation_rules(self, org, created_by):
        from apps.support_desk.models import SupportAutomationRule

        rules = []
        for row in AUTOMATION_RULES:
            rule, _ = SupportAutomationRule.objects.get_or_create(
                organization=org,
                name=row["name"],
                defaults={
                    "description": f'{row["description"]} {DEMO_MARKER}',
                    "trigger_type": row["trigger_type"],
                    "conditions": row["conditions"],
                    "actions": row["actions"],
                    "priority": row["priority"],
                    "run_once_per_ticket": row["run_once_per_ticket"],
                    "is_active": True,
                    "created_by": created_by,
                },
            )
            rules.append(rule)

        self.stdout.write(f"  {len(rules)} automation rules ready.")
        return rules

    # ── Tickets ──────────────────────────────────────────────────────

    def _seed_tickets(self, org, users, count):
        from apps.support_desk.models import SupportCommunicationLog, SupportTicket, SupportTicketComment

        now = timezone.now()
        tickets = []

        # Status distribution weights
        status_weights = [
            (SupportTicket.Status.OPEN, 25),
            (SupportTicket.Status.IN_PROGRESS, 25),
            (SupportTicket.Status.PENDING_REQUESTER, 10),
            (SupportTicket.Status.ESCALATED, 8),
            (SupportTicket.Status.RESOLVED, 18),
            (SupportTicket.Status.CLOSED, 14),
        ]
        statuses = []
        for status, weight in status_weights:
            statuses.extend([status] * weight)

        priority_pool = (
            ["critical"] * 12
            + ["high"] * 25
            + ["medium"] * 40
            + ["low"] * 23
        )

        for i in range(count):
            category, subject = random.choice(TICKET_SUBJECTS)
            # Add slight variation to avoid exact duplicates
            if i > len(TICKET_SUBJECTS):
                subject = f"{subject} (follow-up #{i - len(TICKET_SUBJECTS) + 1})"

            priority = random.choice(priority_pool)
            status = random.choice(statuses)

            requester = random.choice(users)
            agent = random.choice(users) if random.random() > 0.15 else None

            # Spread creation dates across last 90 days
            created_offset = timedelta(
                days=random.randint(0, 90),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            created_at = now - created_offset

            description = f"{TICKET_DESCRIPTIONS.get(category, '')} {DEMO_MARKER}"

            ticket = SupportTicket(
                organization=org,
                subject=subject,
                description=description,
                requester=requester,
                assigned_agent=agent,
                category=category,
                priority=priority,
                status=status,
            )
            ticket.save()

            # Backdate created_at
            SupportTicket.objects.filter(pk=ticket.pk).update(created_at=created_at)

            # Set first_response_at for most non-open tickets
            if status != SupportTicket.Status.OPEN and random.random() > 0.2:
                response_delay = timedelta(
                    hours=random.uniform(0.25, 12),
                    minutes=random.randint(0, 59),
                )
                first_response_at = created_at + response_delay
                SupportTicket.objects.filter(pk=ticket.pk).update(
                    first_response_at=first_response_at
                )

            # Satisfaction score for closed tickets
            if status == SupportTicket.Status.CLOSED and random.random() > 0.3:
                SupportTicket.objects.filter(pk=ticket.pk).update(
                    customer_satisfaction_score=random.choice([3, 4, 4, 5, 5, 5, 2, 1]),
                )

            tickets.append(ticket)

            # ── Comments ───────────────────────────────────────────
            comment_count = random.randint(1, 5) if status != SupportTicket.Status.OPEN else random.randint(0, 2)
            for c_idx in range(comment_count):
                comment_type = random.choice(["internal_note", "requester_reply"])
                body_choices = COMMENT_TEMPLATES[comment_type]
                body = f"{random.choice(body_choices)} {DEMO_MARKER}"
                author = agent if comment_type == "internal_note" and agent else requester

                comment = SupportTicketComment.objects.create(
                    ticket=ticket,
                    author=author,
                    comment_type=comment_type,
                    body=body,
                )
                comment_time = created_at + timedelta(hours=random.randint(1, 72) * (c_idx + 1))
                SupportTicketComment.objects.filter(pk=comment.pk).update(created_at=comment_time)

            # ── Communication Logs ─────────────────────────────────
            log_count = random.randint(1, 4)
            log_templates = random.sample(
                COMMUNICATION_DATA, min(log_count, len(COMMUNICATION_DATA))
            )
            for l_idx, tpl in enumerate(log_templates):
                log_time = created_at + timedelta(hours=random.randint(0, 48) * (l_idx + 1))
                author = agent if tpl["direction"] != "inbound" and agent else requester

                call_duration = None
                if tpl["channel"] == "phone":
                    call_duration = random.randint(60, 1800)

                SupportCommunicationLog.objects.create(
                    organization=org,
                    ticket=ticket,
                    author=author,
                    interaction_type=tpl["interaction_type"],
                    direction=tpl["direction"],
                    channel=tpl["channel"],
                    subject=f'{tpl["subject"]} {DEMO_MARKER}',
                    message=tpl["message"],
                    call_duration_seconds=call_duration,
                    happened_at=log_time,
                )

        self.stdout.write(f"  {len(tickets)} tickets created (with comments and communication logs).")
        return tickets

    # ── Automation Runs ──────────────────────────────────────────────

    def _seed_automation_runs(self, org, rules, tickets):
        from apps.support_desk.models import SupportAutomationRun

        if not rules or not tickets:
            return 0

        now = timezone.now()
        created = 0

        # Generate runs for ~40% of tickets
        sampled_tickets = random.sample(tickets, min(len(tickets), int(len(tickets) * 0.4)))
        for ticket in sampled_tickets:
            rule = random.choice(rules)
            is_matched = random.random() > 0.15  # 85% matched, 15% failed
            status = "matched" if is_matched else "failed"

            run_time = now - timedelta(
                days=random.randint(0, 60),
                hours=random.randint(0, 23),
            )

            run = SupportAutomationRun.objects.create(
                organization=org,
                rule=rule,
                ticket=ticket,
                trigger_type=rule.trigger_type,
                status=status,
                summary=f'Rule "{rule.name}" {status} on {ticket.ticket_id} {DEMO_MARKER}',
                details={
                    "rule_id": rule.id,
                    "ticket_id": ticket.ticket_id,
                    "conditions_evaluated": rule.conditions,
                    "actions_applied": rule.actions if is_matched else {},
                    "seeded": True,
                },
            )
            SupportAutomationRun.objects.filter(pk=run.pk).update(created_at=run_time)
            created += 1

        self.stdout.write(f"  {created} automation runs created.")
        return created

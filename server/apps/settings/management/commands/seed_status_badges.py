from django.core.management.base import BaseCommand

from apps.settings.models import MasterDataEntry

# (code, label, variant)
# Variants: neutral, muted, info, success, warning, danger, orange, violet, rose
SEED_DATA = [
    # --- Common lifecycle ---
    ("draft", "Draft", "neutral"),
    ("new", "New", "neutral"),
    ("not_started", "Not Started", "neutral"),
    ("submitted", "Submitted", "info"),
    ("under_review", "Under Review", "violet"),
    ("approved", "Approved", "success"),
    ("rejected", "Rejected", "danger"),
    ("cancelled", "Cancelled", "muted"),
    ("archived", "Archived", "muted"),
    # --- Progress ---
    ("pending", "Pending", "warning"),
    ("in_progress", "In Progress", "info"),
    ("completed", "Completed", "success"),
    ("on_hold", "On Hold", "warning"),
    ("paused", "Paused", "warning"),
    ("scheduled", "Scheduled", "info"),
    ("running", "Running", "info"),
    # --- Activation ---
    ("active", "Active", "success"),
    ("inactive", "Inactive", "muted"),
    ("suspended", "Suspended", "danger"),
    ("dormant", "Dormant", "muted"),
    ("dissolved", "Dissolved", "muted"),
    ("under_formation", "Under Formation", "info"),
    ("frozen", "Frozen", "warning"),
    ("abolished", "Abolished", "muted"),
    # --- Finance ---
    ("paid", "Paid", "success"),
    ("partially_paid", "Partially Paid", "warning"),
    ("overdue", "Overdue", "warning"),
    ("due", "Due", "warning"),
    ("past_due", "Past Due", "warning"),
    ("waived", "Waived", "muted"),
    ("posted", "Posted", "success"),
    ("reversed", "Reversed", "muted"),
    ("calculated", "Calculated", "info"),
    ("distributed", "Distributed", "success"),
    # --- Procurement ---
    ("ordered", "Ordered", "info"),
    ("issued", "Issued", "info"),
    ("partially_received", "Partially Received", "warning"),
    ("received", "Received", "success"),
    ("inspected", "Inspected", "info"),
    ("accepted", "Accepted", "success"),
    ("partially_accepted", "Partially Accepted", "warning"),
    ("evaluation", "Evaluation", "info"),
    ("shortlisted", "Shortlisted", "info"),
    ("winner", "Winner", "success"),
    # --- Documents ---
    ("superseded", "Superseded", "violet"),
    ("declined", "Declined", "danger"),
    # --- Communication ---
    ("sent", "Sent", "info"),
    ("delivered", "Delivered", "success"),
    ("read", "Read", "success"),
    ("failed", "Failed", "danger"),
    ("bounced", "Bounced", "danger"),
    ("opened", "Opened", "info"),
    ("clicked", "Clicked", "success"),
    ("unsubscribed", "Unsubscribed", "muted"),
    # --- Support ---
    ("open", "Open", "info"),
    ("pending_requester", "Pending Requester", "warning"),
    ("escalated", "Escalated", "orange"),
    ("resolved", "Resolved", "success"),
    ("closed", "Closed", "muted"),
    ("acknowledged", "Acknowledged", "info"),
    ("matched", "Matched", "success"),
    # --- CRM ---
    ("won", "Won", "success"),
    ("lost", "Lost", "muted"),
    ("disqualified", "Disqualified", "muted"),
    ("expired", "Expired", "muted"),
    ("hold", "Hold", "warning"),
    ("reserved", "Reserved", "info"),
    ("payment_pending", "Payment Pending", "warning"),
    ("converting", "Converting", "info"),
    ("converted", "Converted", "success"),
    # --- Projects ---
    ("planning", "Planning", "info"),
    ("mitigated", "Mitigated", "success"),
    ("skipped", "Skipped", "muted"),
    ("planned", "Planned", "info"),
    ("passed", "Passed", "success"),
    ("blocked", "Blocked", "danger"),
    ("reviewed", "Reviewed", "info"),
    # --- Risk / severity ---
    ("critical", "Critical", "rose"),
    ("breached", "Breached", "rose"),
    ("urgent", "Urgent", "orange"),
    # --- Compliance ---
    ("compliant", "Compliant", "success"),
    ("non_compliant", "Non-Compliant", "danger"),
    ("partially_compliant", "Partially Compliant", "warning"),
    ("pending_review", "Pending Review", "warning"),
    ("remediation", "Remediation", "warning"),
    ("appealed", "Appealed", "violet"),
    # --- HR ---
    ("probation", "Probation", "warning"),
    ("notice_period", "Notice Period", "warning"),
    ("resigned", "Resigned", "muted"),
    ("terminated", "Terminated", "danger"),
    ("withdrawn", "Withdrawn", "muted"),
    ("no_show", "No Show", "danger"),
    ("filled", "Filled", "success"),
    ("extended", "Extended", "warning"),
    ("effective", "Effective", "success"),
    ("enrolled", "Enrolled", "info"),
    ("waitlisted", "Waitlisted", "warning"),
    ("current", "Current", "success"),
    ("published", "Published", "success"),
    ("revoked", "Revoked", "muted"),
    ("assessed", "Assessed", "info"),
    ("filed", "Filed", "info"),
    ("generated", "Generated", "info"),
    ("processing", "Processing", "info"),
    ("trialing", "Trial", "info"),
    ("deprecated", "Deprecated", "muted"),
]


class Command(BaseCommand):
    help = "Seed status badge MDM entries. Idempotent."

    def handle(self, *args, **options):
        created = 0
        updated = 0

        for idx, (code, label, variant) in enumerate(SEED_DATA):
            _, was_created = MasterDataEntry.objects.update_or_create(
                category=MasterDataEntry.Category.STATUS_BADGE,
                code=code,
                defaults={
                    "label": label,
                    "metadata": {"variant": variant},
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
                f"Status badges seeded: {total} entries ({created} created, {updated} updated)."
            )
        )

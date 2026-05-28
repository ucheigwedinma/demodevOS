"""
Generate follow-up reminders for leads that have gone idle.

Usage:
    python manage.py generate_idle_lead_followups
    python manage.py generate_idle_lead_followups --idle-days 5 --due-hours 12
    python manage.py generate_idle_lead_followups --organization-id 2
"""

import logging
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.crm.models import FollowUpRule, FollowUpTask, Lead

logger = logging.getLogger(__name__)

IDLE_RULE_NAME = "Idle Lead Reminder"
IDLE_RULE_DESCRIPTION = (
    "Auto-generated reminder when a lead has no recent activity for the idle threshold."
)


class Command(BaseCommand):
    help = "Generate follow-up tasks for active leads that have gone idle."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Process a single organization id.",
        )
        parser.add_argument(
            "--idle-days",
            type=int,
            default=3,
            help="Minimum idle days before a reminder is generated (default: 3).",
        )
        parser.add_argument(
            "--due-hours",
            type=int,
            default=24,
            help="Hours until the generated follow-up task is due (default: 24).",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        idle_days = max(1, int(options["idle_days"]))
        due_hours = max(1, int(options["due_hours"]))
        idle_cutoff = now - timedelta(days=idle_days)
        target_organization_id = options.get("organization_id")
        organization_ids = (
            [int(target_organization_id)]
            if target_organization_id is not None
            else list(iter_organization_ids())
        )

        total_created = 0
        for organization_id in organization_ids:
            logger.info(
                "crm.command.generate_idle_lead_followups.start organization_id=%s idle_days=%s",
                organization_id,
                idle_days,
            )
            try:
                with rls_context(organization_id, bypass=False):
                    org_created = self._generate_for_org(
                        organization_id=organization_id,
                        now=now,
                        idle_cutoff=idle_cutoff,
                        due_hours=due_hours,
                    )
                    total_created += org_created
            except Exception:
                logger.exception(
                    "crm.command.generate_idle_lead_followups.failed organization_id=%s",
                    organization_id,
                )
                raise

            logger.info(
                "crm.command.generate_idle_lead_followups.success organization_id=%s created=%s",
                organization_id,
                org_created,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Generated {total_created} idle lead follow-up task(s)."
            )
        )

    def _generate_for_org(self, *, organization_id, now, idle_cutoff, due_hours):
        rule, _created = FollowUpRule.objects.get_or_create(
            organization_id=organization_id,
            name=IDLE_RULE_NAME,
            defaults={
                "description": IDLE_RULE_DESCRIPTION,
                "trigger_stage": Lead.PipelineStage.INQUIRY,
                "follow_up_within_hours": due_hours,
                "required_activity_type": "follow_up",
                "auto_assign_to_owner": True,
                "is_active": True,
            },
        )
        updates = []
        if not rule.is_active:
            rule.is_active = True
            updates.append("is_active")
        if rule.follow_up_within_hours != due_hours:
            rule.follow_up_within_hours = due_hours
            updates.append("follow_up_within_hours")
        if updates:
            rule.save(update_fields=[*updates, "updated_at"])

        leads = (
            Lead.objects.filter(
                organization_id=organization_id,
                status=Lead.Status.ACTIVE,
                is_archived=False,
            )
            .annotate(last_activity_at=Max("activities__created_at"))
            .only(
                "id",
                "assigned_to_id",
                "inquiry_date",
                "updated_at",
                "status",
                "is_archived",
            )
        )

        created_count = 0
        local_tz = timezone.get_current_timezone()
        for lead in leads:
            inquiry_dt = timezone.make_aware(
                datetime.combine(lead.inquiry_date, time.min),
                local_tz,
            )
            last_touch = max(
                inquiry_dt,
                lead.updated_at,
                lead.last_activity_at or inquiry_dt,
            )
            if last_touch > idle_cutoff:
                continue

            open_task_exists = FollowUpTask.objects.filter(
                rule=rule,
                lead=lead,
                status__in=[
                    FollowUpTask.Status.PENDING,
                    FollowUpTask.Status.IN_PROGRESS,
                    FollowUpTask.Status.BREACHED,
                    FollowUpTask.Status.ESCALATED,
                ],
            ).exists()
            if open_task_exists:
                continue

            FollowUpTask.objects.create(
                rule=rule,
                lead=lead,
                assigned_to_id=lead.assigned_to_id if rule.auto_assign_to_owner else None,
                due_at=now + timedelta(hours=due_hours),
                notes=(
                    f"Auto reminder: lead has been idle for at least {int((now - last_touch).days)} day(s)."
                ),
            )
            created_count += 1

        return created_count

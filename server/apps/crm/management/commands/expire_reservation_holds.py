"""
Expire reservation holds that have passed their deadline.

Releases the unit back to AVAILABLE and records a HOLD_EXPIRED event.
Run periodically via cron or Celery beat (every 5 minutes recommended).

Usage:
    python manage.py expire_reservation_holds
"""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.rls import iter_organization_ids, rls_context
from apps.crm.models import ReservationEvent, UnitReservation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Expire reservation holds that have passed their deadline"

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            help="Process a single organization id.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        count = 0
        target_organization_id = options.get("organization_id")
        organization_ids = (
            [int(target_organization_id)]
            if target_organization_id is not None
            else list(iter_organization_ids())
        )

        for organization_id in organization_ids:
            logger.info(
                "crm.command.expire_reservation_holds.start organization_id=%s now=%s",
                organization_id,
                now.isoformat(),
            )
            try:
                with rls_context(organization_id, bypass=False):
                    expired_holds = UnitReservation.objects.filter(
                        organization_id=organization_id,
                        status=UnitReservation.Status.HOLD,
                        hold_expires_at__lt=now,
                    ).select_related("unit")

                    org_count = 0
                    for reservation in expired_holds:
                        reservation.status = UnitReservation.Status.EXPIRED
                        reservation.save(update_fields=["status", "updated_at"])

                        reservation.unit.status = "available"
                        reservation.unit.save(update_fields=["status", "updated_at"])

                        ReservationEvent.objects.create(
                            reservation=reservation,
                            event_type=ReservationEvent.EventType.HOLD_EXPIRED,
                            notes="Hold expired automatically.",
                            metadata={"expired_at": str(now)},
                        )
                        org_count += 1
                        count += 1
            except Exception:
                logger.exception(
                    "crm.command.expire_reservation_holds.failed organization_id=%s",
                    organization_id,
                )
                raise
            logger.info(
                "crm.command.expire_reservation_holds.success organization_id=%s expired=%s",
                organization_id,
                org_count,
            )

        logger.info(
            "crm.command.expire_reservation_holds.complete total_expired=%s",
            count,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {count} reservation hold(s)."
            )
        )

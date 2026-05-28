from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from apps.finance.models import Account, JournalEntry, JournalLine, JournalSourceType

from .models import AssetComponent, PreventiveSchedule, WorkOrder

MONEY_QUANTUM = Decimal("0.01")
WARRANTY_HORIZON_DAYS = 90
MAINTENANCE_SOON_DAYS = 30
MAINTENANCE_MONTH_INTERVALS = {
    "daily": 0,
    "weekly": 0,
    "biweekly": 0,
    "monthly": 1,
    "quarterly": 3,
    "semi_annual": 6,
    "annual": 12,
}


def _money(value: Decimal | int | float | str | None) -> Decimal:
    raw = Decimal(str(value or "0"))
    return raw.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _add_months(value: date, months: int) -> date:
    year = value.year + ((value.month - 1 + months) // 12)
    month = ((value.month - 1 + months) % 12) + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def derive_maintenance_due_date(
    *,
    frequency: str,
    commissioned_date: date | None,
    installation_date: date | None,
    today: date | None = None,
) -> date | None:
    if not frequency:
        return None

    base_date = commissioned_date or installation_date or today or timezone.localdate()
    if frequency == "daily":
        return base_date + timedelta(days=1)
    if frequency == "weekly":
        return base_date + timedelta(days=7)
    if frequency == "biweekly":
        return base_date + timedelta(days=14)

    month_interval = MAINTENANCE_MONTH_INTERVALS.get(frequency)
    if not month_interval:
        return base_date
    return _add_months(base_date, month_interval)


def warranty_status_for(asset: AssetComponent, *, today: date | None = None) -> str:
    today = today or timezone.localdate()
    if not asset.warranty_expiry:
        return "not_covered"
    if asset.warranty_expiry < today:
        return "expired"
    if asset.warranty_expiry <= today + timedelta(days=WARRANTY_HORIZON_DAYS):
        return "expiring"
    return "active"


def amc_status_for(asset: AssetComponent, *, today: date | None = None) -> str:
    today = today or timezone.localdate()
    if not asset.amc_end_date:
        return "not_covered"
    if asset.amc_end_date < today:
        return "expired"
    if asset.amc_end_date <= today + timedelta(days=WARRANTY_HORIZON_DAYS):
        return "expiring"
    return "active"


def maintenance_status_for(asset: AssetComponent, *, today: date | None = None) -> str:
    today = today or timezone.localdate()
    if asset.lifecycle_stage == AssetComponent.LifecycleStage.RETIRE:
        return "retired"
    if not asset.maintenance_frequency or not asset.maintenance_next_due_date:
        return "not_scheduled"
    if asset.maintenance_next_due_date < today:
        return "overdue"
    if asset.maintenance_next_due_date <= today + timedelta(days=MAINTENANCE_SOON_DAYS):
        return "due_soon"
    return "scheduled"


def depreciation_ready(asset: AssetComponent) -> bool:
    return bool(
        asset.depreciation_enabled
        and asset.acquisition_cost is not None
        and asset.depreciation_start_date
        and asset.expected_useful_life_years
        and asset.expected_useful_life_years > 0
    )


def monthly_depreciation_for(asset: AssetComponent) -> Decimal | None:
    if not depreciation_ready(asset):
        return None

    depreciable_base = _money(asset.acquisition_cost) - _money(asset.salvage_value)
    if depreciable_base <= 0:
        return None

    useful_life_months = int(asset.expected_useful_life_years or 0) * 12
    if useful_life_months <= 0:
        return None

    return _money(depreciable_base / useful_life_months)


def _elapsed_depreciation_months(start_date: date, end_date: date) -> int:
    if end_date < start_date:
        return 0

    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day >= start_date.day:
        months += 1
    return max(months, 0)


def accumulated_depreciation_for(asset: AssetComponent, *, as_of: date | None = None) -> Decimal | None:
    monthly_amount = monthly_depreciation_for(asset)
    if monthly_amount is None or not asset.depreciation_start_date:
        return None

    end_date = as_of or timezone.localdate()
    if asset.retired_date and asset.retired_date < end_date:
        end_date = asset.retired_date

    useful_life_months = int(asset.expected_useful_life_years or 0) * 12
    elapsed_months = min(_elapsed_depreciation_months(asset.depreciation_start_date, end_date), useful_life_months)
    depreciable_base = max(_money(asset.acquisition_cost) - _money(asset.salvage_value), Decimal("0.00"))
    return min(_money(monthly_amount * elapsed_months), depreciable_base)


def current_book_value_for(asset: AssetComponent, *, as_of: date | None = None) -> Decimal | None:
    if asset.acquisition_cost is None:
        return None

    accumulated = accumulated_depreciation_for(asset, as_of=as_of) or Decimal("0.00")
    book_value = _money(asset.acquisition_cost) - accumulated
    return max(book_value, _money(asset.salvage_value))


def _asset_category_to_work_order_category(asset_category: str) -> str:
    allowed = {choice for choice, _ in WorkOrder.Category.choices}
    return asset_category if asset_category in allowed else WorkOrder.Category.GENERAL


def ensure_preventive_schedule_for_asset(asset: AssetComponent) -> PreventiveSchedule | None:
    existing = (
        PreventiveSchedule.objects.filter(
            organization=asset.organization,
            asset_component=asset,
            auto_generated=True,
        )
        .order_by("id")
        .first()
    )

    should_disable = (
        not asset.auto_schedule_maintenance
        or not asset.maintenance_frequency
        or not asset.maintenance_next_due_date
        or asset.lifecycle_stage == AssetComponent.LifecycleStage.RETIRE
    )
    if should_disable:
        if existing:
            desired_status = (
                PreventiveSchedule.Status.COMPLETED
                if asset.lifecycle_stage == AssetComponent.LifecycleStage.RETIRE
                else PreventiveSchedule.Status.PAUSED
            )
            update_fields: list[str] = []
            if existing.status != desired_status:
                existing.status = desired_status
                update_fields.append("status")
            if desired_status == PreventiveSchedule.Status.COMPLETED and not existing.last_completed_date:
                existing.last_completed_date = asset.retired_date or timezone.localdate()
                update_fields.append("last_completed_date")
            if update_fields:
                existing.save(update_fields=update_fields + ["updated_at"])
        return None

    defaults = {
        "property": asset.property,
        "facility": asset.facility,
        "facility_space": asset.facility_space,
        "vendor": asset.amc_vendor or asset.vendor,
        "title": f"{asset.component_id} preventive maintenance",
        "description": f"Auto-generated maintenance plan for {asset.name}.",
        "category": _asset_category_to_work_order_category(asset.category),
        "frequency": asset.maintenance_frequency,
        "priority": WorkOrder.Priority.MEDIUM,
        "assigned_to": "",
        "next_due_date": asset.maintenance_next_due_date,
        "sla_target_hours": None,
        "generate_days_before": 0,
        "auto_create_work_orders": True,
        "status": PreventiveSchedule.Status.ACTIVE,
        "notes": "Managed automatically from asset management configuration.",
    }

    if existing:
        dirty_fields: list[str] = []
        for field_name, field_value in defaults.items():
            if getattr(existing, field_name) != field_value:
                setattr(existing, field_name, field_value)
                dirty_fields.append(field_name)
        if existing.auto_generated is not True:
            existing.auto_generated = True
            dirty_fields.append("auto_generated")
        if dirty_fields:
            existing.save(update_fields=dirty_fields + ["updated_at"])
        return existing

    return PreventiveSchedule.objects.create(
        organization=asset.organization,
        asset_component=asset,
        auto_generated=True,
        **defaults,
    )


def sync_asset_depreciation_journal(
    asset: AssetComponent,
    *,
    actor=None,
    sync_date: date | None = None,
) -> JournalEntry | None:
    if not depreciation_ready(asset):
        return None

    sync_day = sync_date or timezone.localdate()
    monthly_amount = monthly_depreciation_for(asset)
    if monthly_amount is None or monthly_amount <= 0:
        return None

    expense_account = Account.objects.filter(
        organization=asset.organization,
        code="5400",
        is_active=True,
    ).first()
    accumulated_account = Account.objects.filter(
        organization=asset.organization,
        code="1530",
        is_active=True,
    ).first()
    if not expense_account or not accumulated_account:
        return None

    period_token = sync_day.strftime("%Y%m")
    reference = f"ASSET-DEPR-{asset.id}-{period_token}"
    description = f"Asset depreciation sync for {asset.component_id} ({sync_day.strftime('%b %Y')})"

    with transaction.atomic():
        journal = (
            JournalEntry.objects.select_for_update()
            .filter(
                organization=asset.organization,
                source_type=JournalSourceType.ADJUSTMENT,
                source_id=asset.id,
                reference=reference,
            )
            .order_by("-id")
            .first()
        )
        if journal and journal.status != JournalEntry.Status.DRAFT:
            return journal

        if journal is None:
            journal = JournalEntry.objects.create(
                organization=asset.organization,
                entry_date=sync_day,
                description=description,
                reference=reference,
                source_type=JournalSourceType.ADJUSTMENT,
                source_id=asset.id,
                created_by=actor,
            )
        else:
            journal.entry_date = sync_day
            journal.description = description
            journal.created_by = journal.created_by or actor
            journal.save(update_fields=["entry_date", "description", "created_by", "updated_at"])
            journal.lines.all().delete()

        JournalLine.objects.create(
            journal=journal,
            line_number=1,
            account=expense_account,
            debit_amount=monthly_amount,
            credit_amount=Decimal("0.00"),
            memo=f"Depreciation expense for {asset.component_id}",
        )
        JournalLine.objects.create(
            journal=journal,
            line_number=2,
            account=accumulated_account,
            debit_amount=Decimal("0.00"),
            credit_amount=monthly_amount,
            memo=f"Accumulated depreciation for {asset.component_id}",
        )

    AssetComponent.objects.filter(pk=asset.pk).update(last_depreciation_sync_at=timezone.now())
    journal.refresh_from_db()
    return journal


def sync_asset_workflows(asset_id: int, *, actor=None) -> dict[str, object]:
    asset = (
        AssetComponent.objects.select_related(
            "property",
            "facility",
            "facility_space",
            "facility_space__facility",
            "facility_space__unit",
            "facility_space__unit__property",
            "vendor",
            "amc_vendor",
        )
        .get(pk=asset_id)
    )

    location_updates: dict[str, object] = {}
    if asset.facility_space_id:
        space = asset.facility_space
        if asset.facility_id != space.facility_id:
            location_updates["facility_id"] = space.facility_id
        if asset.unit_id != space.unit_id:
            location_updates["unit_id"] = space.unit_id
        if asset.property_id != space.facility.property_id:
            location_updates["property_id"] = space.facility.property_id
        if not asset.location_description and space.space_label:
            location_updates["location_description"] = space.space_label
    elif asset.facility_id and asset.property_id != asset.facility.property_id:
        location_updates["property_id"] = asset.facility.property_id

    if asset.lifecycle_stage == AssetComponent.LifecycleStage.RETIRE and asset.is_active:
        location_updates["is_active"] = False

    if location_updates:
        AssetComponent.objects.filter(pk=asset.pk).update(**location_updates)
        asset.refresh_from_db()

    schedule = ensure_preventive_schedule_for_asset(asset)
    journal = sync_asset_depreciation_journal(asset, actor=actor)
    return {
        "asset_id": asset.id,
        "schedule_id": schedule.id if schedule else None,
        "journal_id": journal.id if journal else None,
    }

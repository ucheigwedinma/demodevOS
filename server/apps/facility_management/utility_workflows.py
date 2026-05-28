from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.finance.models import Bill

from .models import UtilityBill, UtilityConsumption, UtilityMeter, UtilityMeterReading

ZERO = Decimal("0")
TWOPLACES = Decimal("0.01")
THREEPLACES = Decimal("0.001")

UTILITY_UNIT_MAP = {
    UtilityMeter.UtilityType.ELECTRICITY: "kWh",
    UtilityMeter.UtilityType.WATER: "m3",
    UtilityMeter.UtilityType.GAS: "m3",
    UtilityMeter.UtilityType.DIESEL: "liters",
}

UTILITY_CONSUMPTION_FIELD_MAP = {
    UtilityMeter.UtilityType.ELECTRICITY: "electricity_kwh",
    UtilityMeter.UtilityType.WATER: "water_m3",
    UtilityMeter.UtilityType.GAS: "gas_m3",
    UtilityMeter.UtilityType.DIESEL: "diesel_liters",
}

UTILITY_CARBON_FACTORS = {
    UtilityMeter.UtilityType.ELECTRICITY: Decimal("0.45"),
    UtilityMeter.UtilityType.WATER: Decimal("0.34"),
    UtilityMeter.UtilityType.GAS: Decimal("2.10"),
    UtilityMeter.UtilityType.DIESEL: Decimal("2.68"),
}


def quantize_money(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(value or 0).quantize(TWOPLACES)


def quantize_usage(value: Decimal | int | float | str | None) -> Decimal:
    return Decimal(value or 0).quantize(THREEPLACES)


def utility_consumption_field_for(utility_type: str) -> str:
    return UTILITY_CONSUMPTION_FIELD_MAP.get(
        utility_type,
        UTILITY_CONSUMPTION_FIELD_MAP[UtilityMeter.UtilityType.ELECTRICITY],
    )


def default_unit_for_utility_type(utility_type: str) -> str:
    return UTILITY_UNIT_MAP.get(utility_type, "")


def estimate_carbon_kg_co2e(
    *,
    electricity_kwh: Decimal | int | float | str = ZERO,
    water_m3: Decimal | int | float | str = ZERO,
    gas_m3: Decimal | int | float | str = ZERO,
    diesel_liters: Decimal | int | float | str = ZERO,
) -> Decimal:
    return quantize_money(
        Decimal(electricity_kwh or 0) * UTILITY_CARBON_FACTORS[UtilityMeter.UtilityType.ELECTRICITY]
        + Decimal(water_m3 or 0) * UTILITY_CARBON_FACTORS[UtilityMeter.UtilityType.WATER]
        + Decimal(gas_m3 or 0) * UTILITY_CARBON_FACTORS[UtilityMeter.UtilityType.GAS]
        + Decimal(diesel_liters or 0) * UTILITY_CARBON_FACTORS[UtilityMeter.UtilityType.DIESEL]
    )


def ensure_utility_meter_defaults(meter: UtilityMeter) -> bool:
    changed = False
    update_fields: list[str] = []

    if meter.organization_id != meter.property.organization_id:
        meter.organization = meter.property.organization
        update_fields.append("organization")
        changed = True

    desired_unit = default_unit_for_utility_type(meter.utility_type)
    if desired_unit and meter.unit_of_measure != desired_unit:
        meter.unit_of_measure = desired_unit
        update_fields.append("unit_of_measure")
        changed = True

    if meter.vendor_id and not meter.provider_name:
        meter.provider_name = meter.vendor.name
        update_fields.append("provider_name")
        changed = True

    if changed:
        meter.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def recalculate_meter_reading_series(meter: UtilityMeter) -> dict[str, int]:
    now = timezone.now()
    changed_count = 0
    anomalies_flagged = 0
    trailing_positive_deltas: list[Decimal] = []
    previous_value: Decimal | None = None
    last_reading_at = None

    readings = list(meter.readings.order_by("reading_at", "id"))
    for reading in readings:
        target_date = timezone.localdate(reading.reading_at)
        target_delta = ZERO
        target_is_anomaly = False
        target_reason = ""

        current_value = Decimal(reading.reading_value or 0)
        if previous_value is not None:
            target_delta = quantize_usage(current_value - previous_value)
            if target_delta < ZERO:
                target_is_anomaly = True
                target_reason = "Reading is lower than the previous capture."
            elif trailing_positive_deltas:
                average_delta = sum(trailing_positive_deltas, ZERO) / Decimal(len(trailing_positive_deltas))
                if average_delta > ZERO and target_delta > average_delta * Decimal("2.5") and target_delta > Decimal("10"):
                    target_is_anomaly = True
                    target_reason = "Consumption spike detected against the recent meter pattern."

        if target_delta > ZERO:
            trailing_positive_deltas.append(target_delta)
            trailing_positive_deltas = trailing_positive_deltas[-5:]

        update_kwargs: dict[str, object] = {}
        if reading.reading_date != target_date:
            update_kwargs["reading_date"] = target_date
            reading.reading_date = target_date
        if quantize_usage(reading.consumption_delta) != target_delta:
            update_kwargs["consumption_delta"] = target_delta
            reading.consumption_delta = target_delta
        if reading.is_anomaly != target_is_anomaly:
            update_kwargs["is_anomaly"] = target_is_anomaly
            reading.is_anomaly = target_is_anomaly
        if reading.anomaly_reason != target_reason:
            update_kwargs["anomaly_reason"] = target_reason
            reading.anomaly_reason = target_reason

        if update_kwargs:
            update_kwargs["updated_at"] = now
            UtilityMeterReading.objects.filter(pk=reading.pk).update(**update_kwargs)
            changed_count += 1
        if target_is_anomaly:
            anomalies_flagged += 1

        previous_value = current_value
        last_reading_at = reading.reading_at

    meter_update_kwargs: dict[str, object] = {}
    if meter.last_reading_at != last_reading_at:
        meter_update_kwargs["last_reading_at"] = last_reading_at
        meter.last_reading_at = last_reading_at
    if meter_update_kwargs:
        meter_update_kwargs["updated_at"] = now
        UtilityMeter.objects.filter(pk=meter.pk).update(**meter_update_kwargs)

    return {
        "readings_synced": changed_count,
        "anomalies_flagged": anomalies_flagged,
    }


def _persist_consumption_row(
    *,
    organization,
    property_obj,
    reading_date,
    field_name: str,
    value: Decimal,
) -> bool:
    row = (
        UtilityConsumption.objects.filter(
            organization=organization,
            property=property_obj,
            reading_date=reading_date,
        )
        .order_by("id")
        .first()
    )

    if row is None:
        payload = {
            "organization": organization,
            "property": property_obj,
            "reading_date": reading_date,
            field_name: value,
        }
        UtilityConsumption.objects.create(**payload)
        return True

    current_value = quantize_money(getattr(row, field_name, ZERO))
    if current_value == quantize_money(value):
        return False

    setattr(row, field_name, quantize_money(value))
    row.save(update_fields=[field_name, "updated_at"])
    return True


def rebuild_utility_consumption_for_property(property_obj, utility_type: str) -> int:
    meters = UtilityMeter.objects.filter(
        organization=property_obj.organization,
        property=property_obj,
        utility_type=utility_type,
    )
    field_name = utility_consumption_field_for(utility_type)
    date_totals = defaultdict(lambda: ZERO)

    readings = (
        UtilityMeterReading.objects.filter(
            organization=property_obj.organization,
            meter__in=meters,
        )
        .values("reading_date")
        .annotate(total=Sum("consumption_delta"))
    )
    for row in readings:
        date_totals[row["reading_date"]] = quantize_money(row["total"] or ZERO)

    changed_rows = 0
    existing_rows = UtilityConsumption.objects.filter(
        organization=property_obj.organization,
        property=property_obj,
    ).order_by("id")
    for row in existing_rows:
        target_value = date_totals.get(row.reading_date, ZERO)
        current_value = quantize_money(getattr(row, field_name, ZERO))
        if current_value != target_value:
            setattr(row, field_name, target_value)
            row.save(update_fields=[field_name, "updated_at"])
            changed_rows += 1

    existing_dates = set(existing_rows.values_list("reading_date", flat=True))
    for reading_date, value in date_totals.items():
        if reading_date in existing_dates:
            continue
        if _persist_consumption_row(
            organization=property_obj.organization,
            property_obj=property_obj,
            reading_date=reading_date,
            field_name=field_name,
            value=value,
        ):
            changed_rows += 1

    return changed_rows


def usage_quantity_for_bill_period(bill: UtilityBill) -> Decimal:
    if bill.billing_period_end < bill.billing_period_start:
        return ZERO

    if bill.meter_id:
        aggregate = bill.meter.readings.filter(
            reading_date__gte=bill.billing_period_start,
            reading_date__lte=bill.billing_period_end,
        ).aggregate(total=Sum("consumption_delta"))
        return quantize_usage(aggregate["total"] or ZERO)

    field_name = utility_consumption_field_for(bill.utility_type)
    aggregate = UtilityConsumption.objects.filter(
        organization=bill.organization,
        property=bill.property,
        reading_date__gte=bill.billing_period_start,
        reading_date__lte=bill.billing_period_end,
    ).aggregate(total=Sum(field_name))
    return quantize_usage(aggregate["total"] or ZERO)


def utility_bill_status_for(bill: UtilityBill, *, today=None) -> str:
    today = today or timezone.localdate()
    if bill.status == UtilityBill.Status.CANCELLED:
        return UtilityBill.Status.CANCELLED
    if quantize_money(bill.amount_paid) >= quantize_money(bill.total_amount) and quantize_money(bill.total_amount) > ZERO:
        return UtilityBill.Status.PAID
    if bill.status == UtilityBill.Status.DISPUTED:
        return UtilityBill.Status.DISPUTED
    if bill.issue_date is None:
        return UtilityBill.Status.DRAFT
    if bill.due_date and bill.due_date < today:
        return UtilityBill.Status.OVERDUE
    return UtilityBill.Status.ISSUED


def ensure_utility_bill_defaults(bill: UtilityBill, *, today=None) -> bool:
    today = today or timezone.localdate()
    changed = False
    update_fields: list[str] = []

    if bill.organization_id != bill.property.organization_id:
        bill.organization = bill.property.organization
        update_fields.append("organization")
        changed = True

    if bill.meter_id:
        if bill.property_id != bill.meter.property_id:
            bill.property = bill.meter.property
            update_fields.append("property")
            changed = True
        if bill.utility_type != bill.meter.utility_type:
            bill.utility_type = bill.meter.utility_type
            update_fields.append("utility_type")
            changed = True
        if not bill.provider_name:
            provider_name = bill.meter.provider_name or (bill.meter.vendor.name if bill.meter.vendor_id else "")
            if provider_name:
                bill.provider_name = provider_name
                update_fields.append("provider_name")
                changed = True

    if bill.vendor_id and not bill.provider_name:
        bill.provider_name = bill.vendor.name
        update_fields.append("provider_name")
        changed = True

    usage_quantity = usage_quantity_for_bill_period(bill)
    if usage_quantity > ZERO or quantize_usage(bill.usage_quantity) == ZERO:
        if quantize_usage(bill.usage_quantity) != usage_quantity:
            bill.usage_quantity = usage_quantity
            update_fields.append("usage_quantity")
            changed = True

    usage_value = quantize_usage(bill.usage_quantity)
    unit_rate_value = Decimal(bill.unit_rate or 0)
    calculated_subtotal = (usage_value * unit_rate_value).quantize(TWOPLACES)
    if unit_rate_value > ZERO and usage_value > ZERO:
        calculated_subtotal = calculated_subtotal.quantize(TWOPLACES)
        if quantize_money(bill.subtotal) != calculated_subtotal:
            bill.subtotal = calculated_subtotal
            update_fields.append("subtotal")
            changed = True

    calculated_total = (quantize_money(bill.subtotal) + quantize_money(bill.tax_amount)).quantize(TWOPLACES)
    if quantize_money(bill.total_amount) != calculated_total:
        bill.total_amount = calculated_total
        update_fields.append("total_amount")
        changed = True

    if bill.finance_bill_id:
        finance_bill = bill.finance_bill
        finance_paid = quantize_money(finance_bill.paid_amount)
        if quantize_money(bill.amount_paid) != finance_paid:
            bill.amount_paid = finance_paid
            update_fields.append("amount_paid")
            changed = True
        if finance_bill.status == Bill.Status.CANCELLED and bill.status != UtilityBill.Status.CANCELLED:
            bill.status = UtilityBill.Status.CANCELLED
            update_fields.append("status")
            changed = True
        elif finance_bill.status == Bill.Status.PAID and bill.status != UtilityBill.Status.PAID:
            bill.status = UtilityBill.Status.PAID
            update_fields.append("status")
            changed = True

    target_status = utility_bill_status_for(bill, today=today)
    if bill.status != target_status:
        bill.status = target_status
        update_fields.append("status")
        changed = True

    if changed:
        bill.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
    return changed


def sync_finance_bill_for_utility_bill(bill: UtilityBill) -> bool:
    if not bill.vendor_id:
        return False

    desired_status = {
        UtilityBill.Status.DRAFT: Bill.Status.DRAFT,
        UtilityBill.Status.CANCELLED: Bill.Status.CANCELLED,
        UtilityBill.Status.PAID: Bill.Status.PAID,
        UtilityBill.Status.ISSUED: Bill.Status.APPROVED,
        UtilityBill.Status.OVERDUE: Bill.Status.APPROVED,
        UtilityBill.Status.DISPUTED: Bill.Status.APPROVED,
    }[bill.status]

    note_header = (
        f"Utility bill sync ({bill.get_utility_type_display()})"
        f" [{bill.billing_period_start} to {bill.billing_period_end}]"
    )
    notes = "\n".join(filter(None, [note_header, bill.notes])).strip()

    if bill.finance_bill_id:
        finance_bill = bill.finance_bill
        changed = False
        update_fields: list[str] = []
        field_values = {
            "organization": bill.organization,
            "vendor": bill.vendor,
            "property": bill.property,
            "issue_date": bill.issue_date,
            "due_date": bill.due_date,
            "subtotal": quantize_money(bill.subtotal),
            "tax_amount": quantize_money(bill.tax_amount),
            "total_amount": quantize_money(bill.total_amount),
            "status": desired_status,
            "notes": notes,
        }
        for field_name, value in field_values.items():
            if getattr(finance_bill, field_name) != value:
                setattr(finance_bill, field_name, value)
                update_fields.append(field_name)
                changed = True
        if changed:
            finance_bill.save(update_fields=[*dict.fromkeys([*update_fields, "updated_at"])])
        return changed

    finance_bill = Bill.objects.create(
        organization=bill.organization,
        vendor=bill.vendor,
        property=bill.property,
        issue_date=bill.issue_date,
        due_date=bill.due_date,
        subtotal=quantize_money(bill.subtotal),
        tax_amount=quantize_money(bill.tax_amount),
        total_amount=quantize_money(bill.total_amount),
        status=desired_status,
        notes=notes,
    )
    bill.finance_bill = finance_bill
    bill.save(update_fields=["finance_bill", "updated_at"])
    return True


def run_utility_energy_automation(organization) -> dict[str, int]:
    today = timezone.localdate()
    summary = {
        "meters_synced": 0,
        "readings_synced": 0,
        "anomalies_flagged": 0,
        "consumption_days_synced": 0,
        "bills_synced": 0,
        "finance_bills_synced": 0,
        "overdue_bills": 0,
    }

    property_type_pairs: set[tuple[int, str]] = set()
    properties_by_id = {}

    meters = list(
        UtilityMeter.objects.filter(
            organization=organization,
            property__facility_registry__isnull=False,
        )
        .select_related("property", "vendor")
        .order_by("property_id", "utility_type", "meter_number")
    )
    for meter in meters:
        properties_by_id[meter.property_id] = meter.property
        if ensure_utility_meter_defaults(meter):
            summary["meters_synced"] += 1
        result = recalculate_meter_reading_series(meter)
        summary["readings_synced"] += result["readings_synced"]
        summary["anomalies_flagged"] += result["anomalies_flagged"]
        property_type_pairs.add((meter.property_id, meter.utility_type))

    for property_id, utility_type in property_type_pairs:
        summary["consumption_days_synced"] += rebuild_utility_consumption_for_property(
            properties_by_id[property_id],
            utility_type,
        )

    bills = list(
        UtilityBill.objects.filter(
            organization=organization,
            property__facility_registry__isnull=False,
        )
        .select_related("property", "meter", "meter__vendor", "vendor", "finance_bill")
        .order_by("-billing_period_end", "-id")
    )
    for bill in bills:
        if ensure_utility_bill_defaults(bill, today=today):
            summary["bills_synced"] += 1
        if sync_finance_bill_for_utility_bill(bill):
            summary["finance_bills_synced"] += 1
        if ensure_utility_bill_defaults(bill, today=today):
            summary["bills_synced"] += 1

    summary["overdue_bills"] = UtilityBill.objects.filter(
        organization=organization,
        status=UtilityBill.Status.OVERDUE,
    ).count()
    return summary

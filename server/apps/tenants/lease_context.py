from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from .models import LeaseAgreement

ZERO_DECIMAL = Decimal("0.00")
AUTO_LEASE_CONTEXT_MARKER = "[auto-lease-context]"
DEFAULT_DRAFT_LEASE_TERM_DAYS = 365


def profile_property(profile):
    if getattr(profile, "property_id", None) and getattr(profile, "property", None):
        return profile.property
    if getattr(profile, "unit_id", None) and getattr(profile, "unit", None):
        return profile.unit.property
    if getattr(profile, "facility_id", None) and getattr(profile, "facility", None):
        return profile.facility.property
    if getattr(profile, "facility_space_id", None) and getattr(profile, "facility_space", None):
        return profile.facility_space.facility.property
    return None


def profile_unit(profile):
    if getattr(profile, "unit_id", None) and getattr(profile, "unit", None):
        return profile.unit
    if getattr(profile, "facility_space_id", None) and getattr(profile, "facility_space", None):
        return profile.facility_space.unit
    return None


def profile_facility(profile):
    if getattr(profile, "facility_id", None) and getattr(profile, "facility", None):
        return profile.facility
    if getattr(profile, "facility_space_id", None) and getattr(profile, "facility_space", None):
        return profile.facility_space.facility
    property_record = profile_property(profile)
    if property_record is not None:
        try:
            return property_record.facility_registry
        except ObjectDoesNotExist:
            return None
    return None


def _seed_lease_title(profile) -> str:
    display_name = getattr(profile, "resolved_display_name", "") or getattr(profile, "display_name", "") or "Tenant"
    return f"{display_name} lease context"


def seed_lease_payload_for_profile(profile, *, today=None):
    today = today or timezone.localdate()
    property_record = profile_property(profile)
    facility = profile_facility(profile)
    unit = profile_unit(profile)
    facility_space = getattr(profile, "facility_space", None)

    errors: dict[str, list[str]] = {}
    if property_record is None:
        errors["property"] = ["Assign a property, unit, facility, or space before creating a tenant profile."]
    if property_record is not None and facility is None:
        errors["facility"] = ["Selected property must resolve to a facility before creating a tenant profile."]

    raw_end_date = getattr(profile, "lease_end_date", None) or getattr(profile, "move_out_date", None)
    start_date = (
        getattr(profile, "lease_start_date", None)
        or getattr(profile, "move_in_date", None)
        or (raw_end_date - timedelta(days=DEFAULT_DRAFT_LEASE_TERM_DAYS) if raw_end_date else None)
        or today
    )

    provisional_start = getattr(profile, "lease_start_date", None) is None and getattr(profile, "move_in_date", None) is None
    provisional_end = raw_end_date is None or raw_end_date <= start_date
    end_date = raw_end_date if not provisional_end else start_date + timedelta(days=DEFAULT_DRAFT_LEASE_TERM_DAYS)

    if errors:
        return None, errors

    notes = [
        AUTO_LEASE_CONTEXT_MARKER,
        "Auto-created to keep the tenant profile anchored to a lease relationship.",
    ]
    if provisional_start:
        notes.append("Start date was provisionally derived from onboarding context.")
    if provisional_end:
        notes.append("End date was provisionally set pending final contract terms.")

    return {
        "property": property_record,
        "unit": unit,
        "facility": facility,
        "facility_space": facility_space,
        "title": _seed_lease_title(profile),
        "status": LeaseAgreement.Status.DRAFT,
        "start_date": start_date,
        "end_date": end_date,
        "rent_amount": ZERO_DECIMAL,
        "service_charge_amount": ZERO_DECIMAL,
        "security_deposit": ZERO_DECIMAL,
        "payment_frequency": LeaseAgreement.PaymentFrequency.MONTHLY,
        "escalation_rule": LeaseAgreement.EscalationRule.NONE,
        "notes": " ".join(notes),
    }, {}


def ensure_tenant_profile_lease_context(profile, *, today=None, skip_created_automation=True):
    if profile is None or getattr(profile, "pk", None) is None:
        return None, False, False

    payload, errors = seed_lease_payload_for_profile(profile, today=today)
    if errors:
        return None, False, False

    auto_lease = (
        profile.lease_agreements.filter(notes__icontains=AUTO_LEASE_CONTEXT_MARKER)
        .order_by("id")
        .first()
    )
    if auto_lease is None and profile.lease_agreements.exists():
        return profile.lease_agreements.order_by("id").first(), False, False

    if auto_lease is None:
        lease = LeaseAgreement(
            organization=profile.organization,
            tenant_profile=profile,
            **payload,
        )
        if skip_created_automation:
            lease._skip_created_automation = True
        lease.save()
        return lease, True, False

    update_fields = []
    for field_name, value in payload.items():
        if getattr(auto_lease, field_name) != value:
            setattr(auto_lease, field_name, value)
            update_fields.append(field_name)
    if update_fields:
        auto_lease._skip_created_automation = True
        auto_lease.save(update_fields=list(dict.fromkeys(update_fields + ["updated_at"])))
        return auto_lease, False, True
    return auto_lease, False, False

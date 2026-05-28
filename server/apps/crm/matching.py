from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q

from apps.crm.models import Lead, LeadActivity, LeadProjectInterest, LeadPropertyMatch
from apps.finance.models import PaymentPlan
from apps.projects.models import Project
from apps.properties.models import Property, Unit

BUDGET_WEIGHT = Decimal("40")
LOCATION_WEIGHT = Decimal("25")
UNIT_TYPE_WEIGHT = Decimal("20")
PAYMENT_WEIGHT = Decimal("15")

MAX_UNIT_MATCHES = 20
MAX_PROJECT_MATCHES = 20


def _to_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _round_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_list(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [token.strip() for token in value.split(",") if token.strip()]
    return []


def _lead_preferred_locations(lead: Lead) -> set[str]:
    return {_normalize_text(loc) for loc in _normalize_list(lead.preferred_locations)}


def _lead_preferred_unit_types(lead: Lead) -> set[str]:
    return {
        str(v).strip().lower()
        for v in lead.unit_preferences.values_list("unit_type", flat=True)
        if str(v).strip()
    }


def _lead_effective_payment_capability(lead: Lead) -> str:
    assessment = getattr(lead, "financial_assessment", None)
    if assessment and assessment.recommended_plan:
        return str(assessment.recommended_plan)
    return str(lead.payment_capability or "undetermined")


def _lead_effective_budget(lead: Lead) -> tuple[Decimal | None, Decimal | None]:
    min_budget = _to_decimal(lead.budget_min)
    max_budget = _to_decimal(lead.budget_max)

    assessment = getattr(lead, "financial_assessment", None)
    affordability_cap = _to_decimal(getattr(assessment, "max_affordable_price", None))
    if affordability_cap is not None:
        if max_budget is None:
            max_budget = affordability_cap
        else:
            max_budget = min(max_budget, affordability_cap)
    return min_budget, max_budget


def _budget_fit(price: Decimal | None, min_budget: Decimal | None, max_budget: Decimal | None) -> bool:
    if price is None:
        return False
    if min_budget is None and max_budget is None:
        return False
    if min_budget is not None and price < min_budget:
        return False
    if max_budget is not None and price > max_budget:
        return False
    return True


def _location_fit(preferred_locations: set[str], location_blob: str) -> bool:
    if not preferred_locations:
        return False
    normalized = _normalize_text(location_blob)
    if not normalized:
        return False
    return any(loc in normalized for loc in preferred_locations if loc)


def _payment_fit(preferred_payment: str, has_payment_plan: bool) -> bool:
    pref = (preferred_payment or "undetermined").lower()
    if pref in {"cash", "undetermined", ""}:
        return True
    if pref in {"installment", "mortgage", "mixed"}:
        return has_payment_plan
    return has_payment_plan


def _build_breakdown(
    *,
    budget_fit: bool,
    location_fit: bool,
    unit_type_fit: bool,
    payment_fit: bool,
) -> tuple[Decimal, dict]:
    budget_score = BUDGET_WEIGHT if budget_fit else Decimal("0")
    location_score = LOCATION_WEIGHT if location_fit else Decimal("0")
    unit_type_score = UNIT_TYPE_WEIGHT if unit_type_fit else Decimal("0")
    payment_score = PAYMENT_WEIGHT if payment_fit else Decimal("0")
    total = budget_score + location_score + unit_type_score + payment_score
    breakdown = {
        "budget": float(budget_score),
        "location": float(location_score),
        "unit_type": float(unit_type_score),
        "payment_eligibility": float(payment_score),
    }
    return _round_score(total), breakdown


def _build_reason_summary(
    *,
    budget_fit: bool,
    location_fit: bool,
    unit_type_fit: bool,
    payment_fit: bool,
) -> str:
    hits = []
    misses = []
    if budget_fit:
        hits.append("Budget aligned")
    else:
        misses.append("Budget mismatch")
    if location_fit:
        hits.append("Preferred location matched")
    else:
        misses.append("Location not matched")
    if unit_type_fit:
        hits.append("Unit type matched")
    else:
        misses.append("Unit type not matched")
    if payment_fit:
        hits.append("Payment eligibility matched")
    else:
        misses.append("Payment eligibility mismatch")

    if hits:
        return "; ".join(hits + misses)
    return "; ".join(misses)


def _admin_users_for_org(org) -> list:
    from apps.accounts.models import UserProfile

    return [
        p.user
        for p in UserProfile.objects.filter(
            organization=org,
            role="admin",
            user__is_active=True,
        ).select_related("user")
    ]


def recompute_matches_for_lead(
    *,
    lead: Lead,
    source: str = LeadPropertyMatch.MatchSource.MANUAL_REFRESH,
    property_id: int | None = None,
) -> dict:
    """Recompute active matches for a lead with idempotent upsert behavior."""
    org_id = lead.organization_id
    if not org_id:
        return {"created_count": 0, "updated_count": 0, "deactivated_count": 0, "active_count": 0}

    preferred_locations = _lead_preferred_locations(lead)
    preferred_unit_types = _lead_preferred_unit_types(lead)
    preferred_payment = _lead_effective_payment_capability(lead)
    min_budget, max_budget = _lead_effective_budget(lead)

    units_qs = (
        Unit.objects.select_related("property")
        .filter(
            organization_id=org_id,
            status=Unit.UnitStatus.AVAILABLE,
            property__is_active=True,
        )
    )
    if property_id:
        units_qs = units_qs.filter(property_id=property_id)
    units = list(units_qs)
    unit_ids = [u.id for u in units]

    projects_qs = (
        Project.objects.select_related("property")
        .filter(organization_id=org_id)
        .filter(Q(property__isnull=True) | Q(property__is_active=True))
        .exclude(status=Project.Status.ON_HOLD)
    )
    if property_id:
        projects_qs = projects_qs.filter(property_id=property_id)
    projects = list(projects_qs)

    units_by_property: dict[int, list[Unit]] = {}
    for unit in units:
        units_by_property.setdefault(unit.property_id, []).append(unit)

    unit_plan_ids = set(
        PaymentPlan.objects.filter(
            organization_id=org_id,
            direction=PaymentPlan.Direction.RECEIVABLE,
            status=PaymentPlan.Status.ACTIVE,
            unit_id__in=unit_ids,
        ).values_list("unit_id", flat=True)
    )
    project_plan_ids = set(
        PaymentPlan.objects.filter(
            organization_id=org_id,
            direction=PaymentPlan.Direction.RECEIVABLE,
            status=PaymentPlan.Status.ACTIVE,
            project_id__in=[p.id for p in projects],
        ).values_list("project_id", flat=True)
    )

    unit_candidates = []
    for unit in units:
        property_obj = unit.property
        price = _to_decimal(unit.asking_price)
        budget_fit = _budget_fit(price, min_budget, max_budget)
        location_blob = f"{property_obj.name} {property_obj.address} {unit.location_description}"
        location_fit = _location_fit(preferred_locations, location_blob)
        unit_type_fit = bool(preferred_unit_types) and (str(unit.unit_category).lower() in preferred_unit_types)
        payment_fit = _payment_fit(preferred_payment, unit.id in unit_plan_ids)
        total, breakdown = _build_breakdown(
            budget_fit=budget_fit,
            location_fit=location_fit,
            unit_type_fit=unit_type_fit,
            payment_fit=payment_fit,
        )
        unit_candidates.append(
            {
                "candidate_type": LeadPropertyMatch.CandidateType.UNIT,
                "property": property_obj,
                "unit": unit,
                "project": None,
                "match_score": total,
                "score_breakdown": breakdown,
                "reason_summary": _build_reason_summary(
                    budget_fit=budget_fit,
                    location_fit=location_fit,
                    unit_type_fit=unit_type_fit,
                    payment_fit=payment_fit,
                ),
                "budget_fit": budget_fit,
                "location_fit": location_fit,
                "unit_type_fit": unit_type_fit,
                "payment_eligibility_fit": payment_fit,
            }
        )

    project_candidates = []
    for project in projects:
        property_obj: Property | None = project.property
        related_units = units_by_property.get(project.property_id or 0, [])
        price_candidates = [
            _to_decimal(u.asking_price)
            for u in related_units
            if _to_decimal(u.asking_price) is not None
        ]
        project_price = min(price_candidates) if price_candidates else _to_decimal(project.budget)
        budget_fit = _budget_fit(project_price, min_budget, max_budget)
        location_blob = f"{project.name} {project.location} {property_obj.address if property_obj else ''}"
        location_fit = _location_fit(preferred_locations, location_blob)
        related_categories = {str(u.unit_category).lower() for u in related_units if u.unit_category}
        unit_type_fit = bool(preferred_unit_types.intersection(related_categories)) if preferred_unit_types else False
        has_plan = (project.id in project_plan_ids) or any(u.id in unit_plan_ids for u in related_units)
        payment_fit = _payment_fit(preferred_payment, has_plan)
        total, breakdown = _build_breakdown(
            budget_fit=budget_fit,
            location_fit=location_fit,
            unit_type_fit=unit_type_fit,
            payment_fit=payment_fit,
        )
        project_candidates.append(
            {
                "candidate_type": LeadPropertyMatch.CandidateType.PROJECT,
                "property": property_obj,
                "unit": None,
                "project": project,
                "match_score": total,
                "score_breakdown": breakdown,
                "reason_summary": _build_reason_summary(
                    budget_fit=budget_fit,
                    location_fit=location_fit,
                    unit_type_fit=unit_type_fit,
                    payment_fit=payment_fit,
                ),
                "budget_fit": budget_fit,
                "location_fit": location_fit,
                "unit_type_fit": unit_type_fit,
                "payment_eligibility_fit": payment_fit,
            }
        )

    unit_candidates.sort(key=lambda row: (row["match_score"], row["budget_fit"]), reverse=True)
    project_candidates.sort(key=lambda row: (row["match_score"], row["budget_fit"]), reverse=True)
    selected_rows = unit_candidates[:MAX_UNIT_MATCHES] + project_candidates[:MAX_PROJECT_MATCHES]

    created_count = 0
    updated_count = 0
    active_ids: set[int] = set()

    with transaction.atomic():
        for row in selected_rows:
            lookup = {
                "lead": lead,
                "candidate_type": row["candidate_type"],
            }
            if row["candidate_type"] == LeadPropertyMatch.CandidateType.UNIT:
                lookup["unit"] = row["unit"]
            else:
                lookup["project"] = row["project"]

            defaults = {
                "organization_id": org_id,
                "property": row["property"],
                "match_score": row["match_score"],
                "score_breakdown": row["score_breakdown"],
                "reason_summary": row["reason_summary"],
                "budget_fit": row["budget_fit"],
                "location_fit": row["location_fit"],
                "unit_type_fit": row["unit_type_fit"],
                "payment_eligibility_fit": row["payment_eligibility_fit"],
                "source": source,
                "is_active": True,
            }

            obj, created = LeadPropertyMatch.objects.get_or_create(
                **lookup,
                defaults={
                    **defaults,
                    "status": LeadPropertyMatch.MatchStatus.SUGGESTED,
                },
            )

            if created:
                created_count += 1
            else:
                changed_fields = []
                for field, value in defaults.items():
                    if getattr(obj, field) != value:
                        setattr(obj, field, value)
                        changed_fields.append(field)
                if changed_fields:
                    obj.save(update_fields=changed_fields + ["updated_at"])
                    updated_count += 1
            active_ids.add(obj.id)

        stale_qs = LeadPropertyMatch.objects.filter(
            lead=lead,
            is_active=True,
        )
        if property_id:
            stale_qs = stale_qs.filter(property_id=property_id)
        if active_ids:
            stale_qs = stale_qs.exclude(id__in=active_ids)
        deactivated_count = stale_qs.update(is_active=False)

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "deactivated_count": deactivated_count,
        "active_count": len(active_ids),
    }


def generate_matches_for_qualified_lead(*, lead: Lead) -> dict:
    return recompute_matches_for_lead(
        lead=lead,
        source=LeadPropertyMatch.MatchSource.QUALIFIED_LEAD,
    )


def seed_project_interests_from_matches(*, lead: Lead, limit: int = 3) -> int:
    existing_project_ids = set(lead.project_interests.values_list("project_id", flat=True))
    candidate_project_ids = list(
        lead.property_matches.filter(
            candidate_type=LeadPropertyMatch.CandidateType.PROJECT,
            is_active=True,
            project_id__isnull=False,
        )
        .order_by("-match_score", "-updated_at")
        .values_list("project_id", flat=True)[:limit * 3]
    )
    created_count = 0
    for project_id in candidate_project_ids:
        if project_id in existing_project_ids:
            continue
        LeadProjectInterest.objects.create(
            lead=lead,
            project_id=project_id,
            interest_level=LeadProjectInterest.InterestLevel.MEDIUM,
            notes="Auto-recommended by property matching engine.",
        )
        existing_project_ids.add(project_id)
        created_count += 1
        if created_count >= limit:
            break
    return created_count


def generate_matches_for_property_launch(*, property_obj: Property, actor=None) -> dict:
    from apps.notifications.models import Notification
    from apps.notifications.services import dispatch_workflow_notification

    eligible_stages: Iterable[str] = (
        Lead.PipelineStage.QUALIFIED,
        Lead.PipelineStage.SITE_VISIT,
        Lead.PipelineStage.OFFER_MADE,
        Lead.PipelineStage.RESERVATION,
        Lead.PipelineStage.SPA_ISSUED,
        Lead.PipelineStage.CLOSED,
    )
    leads = (
        Lead.objects.filter(
            organization_id=property_obj.organization_id,
            status=Lead.Status.ACTIVE,
            is_archived=False,
            pipeline_stage__in=eligible_stages,
        )
        .select_related("assigned_to")
        .prefetch_related("unit_preferences")
    )
    admins = _admin_users_for_org(property_obj.organization)

    refreshed = 0
    notified = 0
    for lead in leads:
        result = recompute_matches_for_lead(
            lead=lead,
            source=LeadPropertyMatch.MatchSource.PROPERTY_LAUNCH,
            property_id=property_obj.id,
        )
        if result["active_count"] <= 0:
            continue

        refreshed += 1
        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.NOTE,
            subject="Property launch match suggestions refreshed",
            description=(
                f"Property launch '{property_obj.name}' generated/updated "
                f"{result['active_count']} active recommendation(s)."
            ),
            performed_by=actor if getattr(actor, "is_authenticated", False) else None,
            completed_at=None,
            is_completed=False,
        )

        recipients = list(admins)
        if lead.assigned_to_id and lead.assigned_to not in recipients:
            recipients.append(lead.assigned_to)
        if recipients:
            dispatch_workflow_notification(
                organization=property_obj.organization,
                event_key="crm_property_launch_match",
                recipients=recipients,
                context={
                    "lead_name": lead.full_name,
                    "property_name": property_obj.name,
                    "match_count": result["active_count"],
                    "action_url": f"/crm/property-matching?lead_id={lead.id}",
                },
                link_url=f"/crm/property-matching?lead_id={lead.id}",
                fallback_channels=["in_app"],
                fallback_title=f"Property Match Suggestions — {lead.full_name}",
                fallback_message=(
                    f"{result['active_count']} property match suggestion(s) have been generated for "
                    f"lead '{lead.full_name}' following the launch of '{property_obj.name}'. "
                    f"Please review the matches and reach out to the client."
                ),
                fallback_category=Notification.Category.CRM_LEAD,
                fallback_severity=Notification.Severity.INFO,
            )
            notified += 1

    return {"leads_refreshed": refreshed, "notifications_sent": notified}

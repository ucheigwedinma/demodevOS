from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import UserProfile
from apps.notifications.models import Notification
from apps.settings.currency import get_default_currency_code

from .models import (
    Candidate,
    JobListing,
    JobOffer,
    JobRequisition,
    Position,
    PositionAssignment,
    PositionBudget,
    Vacancy,
)

CRITICAL_ROLE_THRESHOLD = 80
CRITICAL_VACANCY_ALERT_AFTER_DAYS = 30


@dataclass(slots=True)
class PositionBudgetLimit:
    amount: Decimal
    source: str


@dataclass(slots=True)
class BudgetHealth:
    budgeted: Decimal
    committed: Decimal
    pipeline: Decimal
    unallocated: Decimal


def user_has_cfo_override_authority(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    if profile is None:
        return False

    if profile.role == "admin":
        return True

    tokens = []
    assigned_role = getattr(profile, "assigned_role", None)
    if assigned_role is not None:
        tokens.extend(
            [
                (assigned_role.slug or "").lower(),
                (assigned_role.name or "").lower(),
            ]
        )
    tokens.append((profile.job_title or "").lower())
    merged = " ".join(tokens)
    return any(
        keyword in merged
        for keyword in (
            "cfo",
            "chief financial officer",
            "finance director",
            "head of finance",
        )
    )


def _safe_decimal(value, default=Decimal("0")) -> Decimal:
    if value is None:
        return default
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return default


def _position_budget_base_mid(row: PositionBudget) -> Decimal | None:
    if not row.position_id:
        return None
    structure = getattr(row.position, "salary_structure", None)
    if not structure:
        return None

    min_salary = _safe_decimal(getattr(structure, "min_salary", None), default=None)
    max_salary = _safe_decimal(getattr(structure, "max_salary", None), default=None)
    if min_salary is not None and max_salary is not None:
        return (min_salary + max_salary) / Decimal("2")
    return min_salary if min_salary is not None else max_salary


def _position_budget_per_head_cost(row: PositionBudget) -> Decimal:
    base_mid = _position_budget_base_mid(row)
    if base_mid is not None:
        fte = _safe_decimal(getattr(row, "fte", None), Decimal("1"))
        statutory_rate = _safe_decimal(getattr(row, "statutory_benefits_rate", None))
        allowances_rate = _safe_decimal(getattr(row, "allowances_rate", None))
        local_tax_rate = _safe_decimal(getattr(row, "local_tax_rate", None))
        insurance_rate = _safe_decimal(getattr(row, "insurance_rate", None))
        multiplier = Decimal("1") + (
            statutory_rate + allowances_rate + local_tax_rate + insurance_rate
        ) / Decimal("100")
        return base_mid * multiplier * fte

    approved_headcount = max(int(row.approved_headcount or 0), 0)
    if approved_headcount > 0:
        return _safe_decimal(row.budget_amount) / Decimal(str(approved_headcount))
    return Decimal("0")


def _vacancy_pipeline_cost(
    *,
    vacancy: Vacancy,
    budget_row: PositionBudget | None,
) -> Decimal:
    if budget_row is not None:
        return _position_budget_per_head_cost(budget_row)

    position = getattr(vacancy, "position", None)
    structure = getattr(position, "salary_structure", None) if position else None
    if not structure:
        return Decimal("0")

    min_salary = _safe_decimal(getattr(structure, "min_salary", None), default=None)
    max_salary = _safe_decimal(getattr(structure, "max_salary", None), default=None)
    if min_salary is not None and max_salary is not None:
        base_mid = (min_salary + max_salary) / Decimal("2")
    else:
        base_mid = min_salary if min_salary is not None else max_salary
    if base_mid is None:
        return Decimal("0")
    return base_mid * Decimal("1.25")


def get_department_budget_health(
    *,
    organization_id: int,
    department_id: int,
    fiscal_year: int | None = None,
) -> BudgetHealth:
    budgets_qs = PositionBudget.objects.filter(
        organization_id=organization_id,
        department_id=department_id,
    ).select_related(
        "position",
        "position__salary_structure",
    )
    if fiscal_year is not None:
        budgets_qs = budgets_qs.filter(fiscal_year=fiscal_year)

    budget_rows = list(budgets_qs.order_by("-fiscal_year", "-updated_at", "-id"))
    position_budget_map: dict[int, PositionBudget] = {}
    budgeted_total = Decimal("0")
    committed_total = Decimal("0")

    for row in budget_rows:
        budgeted_total += _safe_decimal(row.budget_amount)
        committed_total += _position_budget_per_head_cost(row) * Decimal(str(int(row.filled_headcount or 0)))
        if row.position_id and row.position_id not in position_budget_map:
            position_budget_map[row.position_id] = row

    vacancies_qs = Vacancy.objects.filter(
        organization_id=organization_id,
        position__department_id=department_id,
        status__in=(Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD),
    ).select_related("position", "position__salary_structure")

    pipeline_total = Decimal("0")
    for vacancy in vacancies_qs:
        position_id = vacancy.position_id
        budget_row = position_budget_map.get(position_id) if position_id else None
        pipeline_total += _vacancy_pipeline_cost(vacancy=vacancy, budget_row=budget_row)

    unallocated = budgeted_total - committed_total - pipeline_total
    return BudgetHealth(
        budgeted=budgeted_total,
        committed=committed_total,
        pipeline=pipeline_total,
        unallocated=unallocated,
    )


def get_business_unit_budget_guardrails(
    *,
    organization_id: int,
    fiscal_year: int | None = None,
) -> list[dict[str, object]]:
    budgets_qs = (
        PositionBudget.objects.filter(organization_id=organization_id)
        .select_related("department__division", "position", "position__salary_structure")
        .order_by("-fiscal_year", "-updated_at", "-id")
    )
    if fiscal_year is not None:
        budgets_qs = budgets_qs.filter(fiscal_year=fiscal_year)

    budget_rows = list(budgets_qs)
    position_budget_map: dict[int, PositionBudget] = {}
    buckets: dict[int, dict[str, object]] = {}

    for row in budget_rows:
        division = getattr(row.department, "division", None)
        division_id = getattr(division, "id", None)
        if division_id is None:
            continue

        if division_id not in buckets:
            buckets[division_id] = {
                "division_id": division_id,
                "division_name": division.name,
                "budget_cap": Decimal("0"),
                "committed": Decimal("0"),
                "pipeline": Decimal("0"),
            }

        buckets[division_id]["budget_cap"] += _safe_decimal(row.budget_amount)
        buckets[division_id]["committed"] += _position_budget_per_head_cost(row) * Decimal(
            str(int(row.filled_headcount or 0))
        )
        if row.position_id and row.position_id not in position_budget_map:
            position_budget_map[row.position_id] = row

    vacancies_qs = Vacancy.objects.filter(
        organization_id=organization_id,
        status__in=(Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD),
        position__department__division__isnull=False,
    ).select_related("position", "position__department__division", "position__salary_structure")

    if fiscal_year is not None:
        vacancies_qs = vacancies_qs.filter(
            Q(position__budgets__fiscal_year=fiscal_year) | Q(position__budgets__isnull=True)
        ).distinct()

    for vacancy in vacancies_qs:
        position = getattr(vacancy, "position", None)
        if not position or not position.department_id:
            continue
        division = getattr(position.department, "division", None)
        division_id = getattr(division, "id", None)
        if division_id is None:
            continue

        if division_id not in buckets:
            buckets[division_id] = {
                "division_id": division_id,
                "division_name": division.name,
                "budget_cap": Decimal("0"),
                "committed": Decimal("0"),
                "pipeline": Decimal("0"),
            }

        budget_row = position_budget_map.get(position.id)
        buckets[division_id]["pipeline"] += _vacancy_pipeline_cost(
            vacancy=vacancy,
            budget_row=budget_row,
        )

    guardrails: list[dict[str, object]] = []
    for row in sorted(buckets.values(), key=lambda item: str(item["division_name"])):
        budget_cap = _safe_decimal(row["budget_cap"])
        committed = _safe_decimal(row["committed"])
        pipeline = _safe_decimal(row["pipeline"])
        variance = budget_cap - committed - pipeline
        guardrails.append(
            {
                "division_id": row["division_id"],
                "division_name": row["division_name"],
                "budget_cap": budget_cap,
                "committed": committed,
                "pipeline": pipeline,
                "variance": variance,
                "unallocated_budget": variance,
                "hiring_freeze": variance <= Decimal("0"),
            }
        )
    return guardrails


def _resolve_position_budget_limit(position: Position) -> PositionBudgetLimit | None:
    if position.salary_structure_id and position.salary_structure.max_salary is not None:
        return PositionBudgetLimit(
            amount=Decimal(position.salary_structure.max_salary),
            source=f"Salary Structure: {position.salary_structure.name}",
        )

    current_year = timezone.localdate().year
    candidates = (
        PositionBudget.objects.filter(
            organization_id=position.organization_id,
            department_id=position.department_id,
        )
        .filter(position_id=position.id)
        .order_by("-fiscal_year", "-updated_at", "-id")
    )
    fallback_candidates = (
        PositionBudget.objects.filter(
            organization_id=position.organization_id,
            department_id=position.department_id,
            position__isnull=True,
        )
        .order_by("-fiscal_year", "-updated_at", "-id")
    )

    budget = (
        candidates.filter(status=PositionBudget.Status.APPROVED, fiscal_year=current_year).first()
        or candidates.filter(status=PositionBudget.Status.APPROVED).first()
        or candidates.first()
        or fallback_candidates.filter(
            status=PositionBudget.Status.APPROVED, fiscal_year=current_year,
        ).first()
        or fallback_candidates.filter(status=PositionBudget.Status.APPROVED).first()
        or fallback_candidates.first()
    )
    if budget is None:
        return None

    approved_headcount = (
        budget.approved_headcount
        or position.headcount_budget
        or 1
    )
    approved_headcount = max(int(approved_headcount), 1)
    slot_budget = Decimal(budget.budget_amount) / Decimal(approved_headcount)
    source = f"Position Budget FY{budget.fiscal_year}"
    return PositionBudgetLimit(amount=slot_budget, source=source)


def _resolve_candidate_offer(candidate: Candidate) -> JobOffer | None:
    return (
        candidate.offers.filter(
            status__in=[
                JobOffer.Status.ACCEPTED,
                JobOffer.Status.APPROVED,
                JobOffer.Status.EXTENDED,
                JobOffer.Status.PENDING_APPROVAL,
            ],
        )
        .select_related("position", "requisition", "position__salary_structure")
        .order_by("-responded_at", "-approved_at", "-created_at", "-id")
        .first()
    )


def _resolve_candidate_position(candidate: Candidate, offer: JobOffer | None) -> Position | None:
    if offer and offer.position_id:
        return offer.position
    if offer and offer.requisition_id and offer.requisition.position_id:
        return offer.requisition.position
    if candidate.job_requisition_id and candidate.job_requisition.position_id:
        return candidate.job_requisition.position
    listing = getattr(candidate, "job_listing", None)
    if listing and listing.requisition_id and listing.requisition.position_id:
        return listing.requisition.position
    return None


def enforce_candidate_hire_budget(candidate: Candidate, acting_user) -> None:
    offer = _resolve_candidate_offer(candidate)
    approved_salary = offer.offered_salary if offer and offer.offered_salary is not None else candidate.expected_salary
    if approved_salary is None:
        return

    position = _resolve_candidate_position(candidate, offer)
    if position is None:
        return
    if not getattr(position, "salary_structure_id", None):
        position = Position.objects.select_related("salary_structure").get(pk=position.id)

    budget_limit = _resolve_position_budget_limit(position)
    if budget_limit is None:
        return

    approved_salary_dec = Decimal(approved_salary)
    if approved_salary_dec <= budget_limit.amount:
        return

    if offer and offer.cfo_override_approved:
        return

    if user_has_cfo_override_authority(acting_user):
        if offer and not offer.cfo_override_approved:
            now = timezone.now()
            offer.cfo_override_approved = True
            offer.cfo_override_by = acting_user
            offer.cfo_override_at = now
            if not offer.cfo_override_reason:
                offer.cfo_override_reason = "Auto-stamped by CFO-authorized hire action."
            offer.save(
                update_fields=[
                    "cfo_override_approved",
                    "cfo_override_by",
                    "cfo_override_at",
                    "cfo_override_reason",
                    "updated_at",
                ],
            )
        return

    raise ValidationError(
        {
            "detail": (
                "Salary exceeds the position budget. Candidate cannot be moved to "
                "'Hired' without CFO override."
            ),
            "approved_salary": str(approved_salary_dec),
            "position_budget_limit": str(budget_limit.amount),
            "budget_source": budget_limit.source,
            "requires_cfo_override": True,
        }
    )


def _resolve_recruitment_requester(position: Position):
    division = getattr(getattr(position, "department", None), "division", None)
    for user in [
        getattr(position.department, "head", None),
        getattr(division, "head", None),
    ]:
        if user and user.is_active:
            profile = getattr(user, "profile", None)
            if profile and profile.organization_id == position.organization_id:
                return user

    admin_profile = (
        UserProfile.objects
        .select_related("user")
        .filter(
            organization_id=position.organization_id,
            role="admin",
            user__is_active=True,
        )
        .order_by("id")
        .first()
    )
    if admin_profile and admin_profile.user:
        return admin_profile.user

    user_model = get_user_model()
    org_user = (
        user_model.objects.filter(
            profile__organization_id=position.organization_id,
            is_active=True,
        )
        .order_by("id")
        .first()
    )
    return org_user


def _ensure_draft_recruitment_for_vacant_position(position: Position) -> None:
    if position.slot_status != Position.SlotStatus.VACANT:
        return
    if position.status == Position.Status.ABOLISHED:
        return

    existing_listing = JobListing.objects.filter(
        organization_id=position.organization_id,
        requisition__position_id=position.id,
        status__in=[JobListing.Status.DRAFT, JobListing.Status.ACTIVE],
    ).exists()
    if existing_listing:
        return

    requester = _resolve_recruitment_requester(position)
    if requester is None:
        return

    salary_min = (
        position.salary_structure.min_salary
        if position.salary_structure_id and position.salary_structure.min_salary is not None
        else None
    )
    salary_max = (
        position.salary_structure.max_salary
        if position.salary_structure_id and position.salary_structure.max_salary is not None
        else None
    )
    salary_currency = (
        position.salary_structure.currency
        if position.salary_structure_id
        else None
    )
    priority = (
        Vacancy.Priority.URGENT
        if position.criticality_score >= CRITICAL_ROLE_THRESHOLD
        else Vacancy.Priority.MEDIUM
    )

    with transaction.atomic():
        vacancy = (
            Vacancy.objects.filter(
                organization_id=position.organization_id,
                position_id=position.id,
                status__in=[Vacancy.Status.OPEN, Vacancy.Status.ON_HOLD],
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if vacancy is None:
            vacancy = Vacancy.objects.create(
                organization_id=position.organization_id,
                position=position,
                title=position.title,
                status=Vacancy.Status.OPEN,
                priority=priority,
                hiring_manager=getattr(position.department, "head", None),
                reason="Auto-created because position became vacant.",
                notes="Recruitment trigger from Position vacancy automation.",
            )

        requisition = (
            JobRequisition.objects.filter(
                organization_id=position.organization_id,
                position_id=position.id,
                status__in=[
                    JobRequisition.Status.DRAFT,
                    JobRequisition.Status.PENDING_APPROVAL,
                    JobRequisition.Status.APPROVED,
                ],
            )
            .order_by("-created_at", "-id")
            .first()
        )
        if requisition is None:
            requisition = JobRequisition.objects.create(
                organization_id=position.organization_id,
                title=f"{position.title} Hiring Requisition",
                position=position,
                vacancy=vacancy,
                department=position.department,
                requisition_type="replacement",
                justification=(
                    "Auto-created from Position vacancy trigger."
                ),
                headcount_requested=1,
                priority=JobRequisition.Priority.URGENT
                if priority == Vacancy.Priority.URGENT
                else JobRequisition.Priority.MEDIUM,
                salary_range_min=salary_min,
                salary_range_max=salary_max,
                currency=salary_currency or get_default_currency_code(),
                status=JobRequisition.Status.DRAFT,
                requested_by=requester,
                notes="Automation: position marked vacant.",
            )

        if not JobListing.objects.filter(
            organization_id=position.organization_id,
            requisition_id=requisition.id,
            status__in=[JobListing.Status.DRAFT, JobListing.Status.ACTIVE],
        ).exists():
            salary_display = (
                JobListing.SalaryDisplay.RANGE
                if salary_min is not None or salary_max is not None
                else JobListing.SalaryDisplay.HIDDEN
            )
            JobListing.objects.create(
                organization_id=position.organization_id,
                requisition=requisition,
                title=position.title,
                description=position.description or "",
                requirements=position.requirements or "",
                employment_type=position.employment_type,
                salary_display=salary_display,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=salary_currency or requisition.currency,
                status=JobListing.Status.DRAFT,
                is_internal=True,
                is_external=False,
                notes="Auto-created from vacancy trigger.",
            )

    # Notify about the auto-triggered recruitment pipeline
    try:
        from apps.notifications.services import dispatch_workflow_notification

        dept_name = position.department.name if position.department_id else ""
        admins = [
            p.user
            for p in UserProfile.objects.filter(
                organization_id=position.organization_id,
                role="admin",
                user__is_active=True,
            ).select_related("user")
        ]
        if admins:
            from apps.accounts.models import Organization
            org = Organization.objects.filter(pk=position.organization_id).first()
            dispatch_workflow_notification(
                organization=org,
                event_key="hr_recruitment_auto_triggered",
                recipients=admins,
                fallback_title=f"Recruitment Auto-Triggered — {position.title}",
                fallback_message=(
                    f"A recruitment pipeline has been automatically initiated for the vacant "
                    f"position '{position.title}'"
                    + (f" in {dept_name}" if dept_name else "")
                    + ". A draft vacancy, job requisition, and internal job listing have been "
                    "created and are awaiting review."
                ),
                fallback_category=Notification.Category.HR_LIFECYCLE,
            )
    except Exception:
        pass


def _send_critical_vacancy_alert(position: Position, *, force: bool = False) -> bool:
    if position.criticality_score < CRITICAL_ROLE_THRESHOLD:
        return False
    if position.slot_status != Position.SlotStatus.VACANT:
        return False
    if not position.vacant_since:
        return False
    if not force and position.vacancy_alert_sent_at:
        return False

    threshold_date = timezone.localdate() - timedelta(days=CRITICAL_VACANCY_ALERT_AFTER_DAYS)
    if position.vacant_since > threshold_date:
        return False

    recipient = None
    division = getattr(getattr(position, "department", None), "division", None)
    if division and division.head and division.head.is_active:
        recipient = division.head
    elif position.department.head and position.department.head.is_active:
        recipient = position.department.head
    else:
        recipient = _resolve_recruitment_requester(position)

    if recipient is None:
        return False

    days_open = (timezone.localdate() - position.vacant_since).days
    dept_name = position.department.name if position.department_id else ""
    Notification.objects.create(
        recipient=recipient,
        organization_id=position.organization_id,
        title=f"Critical Position Vacancy — {position.title}",
        message=(
            f"The critical position '{position.title}'"
            + (f" in {dept_name}" if dept_name else "")
            + f" has been vacant for {days_open} day(s). "
            f"Immediate action is required to initiate succession planning or recruitment."
        ),
        severity=Notification.Severity.CRITICAL,
        category=Notification.Category.HR_LIFECYCLE,
        link_url="/hr/positions",
    )
    now = timezone.now()
    Position.objects.filter(pk=position.id).update(vacancy_alert_sent_at=now)
    position.vacancy_alert_sent_at = now
    return True


def sync_position_vacancy_state(
    position_id: int,
    *,
    trigger_recruitment: bool = True,
    trigger_alert: bool = True,
) -> None:
    try:
        position = Position.objects.select_related(
            "department",
            "department__division",
            "department__division__head",
            "department__head",
            "salary_structure",
        ).get(pk=position_id)
    except Position.DoesNotExist:
        return

    has_active_assignment = PositionAssignment.objects.filter(
        position_id=position.id,
        is_active=True,
    ).exists()
    desired_slot_status = position.slot_status
    if has_active_assignment:
        desired_slot_status = Position.SlotStatus.FILLED
    elif position.slot_status != Position.SlotStatus.PROPOSED:
        desired_slot_status = Position.SlotStatus.VACANT

    today = timezone.localdate()
    previous_vacant_since = position.vacant_since
    next_vacant_since = previous_vacant_since
    next_alert_sent_at = position.vacancy_alert_sent_at
    if desired_slot_status == Position.SlotStatus.VACANT:
        if next_vacant_since is None:
            next_vacant_since = today
    else:
        next_vacant_since = None
        next_alert_sent_at = None

    update_kwargs = {}
    if position.slot_status != desired_slot_status:
        update_kwargs["slot_status"] = desired_slot_status
        position.slot_status = desired_slot_status
    if position.vacant_since != next_vacant_since:
        update_kwargs["vacant_since"] = next_vacant_since
        position.vacant_since = next_vacant_since
    if position.vacancy_alert_sent_at != next_alert_sent_at:
        update_kwargs["vacancy_alert_sent_at"] = next_alert_sent_at
        position.vacancy_alert_sent_at = next_alert_sent_at

    if update_kwargs:
        Position.objects.filter(pk=position.id).update(**update_kwargs)

    became_vacant = (
        position.slot_status == Position.SlotStatus.VACANT
        and previous_vacant_since is None
        and position.vacant_since is not None
    )
    if trigger_recruitment and became_vacant:
        _ensure_draft_recruitment_for_vacant_position(position)
    if trigger_alert:
        _send_critical_vacancy_alert(position)


def check_overdue_critical_position_vacancies(
    *,
    organization_id: int | None = None,
) -> int:
    threshold_date = timezone.localdate() - timedelta(days=CRITICAL_VACANCY_ALERT_AFTER_DAYS)
    positions = Position.objects.select_related(
        "department",
        "department__division",
        "department__division__head",
        "department__head",
        "salary_structure",
    ).filter(
        criticality_score__gte=CRITICAL_ROLE_THRESHOLD,
        vacant_since__isnull=False,
        vacant_since__lte=threshold_date,
        vacancy_alert_sent_at__isnull=True,
    )
    if organization_id is not None:
        positions = positions.filter(organization_id=organization_id)

    alerted = 0
    for position in positions:
        sync_position_vacancy_state(
            position.id,
            trigger_recruitment=False,
            trigger_alert=True,
        )
        if Position.objects.filter(
            id=position.id,
            vacancy_alert_sent_at__isnull=False,
        ).exists():
            alerted += 1
    return alerted

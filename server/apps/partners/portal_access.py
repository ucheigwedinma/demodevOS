from __future__ import annotations

from dataclasses import dataclass, field

from django.db.models import Q
from django.utils import timezone

from apps.documents.models import Document

from .models import BudgetScope, PartnerEntitlement, PartnerOnboardingCase, PortalRole

BUDGET_SCOPE_PRIORITY = {
    BudgetScope.NONE: 0,
    BudgetScope.BOQ_ONLY: 1,
    BudgetScope.AGGREGATED: 2,
    BudgetScope.FULL: 3,
}

ROLE_CONFIDENTIALITY_MAP = {
    PortalRole.CLIENT: {
        Document.ConfidentialityLevel.PUBLIC,
        Document.ConfidentialityLevel.INTERNAL,
    },
    PortalRole.CONTRACTOR: {
        Document.ConfidentialityLevel.PUBLIC,
        Document.ConfidentialityLevel.INTERNAL,
        Document.ConfidentialityLevel.CONFIDENTIAL,
    },
    PortalRole.INVESTOR: {
        Document.ConfidentialityLevel.PUBLIC,
        Document.ConfidentialityLevel.INTERNAL,
        Document.ConfidentialityLevel.CONFIDENTIAL,
    },
    PortalRole.LEAD_INVESTOR: {
        Document.ConfidentialityLevel.PUBLIC,
        Document.ConfidentialityLevel.INTERNAL,
        Document.ConfidentialityLevel.CONFIDENTIAL,
        Document.ConfidentialityLevel.RESTRICTED,
    },
}


@dataclass
class PartnerPortalContext:
    is_partner_user: bool = False
    is_preview_mode: bool = False
    organization_id: int | None = None

    case_ids: list[int] = field(default_factory=list)
    entitlement_ids: list[int] = field(default_factory=list)

    partner_types: list[str] = field(default_factory=list)
    portal_roles: list[str] = field(default_factory=list)
    budget_scope: str = BudgetScope.NONE

    can_view_other_investors: bool = False
    can_edit: bool = False
    can_approve: bool = False
    can_comment: bool = True
    can_download_documents: bool = True

    allowed_confidentiality_levels: list[str] = field(default_factory=lambda: [Document.ConfidentialityLevel.PUBLIC])

    project_ids: list[int] = field(default_factory=list)
    spv_entity_ids: list[int] = field(default_factory=list)
    contract_references: list[str] = field(default_factory=list)
    investment_vehicle_references: list[str] = field(default_factory=list)

    customer_ids: list[int] = field(default_factory=list)
    vendor_ids: list[int] = field(default_factory=list)
    investor_ids: list[int] = field(default_factory=list)
    lead_ids: list[int] = field(default_factory=list)
    contact_emails: list[str] = field(default_factory=list)


def _safe_lower(value: str | None) -> str:
    return (value or "").strip().lower()


def _is_admin_like(user) -> bool:
    if getattr(user, "is_superuser", False):
        return True
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "admin")


def _empty_context(*, user) -> PartnerPortalContext:
    profile = getattr(user, "profile", None)
    organization = getattr(profile, "organization", None)
    return PartnerPortalContext(
        organization_id=getattr(organization, "id", None),
    )


def _matched_cases_for_user(*, user):
    profile = getattr(user, "profile", None)
    organization = getattr(profile, "organization", None)

    case_qs = (
        PartnerOnboardingCase.objects.filter(portal_access_granted=True)
        .select_related("lead", "vendor", "investor", "customer", "project", "spv_entity")
        .order_by("-created_at")
    )

    if not getattr(user, "is_superuser", False):
        if not organization:
            return case_qs.none()
        case_qs = case_qs.filter(organization=organization)

    email = _safe_lower(getattr(user, "email", ""))
    if not email:
        return case_qs.none()

    email_filter = (
        Q(contact_email__iexact=email)
        | Q(lead__email__iexact=email)
        | Q(vendor__email__iexact=email)
        | Q(investor__email__iexact=email)
        | Q(customer__email__iexact=email)
    )
    return case_qs.filter(email_filter).distinct()


def resolve_partner_portal_context(user) -> PartnerPortalContext:
    context = _empty_context(user=user)

    matched_cases_qs = _matched_cases_for_user(user=user)
    matched_cases = list(matched_cases_qs[:500])

    if not matched_cases and _is_admin_like(user):
        preview_qs = (
            PartnerOnboardingCase.objects.filter(portal_access_granted=True)
            .select_related("lead", "vendor", "investor", "customer", "project", "spv_entity")
            .order_by("-created_at")
        )
        if not getattr(user, "is_superuser", False):
            if context.organization_id is None:
                return context
            preview_qs = preview_qs.filter(organization_id=context.organization_id)
        matched_cases = list(preview_qs[:500])
        context.is_preview_mode = True

    if not matched_cases:
        return context

    case_ids = [case.id for case in matched_cases]
    today = timezone.localdate()
    entitlements = list(
        PartnerEntitlement.objects.filter(case_id__in=case_ids, is_active=True)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gte=today))
        .select_related("case", "project", "spv_entity")
        .order_by("-created_at")
    )

    if not entitlements and not context.is_preview_mode:
        return context

    project_ids: set[int] = set()
    spv_ids: set[int] = set()
    contract_refs: set[str] = set()
    investment_refs: set[str] = set()
    customer_ids: set[int] = set()
    vendor_ids: set[int] = set()
    investor_ids: set[int] = set()
    lead_ids: set[int] = set()
    contact_emails: set[str] = set()
    partner_types: set[str] = set()
    portal_roles: set[str] = set()
    confidentiality_levels: set[str] = set()

    budget_scope = BudgetScope.NONE
    can_view_other_investors = False
    can_edit = False
    can_approve = False
    can_comment = False
    can_download_documents = False

    for case in matched_cases:
        partner_types.add(case.partner_type)
        if case.project_id:
            project_ids.add(case.project_id)
        if case.spv_entity_id:
            spv_ids.add(case.spv_entity_id)
        if case.contract_reference:
            contract_refs.add(case.contract_reference.strip())
        if case.investment_vehicle_reference:
            investment_refs.add(case.investment_vehicle_reference.strip())
        if case.customer_id:
            customer_ids.add(case.customer_id)
        if case.vendor_id:
            vendor_ids.add(case.vendor_id)
        if case.investor_id:
            investor_ids.add(case.investor_id)
        if case.lead_id:
            lead_ids.add(case.lead_id)

        for value in (
            case.contact_email,
            getattr(case.customer, "email", ""),
            getattr(case.vendor, "email", ""),
            getattr(case.investor, "email", ""),
            getattr(case.lead, "email", ""),
        ):
            normalized = _safe_lower(value)
            if normalized:
                contact_emails.add(normalized)

    for entitlement in entitlements:
        portal_roles.add(entitlement.portal_role)
        if entitlement.project_id:
            project_ids.add(entitlement.project_id)
        if entitlement.spv_entity_id:
            spv_ids.add(entitlement.spv_entity_id)
        if entitlement.contract_reference:
            contract_refs.add(entitlement.contract_reference.strip())
        if entitlement.investment_vehicle_reference:
            investment_refs.add(entitlement.investment_vehicle_reference.strip())

        if BUDGET_SCOPE_PRIORITY[entitlement.budget_scope] > BUDGET_SCOPE_PRIORITY[budget_scope]:
            budget_scope = entitlement.budget_scope

        can_view_other_investors = can_view_other_investors or entitlement.can_view_other_investors
        can_edit = can_edit or entitlement.can_edit
        can_approve = can_approve or entitlement.can_approve
        can_comment = can_comment or entitlement.can_comment
        can_download_documents = can_download_documents or entitlement.can_download_documents

        confidentiality_levels.update(ROLE_CONFIDENTIALITY_MAP.get(entitlement.portal_role, set()))

    if context.is_preview_mode and _is_admin_like(user):
        can_view_other_investors = True
        can_edit = True
        can_approve = True
        can_comment = True
        can_download_documents = True
        confidentiality_levels = {
            Document.ConfidentialityLevel.PUBLIC,
            Document.ConfidentialityLevel.INTERNAL,
            Document.ConfidentialityLevel.CONFIDENTIAL,
            Document.ConfidentialityLevel.RESTRICTED,
        }

    context.case_ids = sorted(case_ids)
    context.entitlement_ids = sorted(entitlement.id for entitlement in entitlements)
    context.partner_types = sorted(partner_types)
    context.portal_roles = sorted(portal_roles)
    context.budget_scope = budget_scope
    context.can_view_other_investors = can_view_other_investors
    context.can_edit = can_edit
    context.can_approve = can_approve
    context.can_comment = can_comment
    context.can_download_documents = can_download_documents
    context.allowed_confidentiality_levels = sorted(confidentiality_levels) or [Document.ConfidentialityLevel.PUBLIC]
    context.project_ids = sorted(project_ids)
    context.spv_entity_ids = sorted(spv_ids)
    context.contract_references = sorted(contract_refs)
    context.investment_vehicle_references = sorted(investment_refs)
    context.customer_ids = sorted(customer_ids)
    context.vendor_ids = sorted(vendor_ids)
    context.investor_ids = sorted(investor_ids)
    context.lead_ids = sorted(lead_ids)
    context.contact_emails = sorted(contact_emails)
    context.is_partner_user = bool(entitlements)
    return context


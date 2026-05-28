from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    BudgetScope,
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    PartnerEntitlement,
    PartnerOnboardingApproval,
    PartnerOnboardingAuditLog,
    PartnerOnboardingCase,
    PartnerOnboardingIntakeDocument,
    PartnerOnboardingStageProgress,
    PartnerType,
    PortalRole,
)


@dataclass
class AccessGrantResult:
    ok: bool
    reason: str = ""


@dataclass
class IntakeGateResult:
    ok: bool
    reason: str = ""
    required_total: int = 0
    approved_total: int = 0
    missing_requirements: list[dict] | None = None


def _actor_role_label(user) -> str:
    if not user:
        return ""
    if getattr(user, "is_superuser", False):
        return "superuser"
    profile = getattr(user, "profile", None)
    if not profile:
        return ""
    if profile.role == "admin":
        return "org_admin"
    if profile.assigned_role_id:
        return profile.assigned_role.name
    return "member"


def _extract_ip(request) -> str | None:
    if request is None:
        return None
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")


def log_audit_event(
    *,
    case: PartnerOnboardingCase,
    event_type: str,
    message: str,
    actor=None,
    request=None,
    payload: dict | None = None,
):
    PartnerOnboardingAuditLog.objects.create(
        case=case,
        event_type=event_type,
        actor=actor,
        actor_role_label=_actor_role_label(actor),
        ip_address=_extract_ip(request),
        message=message,
        payload=payload or {},
    )


def resolve_default_template(*, organization, partner_type: str) -> OnboardingTemplate | None:
    org_template = (
        OnboardingTemplate.objects.filter(
            organization=organization,
            partner_type=partner_type,
            is_active=True,
            is_default=True,
        )
        .order_by("-version", "name")
        .first()
    )
    if org_template:
        return org_template

    return (
        OnboardingTemplate.objects.filter(
            organization__isnull=True,
            partner_type=partner_type,
            is_active=True,
            is_default=True,
        )
        .order_by("-version", "name")
        .first()
    )


def _sync_case_current_stage(case: PartnerOnboardingCase):
    next_stage_progress = (
        case.stage_progress.select_related("template_stage")
        .filter(
            status__in=[
                PartnerOnboardingStageProgress.Status.NOT_STARTED,
                PartnerOnboardingStageProgress.Status.IN_PROGRESS,
                PartnerOnboardingStageProgress.Status.BLOCKED,
            ]
        )
        .order_by("template_stage__sequence", "id")
        .first()
    )
    case.current_stage = next_stage_progress.template_stage if next_stage_progress else None


def _required_stage_counts(case: PartnerOnboardingCase) -> tuple[int, int]:
    required_qs = case.stage_progress.filter(is_required=True)
    total_required = required_qs.count()
    completed_required = required_qs.filter(
        status__in=[
            PartnerOnboardingStageProgress.Status.COMPLETED,
            PartnerOnboardingStageProgress.Status.WAIVED,
        ]
    ).count()
    return total_required, completed_required


def evaluate_intake_gate(*, case: PartnerOnboardingCase) -> IntakeGateResult:
    if not case.template_id:
        return IntakeGateResult(
            ok=False,
            reason="Case template is required to evaluate onboarding intake documents.",
        )

    required_rows = list(
        OnboardingTemplateDocumentRequirement.objects.filter(
            template_id=case.template_id,
            is_required=True,
        )
        .select_related("applies_to_stage")
        .order_by("sequence", "id")
    )
    required_total = len(required_rows)
    if required_total == 0:
        return IntakeGateResult(
            ok=True,
            reason="No required intake documents configured for this template.",
            required_total=0,
            approved_total=0,
            missing_requirements=[],
        )

    approved_requirement_ids = set(
        PartnerOnboardingIntakeDocument.objects.filter(
            case=case,
            requirement_id__in=[row.id for row in required_rows],
            status__in=[
                PartnerOnboardingIntakeDocument.ReviewStatus.APPROVED,
                PartnerOnboardingIntakeDocument.ReviewStatus.WAIVED,
            ],
        )
        .values_list("requirement_id", flat=True)
        .distinct()
    )
    approved_total = len(approved_requirement_ids)

    missing = [
        {
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "stage_code": row.applies_to_stage.code if row.applies_to_stage_id and row.applies_to_stage else None,
            "stage_name": row.applies_to_stage.name if row.applies_to_stage_id and row.applies_to_stage else None,
        }
        for row in required_rows
        if row.id not in approved_requirement_ids
    ]

    if not missing:
        return IntakeGateResult(
            ok=True,
            reason="Required intake documents are approved.",
            required_total=required_total,
            approved_total=approved_total,
            missing_requirements=[],
        )

    return IntakeGateResult(
        ok=False,
        reason="Required onboarding intake documents are missing approval.",
        required_total=required_total,
        approved_total=approved_total,
        missing_requirements=missing,
    )


def _stage_intake_requirement_snapshot(*, case: PartnerOnboardingCase) -> tuple[set[int], dict[int, list[str]]]:
    if not case.template_id:
        return set(), {}

    required_rows = list(
        OnboardingTemplateDocumentRequirement.objects.filter(
            template_id=case.template_id,
            is_required=True,
            applies_to_stage_id__isnull=False,
        ).values("id", "code", "applies_to_stage_id")
    )
    if not required_rows:
        return set(), {}

    requirement_ids = [row["id"] for row in required_rows]
    stage_ids = {int(row["applies_to_stage_id"]) for row in required_rows if row["applies_to_stage_id"] is not None}

    approved_requirement_ids = set(
        PartnerOnboardingIntakeDocument.objects.filter(
            case=case,
            requirement_id__in=requirement_ids,
            status__in=[
                PartnerOnboardingIntakeDocument.ReviewStatus.APPROVED,
                PartnerOnboardingIntakeDocument.ReviewStatus.WAIVED,
            ],
        )
        .values_list("requirement_id", flat=True)
        .distinct()
    )

    missing_by_stage: dict[int, list[str]] = {}
    for row in required_rows:
        requirement_id = int(row["id"])
        stage_id = row["applies_to_stage_id"]
        if stage_id is None or requirement_id in approved_requirement_ids:
            continue
        stage_id_int = int(stage_id)
        missing_by_stage.setdefault(stage_id_int, []).append(str(row["code"]))

    for stage_id in list(missing_by_stage.keys()):
        missing_by_stage[stage_id] = sorted(set(missing_by_stage[stage_id]))

    return stage_ids, missing_by_stage


def _missing_stage_requirement_codes(*, case: PartnerOnboardingCase, template_stage_id: int) -> list[str]:
    _stage_ids, missing_by_stage = _stage_intake_requirement_snapshot(case=case)
    return list(missing_by_stage.get(template_stage_id, []))


def sync_stage_kyc_gate_from_intake_documents(
    *,
    case: PartnerOnboardingCase,
    actor=None,
    request=None,
):
    stage_ids, missing_by_stage = _stage_intake_requirement_snapshot(case=case)
    if not stage_ids:
        return

    stage_progress_rows = list(
        case.stage_progress.select_related("template_stage").filter(template_stage_id__in=stage_ids)
    )
    if not stage_progress_rows:
        return

    changed_any = False
    for progress in stage_progress_rows:
        missing_codes = missing_by_stage.get(progress.template_stage_id, [])
        metadata = dict(progress.metadata or {})
        locked_by_gate = bool(metadata.get("intake_gate_locked"))
        old_status = progress.status
        update_fields: list[str] = []

        if missing_codes:
            metadata["intake_gate_locked"] = True
            metadata["intake_gate_missing_requirements"] = missing_codes
            if progress.status not in (
                PartnerOnboardingStageProgress.Status.COMPLETED,
                PartnerOnboardingStageProgress.Status.WAIVED,
                PartnerOnboardingStageProgress.Status.BLOCKED,
            ):
                progress.status = PartnerOnboardingStageProgress.Status.BLOCKED
                update_fields.append("status")
        else:
            if "intake_gate_locked" in metadata:
                metadata.pop("intake_gate_locked", None)
            if "intake_gate_missing_requirements" in metadata:
                metadata.pop("intake_gate_missing_requirements", None)
            if (
                progress.status == PartnerOnboardingStageProgress.Status.BLOCKED
                and locked_by_gate
            ):
                progress.status = (
                    PartnerOnboardingStageProgress.Status.IN_PROGRESS
                    if progress.started_at
                    else PartnerOnboardingStageProgress.Status.NOT_STARTED
                )
                update_fields.append("status")

        if metadata != (progress.metadata or {}):
            progress.metadata = metadata
            update_fields.append("metadata")

        if not update_fields:
            continue

        progress.save(update_fields=[*update_fields, "updated_at"])
        changed_any = True

        if old_status != progress.status:
            if progress.status == PartnerOnboardingStageProgress.Status.BLOCKED:
                message = (
                    f"Stage '{progress.template_stage.name}' auto-blocked due to missing required documents."
                )
            else:
                message = (
                    f"Stage '{progress.template_stage.name}' auto-unblocked after required documents were approved."
                )
            log_audit_event(
                case=case,
                event_type=PartnerOnboardingAuditLog.EventType.STAGE_STATUS_CHANGED,
                message=message,
                actor=actor,
                request=request,
                payload={
                    "stage_progress_id": progress.id,
                    "stage_code": progress.template_stage.code,
                    "old_status": old_status,
                    "new_status": progress.status,
                    "automation": "kyc_intake_stage_gate",
                    "missing_requirements": missing_codes,
                },
            )

    if changed_any:
        recompute_case_status(case)


def recompute_case_status(case: PartnerOnboardingCase):
    total_required, completed_required = _required_stage_counts(case)
    _sync_case_current_stage(case)

    if case.portal_access_granted:
        case.status = PartnerOnboardingCase.Status.ACTIVE
    elif case.status in (
        PartnerOnboardingCase.Status.REJECTED,
        PartnerOnboardingCase.Status.CANCELLED,
        PartnerOnboardingCase.Status.SUSPENDED,
    ):
        pass
    elif total_required > 0 and completed_required == total_required:
        if case.status != PartnerOnboardingCase.Status.APPROVED:
            case.status = PartnerOnboardingCase.Status.UNDER_REVIEW
    elif completed_required > 0:
        case.status = PartnerOnboardingCase.Status.IN_PROGRESS
    elif case.status == PartnerOnboardingCase.Status.DRAFT:
        pass
    else:
        case.status = PartnerOnboardingCase.Status.IN_PROGRESS

    case.save(update_fields=["current_stage", "status", "updated_at"])


def initialize_case_stages(*, case: PartnerOnboardingCase, actor=None, request=None):
    if not case.template_id:
        return

    if case.stage_progress.exists():
        return

    stage_rows = []
    for stage in case.template.stages.order_by("sequence"):
        status = PartnerOnboardingStageProgress.Status.NOT_STARTED
        if stage.auto_complete:
            status = PartnerOnboardingStageProgress.Status.COMPLETED
        stage_rows.append(
            PartnerOnboardingStageProgress(
                case=case,
                template_stage=stage,
                status=status,
                is_required=stage.is_required,
                started_at=timezone.now() if status == PartnerOnboardingStageProgress.Status.IN_PROGRESS else None,
                completed_at=timezone.now() if status == PartnerOnboardingStageProgress.Status.COMPLETED else None,
                completed_by=actor if status == PartnerOnboardingStageProgress.Status.COMPLETED else None,
            )
        )

    PartnerOnboardingStageProgress.objects.bulk_create(stage_rows)
    recompute_case_status(case)

    log_audit_event(
        case=case,
        event_type=PartnerOnboardingAuditLog.EventType.STAGES_INITIALIZED,
        message="Onboarding stages initialized from template.",
        actor=actor,
        request=request,
        payload={
            "template_id": case.template_id,
            "template_name": case.template.name,
            "stage_count": len(stage_rows),
        },
    )


def mark_stage_progress(
    *,
    case: PartnerOnboardingCase,
    progress: PartnerOnboardingStageProgress,
    status_value: str,
    notes: str,
    actor,
    request=None,
):
    missing_codes = _missing_stage_requirement_codes(
        case=case,
        template_stage_id=progress.template_stage_id,
    )
    if missing_codes and status_value in (
        PartnerOnboardingStageProgress.Status.IN_PROGRESS,
        PartnerOnboardingStageProgress.Status.COMPLETED,
        PartnerOnboardingStageProgress.Status.WAIVED,
    ):
        missing_codes_label = ", ".join(missing_codes)
        raise ValidationError(
            {
                "detail": (
                    f"Stage '{progress.template_stage.name}' is blocked until required intake "
                    f"documents are approved. Missing: {missing_codes_label}."
                )
            }
        )

    old_status = progress.status
    progress.status = status_value
    progress.notes = notes

    if status_value == PartnerOnboardingStageProgress.Status.IN_PROGRESS and not progress.started_at:
        progress.started_at = timezone.now()

    if status_value in (
        PartnerOnboardingStageProgress.Status.COMPLETED,
        PartnerOnboardingStageProgress.Status.WAIVED,
    ):
        progress.completed_at = timezone.now()
        progress.completed_by = actor
    else:
        progress.completed_at = None
        progress.completed_by = None

    progress.save(
        update_fields=[
            "status",
            "notes",
            "started_at",
            "completed_at",
            "completed_by",
            "updated_at",
        ]
    )

    recompute_case_status(case)

    log_audit_event(
        case=case,
        event_type=PartnerOnboardingAuditLog.EventType.STAGE_STATUS_CHANGED,
        message=f"Stage '{progress.template_stage.name}' moved from {old_status} to {status_value}.",
        actor=actor,
        request=request,
        payload={
            "stage_progress_id": progress.id,
            "stage_code": progress.template_stage.code,
            "old_status": old_status,
            "new_status": status_value,
        },
    )


def record_approval(
    *,
    case: PartnerOnboardingCase,
    decision: str,
    actor,
    stage_progress: PartnerOnboardingStageProgress | None = None,
    approver_role_label: str = "",
    comments: str = "",
    metadata: dict | None = None,
    request=None,
) -> PartnerOnboardingApproval:
    approval = PartnerOnboardingApproval.objects.create(
        case=case,
        stage_progress=stage_progress,
        decision=decision,
        approver_role_label=approver_role_label,
        comments=comments,
        metadata=metadata or {},
        decided_by=actor,
    )

    old_status = case.status
    if decision == PartnerOnboardingApproval.Decision.APPROVED:
        case.status = PartnerOnboardingCase.Status.APPROVED
    elif decision == PartnerOnboardingApproval.Decision.REJECTED:
        case.status = PartnerOnboardingCase.Status.REJECTED
    else:
        case.status = PartnerOnboardingCase.Status.IN_PROGRESS

    case.save(update_fields=["status", "updated_at"])

    log_audit_event(
        case=case,
        event_type=PartnerOnboardingAuditLog.EventType.APPROVAL_RECORDED,
        message=f"Approval decision recorded: {decision}.",
        actor=actor,
        request=request,
        payload={
            "approval_id": approval.id,
            "decision": decision,
            "old_case_status": old_status,
            "new_case_status": case.status,
            "stage_progress_id": stage_progress.id if stage_progress else None,
        },
    )
    return approval


def _default_matrix_for_case(case: PartnerOnboardingCase, portal_role: str | None) -> dict:
    resolved_role = portal_role
    if not resolved_role:
        if case.partner_type == PartnerType.CLIENT:
            resolved_role = PortalRole.CLIENT
        elif case.partner_type == PartnerType.CONTRACTOR:
            resolved_role = PortalRole.CONTRACTOR
        else:
            resolved_role = PortalRole.INVESTOR

    if resolved_role == PortalRole.CLIENT:
        return {
            "portal_role": resolved_role,
            "budget_scope": BudgetScope.NONE,
            "can_view_other_investors": False,
            "can_edit": False,
            "can_approve": False,
        }

    if resolved_role == PortalRole.CONTRACTOR:
        return {
            "portal_role": resolved_role,
            "budget_scope": BudgetScope.BOQ_ONLY,
            "can_view_other_investors": False,
            "can_edit": True,
            "can_approve": False,
        }

    if resolved_role == PortalRole.LEAD_INVESTOR:
        return {
            "portal_role": resolved_role,
            "budget_scope": BudgetScope.FULL,
            "can_view_other_investors": True,
            "can_edit": False,
            "can_approve": True,
        }

    return {
        "portal_role": PortalRole.INVESTOR,
        "budget_scope": BudgetScope.AGGREGATED,
        "can_view_other_investors": False,
        "can_edit": False,
        "can_approve": False,
    }


def provision_entitlement(
    *,
    case: PartnerOnboardingCase,
    actor,
    portal_role: str | None = None,
    project_id: int | None = None,
    spv_entity_id: int | None = None,
    contract_reference: str | None = None,
    investment_vehicle_reference: str | None = None,
    request=None,
) -> PartnerEntitlement:
    matrix = _default_matrix_for_case(case, portal_role)

    entitlement = PartnerEntitlement.objects.create(
        case=case,
        organization=case.organization,
        portal_role=matrix["portal_role"],
        project_id=project_id if project_id is not None else case.project_id,
        spv_entity_id=spv_entity_id if spv_entity_id is not None else case.spv_entity_id,
        contract_reference=(contract_reference if contract_reference is not None else case.contract_reference) or "",
        investment_vehicle_reference=(
            investment_vehicle_reference
            if investment_vehicle_reference is not None
            else case.investment_vehicle_reference
        )
        or "",
        budget_scope=matrix["budget_scope"],
        can_view_other_investors=matrix["can_view_other_investors"],
        can_edit=matrix["can_edit"],
        can_approve=matrix["can_approve"],
        created_by=actor,
    )

    log_audit_event(
        case=case,
        event_type=PartnerOnboardingAuditLog.EventType.ENTITLEMENT_PROVISIONED,
        message="Entitlement provisioned from partner matrix.",
        actor=actor,
        request=request,
        payload={
            "entitlement_id": entitlement.id,
            "portal_role": entitlement.portal_role,
            "budget_scope": entitlement.budget_scope,
            "project_id": entitlement.project_id,
            "spv_entity_id": entitlement.spv_entity_id,
            "contract_reference": entitlement.contract_reference,
            "investment_vehicle_reference": entitlement.investment_vehicle_reference,
        },
    )
    return entitlement


def _enable_customer_support_ticketing_for_case(*, case: PartnerOnboardingCase):
    if case.partner_type != PartnerType.CLIENT:
        return None

    customer = case.customer
    if customer is None and case.lead_id and case.lead and case.lead.converted_customer_id:
        customer = case.lead.converted_customer

    if customer is None:
        return None

    now = timezone.now()
    update_fields: list[str] = []
    if not customer.support_ticketing_enabled:
        customer.support_ticketing_enabled = True
        update_fields.append("support_ticketing_enabled")
    if customer.support_ticketing_enabled_at is None:
        customer.support_ticketing_enabled_at = now
        update_fields.append("support_ticketing_enabled_at")

    if update_fields:
        update_fields.append("updated_at")
        customer.save(update_fields=update_fields)

    if case.customer_id is None:
        case.customer = customer
        case.save(update_fields=["customer", "updated_at"])

    return customer


def grant_portal_access(*, case: PartnerOnboardingCase, actor, request=None) -> AccessGrantResult:
    intake_gate = evaluate_intake_gate(case=case)
    if not intake_gate.ok:
        missing_codes = ", ".join(item["code"] for item in (intake_gate.missing_requirements or []))
        return AccessGrantResult(
            False,
            (
                "Required onboarding intake documents are not fully approved "
                f"({intake_gate.approved_total}/{intake_gate.required_total}). "
                f"Missing: {missing_codes or 'n/a'}."
            ),
        )

    if case.status != PartnerOnboardingCase.Status.APPROVED:
        return AccessGrantResult(False, "Case must be approved before portal access can be granted.")

    if not case.has_erp_profile:
        return AccessGrantResult(False, "ERP profile is required before granting portal access.")

    if not case.entitlements.filter(is_active=True).exists():
        return AccessGrantResult(False, "At least one active entitlement is required before access grant.")

    with transaction.atomic():
        case.portal_access_granted = True
        case.portal_access_granted_at = timezone.now()
        case.status = PartnerOnboardingCase.Status.ACTIVE
        case.save(
            update_fields=[
                "portal_access_granted",
                "portal_access_granted_at",
                "status",
                "updated_at",
            ]
        )

        support_customer = _enable_customer_support_ticketing_for_case(case=case)

        access_stage = case.stage_progress.select_related("template_stage").filter(
            template_stage__code="portal_access_granted"
        ).first()
        if access_stage:
            mark_stage_progress(
                case=case,
                progress=access_stage,
                status_value=PartnerOnboardingStageProgress.Status.COMPLETED,
                notes="Portal access granted.",
                actor=actor,
                request=request,
            )

        log_audit_event(
            case=case,
            event_type=PartnerOnboardingAuditLog.EventType.PORTAL_ACCESS_GRANTED,
            message="Portal access granted after approval, ERP profile, and entitlement checks.",
            actor=actor,
            request=request,
            payload={
                "portal_access_granted_at": case.portal_access_granted_at.isoformat(),
                "support_ticketing_customer_id": support_customer.id if support_customer else None,
                "support_ticketing_enabled": bool(
                    support_customer and support_customer.support_ticketing_enabled
                ),
                "support_ticketing_enabled_at": (
                    support_customer.support_ticketing_enabled_at.isoformat()
                    if support_customer and support_customer.support_ticketing_enabled_at
                    else None
                ),
            },
        )

    return AccessGrantResult(True, "Portal access granted.")


@dataclass
class EntityCreationResult:
    ok: bool
    reason: str = ""
    entity: object | None = None
    entity_type: str = ""


def create_erp_entity(
    *,
    case: PartnerOnboardingCase,
    actor,
    request=None,
) -> EntityCreationResult:
    """Auto-create the ERP entity (Customer/Investor/Vendor) from onboarding case data."""

    if case.has_erp_profile:
        return EntityCreationResult(False, "ERP entity already exists for this case.")

    if case.status not in (
        PartnerOnboardingCase.Status.APPROVED,
        PartnerOnboardingCase.Status.UNDER_REVIEW,
        PartnerOnboardingCase.Status.IN_PROGRESS,
    ):
        return EntityCreationResult(False, "Case must be at least in progress to create an ERP entity.")

    lead = case.lead
    contact_name = case.contact_name or (lead.full_name if lead else "")
    contact_email = case.contact_email or (lead.email if lead else "")
    contact_phone = case.contact_phone or (lead.phone if lead else "")

    with transaction.atomic():
        entity = None
        entity_type = ""

        if case.partner_type == PartnerType.CLIENT:
            from apps.finance.models import Customer

            entity = Customer.objects.create(
                name=contact_name,
                contact_person=contact_name,
                email=contact_email,
                phone=contact_phone,
                address="",
                notes=f"Created from partner onboarding case: {case.title}",
            )
            case.customer = entity
            entity_type = "customer"

            if lead and not lead.converted_customer_id:
                lead.converted_customer = entity

        elif case.partner_type == PartnerType.CONTRACTOR:
            from apps.procurement.models import Vendor

            entity = Vendor.objects.create(
                organization=case.organization,
                name=contact_name,
                contact_person=contact_name,
                email=contact_email,
                phone=contact_phone,
                category=Vendor.Category.CONTRACTOR,
                notes=f"Created from partner onboarding case: {case.title}",
            )
            case.vendor = entity
            entity_type = "vendor"

        elif case.partner_type == PartnerType.INVESTOR:
            from apps.finance.models import Investor

            entity = Investor.objects.create(
                organization=case.organization,
                name=contact_name,
                investor_type=Investor.InvestorType.INDIVIDUAL,
                contact_person=contact_name,
                email=contact_email,
                phone=contact_phone,
                entity_name=lead.company if lead and lead.company else "",
                notes=f"Created from partner onboarding case: {case.title}",
            )
            case.investor = entity
            entity_type = "investor"

        else:
            return EntityCreationResult(False, f"Unknown partner type: {case.partner_type}")

        case.save(update_fields=["customer", "vendor", "investor", "updated_at"])

        log_audit_event(
            case=case,
            event_type=PartnerOnboardingAuditLog.EventType.ERP_ENTITY_CREATED,
            message=f"ERP {entity_type} entity created: {entity}.",
            actor=actor,
            request=request,
            payload={
                "entity_type": entity_type,
                "entity_id": entity.id,
                "entity_name": str(entity),
            },
        )

        # Auto-complete the ERP creation stage if it exists
        erp_stage_codes = {
            PartnerType.CLIENT: "erp_client_creation",
            PartnerType.CONTRACTOR: "erp_vendor_creation",
            PartnerType.INVESTOR: "erp_investor_profile",
        }
        stage_code = erp_stage_codes.get(case.partner_type)
        if stage_code:
            erp_stage = (
                case.stage_progress.select_related("template_stage")
                .filter(template_stage__code=stage_code)
                .first()
            )
            if erp_stage and erp_stage.status != PartnerOnboardingStageProgress.Status.COMPLETED:
                mark_stage_progress(
                    case=case,
                    progress=erp_stage,
                    status_value=PartnerOnboardingStageProgress.Status.COMPLETED,
                    notes=f"Auto-completed: {entity_type} entity created.",
                    actor=actor,
                    request=request,
                )

        # Archive lead if present
        if lead:
            _archive_lead(lead=lead, reason=case.get_partner_type_display(), actor=actor)
            log_audit_event(
                case=case,
                event_type=PartnerOnboardingAuditLog.EventType.LEAD_ARCHIVED,
                message=f"Lead '{lead.full_name}' archived after ERP entity creation.",
                actor=actor,
                request=request,
                payload={
                    "lead_id": lead.id,
                    "lead_name": lead.full_name,
                    "archived_reason": case.get_partner_type_display(),
                },
            )

    return EntityCreationResult(True, f"{entity_type.title()} created successfully.", entity, entity_type)


def _archive_lead(*, lead, reason: str, actor=None):
    """Mark a CRM lead as archived (read-only)."""
    from apps.crm.models import Lead, LeadStageTransition

    lead.is_archived = True
    lead.archived_at = timezone.now()
    lead.archived_reason = reason
    lead.status = Lead.Status.WON

    if lead.pipeline_stage != Lead.PipelineStage.CLOSED:
        old_stage = lead.pipeline_stage
        lead.pipeline_stage = Lead.PipelineStage.CLOSED
        lead.closed_date = timezone.now().date()
        LeadStageTransition.objects.create(
            lead=lead,
            from_stage=old_stage,
            to_stage=Lead.PipelineStage.CLOSED,
            transitioned_by=actor,
            notes=f"Auto-transitioned on entity handoff ({reason}).",
        )

    lead.save()

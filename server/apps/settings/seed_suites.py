from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, TextIO

from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import Organization
from apps.facility_management.tasks import (
    run_scheduled_documents_drawings_workflows,
    run_scheduled_health_safety_compliance_workflows,
    run_scheduled_maintenance_workflows,
    run_scheduled_service_request_helpdesk_workflows,
    run_scheduled_space_occupancy_workflows,
    run_scheduled_utility_energy_workflows,
)
from apps.tenants.tasks import run_scheduled_tenant_operations_workflows


@dataclass(frozen=True)
class SuiteRunContext:
    organization_ids: list[int]
    flush: bool
    dry_run: bool
    continue_on_error: bool
    stdout: TextIO
    stderr: TextIO


@dataclass(frozen=True)
class SuiteStep:
    key: str
    label: str
    category: str
    run: Callable[[SuiteRunContext], str]
    command_name: str | None = None
    task_name: str | None = None


SUITE_GUARD_COMMAND_PREFIXES = (
    "seed_",
    "dispatch_",
    "expire_",
    "generate_",
    "run_",
    "sync_",
)

SUITE_GUARD_IGNORED_COMMANDS = frozenset(
    {
        "seed_demo_suite",
        "seed_platform_suite",
        # Phase 2 granular commands are intentionally covered by seed_documents_phase2_all.
        "seed_documents_phase2_document_types",
        "seed_documents_phase2_owner_roles",
        "seed_documents_phase2_retention_policies",
        "seed_documents_phase2_workflow_phases",
    }
)


def resolve_target_organization_ids(requested_ids: Sequence[int] | None) -> list[int]:
    normalized = list(dict.fromkeys(int(value) for value in (requested_ids or [])))
    query = Organization.objects.order_by("id")

    if not normalized:
        return list(query.values_list("id", flat=True))

    existing = list(query.filter(id__in=normalized).values_list("id", flat=True))
    missing = [org_id for org_id in normalized if org_id not in set(existing)]
    if missing:
        raise CommandError(
            "Unknown organization id(s): " + ", ".join(str(org_id) for org_id in missing)
        )
    return existing


def filter_steps(steps: Sequence[SuiteStep], requested_keys: Sequence[str] | None) -> list[SuiteStep]:
    if not requested_keys:
        return list(steps)

    lookup = {step.key: step for step in steps}
    missing = [key for key in requested_keys if key not in lookup]
    if missing:
        raise CommandError(
            "Unknown step key(s): " + ", ".join(missing)
        )
    return [lookup[key] for key in requested_keys]


def describe_steps(steps: Sequence[SuiteStep]) -> list[str]:
    return [f"{step.key:<34} {step.category:<10} {step.label}" for step in steps]


def run_suite(
    *,
    suite_name: str,
    steps: Sequence[SuiteStep],
    context: SuiteRunContext,
) -> None:
    total = len(steps)
    failures: list[tuple[str, str]] = []

    if not steps:
        raise CommandError(f"{suite_name} has no steps to run.")

    for index, step in enumerate(steps, start=1):
        context.stdout.write(f"[{index}/{total}] {step.key} - {step.label}")
        try:
            detail = step.run(context)
        except Exception as exc:
            failures.append((step.key, str(exc)))
            context.stderr.write(f"  FAILED: {exc}")
            if not context.continue_on_error:
                raise CommandError(
                    f"{suite_name} stopped on step '{step.key}': {exc}"
                ) from exc
            continue

        if detail:
            context.stdout.write(f"  OK: {detail}")
        else:
            context.stdout.write("  OK")

    if failures:
        summary = "; ".join(f"{key} ({message})" for key, message in failures)
        raise CommandError(f"{suite_name} completed with failures: {summary}")


def make_global_command_step(
    *,
    key: str,
    label: str,
    command_name: str,
    category: str = "seed",
    base_kwargs: dict[str, Any] | None = None,
) -> SuiteStep:
    defaults = dict(base_kwargs or {})

    def _run(context: SuiteRunContext) -> str:
        if context.dry_run:
            return f"dry-run command={command_name} kwargs={defaults}"
        call_command(command_name, stdout=context.stdout, stderr=context.stderr, **defaults)
        return f"command={command_name}"

    return SuiteStep(
        key=key,
        label=label,
        category=category,
        run=_run,
        command_name=command_name,
    )


def make_per_org_command_step(
    *,
    key: str,
    label: str,
    command_name: str,
    org_kwarg: str,
    category: str = "seed",
    org_value: Callable[[int], Any] | None = None,
    base_kwargs: dict[str, Any] | None = None,
    flush_kwargs: dict[str, Any] | None = None,
) -> SuiteStep:
    defaults = dict(base_kwargs or {})
    flush_defaults = dict(flush_kwargs or {})
    to_value = org_value or (lambda org_id: org_id)

    def _run(context: SuiteRunContext) -> str:
        if not context.organization_ids:
            return "skipped (no organizations found)"

        run_count = 0
        for org_id in context.organization_ids:
            kwargs = dict(defaults)
            kwargs[org_kwarg] = to_value(org_id)
            if context.flush and flush_defaults:
                kwargs.update(flush_defaults)

            if context.dry_run:
                context.stdout.write(
                    f"  DRY-RUN org={org_id} command={command_name} kwargs={kwargs}"
                )
            else:
                call_command(command_name, stdout=context.stdout, stderr=context.stderr, **kwargs)
            run_count += 1

        return f"command={command_name} org-runs={run_count}"

    return SuiteStep(
        key=key,
        label=label,
        category=category,
        run=_run,
        command_name=command_name,
    )


def make_task_step(
    *,
    key: str,
    label: str,
    task_func: Callable[[list[int] | None], Any],
    category: str = "workflow",
) -> SuiteStep:
    def _run(context: SuiteRunContext) -> str:
        if not context.organization_ids:
            return "skipped (no organizations found)"
        if context.dry_run:
            return f"dry-run task={task_func.__name__} organization_ids={context.organization_ids}"

        result = task_func(context.organization_ids)
        context.stdout.write("  " + json.dumps(result, sort_keys=True, default=str))
        return f"task={task_func.__name__} orgs={len(context.organization_ids)}"

    return SuiteStep(
        key=key,
        label=label,
        category=category,
        run=_run,
        task_name=task_func.__name__,
    )


CORE_SEED_STEPS: tuple[SuiteStep, ...] = (
    make_global_command_step(
        key="platform_editions",
        label="Seed platform editions",
        command_name="seed_platform_editions",
    ),
    make_global_command_step(
        key="subscription_addons",
        label="Seed subscription add-ons",
        command_name="seed_subscription_addons",
    ),
    make_global_command_step(
        key="feature_flags",
        label="Seed feature flags",
        command_name="seed_feature_flags",
    ),
    make_global_command_step(
        key="master_data",
        label="Seed master data",
        command_name="seed_master_data",
    ),
    make_global_command_step(
        key="status_badges",
        label="Seed status badges",
        command_name="seed_status_badges",
    ),
    make_global_command_step(
        key="project_templates",
        label="Seed global project templates",
        command_name="seed_project_templates",
    ),
    make_global_command_step(
        key="project_phases",
        label="Seed phase templates",
        command_name="seed_project_phases",
    ),
    make_global_command_step(
        key="project_milestones",
        label="Seed milestone templates",
        command_name="seed_project_milestones",
    ),
    make_global_command_step(
        key="project_tasks",
        label="Seed task templates",
        command_name="seed_project_tasks",
    ),
    make_global_command_step(
        key="sync_org_rls",
        label="Synchronize organization RLS policies",
        command_name="sync_org_rls",
        category="ops",
    ),
    make_per_org_command_step(
        key="seed_rbac",
        label="Seed RBAC roles",
        command_name="seed_rbac",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="access_scopes",
        label="Seed access scopes",
        command_name="seed_access_scopes",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="access_policies",
        label="Seed access policies",
        command_name="seed_access_policies",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="risk_mitigation_rules",
        label="Seed risk mitigation rules",
        command_name="seed_risk_mitigation_rules",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="platform_governance",
        label="Seed platform governance",
        command_name="seed_platform_governance",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="metrics_contract",
        label="Seed metrics contract",
        command_name="seed_metrics_contract",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="sync_rbac_groups",
        label="Sync RBAC to Django groups",
        command_name="sync_rbac_to_django_groups",
        org_kwarg="org_id",
    ),
    make_per_org_command_step(
        key="process_authority",
        label="Seed process authority",
        command_name="seed_process_authority",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="documents_phase1_domains",
        label="Seed document domains",
        command_name="seed_documents_phase1_domains",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="documents_phase1_charter",
        label="Seed document charter",
        command_name="seed_documents_phase1_charter",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="documents_phase1_vocabulary",
        label="Seed document vocabulary",
        command_name="seed_documents_phase1_vocabulary",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="documents_phase2",
        label="Seed document phase 2 lookups",
        command_name="seed_documents_phase2_all",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="documents_phase4_scopes",
        label="Seed document access scopes",
        command_name="seed_documents_phase4_access_scopes",
        org_kwarg="org",
    ),
    make_per_org_command_step(
        key="documents_phase5_workflows",
        label="Seed document workflows",
        command_name="seed_documents_phase5_workflows",
        org_kwarg="org",
    ),
    make_global_command_step(
        key="partner_templates_global",
        label="Seed global partner onboarding templates",
        command_name="seed_partner_onboarding_templates",
        base_kwargs={"set_default": True},
    ),
    make_per_org_command_step(
        key="partner_templates_org",
        label="Seed organization partner onboarding templates",
        command_name="seed_partner_onboarding_templates",
        org_kwarg="organization_id",
        base_kwargs={"set_default": True},
    ),
)


DEMO_SEED_STEPS: tuple[SuiteStep, ...] = (
    make_per_org_command_step(
        key="crm_demo",
        label="Seed CRM demo data",
        command_name="seed_crm_demo",
        org_kwarg="organization_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="properties_demo",
        label="Seed properties demo data",
        command_name="seed_properties_demo",
        org_kwarg="org_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"reseed": True},
    ),
    make_per_org_command_step(
        key="finance_demo",
        label="Seed finance demo data",
        command_name="seed_finance_demo",
        org_kwarg="organization_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="projects_demo",
        label="Seed projects demo data",
        command_name="seed_projects_demo",
        org_kwarg="org_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="procurement_demo",
        label="Seed procurement demo data",
        command_name="seed_procurement_demo",
        org_kwarg="org_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="support_desk_demo",
        label="Seed support desk demo data",
        command_name="seed_support_desk",
        org_kwarg="organization_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="knowledge_base_demo",
        label="Seed knowledge base demo data",
        command_name="seed_knowledge_base",
        org_kwarg="organization_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="partners_demo",
        label="Seed partners demo data",
        command_name="seed_partners_demo",
        org_kwarg="org_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
    make_per_org_command_step(
        key="hr_workforce_demo",
        label="Seed HR workforce planning demo data",
        command_name="seed_hr_workforce_planning",
        org_kwarg="organization_ids",
        org_value=lambda org_id: [org_id],
        flush_kwargs={"flush": True},
    ),
)


OPERATIONAL_STEPS: tuple[SuiteStep, ...] = (
    make_per_org_command_step(
        key="expire_reservation_holds",
        label="Expire reservation holds",
        command_name="expire_reservation_holds",
        org_kwarg="organization_id",
        category="ops",
    ),
    make_per_org_command_step(
        key="idle_lead_followups",
        label="Generate idle lead follow-ups",
        command_name="generate_idle_lead_followups",
        org_kwarg="organization_id",
        category="ops",
    ),
    make_per_org_command_step(
        key="scheduled_reports",
        label="Dispatch scheduled reports",
        command_name="dispatch_scheduled_reports",
        org_kwarg="organization_id",
        category="ops",
    ),
    make_per_org_command_step(
        key="documents_compliance_monitor",
        label="Run documents compliance monitor",
        command_name="run_documents_compliance_monitor",
        org_kwarg="organization_id",
        category="ops",
    ),
    make_per_org_command_step(
        key="inventory_from_procurement",
        label="Sync inventory from procurement receipts",
        command_name="sync_inventory_from_procurement",
        org_kwarg="organization_id",
        category="ops",
    ),
    make_per_org_command_step(
        key="inventory_from_project_costs",
        label="Sync inventory from project costs",
        command_name="sync_inventory_from_project_costs",
        org_kwarg="organization_id",
        category="ops",
    ),
)


WORKFLOW_STEPS: tuple[SuiteStep, ...] = (
    make_task_step(
        key="tenant_workflows",
        label="Run tenant automation workflows",
        task_func=run_scheduled_tenant_operations_workflows,
    ),
    make_task_step(
        key="maintenance_workflows",
        label="Run maintenance workflows",
        task_func=run_scheduled_maintenance_workflows,
    ),
    make_task_step(
        key="service_request_workflows",
        label="Run service request workflows",
        task_func=run_scheduled_service_request_helpdesk_workflows,
    ),
    make_task_step(
        key="space_occupancy_workflows",
        label="Run space and occupancy workflows",
        task_func=run_scheduled_space_occupancy_workflows,
    ),
    make_task_step(
        key="utility_energy_workflows",
        label="Run utility and energy workflows",
        task_func=run_scheduled_utility_energy_workflows,
    ),
    make_task_step(
        key="health_safety_workflows",
        label="Run health, safety, and compliance workflows",
        task_func=run_scheduled_health_safety_compliance_workflows,
    ),
    make_task_step(
        key="documents_drawings_workflows",
        label="Run documents and drawings workflows",
        task_func=run_scheduled_documents_drawings_workflows,
    ),
)


def build_platform_suite(
    *,
    include_ops: bool = False,
    include_workflows: bool = False,
) -> list[SuiteStep]:
    steps = list(CORE_SEED_STEPS)
    if include_ops:
        steps.extend(OPERATIONAL_STEPS)
    if include_workflows:
        steps.extend(WORKFLOW_STEPS)
    return steps


def build_demo_suite(
    *,
    include_core: bool = True,
    include_ops: bool = False,
    include_workflows: bool = False,
) -> list[SuiteStep]:
    steps: list[SuiteStep] = []
    if include_core:
        steps.extend(CORE_SEED_STEPS)
    steps.extend(DEMO_SEED_STEPS)
    if include_ops:
        steps.extend(OPERATIONAL_STEPS)
    if include_workflows:
        steps.extend(WORKFLOW_STEPS)
    return steps


def registered_suite_command_names() -> set[str]:
    return {
        step.command_name
        for step in (*CORE_SEED_STEPS, *DEMO_SEED_STEPS, *OPERATIONAL_STEPS)
        if step.command_name
    }


def registered_suite_workflow_task_names() -> set[str]:
    return {
        step.task_name
        for step in WORKFLOW_STEPS
        if step.task_name
    }

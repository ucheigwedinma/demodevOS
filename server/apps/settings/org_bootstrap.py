"""
Bootstrap all org-scoped seed data for a new organization.

Called from the Organization post_save signal after RBAC roles
and role scopes have already been seeded.
"""

import logging
from io import StringIO

logger = logging.getLogger(__name__)


def _safe_seed(func, org_name, step_name):
    """Run a seed step, logging errors without aborting the rest."""
    try:
        func()
    except Exception:
        logger.exception("Failed to seed %s for org '%s'", step_name, org_name)


def bootstrap_new_organization(org):
    """Run all org-scoped seeds for a newly created organization."""
    from django.core.management import call_command

    sink = StringIO()
    org_id = str(org.id)
    name = org.name

    # 1. Module activation (subscription-tier modules)
    def _module_activation():
        from apps.settings.models import TIER_MODULE_MAP, ModuleActivationSettings

        ModuleActivationSettings.objects.get_or_create(
            organization=org,
            defaults={
                "enabled_modules": sorted(
                    TIER_MODULE_MAP.get(org.subscription_tier, set())
                ),
            },
        )

    _safe_seed(_module_activation, name, "module activation")

    # 2. Contextual access policies
    def _access_policies():
        from apps.settings.contextual_policy_defaults import seed_contextual_access_policies_for_org

        seed_contextual_access_policies_for_org(org)

    _safe_seed(_access_policies, name, "access policies")

    # 3. Risk mitigation rules
    _safe_seed(
        lambda: call_command(
            "seed_risk_mitigation_rules", "--org", org_id, stdout=sink, stderr=sink
        ),
        name,
        "risk mitigation rules",
    )

    # 4. Platform governance (notifications, workflows, approval policies)
    _safe_seed(
        lambda: call_command(
            "seed_platform_governance", "--org", org_id, stdout=sink, stderr=sink
        ),
        name,
        "platform governance",
    )

    # 5. Metrics contract (KPI definitions)
    _safe_seed(
        lambda: call_command(
            "seed_metrics_contract", "--org", org_id, stdout=sink, stderr=sink
        ),
        name,
        "metrics contract",
    )

    # 6. Process authority (workflow roles, approvers)
    def _process_authority():
        from apps.workflows.process_authority_defaults import seed_process_authority_for_org

        seed_process_authority_for_org(org)

    _safe_seed(_process_authority, name, "process authority")

    # 7. Document control — Phase 1
    def _doc_phase1():
        from apps.documents.phase1_seed import seed_phase1_charter, seed_phase1_domains, seed_phase1_vocabulary

        seed_phase1_charter(organization=org)
        seed_phase1_domains(organization=org)
        seed_phase1_vocabulary(organization=org)

    _safe_seed(_doc_phase1, name, "document phase 1")

    # 8. Document control — Phase 2
    def _doc_phase2():
        from apps.documents.phase2_seed import (
            seed_phase2_document_types,
            seed_phase2_owner_roles,
            seed_phase2_retention_policies,
            seed_phase2_workflow_phases,
        )

        seed_phase2_document_types(organization=org)
        seed_phase2_owner_roles(organization=org)
        seed_phase2_workflow_phases(organization=org)
        seed_phase2_retention_policies(organization=org)

    _safe_seed(_doc_phase2, name, "document phase 2")

    # 9. Document role scopes (depends on RBAC roles)
    _safe_seed(
        lambda: call_command(
            "seed_documents_phase4_access_scopes",
            "--org",
            org_id,
            stdout=sink,
            stderr=sink,
        ),
        name,
        "document role scopes",
    )

    # 10. Document workflows (depends on document types from phase 2)
    _safe_seed(
        lambda: call_command(
            "seed_documents_phase5_workflows",
            "--org",
            org_id,
            stdout=sink,
            stderr=sink,
        ),
        name,
        "document workflows",
    )

    logger.info(
        "Bootstrapped org-scoped seed data for '%s' (id=%d)", name, org.id
    )

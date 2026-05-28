from django.core.management.base import BaseCommand

from apps.accounts.models import Organization
from apps.settings.models import TIER_MODULE_MAP, FeatureFlagDefinition, Module, ModuleActivationSettings

FLAG_SEED_DATA = [
    # --- Properties ---
    {
        "key": "beta_ai_valuations",
        "name": "AI Valuation Suggestions",
        "description": "Machine learning-powered property valuation recommendations based on comparable sales and market data.",
        "module": Module.PROPERTIES,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    {
        "key": "beta_gis_map_view",
        "name": "GIS Map View",
        "description": "Interactive map view of property portfolio with geospatial analytics.",
        "module": Module.PROPERTIES,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    # --- Projects ---
    {
        "key": "beta_variation_workflow",
        "name": "Variation Order Workflow",
        "description": "Automated approval workflow for construction variation orders.",
        "module": Module.PROJECTS,
        "scope": FeatureFlagDefinition.FlagScope.PROJECT,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    {
        "key": "pilot_field_ops_mobile",
        "name": "Mobile Field Operations",
        "description": "Mobile-optimized field operations interface for site reports and inspections.",
        "module": Module.PROJECTS,
        "scope": FeatureFlagDefinition.FlagScope.PROJECT,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    # --- Finance ---
    {
        "key": "beta_auto_reconciliation",
        "name": "Auto Bank Reconciliation",
        "description": "Automatic matching of bank statement entries with bills and invoices.",
        "module": Module.FINANCE,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    {
        "key": "beta_multi_currency",
        "name": "Multi-Currency Support",
        "description": "Handle transactions and reporting in multiple currencies with automatic FX rates.",
        "module": Module.FINANCE,
        "scope": FeatureFlagDefinition.FlagScope.REGION,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    # --- Analytics ---
    {
        "key": "beta_predictive_analytics",
        "name": "Predictive Analytics",
        "description": "AI-powered forecasting for project costs, timelines, and market trends.",
        "module": Module.ANALYTICS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    # --- Compliance ---
    {
        "key": "beta_regulatory_alerts",
        "name": "Regulatory Change Alerts",
        "description": "Automated monitoring and alerts for regulatory changes affecting your portfolio.",
        "module": Module.COMPLIANCE,
        "scope": FeatureFlagDefinition.FlagScope.REGION,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    # --- Edition-gated (Growth excluded, Scale+) ---
    {
        "key": "hr_payroll_processing",
        "name": "Payroll Processing",
        "description": "Payroll processing and runs including salary calculations, deductions, and payslip generation.",
        "module": Module.HR,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "analytics_custom_report_builder",
        "name": "Custom Report Builder",
        "description": "Drag-and-drop report builder with custom data sources, filters, and visualisations.",
        "module": Module.ANALYTICS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "procurement_three_way_matching",
        "name": "3-Way Matching",
        "description": "Automated three-way matching of purchase orders, goods receipts, and supplier invoices.",
        "module": Module.PROCUREMENT,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "procurement_tender_comparison",
        "name": "Tender Comparison & Scoring",
        "description": "Side-by-side tender comparison with weighted scoring matrices for bid evaluation.",
        "module": Module.PROCUREMENT,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "documents_expiry_management",
        "name": "Expiry Management & Alerts",
        "description": "Automated tracking of document expiry dates with configurable alert notifications.",
        "module": Module.DOCUMENTS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "documents_audit_trail",
        "name": "Audit Trail & Modification History",
        "description": "Full document audit trail with version history, modification tracking, and change attribution.",
        "module": Module.DOCUMENTS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    # --- CRM ---
    {
        "key": "crm_lead_scoring",
        "name": "Lead Scoring & Risk Assessment",
        "description": "Affordability scoring, DTI ratio analysis, risk factor detection, and mortgage pre-qualification tracking.",
        "module": Module.CRM,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "crm_broker_commission_engine",
        "name": "Broker Commission Engine",
        "description": "Tiered broker system (Platinum/Gold/Silver/Bronze) with performance multipliers, multi-type commission structures (percentage/fixed/tiered), and earning approval workflows.",
        "module": Module.CRM,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "beta_crm_campaign_automation",
        "name": "Campaign & Follow-Up Automation",
        "description": "Multi-channel campaign management (Email, WhatsApp, SMS) with delivery metrics, SLA-driven follow-up rules, and breach escalation.",
        "module": Module.CRM,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    # --- Tenants ---
    {
        "key": "beta_tenant_portal",
        "name": "Tenant Self-Service Portal",
        "description": "Self-service portal for property tenants to submit service requests, view lease details, and communicate with management.",
        "module": Module.TENANTS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    {
        "key": "beta_lease_management",
        "name": "Lease Lifecycle Management",
        "description": "Lease tracking with renewal workflows, rent escalation schedules, and occupancy analytics.",
        "module": Module.TENANTS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    # --- Contracts ---
    {
        "key": "beta_contract_lifecycle",
        "name": "Contract Lifecycle Management",
        "description": "End-to-end contract management with clause library, version tracking, and obligation monitoring.",
        "module": Module.CONTRACTS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    {
        "key": "beta_contract_e_signatures",
        "name": "Digital Signature Integration",
        "description": "E-signature workflows via DocuSign, Adobe Sign, and Dropbox Sign for contract execution.",
        "module": Module.CONTRACTS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    # --- IAM ---
    {
        "key": "iam_oauth_sso",
        "name": "OAuth Single Sign-On",
        "description": "OAuth 2.0 with PKCE for Google, Microsoft (Azure AD), and Apple sign-in.",
        "module": Module.IAM,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "growth",
    },
    {
        "key": "iam_service_accounts",
        "name": "Service Accounts & API Keys",
        "description": "Programmatic API access via service accounts with scoped API key generation, revocation, and usage tracking.",
        "module": Module.IAM,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "beta_iam_advanced_security",
        "name": "Advanced Security Controls",
        "description": "Organization-wide MFA enforcement, server-side session management with device tracking, and security event audit logging.",
        "module": Module.IAM,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    # --- Support Desk ---
    {
        "key": "support_desk_knowledge_base",
        "name": "Knowledge Base",
        "description": "Knowledge article management with draft/review/publish workflow, portal visibility controls, and view/helpfulness tracking.",
        "module": Module.SUPPORT_DESK,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "support_desk_automation",
        "name": "Ticket Automation & SLA Escalation",
        "description": "Rule-based ticket automation with SLA threshold triggers, auto-escalation paths, and execution logging.",
        "module": Module.SUPPORT_DESK,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "beta_support_desk_multichannel",
        "name": "Multi-Channel Support",
        "description": "Support interactions via WhatsApp, SMS, and live chat in addition to email and portal.",
        "module": Module.SUPPORT_DESK,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "growth",
    },
    # --- Settings ---
    {
        "key": "settings_contextual_access_policies",
        "name": "Contextual Access Policies",
        "description": "Conditional access rules based on IP range, device type, time of day, location, and MFA status.",
        "module": Module.SETTINGS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "settings_data_scoping",
        "name": "Data Scope Management",
        "description": "Fine-grained data visibility scoping (self, department, project, organization) with per-role and per-user overrides.",
        "module": Module.SETTINGS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": True,
        "minimum_tier": "scale",
    },
    {
        "key": "settings_geo_ip_restrictions",
        "name": "Geo & IP Restrictions",
        "description": "Country-level geo-blocking and IP whitelist enforcement for organization access.",
        "module": Module.SETTINGS,
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
    # --- Platform-wide ---
    {
        "key": "beta_dark_mode",
        "name": "Dark Mode",
        "description": "Dark color scheme for the entire platform interface.",
        "module": "",
        "scope": FeatureFlagDefinition.FlagScope.GLOBAL,
        "default_enabled": False,
        "minimum_tier": "essentials",
    },
    {
        "key": "beta_api_webhooks",
        "name": "API Webhooks",
        "description": "Outbound webhook notifications for key events (project updates, approvals, etc.).",
        "module": "",
        "scope": FeatureFlagDefinition.FlagScope.ORG,
        "default_enabled": False,
        "minimum_tier": "scale",
    },
]


class Command(BaseCommand):
    help = "Seed feature flag definitions and module activation defaults. Idempotent."

    def handle(self, *args, **options):
        # 1. Seed flag definitions (global, not per-org)
        flags_created = 0
        flags_updated = 0

        for row in FLAG_SEED_DATA:
            _, created = FeatureFlagDefinition.objects.update_or_create(
                key=row["key"],
                defaults={
                    "name": row["name"],
                    "description": row["description"],
                    "module": row["module"],
                    "scope": row["scope"],
                    "default_enabled": row["default_enabled"],
                    "minimum_tier": row["minimum_tier"],
                    "is_active": True,
                },
            )
            if created:
                flags_created += 1
            else:
                flags_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Feature flags: {flags_created} created, {flags_updated} updated."
            )
        )

        # 2. Seed module activation per org
        orgs = list(Organization.objects.all())
        if not orgs:
            self.stdout.write(self.style.WARNING("No organizations found."))
            return

        activations_created = 0
        for org in orgs:
            _, created = ModuleActivationSettings.objects.get_or_create(
                organization=org,
                defaults={
                    "enabled_modules": sorted(
                        TIER_MODULE_MAP.get(org.subscription_tier, set())
                    ),
                },
            )
            if created:
                activations_created += 1
                self.stdout.write(f"  {org.name}: module activation created")
            else:
                self.stdout.write(f"  {org.name}: already exists, skipped")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {activations_created} module activation(s) created "
                f"across {len(orgs)} org(s)."
            )
        )

"""
RBAC default configuration: permission registry, default role permissions,
and the idempotent seed function used by migrations, signals, and the
management command.
"""

# ---------------------------------------------------------------------------
# Permission Registry — served to the frontend for rendering the matrix grid
# ---------------------------------------------------------------------------

PERMISSION_REGISTRY = [
    {
        "module": "properties",
        "label": "Properties",
        "sub_modules": [
            {"key": "properties.properties", "label": "Properties", "actions": ["view", "create", "edit", "delete", "export"]},
            {"key": "properties.units", "label": "Units", "actions": ["view", "create", "edit", "delete"]},
            {"key": "properties.images", "label": "Images", "actions": ["view", "create", "delete"]},
            {"key": "properties.documents", "label": "Documents", "actions": ["view", "create", "delete", "export"]},
            {"key": "properties.valuations", "label": "Valuations", "actions": ["view", "create", "edit", "delete"]},
            {"key": "properties.ownerships", "label": "Ownerships", "actions": ["view", "create", "edit", "delete"]},
            {"key": "properties.encumbrances", "label": "Encumbrances", "actions": ["view", "create", "edit", "delete"]},
        ],
    },
    {
        "module": "projects",
        "label": "Projects",
        "sub_modules": [
            {"key": "projects.projects", "label": "Projects", "actions": ["view", "create", "edit", "delete", "export", "assign"]},
            {"key": "projects.phases", "label": "Phases", "actions": ["view", "create", "edit", "delete"]},
            {"key": "projects.tasks", "label": "Tasks", "actions": ["view", "create", "edit", "delete", "assign"]},
            {"key": "projects.milestones", "label": "Milestones", "actions": ["view", "create", "edit", "delete"]},
            {"key": "projects.costs", "label": "Costs", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
        ],
    },
    {
        "module": "finance",
        "label": "Finance",
        "sub_modules": [
            {"key": "finance.bills", "label": "Bills", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
            {"key": "finance.invoices", "label": "Invoices", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
            {"key": "finance.customers", "label": "Customers", "actions": ["view", "create", "edit", "delete"]},
            {"key": "finance.payments", "label": "Payments", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "finance.accounts", "label": "Chart of Accounts", "actions": ["view", "create", "edit", "delete"]},
            {"key": "finance.budgets", "label": "Budgets", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "finance.reports", "label": "Finance Reports", "actions": ["view", "export"]},
        ],
    },
    {
        "module": "procurement",
        "label": "Procurement",
        "sub_modules": [
            {"key": "procurement.vendors", "label": "Vendors", "actions": ["view", "create", "edit", "delete", "export"]},
            {"key": "procurement.requisitions", "label": "Requisitions", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
            {"key": "procurement.orders", "label": "Purchase Orders", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
            {"key": "procurement.receipts", "label": "Goods Receipts", "actions": ["view", "create", "edit", "delete"]},
            {"key": "procurement.rfqs", "label": "RFQs", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
            {"key": "procurement.tenders", "label": "Tender Comparisons", "actions": ["view", "create", "edit", "delete", "approve", "export"]},
        ],
    },
    {
        "module": "documents",
        "label": "Documents",
        "sub_modules": [
            {
                "key": "documents.all",
                "label": "Documents",
                "actions": [
                    "view",
                    "comment",
                    "upload_version",
                    "approve",
                    "archive",
                    "admin_override",
                ],
            },
        ],
    },
    {
        "module": "analytics",
        "label": "Analytics",
        "sub_modules": [
            {"key": "analytics.all", "label": "Analytics", "actions": ["view", "export"]},
        ],
    },
    {
        "module": "crm",
        "label": "CRM",
        "sub_modules": [
            {"key": "crm.all", "label": "CRM", "actions": ["view", "create", "edit", "delete", "export"]},
        ],
    },
    {
        "module": "tenants",
        "label": "Tenants",
        "sub_modules": [
            {"key": "tenants.all", "label": "Tenants", "actions": ["view", "create", "edit", "delete", "export"]},
        ],
    },
    {
        "module": "contracts",
        "label": "Contracts",
        "sub_modules": [
            {"key": "contracts.all", "label": "Contracts", "actions": ["view", "create", "edit", "delete", "export"]},
        ],
    },
    {
        "module": "compliance",
        "label": "Compliance",
        "sub_modules": [
            {"key": "compliance.all", "label": "Compliance", "actions": ["view", "create", "edit", "delete", "export"]},
        ],
    },
    {
        "module": "hr",
        "label": "Human Resources",
        "sub_modules": [
            {"key": "hr.org_structure", "label": "Organization Structure", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.positions", "label": "Positions", "actions": ["view", "create", "edit", "delete", "export"]},
            {"key": "hr.budgeting", "label": "Position Budgeting", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.vacancies", "label": "Vacancies", "actions": ["view", "create", "edit", "delete", "export"]},
            {"key": "hr.employee_directory", "label": "Employee Directory", "actions": ["view", "create", "edit", "delete", "export"]},
            {"key": "hr.compensation", "label": "Compensation", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.requisitions", "label": "Job Requisitions", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.job_listings", "label": "Job Listings", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.candidates", "label": "Candidates", "actions": ["view", "create", "edit", "delete", "export"]},
            {"key": "hr.interviews", "label": "Interviews", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.offers", "label": "Job Offers", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.onboarding", "label": "Onboarding", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.performance", "label": "Performance Management", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.skills", "label": "Skills & Capability", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.learning", "label": "Learning & Development", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.attendance", "label": "Attendance & Leave", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.payroll", "label": "Payroll & Compensation", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.lifecycle", "label": "Employee Lifecycle", "actions": ["view", "create", "edit", "delete", "approve"]},
            {"key": "hr.analytics", "label": "Workforce Analytics", "actions": ["view", "create", "edit", "delete"]},
            {"key": "hr.documents", "label": "HR Documents & Policies", "actions": ["view", "create", "edit", "delete", "approve"]},
        ],
    },
    {
        "module": "iam",
        "label": "Identity & Access",
        "sub_modules": [
            {"key": "iam.users", "label": "User Management", "actions": ["view", "create", "edit", "delete"]},
            {"key": "iam.service_accounts", "label": "Service Accounts", "actions": ["view", "create", "edit", "delete"]},
            {"key": "iam.mfa_settings", "label": "MFA Settings", "actions": ["view", "edit"]},
        ],
    },
    {
        "module": "support_desk",
        "label": "Support Desk",
        "sub_modules": [
            {"key": "support_desk.overview", "label": "Overview", "actions": ["view"]},
            {"key": "support_desk.tickets", "label": "Tickets", "actions": ["view", "create", "edit", "delete", "assign", "comment"]},
            {"key": "support_desk.requests", "label": "Requests", "actions": ["view", "create", "edit", "delete", "assign", "comment"]},
            {"key": "support_desk.knowledge_base", "label": "Knowledge Base", "actions": ["view", "create", "edit", "delete", "approve", "archive"]},
            {"key": "support_desk.sla_escalations", "label": "SLA & Escalations", "actions": ["view", "edit", "configure"]},
            {"key": "support_desk.communication", "label": "Communication", "actions": ["view", "create", "edit", "delete", "comment"]},
            {"key": "support_desk.automation", "label": "Automation", "actions": ["view", "create", "edit", "delete", "configure"]},
            {"key": "support_desk.reports", "label": "Reports", "actions": ["view", "export"]},
            {"key": "support_desk.configuration", "label": "Configuration", "actions": ["view", "edit", "configure"]},
        ],
    },
    {
        "module": "settings",
        "label": "Settings",
        "sub_modules": [
            {"key": "settings.company_profile", "label": "Company Profile", "actions": ["view", "edit"]},
            {"key": "settings.subsidiaries", "label": "Subsidiaries", "actions": ["view", "create", "edit", "delete"]},
            {"key": "settings.hierarchy", "label": "Hierarchy", "actions": ["view", "create", "edit", "delete"]},
            {"key": "settings.roles", "label": "Roles & Permissions", "actions": ["view", "create", "edit", "delete", "configure"]},
            {"key": "settings.security", "label": "Security Controls", "actions": ["view", "edit", "configure"]},
            {"key": "settings.system_preferences", "label": "System Preferences", "actions": ["view", "edit", "configure"]},
            {"key": "settings.audit_compliance", "label": "Audit & Compliance", "actions": ["view", "edit"]},
            {"key": "settings.workflow_templates", "label": "Workflow Templates", "actions": ["view", "create", "edit", "delete"]},
            {"key": "settings.approval_policies", "label": "Approval Policies", "actions": ["view", "create", "edit", "delete"]},
            {"key": "settings.delegations", "label": "Delegations", "actions": ["view", "create", "edit", "delete"]},
            {"key": "settings.subscriptions", "label": "Subscriptions", "actions": ["view", "edit", "manage"]},
        ],
    },
]


# ---------------------------------------------------------------------------
# Default Role Definitions
# ---------------------------------------------------------------------------

SYSTEM_ROLES = [
    ("Developer Executive", "developer-executive", "Full platform access for C-suite executives and managing directors."),
    ("Project Director", "project-director", "Manages development projects, properties, and project teams."),
    ("Sales Manager", "sales-manager", "Manages sales pipeline, customer relationships, and unit availability."),
    ("Finance Controller", "finance-controller", "Full control over financial operations including bills, invoices, and approvals."),
    ("Procurement Officer", "procurement-officer", "Manages the full procurement lifecycle from requisitions to goods receipts."),
    ("Governance Officer", "governance-officer", "Oversees compliance, document governance, and organizational policies."),
    ("Legal", "legal", "Legal review and advisory access across contracts and compliance."),
    ("External Consultant", "external-consultant", "Limited read-only access for external advisors and consultants."),
    ("Auditor", "auditor", "Read-only access with export capability for audit purposes."),
    ("Board Viewer", "board-viewer", "Dashboard and report viewing only for board members."),
    ("Super Admin", "super-admin", "Unrestricted platform access with full configuration and override capabilities."),
    ("System Admin", "system-admin", "Manages platform settings, integrations, security controls, and system configuration."),
    ("Department Admin", "department-admin", "Full access within a specific department; manages department users and workflows."),
    ("Manager", "manager", "Operational access for team leads — view, create, edit, approve within assigned modules."),
    ("Staff", "staff", "Standard user access — view and create within assigned modules."),
    ("External Auditor", "external-auditor", "Read-only access with export for external audit engagements."),
    ("Guest", "guest", "Minimal read-only access to selected modules for temporary or guest users."),
]


# ---------------------------------------------------------------------------
# Default Permission Matrix
# Each entry: (sub_module, [actions])
# ---------------------------------------------------------------------------

def _all_actions_for_registry():
    """Build a mapping of sub_module -> all available actions from the registry."""
    result = {}
    for mod in PERMISSION_REGISTRY:
        for sm in mod["sub_modules"]:
            result[sm["key"]] = sm["actions"]
    return result


_ALL_ACTIONS = _all_actions_for_registry()


def _all_permissions():
    """Every sub_module with all its actions — full access."""
    return [(sm, actions) for sm, actions in _ALL_ACTIONS.items()]


def _view_only(*modules):
    """View-only access for the given module prefixes."""
    return [
        (sm, ["view"])
        for sm, actions in _ALL_ACTIONS.items()
        if any(sm.startswith(m + ".") or sm.startswith(m + ".") for m in modules)
        and "view" in actions
    ]


def _view_export(*modules):
    """View + export access for the given module prefixes."""
    result = []
    for sm, actions in _ALL_ACTIONS.items():
        if any(sm.startswith(m + ".") for m in modules):
            granted = [a for a in ["view", "export"] if a in actions]
            if granted:
                result.append((sm, granted))
    return result


def _full_access(*modules):
    """All actions for the given module prefixes."""
    return [
        (sm, actions)
        for sm, actions in _ALL_ACTIONS.items()
        if any(sm.startswith(m + ".") for m in modules)
    ]


DEFAULT_ROLE_PERMISSIONS = {
    # Developer Executive — full access to everything
    "developer-executive": _all_permissions(),

    # Project Director — full properties + projects, operational document control
    "project-director": (
        _full_access("properties", "projects")
        + _view_only("finance", "procurement", "analytics", "hr", "settings")
        + [("documents.all", ["view", "comment", "upload_version", "approve", "archive"])]
        + [
            ("settings.workflow_templates", ["view"]),
            ("settings.approval_policies", ["view"]),
            ("settings.delegations", ["view", "create"]),
        ]
    ),

    # Sales Manager — full CRM + tenants, scoped document collaboration
    "sales-manager": (
        [
            ("properties.properties", ["view", "edit", "export"]),
            ("properties.units", ["view", "edit"]),
            ("properties.images", ["view"]),
            ("properties.documents", ["view"]),
            ("properties.valuations", ["view"]),
            ("properties.ownerships", ["view"]),
            ("properties.encumbrances", ["view"]),
        ]
        + _view_only("projects", "finance")
        + _full_access("crm", "tenants")
        + _view_only("analytics", "hr", "settings")
        + [("documents.all", ["view", "comment", "upload_version"])]
    ),

    # Finance Controller — full finance, can review and approve document records
    "finance-controller": (
        _full_access("finance")
        + [
            ("procurement.vendors", ["view"]),
            ("procurement.requisitions", ["view", "approve"]),
            ("procurement.orders", ["view", "approve"]),
            ("procurement.receipts", ["view"]),
        ]
        + _view_only("properties", "projects", "analytics", "hr", "settings")
        + [("documents.all", ["view", "comment", "approve"])]
        + [
            ("settings.workflow_templates", ["view"]),
            ("settings.approval_policies", ["view"]),
            ("settings.delegations", ["view", "create"]),
        ]
    ),

    # Procurement Officer — full procurement, can collaborate on vendor/project documents
    "procurement-officer": (
        _full_access("procurement")
        + _view_only("properties", "projects", "finance", "analytics", "hr", "settings")
        + [("documents.all", ["view", "comment", "upload_version"])]
    ),

    # Governance Officer — full compliance + documents, view+edit settings, view rest
    "governance-officer": (
        _full_access("compliance", "documents")
        + [
            ("settings.company_profile", ["view", "edit"]),
            ("settings.subsidiaries", ["view", "edit"]),
            ("settings.hierarchy", ["view", "edit"]),
            ("settings.roles", ["view"]),
            ("settings.security", ["view", "edit"]),
            ("settings.system_preferences", ["view", "edit"]),
            ("settings.audit_compliance", ["view", "edit"]),
            ("settings.workflow_templates", ["view", "create", "edit", "delete"]),
            ("settings.approval_policies", ["view", "create", "edit", "delete"]),
            ("settings.delegations", ["view", "create", "edit"]),
        ]
        + _view_only("properties", "projects", "finance", "procurement", "analytics", "hr", "iam", "support_desk")
    ),

    # Legal — view + export across most modules, full documents
    "legal": (
        _view_export("properties", "projects", "finance", "procurement", "analytics")
        + _full_access("compliance", "documents")
        + _view_only("hr", "settings")
    ),

    # External Consultant — view-only on properties, projects
    "external-consultant": (
        _view_only("properties", "projects")
    ),

    # Auditor — view + export everywhere
    "auditor": (
        _view_export(
            "properties", "projects", "finance", "procurement",
            "documents", "analytics", "compliance", "crm",
            "tenants", "contracts", "hr", "settings",
        )
        + _view_only("iam", "support_desk")
    ),

    # Board Viewer — view-only on analytics, properties, projects, finance, HR structure
    "board-viewer": (
        _view_only("analytics", "properties", "projects", "finance")
        + [
            ("hr.org_structure", ["view"]),
            ("hr.positions", ["view"]),
            ("hr.employee_directory", ["view"]),
            ("hr.requisitions", ["view"]),
            ("hr.candidates", ["view"]),
        ]
    ),

    # Super Admin — full access to everything (same as Developer Executive)
    "super-admin": _all_permissions(),

    # System Admin — full settings, security, roles, IAM; view-only on operational modules
    "system-admin": (
        _full_access("settings", "iam")
        + _full_access("support_desk")
        + _full_access("compliance")
        + _view_only("properties", "projects", "finance", "procurement", "analytics", "crm", "tenants", "contracts", "hr")
        + [("documents.all", ["view", "comment", "admin_override"])]
    ),

    # Department Admin — full access on core operational modules, limited settings
    "department-admin": (
        _full_access("properties", "projects", "finance", "procurement", "crm", "hr")
        + _full_access("support_desk")
        + [("documents.all", ["view", "comment", "upload_version", "approve", "archive"])]
        + _view_only("analytics", "compliance", "tenants", "contracts")
        + [
            ("iam.users", ["view", "edit"]),
            ("iam.service_accounts", ["view"]),
            ("iam.mfa_settings", ["view"]),
            ("settings.company_profile", ["view"]),
            ("settings.roles", ["view"]),
            ("settings.workflow_templates", ["view", "create", "edit"]),
            ("settings.approval_policies", ["view"]),
            ("settings.delegations", ["view", "create", "edit"]),
        ]
    ),

    # Manager — view, create, edit, approve within operational modules
    "manager": (
        [
            ("properties.properties", ["view", "create", "edit", "export"]),
            ("properties.units", ["view", "create", "edit"]),
            ("properties.images", ["view", "create"]),
            ("properties.documents", ["view", "create", "export"]),
            ("properties.valuations", ["view", "create", "edit"]),
            ("properties.ownerships", ["view"]),
            ("properties.encumbrances", ["view"]),
        ]
        + [
            ("projects.projects", ["view", "create", "edit", "assign"]),
            ("projects.phases", ["view", "create", "edit"]),
            ("projects.tasks", ["view", "create", "edit", "assign"]),
            ("projects.milestones", ["view", "create", "edit"]),
            ("projects.costs", ["view", "create", "edit", "approve"]),
        ]
        + [
            ("finance.bills", ["view", "create", "edit", "approve"]),
            ("finance.invoices", ["view", "create", "edit", "approve"]),
            ("finance.customers", ["view", "create", "edit"]),
            ("finance.payments", ["view", "create", "approve"]),
            ("finance.accounts", ["view"]),
            ("finance.budgets", ["view", "create", "edit", "approve"]),
            ("finance.reports", ["view"]),
        ]
        + _view_only("procurement", "analytics", "compliance", "settings")
        + [("documents.all", ["view", "comment", "upload_version", "approve"])]
        + [("crm.all", ["view", "create", "edit"])]
        + [
            ("support_desk.overview", ["view"]),
            ("support_desk.tickets", ["view", "create", "edit", "assign", "comment"]),
            ("support_desk.requests", ["view", "create", "edit", "assign", "comment"]),
            ("support_desk.knowledge_base", ["view"]),
            ("support_desk.sla_escalations", ["view"]),
            ("support_desk.communication", ["view"]),
            ("support_desk.automation", ["view"]),
            ("support_desk.reports", ["view"]),
            ("support_desk.configuration", ["view"]),
        ]
        + [
            ("hr.org_structure", ["view"]),
            ("hr.positions", ["view", "create", "edit"]),
            ("hr.budgeting", ["view", "create", "edit", "approve"]),
            ("hr.vacancies", ["view", "create", "edit"]),
            ("hr.employee_directory", ["view", "create", "edit"]),
            ("hr.compensation", ["view"]),
            ("hr.requisitions", ["view", "create", "edit", "approve"]),
            ("hr.job_listings", ["view", "create", "edit"]),
            ("hr.candidates", ["view", "create", "edit"]),
            ("hr.interviews", ["view", "create", "edit"]),
            ("hr.offers", ["view"]),
            ("hr.onboarding", ["view", "create", "edit"]),
            ("hr.performance", ["view", "create", "edit", "approve"]),
            ("hr.skills", ["view", "create", "edit"]),
            ("hr.learning", ["view", "create", "edit"]),
            ("hr.attendance", ["view", "create", "edit", "approve"]),
            ("hr.payroll", ["view", "create", "edit", "approve"]),
            ("hr.lifecycle", ["view", "create", "edit", "approve"]),
            ("hr.analytics", ["view", "create", "edit"]),
            ("hr.documents", ["view", "create", "edit", "approve"]),
        ]
    ),

    # Staff — view and create within assigned modules
    "staff": (
        [
            ("properties.properties", ["view", "create"]),
            ("properties.units", ["view"]),
            ("properties.images", ["view", "create"]),
            ("properties.documents", ["view", "create"]),
            ("properties.valuations", ["view"]),
            ("properties.ownerships", ["view"]),
            ("properties.encumbrances", ["view"]),
        ]
        + [
            ("projects.projects", ["view"]),
            ("projects.phases", ["view"]),
            ("projects.tasks", ["view", "create", "edit"]),
            ("projects.milestones", ["view"]),
            ("projects.costs", ["view", "create"]),
        ]
        + _view_only("finance", "procurement", "analytics", "hr", "settings")
        + [("documents.all", ["view", "comment", "upload_version"])]
        + [("crm.all", ["view", "create"])]
        + [
            ("support_desk.overview", ["view"]),
            ("support_desk.tickets", ["view", "create", "edit", "comment"]),
            ("support_desk.requests", ["view", "create", "edit", "comment"]),
            ("support_desk.knowledge_base", ["view"]),
            ("support_desk.sla_escalations", ["view"]),
            ("support_desk.communication", ["view"]),
            ("support_desk.automation", ["view"]),
            ("support_desk.reports", ["view"]),
            ("support_desk.configuration", ["view"]),
        ]
    ),

    # External Auditor — view + export everywhere (same as Auditor)
    "external-auditor": (
        _view_export(
            "properties", "projects", "finance", "procurement",
            "documents", "analytics", "compliance", "crm",
            "tenants", "contracts", "hr", "settings",
        )
        + _view_only("iam", "support_desk")
    ),

    # Guest — minimal read-only on a few modules
    "guest": (
        _view_only("properties", "projects", "analytics")
    ),
}


# ---------------------------------------------------------------------------
# Seed Function — idempotent, used by migration + signal + management command
# ---------------------------------------------------------------------------

def seed_roles_for_org(org, reset_permissions=False):
    """
    Create the 17 system roles for the given organization with default
    permissions. Uses get_or_create so it's safe to re-run.

    If reset_permissions=True, re-applies the default permission matrix to
    existing system roles (useful after updating defaults in code).

    Returns (created_count, existing_count).
    """
    from .models import Permission, Role, RolePermission

    for module_cfg in PERMISSION_REGISTRY:
        module = module_cfg["module"]
        for sub_module_cfg in module_cfg["sub_modules"]:
            sub_module = sub_module_cfg["key"]
            for action in sub_module_cfg["actions"]:
                Permission.objects.get_or_create(
                    sub_module=sub_module,
                    action=action,
                    defaults={
                        "module": module,
                        "key": f"{sub_module}.{action}",
                    },
                )

    created_count = 0
    existing_count = 0

    for name, slug, description in SYSTEM_ROLES:
        role, created = Role.objects.get_or_create(
            organization=org,
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "is_system": True,
            },
        )

        if created:
            created_count += 1
        else:
            existing_count += 1

        # Seed permissions if the role was just created or reset requested
        if created or reset_permissions:
            if not created:
                RolePermission.objects.filter(role=role).delete()

            seen = set()
            perms_to_create = []
            for sub_module, actions in DEFAULT_ROLE_PERMISSIONS.get(slug, []):
                module = sub_module.split(".")[0]
                for action in actions:
                    key = (sub_module, action)
                    if key in seen:
                        continue
                    seen.add(key)
                    permission_obj, _ = Permission.objects.get_or_create(
                        sub_module=sub_module,
                        action=action,
                        defaults={
                            "module": module,
                            "key": f"{sub_module}.{action}",
                        },
                    )
                    perms_to_create.append(
                        RolePermission(
                            role=role,
                            permission=permission_obj,
                            module=permission_obj.module,
                            sub_module=permission_obj.sub_module,
                            action=permission_obj.action,
                        )
                    )
            RolePermission.objects.bulk_create(perms_to_create)

    return created_count, existing_count

/**
 * Centralized module gating configuration.
 *
 * Every UI element that depends on a backend module references this file.
 * Disable a module once here → sidebar, settings, project tabs, top nav,
 * and route guards all update automatically.
 */

// ---------------------------------------------------------------------------
// 1. Sidebar sections → backend module key
//    Sections NOT listed here (e.g. "dashboard") are always visible.
// ---------------------------------------------------------------------------
export const SIDEBAR_MODULE_MAP: Record<string, string> = {
  projects: "projects",
  construction: "construction",
  properties: "properties",
  documents: "documents",
  procurement: "procurement",
  "material-management": "procurement",
  inventory: "procurement",
  boq: "procurement",
  contracts: "contracts",
  crm: "crm",
  "support-desk": "support_desk",
  partners: "crm",
  hr: "hr",
  finance: "finance",
  "finance-dashboard": "finance",
  budgets: "finance",
  "cost-tracking": "finance",
  "sales-pipeline": "crm",
  "facility-management": "facility_management",
  tenants: "tenants",
  "project-planning": "projects",
  payroll: "payroll",
  treasury: "finance",
  accounting: "finance",
  "compliance-governance": "compliance",
  permits: "compliance",
  "audit-logs": "compliance",
  "risk-management": "projects",
  "internal-tasks": "support_desk",
  calendar: "calendar",
  teams: "hr",
  mail: "mail",
  "property-registry": "properties",
};

// ---------------------------------------------------------------------------
// 2. Top-nav icons → backend module key
// ---------------------------------------------------------------------------
export const TOP_NAV_MODULE_MAP: Record<string, string> = {
  reports: "analytics",
  iam: "iam",
};

// ---------------------------------------------------------------------------
// 3. Settings sidebar — section-level gating
//    Sections NOT listed here are always visible.
// ---------------------------------------------------------------------------
export const SETTINGS_SECTION_MODULE_MAP: Record<string, string> = {
  Integrations: "finance",
  Performance: "analytics",
  Reporting: "analytics",
  Communication: "hr",
  Projects: "projects",
  Escalation: "compliance",
  "Partner Gateway": "crm",
};

// ---------------------------------------------------------------------------
// 4. Settings sidebar — item-level gating (for mixed sections)
//    Items NOT listed here are always visible within their section.
// ---------------------------------------------------------------------------
export const SETTINGS_ITEM_MODULE_MAP: Record<string, string> = {
  "/settings/audit": "compliance",
  "/settings/backup-dr": "compliance",
};

// ---------------------------------------------------------------------------
// 5. Sidebar sub-item gating (for items within an always-visible section
//    that depend on a different module than their parent)
//    Items NOT listed here are always visible within their section.
// ---------------------------------------------------------------------------
export const SIDEBAR_SUBITEM_MODULE_MAP: Record<string, string> = {
  "/projects/execution-stats": "analytics",
  "/dashboard/board-metrics": "analytics",
  "/dashboard/portfolio-analysis": "analytics",
};

// ---------------------------------------------------------------------------
// 6. Tier gating — sidebar sections that require a minimum subscription tier
//    Tier levels: essentials=0, growth=1, scale=2, custom=3
//    Sections NOT listed here have no tier requirement.
// ---------------------------------------------------------------------------
export const SIDEBAR_TIER_MAP: Record<string, number> = {
  "executive-dashboard": 2, // Scale+
};

// Route prefix → minimum tier level (for URL-level guards)
export const ROUTE_TIER_MAP: Record<string, number> = {
  "/dashboard/executive": 2, // Scale+
};

// ---------------------------------------------------------------------------
// 7. Project detail tabs → backend module key
//    Tabs NOT listed here are always visible.
// ---------------------------------------------------------------------------
export const PROJECT_TAB_MODULE_MAP: Record<string, string> = {
  cap_table: "finance",
  distributions: "finance",
};

// ---------------------------------------------------------------------------
// 7. Route prefix → backend module key (for URL-level guards)
//    If a user navigates directly to a gated route, redirect to "/".
//    More-specific prefixes MUST come before less-specific ones.
// ---------------------------------------------------------------------------
export const ROUTE_MODULE_MAP: Record<string, string> = {
  "/projects/execution-stats": "analytics",
  "/projects": "projects",
  "/construction": "construction",
  "/project-planning": "projects",
  "/properties": "properties",
  "/documents": "documents",
  "/procurement": "procurement",
  "/inventory": "procurement",
  "/material-management": "procurement",
  "/boq": "procurement",
  "/contracts": "contracts",
  "/crm": "crm",
  "/sales-pipeline": "crm",
  "/support-desk": "support_desk",
  "/internal-tasks": "support_desk",
  "/partners": "crm",
  "/hr": "hr",
  "/payroll": "payroll",
  "/teams": "hr",
  "/finance": "finance",
  "/treasury": "finance",
  "/accounting": "finance",
  "/reports": "analytics",
  "/iam": "iam",
  "/dashboard/portfolio-analysis": "analytics",
  "/dashboard/board-metrics": "analytics",
  "/facility-management": "facility_management",
  "/tenants": "tenants",
  "/compliance": "compliance",
  "/permits": "compliance",
  "/audit-logs": "compliance",
  "/risk-management": "projects",
  "/calendar": "calendar",
  "/mail": "mail",
};

// ---------------------------------------------------------------------------
// All known modules (mirrors backend Module enum in settings/models.py)
// Used for superuser bypass — superusers always have access to everything.
// ---------------------------------------------------------------------------
export const ALL_MODULES: ReadonlySet<string> = new Set([
  "properties",
  "projects",
  "finance",
  "procurement",
  "documents",
  "analytics",
  "crm",
  "tenants",
  "contracts",
  "compliance",
  "hr",
  "iam",
  "support_desk",
  "facility_management",
  "construction",
  "payroll",
  "calendar",
  "mail",
  "settings",
]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Check whether a given module is enabled in the provided set.
 */
export function isModuleEnabled(
  enabledModules: Set<string>,
  moduleKey: string | undefined,
): boolean {
  if (!moduleKey) return true; // no gate → always visible
  return enabledModules.has(moduleKey);
}

/**
 * Given a pathname, return the module key that gates it (if any).
 */
export function getRouteModule(pathname: string): string | undefined {
  for (const [prefix, moduleKey] of Object.entries(ROUTE_MODULE_MAP)) {
    if (pathname === prefix || pathname.startsWith(prefix + "/")) {
      return moduleKey;
    }
  }
  return undefined;
}

const TIER_LEVELS: Record<string, number> = { essentials: 0, growth: 1, scale: 2, custom: 3 };

/**
 * Resolve the user's numeric tier level from their subscription.
 * Returns -1 if no subscription (unsubscribed users can't access tier-gated features).
 */
export function getUserTierLevel(subscription: { edition_key: string } | null): number {
  if (!subscription) return -1;
  return TIER_LEVELS[subscription.edition_key] ?? -1;
}

/**
 * Given a pathname, return the minimum tier level required (if any).
 */
export function getRouteTier(pathname: string): number | undefined {
  for (const [prefix, tier] of Object.entries(ROUTE_TIER_MAP)) {
    if (pathname === prefix || pathname.startsWith(prefix + "/")) {
      return tier;
    }
  }
  return undefined;
}

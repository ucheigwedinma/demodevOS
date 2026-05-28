<script lang="ts">
  import { page } from "$app/stores";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import {
    SETTINGS_SECTION_MODULE_MAP,
    SETTINGS_ITEM_MODULE_MAP,
    isModuleEnabled,
  } from "$lib/modules";

  let { children } = $props();

  type MenuItem = { href: string; label: string; exact?: boolean };
  type MenuSection = { title: string; items: MenuItem[] };

  const menuSections: MenuSection[] = [
    {
      title: "Organization",
      items: [
        { href: "/settings", label: "Company Profile", exact: true },
        { href: "/settings/subsidiaries", label: "Subsidiaries" },
        { href: "/settings/hierarchy", label: "Hierarchy" },
        { href: "/settings/preferences", label: "System Preferences" },
      ],
    },
    {
      title: "Platform",
      items: [
        { href: "/settings/modules", label: "Modules & Features" },
        { href: "/settings/subscription", label: "Subscription" },
      ],
    },
    {
      title: "Data Management",
      items: [
        { href: "/settings/master-data", label: "Master Data" },
      ],
    },
    {
      title: "Security",
      items: [
        { href: "/settings/security", label: "Security Controls" },
        { href: "/settings/backup-dr", label: "Backup & DR" },
      ],
    },
    {
      title: "Audit & Activity Logs",
      items: [
        { href: "/settings/audit", label: "Audit & Compliance", exact: true },
        { href: "/settings/audit/login-activity", label: "Login Activity" },
        { href: "/settings/audit/access-logs", label: "Access Logs" },
        { href: "/settings/audit/permission-changes", label: "Permission Changes" },
        { href: "/settings/audit/role-changes", label: "Role Changes" },
        { href: "/settings/audit/failed-logins", label: "Failed Login Attempts" },
        { href: "/settings/audit/privilege-escalations", label: "Privilege Escalations" },
        { href: "/settings/audit/security-alerts", label: "Security Alerts" },
      ],
    },
    {
      title: "Integrations",
      items: [
        { href: "/settings/integration-governance", label: "Integration Governance" },
      ],
    },
    {
      title: "Performance",
      items: [
        { href: "/settings/kpi-performance", label: "KPI Configuration" },
      ],
    },
    {
      title: "Reporting",
      items: [
        { href: "/settings/reporting-engine", label: "Reporting Engine" },
      ],
    },
    {
      title: "Communication",
      items: [
        { href: "/settings/communication-branding", label: "Branding & Templates" },
      ],
    },
    {
      title: "Projects",
      items: [
        { href: "/settings/project-governance", label: "Project Governance" },
        { href: "/settings/project-templates", label: "Project Templates" },
        { href: "/settings/stage-gates", label: "Stage Gates" },
        { href: "/settings/risk-framework", label: "Risk Framework" },
      ],
    },
    {
      title: "Escalation",
      items: [
        { href: "/settings/escalation-matrix", label: "Escalation Matrix" },
      ],
    },
    {
      title: "Workflows",
      items: [
        { href: "/settings/workflows", label: "Workflow Builder", exact: true },
        { href: "/settings/workflows/policies", label: "Approval Policies" },
        { href: "/settings/workflows/delegations", label: "Delegations" },
        { href: "/settings/document-automation", label: "Document Automation" },
        { href: "/settings/notifications", label: "Workflow Notifications" },
      ],
    },
    {
      title: "Partner Gateway",
      items: [
        { href: "/settings/partner-gateway", label: "Onboarding Cases", exact: true },
        { href: "/settings/partner-gateway/templates", label: "Onboarding Templates" },
        { href: "/settings/partner-gateway/intake", label: "Intake Documents" },
        { href: "/settings/partner-gateway/approvals", label: "Approvals Queue" },
        { href: "/settings/partner-gateway/entitlements", label: "Entitlement Matrix" },
        { href: "/settings/partner-gateway/audit", label: "Audit Timeline" },
      ],
    },
  ];

  const enabledModules = $derived(onboarding.enabledModules);

  const visibleSections = $derived(
    menuSections
      .filter((s) => isModuleEnabled(enabledModules, SETTINGS_SECTION_MODULE_MAP[s.title]))
      .map((s) => ({
        ...s,
        items: s.items.filter((i) => isModuleEnabled(enabledModules, SETTINGS_ITEM_MODULE_MAP[i.href])),
      }))
      .filter((s) => s.items.length > 0)
  );

  function isActive(href: string, exact?: boolean): boolean {
    if (exact) return $page.url.pathname === href;
    return $page.url.pathname.startsWith(href);
  }
</script>

<div class="h-screen flex flex-col bg-neutral-50 font-sans">
  <!-- Top Nav -->
  <header class="bg-neutral-800 shrink-0">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <a href="/" class="text-lg">
          <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>
        </a>
        <span class="text-neutral-600">|</span>
        <h1 class="text-sm font-semibold text-white">Settings</h1>
      </div>
      <a
        href="/"
        class="flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to app
      </a>
    </div>
  </header>

  <!-- Body -->
  <div class="max-w-7xl mx-auto px-6 flex gap-8 flex-1 min-h-0 w-full">
    <!-- Settings Sidebar -->
    <aside class="w-56 shrink-0 overflow-y-auto py-8">
      {#each visibleSections as section}
        <div class="mb-8">
          <p class="text-[11px] font-semibold text-neutral-400 uppercase tracking-wider mb-3 px-3">
            {section.title}
          </p>
          <nav class="space-y-0.5">
            {#each section.items as item}
              <a
                href={item.href}
                class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                       {isActive(item.href, item.exact)
                         ? 'bg-neutral-800 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700'}"
              >
                {item.label}
              </a>
            {/each}
          </nav>
        </div>
      {/each}
    </aside>

    <!-- Settings Content -->
    <div class="flex-1 min-w-0 overflow-y-auto py-8">
      {@render children()}
    </div>
  </div>
</div>

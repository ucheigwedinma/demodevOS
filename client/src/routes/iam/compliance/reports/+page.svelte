<script lang="ts">
  // Compliance reports — surfaces curated links into the existing
  // settings reporting engine + shortcuts to the audit feed slices
  // most useful for compliance evidence (SOC 2 / ISO 27001 / NIS2).

  const REPORT_LINKS: { title: string; description: string; href: string; tag: string }[] = [
    {
      title: "Audit log export (full IAM feed)",
      description: "All authentication, role-change, permission-change, and access-request events. The canonical evidence source for SOC 2 CC-6.x controls.",
      href: "/settings/audit/access-logs",
      tag: "Audit",
    },
    {
      title: "Failed login attempts",
      description: "Anomalous-login evidence for SOC 2 CC-7.2 and ISO 27001 A.9.4.2.",
      href: "/settings/audit/failed-logins",
      tag: "Audit",
    },
    {
      title: "Permission changes",
      description: "Who changed which role's permission matrix and when. SOC 2 CC-6.3.",
      href: "/settings/audit/permission-changes",
      tag: "Audit",
    },
    {
      title: "Role changes",
      description: "User-role assignment / removal trail. SOC 2 CC-6.2 / ISO 27001 A.9.2.2.",
      href: "/settings/audit/role-changes",
      tag: "Audit",
    },
    {
      title: "Privilege escalations",
      description: "Approved 'sudo' grants and revocations — most-scrutinised events during audit.",
      href: "/settings/audit/privilege-escalations",
      tag: "Audit",
    },
    {
      title: "Dormant accounts",
      description: "Inactive-account inventory required by SOC 2 CC-6.2 / ISO 27001 A.9.2.5.",
      href: "/iam/compliance/dormant-accounts",
      tag: "Compliance",
    },
    {
      title: "Privilege risk distribution",
      description: "Snapshot of privilege concentration. Useful for least-privilege-trend reporting.",
      href: "/iam/compliance/privilege-risk",
      tag: "Compliance",
    },
    {
      title: "Access reviews — open campaigns",
      description: "Live attestation status. Drill into a campaign for full per-user evidence.",
      href: "/iam/compliance/access-reviews",
      tag: "Compliance",
    },
    {
      title: "Reporting Engine (custom reports)",
      description: "Build, schedule, and dispatch custom report templates from the platform reporting engine.",
      href: "/settings/reporting-engine",
      tag: "Reporting",
    },
  ];
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Compliance Reports</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Curated shortcuts to evidence sources for common compliance frameworks
      (SOC 2, ISO 27001, NIS2). Each link opens the underlying audit page or
      analytics view; export from there as needed.
    </p>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    {#each REPORT_LINKS as link}
      <a href={link.href}
        class="rounded-xl border border-neutral-200 bg-white p-5 hover:border-neutral-400 hover:shadow-sm transition-all">
        <div class="flex items-start justify-between gap-3 mb-2">
          <p class="text-sm font-semibold text-neutral-900">{link.title}</p>
          <span class="shrink-0 inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
            {link.tag}
          </span>
        </div>
        <p class="text-xs text-neutral-600">{link.description}</p>
        <p class="mt-3 text-xs font-medium text-neutral-500">Open →</p>
      </a>
    {/each}
  </div>

  <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
    <p class="font-medium text-neutral-700 mb-1">About this page</p>
    <p>
      This is a curated index, not a custom report builder — for ad-hoc compliance reports
      with bespoke filters and scheduled delivery, use the
      <a href="/settings/reporting-engine" class="underline underline-offset-2 hover:text-neutral-800">Reporting Engine</a>.
      A future iteration may add one-click PDF / CSV export for each row above; for now, each linked page
      surfaces its own data which can be copied or screenshotted as evidence.
    </p>
  </div>
</div>

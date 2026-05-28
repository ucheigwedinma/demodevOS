<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    ConstructionReportListItem,
    ConstructionReportDetail,
    ReportCategory,
    ReportStatus,
    ReportFrequency,
    ReportsSummary,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── State ─────────────────────────────────────────────────────────────
  let rows = $state<ConstructionReportListItem[]>([]);
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchInput = $state("");
  let searchQuery = $state("");
  let categoryFilter = $state("");
  let statusFilter = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let summary = $state<ReportsSummary | null>(null);
  const pageSize = 15;

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<ConstructionReportDetail | null>(null);
  let detailLoading = $state(false);

  // Create drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      title: "",
      category: "progress" as ReportCategory,
      status: "draft" as ReportStatus,
      frequency: "ad_hoc" as ReportFrequency,
      reporting_period_start: "",
      reporting_period_end: "",
      executive_summary: "",
      key_highlights: "",
      key_risks: "",
      recommendations: "",
      recipients: "",
      prepared_by: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let devIdx = 0;
  const SAMPLES = [
    {
      title: "Monthly Progress Report — March 2026",
      category: "progress" as ReportCategory,
      frequency: "monthly" as ReportFrequency,
      reporting_period_start: "2026-03-01",
      reporting_period_end: "2026-03-31",
      executive_summary: "Project is tracking at 58.3% completion against a planned 62.0%, representing a 3.7% schedule variance. The primary driver is a 5-day delay in MEP rough-in due to late conduit delivery. Structural works remain ahead of schedule. Cost performance is within 2% of budget with no material overruns identified.",
      key_highlights: "1. Superstructure concrete pour completed for all 8 levels — 3 days ahead of schedule\n2. Roofing membrane installation at 90% — on track for completion by April 5\n3. First elevator car delivered and staged in basement\n4. 124 consecutive safe days — zero lost-time injuries\n5. Quality inspection pass rate at 94.2% (target >90%)",
      key_risks: "1. MEP conduit supplier experiencing stock shortages — mitigation: secondary supplier identified\n2. Rainy season approaching — outdoor works may face 10-15% productivity reduction\n3. Aluminium window frames pending design revision — potential 2-week delay on facade",
      recommendations: "1. Accelerate MEP rough-in with additional crew to recover 5-day lag\n2. Pre-order critical facade materials before design revision is finalised\n3. Schedule weekend concrete pours to build buffer before rains begin",
      prepared_by: "Engr. Adewale Okonkwo — Project Manager",
      recipients: "CEO, Lead Architect, Bank Representative, Investor Group",
    },
    {
      title: "Monthly Cost Report (MCR) — March 2026",
      category: "financial" as ReportCategory,
      frequency: "monthly" as ReportFrequency,
      reporting_period_start: "2026-03-01",
      reporting_period_end: "2026-03-31",
      executive_summary: "Total project expenditure stands at ₦346M against a revised budget of ₦690M (50.1% spent). Forecast at completion is ₦698M, representing a potential ₦8M (1.2%) overrun driven primarily by substructure piling variations. Contingency drawdown is at 35% — within acceptable limits.",
      key_highlights: "1. Cash disbursement this month: ₦42.5M (within plan)\n2. 3 new POs issued totalling ₦18.2M (MEP contractor mobilisation)\n3. Variation Order VO-003 approved: +₦5M for additional piling at Grid F7-F9\n4. 98% of invoices paid within 30-day terms",
      key_risks: "1. Substructure costs ₦7M over original budget — offset partially by ₦2M savings in external works\n2. Steel price increase of 8% may affect remaining superstructure package\n3. Currency fluctuation risk on imported elevator equipment (USD-denominated)",
      recommendations: "1. Lock in steel price with forward contract for remaining 120 tonnes\n2. Transfer ₦3M savings from landscaping to cover substructure overrun\n3. Review elevator payment schedule to minimise FX exposure",
      prepared_by: "QS Funke Adeyemi",
      recipients: "CFO, Project Director, Bank QS, Investor Relations",
    },
  ];

  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length];
    devIdx++;
    form = {
      ...defaultForm(),
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      title: s.title,
      category: s.category,
      frequency: s.frequency,
      reporting_period_start: s.reporting_period_start,
      reporting_period_end: s.reporting_period_end,
      executive_summary: s.executive_summary,
      key_highlights: s.key_highlights,
      key_risks: s.key_risks,
      recommendations: s.recommendations,
      prepared_by: s.prepared_by,
      recipients: s.recipients,
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchReports() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (categoryFilter) params.category = categoryFilter;
      if (statusFilter) params.status = statusFilter;
      const [res, sum, projRes] = await Promise.all([
        api.get<PaginatedResponse<ConstructionReportListItem>>("/projects/construction-reports/", params),
        summary ? Promise.resolve(summary) : api.get<ReportsSummary>("/projects/construction-reports/summary/"),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      rows = res.results;
      totalCount = res.count;
      if (!summary) summary = sum;
      if (projRes) projects = projRes.results;
    } catch { rows = []; totalCount = 0; }
    loading = false;
  }

  $effect(() => {
    void searchQuery; void categoryFilter; void statusFilter; void currentPage;
    fetchReports();
  });

  function onSearch(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); currentPage = 1; }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<ConstructionReportDetail>(`/projects/construction-reports/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveReport(e: Event) {
    e.preventDefault();
    if (!form.title.trim() || !form.project) { toast.error("Validation", "Title and project are required."); return; }
    saving = true;
    try {
      await api.post("/projects/construction-reports/", {
        ...form,
        project: Number(form.project),
        reporting_period_start: form.reporting_period_start || null,
        reporting_period_end: form.reporting_period_end || null,
      });
      toast.success("Report created", `"${form.title}" saved as draft.`);
      createOpen = false;
      form = defaultForm();
      summary = null;
      await fetchReports();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startRow = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endRow = $derived(Math.min(currentPage * pageSize, totalCount));

  function categoryColor(c: string): string {
    switch (c) {
      case "financial": return "bg-emerald-100 text-emerald-800";
      case "progress": return "bg-blue-100 text-blue-800";
      case "hse": return "bg-amber-100 text-amber-800";
      case "contractual": return "bg-indigo-100 text-indigo-800";
      case "executive": return "bg-neutral-800 text-white";
      default: return "bg-neutral-100 text-neutral-600";
    }
  }

  const categoryLabels: Record<string, string> = {
    financial: "Financial",
    progress: "Progress",
    hse: "HSE & Compliance",
    contractual: "Contractual",
    executive: "Executive",
    custom: "Custom",
  };
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Reports</h1>
      <p class="mt-1 text-sm text-neutral-500">Intelligence hub — synthesize project data into board-ready documents.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Report</button>
  </div>

  <!-- Category Cards -->
  {#if summary}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Reports</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary.total}</p>
      </div>
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Drafts</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{summary.drafts}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Published</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{summary.published}</p>
      </div>
      {#each summary.by_category.slice(0, 3) as cat}
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{categoryLabels[cat.category] ?? cat.category}</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{cat.count}</p>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Filters + Table -->
  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <input type="text" value={searchInput} oninput={onSearch} placeholder="Search report number, title, author..." class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={categoryFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Categories</option>
          <option value="financial">Financial</option>
          <option value="progress">Progress</option>
          <option value="hse">HSE & Compliance</option>
          <option value="contractual">Contractual</option>
          <option value="executive">Executive Summary</option>
          <option value="custom">Custom</option>
        </select>
        <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="in_review">In Review</option>
          <option value="approved">Approved</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if rows.length === 0}
      <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No reports match the current filters.</p></div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[900px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Report #</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Category</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Period</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Prepared By</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as report}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(report.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{report.report_number}</td>
                <td class="px-4 py-3 text-sm text-neutral-900 max-w-[260px] truncate">{report.title}</td>
                <td class="px-4 py-3"><span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold {categoryColor(report.category)}">{report.category_display}</span></td>
                <td class="px-4 py-3"><StatusBadge status={report.status} /></td>
                <td class="px-4 py-3 text-sm text-neutral-600">{report.project_name}</td>
                <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(report.reporting_period_start)} — {fmtDate(report.reporting_period_end)}</td>
                <td class="px-4 py-3 text-sm text-neutral-600">{report.prepared_by || "--"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
        <p class="text-xs text-neutral-500">Showing <span class="font-semibold text-neutral-700">{startRow}</span>–<span class="font-semibold text-neutral-700">{endRow}</span> of <span class="font-semibold text-neutral-700">{totalCount}</span></p>
        <div class="flex items-center gap-2">
          <button onclick={() => (currentPage = Math.max(1, currentPage - 1))} disabled={currentPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
          <span class="text-xs font-medium text-neutral-600">Page {currentPage} of {totalPages}</span>
          <button onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))} disabled={currentPage >= totalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>
</div>

<!-- ═══════════ REPORT DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.report_number ?? "Report"} subtitle={detail?.title ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Header bar -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold {categoryColor(detail.category)}">{detail.category_display}</span>
          <StatusBadge status={detail.status} />
        </div>
        <span class="text-xs text-neutral-500">{detail.frequency_display}</span>
      </div>

      <!-- Meta -->
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{detail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Reporting Period</p><p class="text-sm text-neutral-900">{fmtDate(detail.reporting_period_start)} — {fmtDate(detail.reporting_period_end)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Prepared By</p><p class="text-sm text-neutral-900">{detail.prepared_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Reviewed By</p><p class="text-sm text-neutral-900">{detail.reviewed_by || "--"}</p></div>
      </div>

      <!-- Executive Summary -->
      {#if detail.executive_summary}
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-2">Executive Summary</p>
          <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.executive_summary}</p>
        </div>
      {/if}

      <!-- Key Highlights -->
      {#if detail.key_highlights}
        <div class="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-700 mb-2">Key Highlights</p>
          <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.key_highlights}</p>
        </div>
      {/if}

      <!-- Key Risks -->
      {#if detail.key_risks}
        <div class="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-amber-700 mb-2">Key Risks</p>
          <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.key_risks}</p>
        </div>
      {/if}

      <!-- Recommendations -->
      {#if detail.recommendations}
        <div class="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-2">Recommendations</p>
          <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.recommendations}</p>
        </div>
      {/if}

      <!-- Recipients -->
      {#if detail.recipients}
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Recipients</p><p class="text-sm text-neutral-700">{detail.recipients}</p></div>
      {/if}

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE REPORT DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Report" subtitle="Draft a construction report" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveReport} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={form.title} placeholder="e.g. Monthly Progress Report — March 2026" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Category</span><select bind:value={form.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="financial">Financial</option><option value="progress">Progress</option><option value="hse">HSE & Compliance</option><option value="contractual">Contractual</option><option value="executive">Executive Summary</option><option value="custom">Custom</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Frequency</span><select bind:value={form.frequency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="weekly">Weekly</option><option value="fortnightly">Fortnightly</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="ad_hoc">Ad Hoc</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Prepared By</span><input bind:value={form.prepared_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Period Start</span><DateInput bind:value={form.reporting_period_start} /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Period End</span><DateInput bind:value={form.reporting_period_end} /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Executive Summary</span><textarea bind:value={form.executive_summary} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Key Highlights</span><textarea bind:value={form.key_highlights} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Key Risks</span><textarea bind:value={form.key_risks} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Recommendations</span><textarea bind:value={form.recommendations} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Recipients</span><input bind:value={form.recipients} placeholder="Comma-separated names/roles" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Report"}</button>
    </div>
  </form>
</DrawerShell>

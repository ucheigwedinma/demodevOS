<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectReportListItem,
    ProjectReportDetail,
    ProjectReportType,
    RAGStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let reports = $state<ProjectReportListItem[]>([]);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");
  let typeFilter = $state("");

  let detailOpen = $state(false);
  let detail = $state<ProjectReportDetail | null>(null);
  let detailLoading = $state(false);

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", title: "", report_type: "executive" as ProjectReportType,
      report_date: new Date().toISOString().split("T")[0],
      period_start: "", period_end: "",
      schedule_rag: "green" as RAGStatus, budget_rag: "green" as RAGStatus,
      quality_rag: "green" as RAGStatus, safety_rag: "green" as RAGStatus,
      executive_summary: "", prepared_by: "", notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      title: "Monthly Executive Report — March 2026",
      report_type: "executive",
      report_date: "2026-03-31",
      period_start: "2026-03-01",
      period_end: "2026-03-31",
      schedule_rag: "amber",
      budget_rag: "green",
      quality_rag: "green",
      safety_rag: "green",
      executive_summary: "Phase 1 superstructure on track at 68% completion. Minor schedule pressure on MEP rough-in due to delayed equipment delivery from China (ETA +10 days). Budget remains within 2% of baseline. No safety incidents reported this period.",
      prepared_by: "Project Director — Uche Igwedinma",
      notes: "Steering Committee review scheduled for April 5th.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      if (typeFilter) params.report_type = typeFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProjectReportListItem>>("/projects/reports/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      reports = res.results;
      if (projRes) projects = projRes.results;
    } catch { reports = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; void typeFilter; fetchData(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<ProjectReportDetail>(`/projects/reports/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveReport(e: Event) {
    e.preventDefault();
    if (!form.project || !form.title.trim()) { toast.error("Required", "Project and title are required."); return; }
    saving = true;
    try {
      await api.post("/projects/reports/", {
        ...form,
        project: Number(form.project),
        period_start: form.period_start || null,
        period_end: form.period_end || null,
        key_achievements: [], key_issues: [], top_risks: [],
      });
      toast.success("Report created", `"${form.title}" saved.`);
      createOpen = false;
      form = defaultForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Failed.") : "Failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }

  function ragColor(r: string): string {
    if (r === "green") return "bg-emerald-500";
    if (r === "amber") return "bg-amber-500";
    return "bg-red-500";
  }

  function ragBg(r: string): string {
    if (r === "green") return "bg-emerald-50 border-emerald-200";
    if (r === "amber") return "bg-amber-50 border-amber-200";
    return "bg-red-50 border-red-200";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Reports</h1>
      <p class="mt-1 text-sm text-neutral-500">Executive summaries, financial analysis, schedule variance, and risk reports.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={typeFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Types</option>
        <option value="executive">Executive</option><option value="financial">Financial</option><option value="schedule">Schedule</option>
        <option value="risk">Risk</option><option value="investor">Investor</option><option value="monthly">Monthly</option><option value="custom">Custom</option>
      </select>
      <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Report</button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if reports.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No reports found.</p></div>
  {:else}
    <div class="space-y-3">
      {#each reports as r}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openDetail(r.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <div class="flex items-center gap-2 mb-1">
                <span class="text-[10px] font-semibold text-neutral-400">{r.reference}</span>
                <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-neutral-100 text-neutral-600">{r.report_type_display}</span>
                {#if r.is_frozen}<span class="text-[9px] font-bold text-indigo-600 bg-indigo-50 rounded px-1.5 py-0.5">FROZEN</span>{/if}
              </div>
              <p class="text-sm font-semibold text-neutral-900">{r.title}</p>
              <p class="text-xs text-neutral-500 mt-0.5">{r.project_name} — {fmtDate(r.report_date)}</p>
            </div>
            <!-- RAG dots -->
            <div class="flex items-center gap-2">
              <div class="flex flex-col items-center gap-0.5"><span class="h-3 w-3 rounded-full {ragColor(r.schedule_rag)}"></span><span class="text-[8px] text-neutral-400">Sch</span></div>
              <div class="flex flex-col items-center gap-0.5"><span class="h-3 w-3 rounded-full {ragColor(r.budget_rag)}"></span><span class="text-[8px] text-neutral-400">Bud</span></div>
              <div class="flex flex-col items-center gap-0.5"><span class="h-3 w-3 rounded-full {ragColor(r.quality_rag)}"></span><span class="text-[8px] text-neutral-400">Qlt</span></div>
              <div class="flex flex-col items-center gap-0.5"><span class="h-3 w-3 rounded-full {ragColor(r.safety_rag)}"></span><span class="text-[8px] text-neutral-400">HSE</span></div>
            </div>
          </div>
          <div class="flex items-center gap-6 text-xs text-neutral-500">
            {#if r.overall_completion_pct}<span>Completion: <span class="font-semibold text-neutral-700">{r.overall_completion_pct}%</span></span>{/if}
            {#if r.original_budget}<span>Budget: <span class="font-semibold text-neutral-700">{fmtC(r.original_budget)}</span></span>{/if}
            {#if r.budget_variance_pct !== null}<span class="{Number(r.budget_variance_pct) >= 0 ? 'text-emerald-600' : 'text-red-600'} font-semibold">Variance: {r.budget_variance_pct}%</span>{/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Report Detail" subtitle={detail ? `${detail.reference} — ${detail.title}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <div class="flex items-center gap-3">
        <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-neutral-100 text-neutral-600">{detail.report_type_display}</span>
        <span class="text-xs text-neutral-500">{fmtDate(detail.report_date)}</span>
        {#if detail.period_start}<span class="text-xs text-neutral-400">Period: {fmtDate(detail.period_start)} — {fmtDate(detail.period_end)}</span>{/if}
        {#if detail.is_frozen}<span class="text-[9px] font-bold text-indigo-600 bg-indigo-50 rounded px-1.5 py-0.5">FROZEN SNAPSHOT</span>{/if}
      </div>

      <!-- RAG Traffic Lights -->
      <div class="grid grid-cols-4 gap-3">
        {#each [["Schedule", detail.schedule_rag], ["Budget", detail.budget_rag], ["Quality", detail.quality_rag], ["Safety", detail.safety_rag]] as [label, rag]}
          <div class="rounded-lg border p-3 text-center {ragBg(rag as string)}">
            <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">{label}</p>
            <div class="flex items-center justify-center mt-1.5"><span class="h-5 w-5 rounded-full {ragColor(rag as string)}"></span></div>
          </div>
        {/each}
      </div>

      {#if detail.executive_summary}
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Executive Summary</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.executive_summary}</p></div>
      {/if}

      {#if detail.key_achievements && detail.key_achievements.length > 0}
        <div>
          <p class="text-[10px] font-semibold uppercase text-emerald-600 mb-1">Key Achievements</p>
          <ul class="space-y-1">{#each detail.key_achievements as a}<li class="flex items-center gap-2 text-sm"><span class="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0"></span><span class="text-neutral-700">{a}</span></li>{/each}</ul>
        </div>
      {/if}

      {#if detail.key_issues && detail.key_issues.length > 0}
        <div>
          <p class="text-[10px] font-semibold uppercase text-amber-600 mb-1">Key Issues</p>
          <ul class="space-y-1">{#each detail.key_issues as i}<li class="flex items-center gap-2 text-sm"><span class="h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0"></span><span class="text-neutral-700">{i}</span></li>{/each}</ul>
        </div>
      {/if}

      <!-- Financial Snapshot -->
      {#if detail.original_budget}
        <div>
          <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Financial Snapshot</p>
          <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
            <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Budget</p><p class="mt-1 text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.original_budget)}</p></div>
            <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Committed</p><p class="mt-1 text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.committed_spend)}</p></div>
            <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Actual</p><p class="mt-1 text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.actual_spend)}</p></div>
            <div class="rounded-lg border p-3 text-center {Number(detail.budget_variance_pct || 0) >= 0 ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}"><p class="text-[9px] font-semibold uppercase {Number(detail.budget_variance_pct || 0) >= 0 ? 'text-emerald-700' : 'text-red-700'}">Variance</p><p class="mt-1 text-sm font-bold tabular-nums {Number(detail.budget_variance_pct || 0) >= 0 ? 'text-emerald-900' : 'text-red-900'}">{detail.budget_variance_pct !== null ? `${detail.budget_variance_pct}%` : "--"}</p></div>
          </div>
          {#if detail.contingency_used_pct}<p class="text-xs text-neutral-500 mt-2">Contingency used: <span class="font-semibold text-neutral-700">{detail.contingency_used_pct}%</span></p>{/if}
        </div>
      {/if}

      <!-- Schedule -->
      {#if detail.schedule_variance_summary}
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Schedule Variance</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.schedule_variance_summary}</p></div>
      {/if}
      {#if detail.critical_path_impact}
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3"><p class="text-[10px] font-semibold uppercase text-amber-700 mb-1">Critical Path Impact</p><p class="text-sm text-amber-900 whitespace-pre-line">{detail.critical_path_impact}</p></div>
      {/if}

      <!-- Top Risks -->
      {#if detail.top_risks && detail.top_risks.length > 0}
        <div>
          <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Top Risks</p>
          <div class="space-y-2">
            {#each detail.top_risks as risk}
              <div class="rounded-lg border border-neutral-200 p-3">
                <p class="text-sm font-medium text-neutral-900">{risk.risk}</p>
                <div class="flex items-center gap-4 mt-1 text-xs text-neutral-500">
                  <span>Impact: <span class="font-semibold">{risk.impact}</span></span>
                  <span>Probability: <span class="font-semibold">{risk.probability}</span></span>
                  {#if risk.owner}<span>Owner: <span class="font-semibold">{risk.owner}</span></span>{/if}
                </div>
                {#if risk.mitigation}<p class="text-xs text-neutral-600 mt-1">Mitigation: {risk.mitigation}</p>{/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <div class="grid grid-cols-2 gap-3 text-sm">
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Prepared By</p><p class="text-neutral-900">{detail.prepared_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Approved By</p><p class="text-neutral-900">{detail.approved_by || "--"}</p></div>
      </div>

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Report" subtitle="Create a project report snapshot" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveReport} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Report Type</span><select bind:value={form.report_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="executive">Executive</option><option value="financial">Financial</option><option value="schedule">Schedule</option>
        <option value="risk">Risk</option><option value="investor">Investor</option><option value="monthly">Monthly</option><option value="custom">Custom</option>
      </select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={form.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Report Date</span><input type="date" bind:value={form.report_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Period Start</span><input type="date" bind:value={form.period_start} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Period End</span><input type="date" bind:value={form.period_end} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-4 gap-3">
      {#each [["schedule_rag", "Schedule"], ["budget_rag", "Budget"], ["quality_rag", "Quality"], ["safety_rag", "Safety"]] as [key, label]}
        <label>
          <span class="mb-1 block text-xs font-semibold text-neutral-600">{label} RAG</span>
          <select bind:value={form[key as keyof typeof form]} class="w-full rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="green">Green</option><option value="amber">Amber</option><option value="red">Red</option>
          </select>
        </label>
      {/each}
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Executive Summary</span><textarea bind:value={form.executive_summary} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Prepared By</span><input bind:value={form.prepared_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Report"}</button>
    </div>
  </form>
</DrawerShell>

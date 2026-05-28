<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    FeasibilityStudyListItem,
    FeasibilityStudyDetail,
    FeasibilityStatus,
    FeasibilityRiskLevel,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── State ─────────────────────────────────────────────────────────────
  let rows = $state<FeasibilityStudyListItem[]>([]);
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let projectFilter = $state("");
  let statusFilter = $state("");
  const pageSize = 15;

  // Detail
  let detailOpen = $state(false);
  let detail = $state<FeasibilityStudyDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"financial" | "market" | "sensitivity">("financial");

  // Create
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      version: "1.0",
      total_sales_value: "",
      other_income: "0",
      number_of_units: "0",
      avg_price_per_unit: "",
      avg_price_per_sqm: "",
      land_cost: "",
      land_legal_fees: "",
      construction_cost: "",
      professional_fees: "",
      professional_fees_pct: "8",
      marketing_sales_cost: "",
      sales_commission_pct: "5",
      finance_cost: "",
      contingency: "",
      contingency_pct: "5",
      target_irr: "25",
      expected_irr: "",
      hurdle_rate: "25",
      breakeven_units_pct: "",
      sales_velocity: "",
      project_duration_months: "36",
      market_risk: "medium" as FeasibilityRiskLevel,
      finance_risk: "medium" as FeasibilityRiskLevel,
      construction_risk: "medium" as FeasibilityRiskLevel,
      demand_analysis: "",
      pricing_benchmarks: "",
      prepared_by: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      total_sales_value: "18500000000",
      other_income: "450000000",
      number_of_units: "180",
      avg_price_per_unit: "102777778",
      avg_price_per_sqm: "850000",
      land_cost: "2800000000",
      land_legal_fees: "140000000",
      construction_cost: "7200000000",
      professional_fees: "576000000",
      professional_fees_pct: "8",
      marketing_sales_cost: "948500000",
      sales_commission_pct: "5",
      finance_cost: "720000000",
      contingency: "360000000",
      contingency_pct: "5",
      target_irr: "25",
      expected_irr: "28.5",
      hurdle_rate: "25",
      breakeven_units_pct: "65",
      sales_velocity: "4",
      project_duration_months: "30",
      market_risk: "low",
      finance_risk: "medium",
      construction_risk: "medium",
      demand_analysis: "Victoria Island office vacancy at 15% (down from 22% in 2024). Grade A rents averaging ₦120,000/sqm/annum. Residential absorption rate: 6-8 units/month for developments priced ₦100M-₦250M. Strong demand for mixed-use with retail podium. Competitor projects: Eko Atlantic (90% sold), Landmark Beach Towers (75% sold).",
      pricing_benchmarks: "Office: ₦120,000-₦180,000/sqm/annum rent; ₦800,000-₦1,200,000/sqm sale\nResidential: ₦850,000-₦1,100,000/sqm\nRetail podium: ₦150,000-₦200,000/sqm/annum",
      prepared_by: "QS Funke Adeyemi",
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchStudies() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (projectFilter) params.project = projectFilter;
      if (statusFilter) params.status = statusFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<FeasibilityStudyListItem>>("/projects/feasibility/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      rows = res.results;
      totalCount = res.count;
      if (projRes) projects = projRes.results;
    } catch { rows = []; totalCount = 0; }
    loading = false;
  }

  $effect(() => { void projectFilter; void statusFilter; void currentPage; fetchStudies(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "financial";
    try { detail = await api.get<FeasibilityStudyDetail>(`/projects/feasibility/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveStudy(e: Event) {
    e.preventDefault();
    if (!form.project) { toast.error("Required", "Select a project."); return; }
    saving = true;
    try {
      await api.post("/projects/feasibility/", {
        ...form,
        project: Number(form.project),
        number_of_units: Number(form.number_of_units) || 0,
        project_duration_months: Number(form.project_duration_months) || 36,
      });
      toast.success("Feasibility study created", "");
      createOpen = false;
      form = defaultForm();
      await fetchStudies();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtPct(v: string | number | null): string { if (v === null || v === "" || v === "0.00") return "--"; return `${Number(v).toFixed(1)}%`; }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  function riskColor(r: string): string {
    if (r === "low") return "bg-emerald-100 text-emerald-800";
    if (r === "high") return "bg-red-100 text-red-800";
    return "bg-amber-100 text-amber-800";
  }

  // Cost breakdown for donut
  function costSlices(d: FeasibilityStudyDetail): { label: string; value: number; color: string }[] {
    return [
      { label: "Land", value: Number(d.land_cost) + Number(d.land_legal_fees), color: "bg-blue-500" },
      { label: "Construction", value: Number(d.construction_cost), color: "bg-emerald-500" },
      { label: "Professional", value: Number(d.professional_fees), color: "bg-indigo-500" },
      { label: "Marketing", value: Number(d.marketing_sales_cost), color: "bg-amber-500" },
      { label: "Finance", value: Number(d.finance_cost), color: "bg-rose-500" },
      { label: "Contingency", value: Number(d.contingency), color: "bg-neutral-400" },
    ].filter(s => s.value > 0);
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Development</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Feasibility & Viability</h1>
      <p class="mt-1 text-sm text-neutral-500">Stress-test development economics — GDV, cost stack, IRR, and sensitivity analysis.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Study</button>
  </div>

  <!-- Filters -->
  <div class="flex items-center gap-3">
    <select bind:value={projectFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
    <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="draft">Draft</option>
      <option value="in_review">In Review</option>
      <option value="approved">Approved</option>
      <option value="rejected">Rejected</option>
    </select>
  </div>

  <!-- Table -->
  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if rows.length === 0}
      <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No feasibility studies found.</p></div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1050px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Ref</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">GDV</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">TDC</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Profit</th>
              <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">IRR</th>
              <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">PoC</th>
              <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Risk</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as row}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(row.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{row.study_ref} <span class="text-neutral-400 font-normal">v{row.version}</span></td>
                <td class="px-4 py-3 text-sm text-neutral-700">{row.project_name}</td>
                <td class="px-4 py-3"><StatusBadge status={row.status} /></td>
                <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-emerald-700">{fmtC(row.gdv)}</td>
                <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-700">{fmtC(row.total_development_cost)}</td>
                <td class="px-4 py-3 text-right text-sm font-bold tabular-nums {Number(row.profit) >= 0 ? 'text-emerald-600' : 'text-red-600'}">{fmtC(row.profit)}</td>
                <td class="px-4 py-3 text-center text-sm font-bold tabular-nums {row.meets_hurdle ? 'text-emerald-600' : 'text-amber-600'}">{fmtPct(row.expected_irr)}</td>
                <td class="px-4 py-3 text-center text-sm tabular-nums text-neutral-700">{row.profit_on_cost.toFixed(1)}%</td>
                <td class="px-4 py-3 text-center">
                  <div class="flex items-center justify-center gap-1">
                    <span class="w-2 h-2 rounded-full {riskColor(row.market_risk)}"></span>
                    <span class="w-2 h-2 rounded-full {riskColor(row.finance_risk)}"></span>
                    <span class="w-2 h-2 rounded-full {riskColor(row.construction_risk)}"></span>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if totalCount > pageSize}
        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalCount)} of {totalCount}</p>
          <div class="flex items-center gap-2">
            <button onclick={() => (currentPage = Math.max(1, currentPage - 1))} disabled={currentPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {currentPage} of {totalPages}</span>
            <button onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))} disabled={currentPage >= totalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    {/if}
  </section>
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.study_ref ?? "Study"} subtitle={detail ? `${detail.project_name} — v${detail.version}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Viability Scorecard -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <StatusBadge status={detail.status} />
          <span class="text-xs text-neutral-500">v{detail.version}</span>
        </div>
        <span class="text-xs text-neutral-500">By {detail.prepared_by || "--"}</span>
      </div>

      <div class="grid grid-cols-4 gap-3">
        <div class="rounded-lg border-2 {detail.meets_hurdle ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'} p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider {detail.meets_hurdle ? 'text-emerald-700' : 'text-amber-700'}">IRR</p>
          <p class="mt-1 text-2xl font-bold tabular-nums {detail.meets_hurdle ? 'text-emerald-600' : 'text-amber-600'}">{fmtPct(detail.expected_irr)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Profit on Cost</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{detail.profit_on_cost.toFixed(1)}%</p>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Margin</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{detail.margin_pct.toFixed(1)}%</p>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Break-even</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtPct(detail.breakeven_units_pct)}</p>
          <p class="text-[8px] text-neutral-400">of units</p>
        </div>
      </div>

      <!-- Risk Heatmap -->
      <div class="flex items-center gap-4">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Risk:</span>
        <span class="rounded-full px-2.5 py-0.5 text-[10px] font-semibold {riskColor(detail.market_risk)}">Market {detail.market_risk}</span>
        <span class="rounded-full px-2.5 py-0.5 text-[10px] font-semibold {riskColor(detail.finance_risk)}">Finance {detail.finance_risk}</span>
        <span class="rounded-full px-2.5 py-0.5 text-[10px] font-semibold {riskColor(detail.construction_risk)}">Construction {detail.construction_risk}</span>
      </div>

      <!-- Tabs -->
      <div class="border-b border-neutral-200">
        <nav class="-mb-px flex gap-4">
          <button class="border-b-2 px-1 pb-2 text-xs font-medium {detailTab === 'financial' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}" onclick={() => (detailTab = 'financial')}>Financial Model</button>
          <button class="border-b-2 px-1 pb-2 text-xs font-medium {detailTab === 'market' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}" onclick={() => (detailTab = 'market')}>Market Study</button>
          <button class="border-b-2 px-1 pb-2 text-xs font-medium {detailTab === 'sensitivity' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}" onclick={() => (detailTab = 'sensitivity')}>Sensitivity</button>
        </nav>
      </div>

      {#if detailTab === "financial"}
        <!-- Revenue -->
        <div class="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-emerald-700 mb-2">Revenue (GDV)</p>
          <div class="grid grid-cols-2 gap-3">
            <div><p class="text-[10px] text-neutral-400">Total Sales</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(detail.total_sales_value)}</p></div>
            <div><p class="text-[10px] text-neutral-400">Other Income</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(detail.other_income)}</p></div>
            <div><p class="text-[10px] text-neutral-400">Units</p><p class="text-sm text-neutral-900">{detail.number_of_units}</p></div>
            <div><p class="text-[10px] text-neutral-400">Avg/Unit</p><p class="text-sm text-neutral-900 tabular-nums">{fmtCFull(detail.avg_price_per_unit)}</p></div>
          </div>
          <div class="mt-2 pt-2 border-t border-emerald-200 flex justify-between">
            <span class="text-xs font-semibold text-emerald-700">Total GDV</span>
            <span class="text-sm font-bold text-emerald-900 tabular-nums">{fmtCFull(detail.gdv)}</span>
          </div>
        </div>

        <!-- Cost Stack -->
        <div class="rounded-lg border border-neutral-200 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-3">Cost Stack</p>
          <div class="space-y-2">
            {#each costSlices(detail) as slice}
              {@const total = Number(detail.total_development_cost)}
              <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full {slice.color} shrink-0"></span>
                <span class="flex-1 text-xs text-neutral-700">{slice.label}</span>
                <span class="text-xs font-bold tabular-nums text-neutral-900 w-28 text-right">{fmtC(slice.value)}</span>
                <span class="text-[10px] tabular-nums text-neutral-400 w-12 text-right">{total > 0 ? (slice.value / total * 100).toFixed(0) : 0}%</span>
              </div>
            {/each}
          </div>
          <div class="mt-3 pt-2 border-t border-neutral-200 flex justify-between">
            <span class="text-xs font-semibold text-neutral-600">Total Development Cost</span>
            <span class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(detail.total_development_cost)}</span>
          </div>
        </div>

        <!-- Profit -->
        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Profit</p>
            <p class="text-lg font-bold text-emerald-900 tabular-nums mt-1">{fmtCFull(detail.profit)}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Duration</p>
            <p class="text-lg font-bold text-neutral-900 tabular-nums mt-1">{detail.project_duration_months} months</p>
          </div>
        </div>

      {:else if detailTab === "market"}
        {#if detail.demand_analysis}
          <div class="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
            <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-2">Demand Analysis</p>
            <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.demand_analysis}</p>
          </div>
        {/if}

        {#if detail.competitor_projects.length > 0}
          <div>
            <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-2">Competitor Projects</p>
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Project</th>
                    <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Units</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Price/Unit</th>
                    <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Price/sqm</th>
                    <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Status</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each detail.competitor_projects as comp}
                    <tr>
                      <td class="px-3 py-2 text-xs text-neutral-900">{comp.name}</td>
                      <td class="px-3 py-2 text-center text-xs tabular-nums">{comp.units}</td>
                      <td class="px-3 py-2 text-right text-xs font-bold tabular-nums">{fmtC(comp.price_per_unit)}</td>
                      <td class="px-3 py-2 text-right text-xs tabular-nums">{fmtC(comp.price_per_sqm)}</td>
                      <td class="px-3 py-2 text-xs text-neutral-600">{comp.status}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}

        {#if detail.pricing_benchmarks}
          <div>
            <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-2">Pricing Benchmarks</p>
            <p class="text-sm text-neutral-700 whitespace-pre-line">{detail.pricing_benchmarks}</p>
          </div>
        {/if}

        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Sales Velocity</p>
            <p class="text-lg font-bold text-neutral-900 tabular-nums mt-1">{detail.sales_velocity} units/mo</p>
          </div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Avg Price/sqm</p>
            <p class="text-lg font-bold text-neutral-900 tabular-nums mt-1">{fmtC(detail.avg_price_per_sqm)}</p>
          </div>
        </div>

      {:else if detailTab === "sensitivity"}
        {#if Object.keys(detail.sensitivity_matrix).length > 0}
          {@const priceChanges = Object.keys(detail.sensitivity_matrix).sort((a, b) => Number(a) - Number(b))}
          {@const costChanges = priceChanges.length > 0 ? Object.keys(detail.sensitivity_matrix[priceChanges[0]]).sort((a, b) => Number(a) - Number(b)) : []}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr>
                  <th class="px-2 py-2 text-[10px] font-semibold text-neutral-500">Price \ Cost</th>
                  {#each costChanges as cc}
                    <th class="px-2 py-2 text-center text-[10px] font-semibold text-neutral-500">{cc}%</th>
                  {/each}
                </tr>
              </thead>
              <tbody>
                {#each priceChanges as pc}
                  <tr>
                    <td class="px-2 py-2 text-[10px] font-semibold text-neutral-500">{pc}%</td>
                    {#each costChanges as cc}
                      {@const irr = detail.sensitivity_matrix[pc]?.[cc] ?? 0}
                      <td class="px-2 py-2 text-center text-xs font-bold tabular-nums {irr >= Number(detail.hurdle_rate) ? 'text-emerald-600 bg-emerald-50' : 'text-red-600 bg-red-50'}">{irr.toFixed(1)}%</td>
                    {/each}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
          <div class="flex items-center gap-4 mt-2">
            <span class="flex items-center gap-1.5 text-xs text-neutral-500"><span class="w-3 h-3 rounded bg-emerald-50 border border-emerald-200"></span> Viable (IRR &ge; {fmtPct(detail.hurdle_rate)})</span>
            <span class="flex items-center gap-1.5 text-xs text-neutral-500"><span class="w-3 h-3 rounded bg-red-50 border border-red-200"></span> Below hurdle</span>
          </div>
        {:else}
          <div class="py-8 text-center"><p class="text-sm text-neutral-400">No sensitivity matrix computed. Add price/cost scenarios when editing.</p></div>
        {/if}
      {/if}

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Feasibility Study" subtitle="Model development economics" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveStudy} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Version</span><input bind:value={form.version} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>

    <!-- Revenue -->
    <div class="rounded-lg border border-emerald-200 bg-emerald-50/30 p-3 space-y-3">
      <p class="text-xs font-semibold text-emerald-700">Revenue (GDV)</p>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Total Sales Value</span><input type="number" step="0.01" bind:value={form.total_sales_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Other Income</span><input type="number" step="0.01" bind:value={form.other_income} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
      <div class="grid grid-cols-3 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Units</span><input type="number" bind:value={form.number_of_units} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Avg/Unit</span><input type="number" step="0.01" bind:value={form.avg_price_per_unit} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Avg/sqm</span><input type="number" step="0.01" bind:value={form.avg_price_per_sqm} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
    </div>

    <!-- Cost Stack -->
    <div class="rounded-lg border border-neutral-200 bg-neutral-50/30 p-3 space-y-3">
      <p class="text-xs font-semibold text-neutral-600">Cost Stack</p>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Land Cost</span><input type="number" step="0.01" bind:value={form.land_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Land Legal Fees</span><input type="number" step="0.01" bind:value={form.land_legal_fees} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Construction Cost</span><input type="number" step="0.01" bind:value={form.construction_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Professional Fees</span><input type="number" step="0.01" bind:value={form.professional_fees} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Marketing & Sales</span><input type="number" step="0.01" bind:value={form.marketing_sales_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Finance Cost</span><input type="number" step="0.01" bind:value={form.finance_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
      <label><span class="mb-1 block text-[10px] text-neutral-500">Contingency</span><input type="number" step="0.01" bind:value={form.contingency} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-3 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Expected IRR (%)</span><input type="number" step="0.1" bind:value={form.expected_irr} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Hurdle Rate (%)</span><input type="number" step="0.1" bind:value={form.hurdle_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Break-even (%)</span><input type="number" step="0.1" bind:value={form.breakeven_units_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-3 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Sales Velocity</span><input type="number" step="0.1" bind:value={form.sales_velocity} placeholder="units/mo" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Duration (months)</span><input type="number" bind:value={form.project_duration_months} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Prepared By</span><input bind:value={form.prepared_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>

    <!-- Risk -->
    <div class="grid grid-cols-3 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Market Risk</span><select bind:value={form.market_risk} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Finance Risk</span><select bind:value={form.finance_risk} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Construction Risk</span><select bind:value={form.construction_risk} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
    </div>

    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Market Demand Analysis</span><textarea bind:value={form.demand_analysis} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Study"}</button>
    </div>
  </form>
</DrawerShell>

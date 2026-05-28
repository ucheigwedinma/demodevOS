<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    CostCodeBudgetListItem,
    CostCodeBudgetDetail,
    CostTransactionItem,
    CostTransactionType,
    CostVarianceSummary,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── State ─────────────────────────────────────────────────────────────
  let summary = $state<CostVarianceSummary | null>(null);
  let budgets = $state<CostCodeBudgetListItem[]>([]);
  let loading = $state(true);
  let budgetsTotal = $state(0);
  let budgetsPage = $state(1);
  let projectFilter = $state("");
  const pageSize = 20;

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<CostCodeBudgetDetail | null>(null);
  let detailLoading = $state(false);

  // Create budget drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  // Add transaction drawer
  let txnOpen = $state(false);
  let txnSaving = $state(false);
  let txnForm = $state(defaultTxnForm());

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      cost_code: "",
      description: "",
      original_budget: "",
      approved_changes: "0",
      committed: "0",
      actual_cost: "0",
      forecast_to_complete: "",
      notes: "",
      sort_order: "0",
    };
  }

  function defaultTxnForm() {
    return {
      project: "",
      cost_code_budget: "",
      transaction_type: "commitment" as CostTransactionType,
      reference: "",
      description: "",
      amount: "",
      transaction_date: new Date().toISOString().slice(0, 10),
      vendor: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let devIdx = 0;
  const BUDGET_SAMPLES = [
    { cost_code: "1000", description: "Land Acquisition & Legal", original_budget: "200000000", forecast_to_complete: "0" },
    { cost_code: "2000", description: "Substructure (Foundation & Piling)", original_budget: "85000000", approved_changes: "5000000", committed: "92000000", actual_cost: "78000000", forecast_to_complete: "16000000" },
    { cost_code: "3000", description: "Superstructure (Concrete & Steel)", original_budget: "180000000", committed: "165000000", actual_cost: "142000000", forecast_to_complete: "42000000" },
    { cost_code: "4000", description: "M&E Services (Electrical, Plumbing, HVAC)", original_budget: "120000000", approved_changes: "-2000000", committed: "100000000", actual_cost: "68000000", forecast_to_complete: "48000000" },
    { cost_code: "5000", description: "External Works & Landscaping", original_budget: "45000000", committed: "20000000", actual_cost: "8000000", forecast_to_complete: "35000000" },
    { cost_code: "6000", description: "Preliminaries & General", original_budget: "60000000", committed: "55000000", actual_cost: "48000000", forecast_to_complete: "14000000" },
  ];

  function devFillBudget() {
    const s = BUDGET_SAMPLES[devIdx % BUDGET_SAMPLES.length];
    devIdx++;
    form = {
      ...defaultForm(),
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      cost_code: s.cost_code,
      description: s.description,
      original_budget: s.original_budget,
      approved_changes: s.approved_changes || "0",
      committed: s.committed || "0",
      actual_cost: s.actual_cost || "0",
      forecast_to_complete: s.forecast_to_complete || "0",
      sort_order: String(devIdx),
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(budgetsPage), page_size: String(pageSize) };
      if (projectFilter) params.project = projectFilter;
      const [budgetRes, summaryRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<CostCodeBudgetListItem>>("/projects/cost-control/budgets/", params),
        api.get<CostVarianceSummary>("/projects/cost-control/budgets/variance-summary/", projectFilter ? { project: projectFilter } : {}),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      budgets = budgetRes.results;
      budgetsTotal = budgetRes.count;
      summary = summaryRes;
      if (projRes) projects = projRes.results;
    } catch { budgets = []; budgetsTotal = 0; }
    loading = false;
  }

  $effect(() => {
    void projectFilter;
    void budgetsPage;
    fetchData();
  });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<CostCodeBudgetDetail>(`/projects/cost-control/budgets/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveBudget(e: Event) {
    e.preventDefault();
    if (!form.project || !form.cost_code.trim() || !form.description.trim()) { toast.error("Validation", "Project, cost code, and description are required."); return; }
    saving = true;
    try {
      await api.post("/projects/cost-control/budgets/", {
        ...form,
        project: Number(form.project),
        original_budget: form.original_budget || "0",
        sort_order: Number(form.sort_order) || 0,
      });
      toast.success("Budget line added", `${form.cost_code} — ${form.description}`);
      createOpen = false;
      form = defaultForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  async function saveTxn(e: Event) {
    e.preventDefault();
    if (!txnForm.cost_code_budget || !txnForm.amount) { toast.error("Validation", "Cost code and amount are required."); return; }
    txnSaving = true;
    try {
      await api.post("/projects/cost-control/transactions/", {
        ...txnForm,
        project: Number(txnForm.project || projectFilter),
        cost_code_budget: Number(txnForm.cost_code_budget),
      });
      toast.success("Transaction recorded", "");
      txnOpen = false;
      txnForm = defaultTxnForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { txnSaving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function varianceColor(v: string | number): string {
    const n = Number(v);
    if (n > 0) return "text-emerald-600";
    if (n === 0) return "text-neutral-500";
    return "text-red-600";
  }

  function varianceBg(v: string | number): string {
    const n = Number(v);
    if (n > 0) return "";
    if (n === 0) return "";
    return "bg-red-50/50";
  }

  const budgetsTotalPages = $derived(Math.max(1, Math.ceil(budgetsTotal / pageSize)));
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Cost Control</h1>
      <p class="mt-1 text-sm text-neutral-500">Variance analysis — planned vs committed vs actual, contingency tracking, and cash flow.</p>
    </div>
    <div class="flex items-center gap-2">
      <button onclick={() => { txnForm = defaultTxnForm(); txnOpen = true; }} class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">+ Transaction</button>
      <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800">+ Budget Line</button>
    </div>
  </div>

  <!-- Project Filter -->
  <div class="flex items-center gap-3">
    <select bind:value={projectFilter} onchange={() => (budgetsPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}
        <option value={String(p.id)}>{p.name}</option>
      {/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else}
    <!-- Variance HUD -->
    {#if summary}
      <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
        <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Original Budget</p>
          <p class="mt-1 text-lg font-bold text-blue-900 tabular-nums">{fmtC(summary.original_budget)}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Revised Budget</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(summary.revised_budget)}</p>
          {#if Number(summary.approved_changes) !== 0}
            <p class="mt-0.5 text-xs text-neutral-500">Changes: {fmtC(summary.approved_changes)}</p>
          {/if}
        </div>
        <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Committed</p>
          <p class="mt-1 text-lg font-bold text-amber-900 tabular-nums">{fmtC(summary.committed)}</p>
        </div>
        <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Actual Cost</p>
          <p class="mt-1 text-lg font-bold text-rose-900 tabular-nums">{fmtC(summary.actual_cost)}</p>
        </div>
        <div class="rounded-xl border-2 {Number(summary.variance) >= 0 ? 'border-emerald-300 bg-emerald-50' : 'border-red-300 bg-red-50'} p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider {Number(summary.variance) >= 0 ? 'text-emerald-700' : 'text-red-700'}">Variance (Budget - FAC)</p>
          <p class="mt-1 text-xl font-bold tabular-nums {varianceColor(summary.variance)}">{Number(summary.variance) >= 0 ? "+" : ""}{fmtC(summary.variance)}</p>
        </div>
      </div>

      <!-- Forecast + Contingency row -->
      <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Forecast</h3>
          <div class="grid grid-cols-2 gap-4">
            <div><p class="text-[10px] text-neutral-400">Forecast to Complete</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(summary.forecast_to_complete)}</p></div>
            <div><p class="text-[10px] text-neutral-400">Forecast at Completion</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(summary.forecast_at_completion)}</p></div>
          </div>
        </div>

        {#if summary.contingency}
          <div class="rounded-xl border border-neutral-200 bg-white p-5">
            <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Contingency Drawdown</h3>
            <div class="flex items-center gap-3 mb-2">
              <div class="flex-1 h-3 bg-neutral-200 rounded-full overflow-hidden">
                <div class="h-full rounded-full transition-all {summary.contingency.drawn_percent > 80 ? 'bg-red-500' : summary.contingency.drawn_percent > 50 ? 'bg-amber-500' : 'bg-emerald-500'}" style="width: {summary.contingency.drawn_percent}%"></div>
              </div>
              <span class="text-sm font-bold tabular-nums text-neutral-700">{summary.contingency.drawn_percent}%</span>
            </div>
            <div class="grid grid-cols-3 gap-3 text-center">
              <div><p class="text-[10px] text-neutral-400">Total</p><p class="text-xs font-semibold tabular-nums">{fmtC(summary.contingency.total)}</p></div>
              <div><p class="text-[10px] text-neutral-400">Drawn</p><p class="text-xs font-semibold tabular-nums text-amber-600">{fmtC(summary.contingency.drawn)}</p></div>
              <div><p class="text-[10px] text-neutral-400">Remaining</p><p class="text-xs font-semibold tabular-nums text-emerald-600">{fmtC(summary.contingency.remaining)}</p></div>
            </div>
          </div>
        {/if}
      </div>

      <!-- Monthly Spend -->
      {#if summary.monthly_spend && summary.monthly_spend.length > 0}
        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">Monthly Spend (Cash Flow)</h3>
          <div class="flex items-end gap-2 h-32">
            {#each summary.monthly_spend as ms}
              {@const maxSpend = Math.max(...summary!.monthly_spend.map(s => Number(s.total)))}
              <div class="flex-1 flex flex-col items-center gap-1">
                <div class="w-full bg-indigo-500 rounded-t" style="height: {maxSpend > 0 ? (Number(ms.total) / maxSpend) * 100 : 0}%"></div>
                <span class="text-[9px] text-neutral-400">{ms.month}</span>
                <span class="text-[9px] font-semibold tabular-nums text-neutral-600">{fmtC(ms.total)}</span>
              </div>
            {/each}
          </div>
        </section>
      {/if}
    {/if}

    <!-- Cost Control Ledger -->
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-4 py-3">
        <h3 class="text-sm font-semibold text-neutral-900">Cost Control Ledger</h3>
      </div>
      {#if budgets.length === 0}
        <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No budget lines defined yet.</p></div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[1100px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-400">Code</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Description</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Original</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Changes</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Revised</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Committed</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Actual</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">FAC</th>
                <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Variance</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each budgets as row}
                <tr class="hover:bg-neutral-50 cursor-pointer {varianceBg(row.variance)}" onclick={() => openDetail(row.id)}>
                  <td class="px-4 py-3 text-sm text-neutral-400">{row.cost_code}</td>
                  <td class="px-4 py-3 text-sm font-medium text-neutral-900">{row.description}</td>
                  <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-900">{fmtC(row.original_budget)}</td>
                  <td class="px-4 py-3 text-right text-sm tabular-nums {Number(row.approved_changes) !== 0 ? (Number(row.approved_changes) > 0 ? 'text-amber-600' : 'text-blue-600') : 'text-neutral-400'}">{Number(row.approved_changes) !== 0 ? (Number(row.approved_changes) > 0 ? "+" : "") + fmtC(row.approved_changes) : "--"}</td>
                  <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-900">{fmtC(row.revised_budget)}</td>
                  <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-700">{fmtC(row.committed)}</td>
                  <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-700">{fmtC(row.actual_cost)}</td>
                  <td class="px-4 py-3 text-right text-sm tabular-nums text-neutral-600">{fmtC(row.forecast_at_completion)}</td>
                  <td class="px-4 py-3 text-right text-sm font-bold tabular-nums {varianceColor(row.variance)}">{Number(row.variance) >= 0 ? "+" : ""}{fmtC(row.variance)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if budgetsTotal > pageSize}
          <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
            <p class="text-xs text-neutral-500">Showing {(budgetsPage - 1) * pageSize + 1}–{Math.min(budgetsPage * pageSize, budgetsTotal)} of {budgetsTotal}</p>
            <div class="flex items-center gap-2">
              <button onclick={() => (budgetsPage = Math.max(1, budgetsPage - 1))} disabled={budgetsPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
              <span class="text-xs font-medium text-neutral-600">Page {budgetsPage} of {budgetsTotalPages}</span>
              <button onclick={() => (budgetsPage = Math.min(budgetsTotalPages, budgetsPage + 1))} disabled={budgetsPage >= budgetsTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
            </div>
          </div>
        {/if}
      {/if}
    </section>
  {/if}
</div>

<!-- ═══════════ BUDGET DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail ? `${detail.cost_code} — ${detail.description}` : "Budget Line"} subtitle="" width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Budget summary cards -->
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-blue-200 bg-blue-50 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Revised Budget</p>
          <p class="mt-1 text-sm font-bold text-blue-900 tabular-nums">{fmtCFull(detail.revised_budget)}</p>
        </div>
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Committed</p>
          <p class="mt-1 text-sm font-bold text-amber-900 tabular-nums">{fmtCFull(detail.committed)}</p>
        </div>
        <div class="rounded-lg border-2 {Number(detail.variance) >= 0 ? 'border-emerald-300 bg-emerald-50' : 'border-red-300 bg-red-50'} p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider {Number(detail.variance) >= 0 ? 'text-emerald-700' : 'text-red-700'}">Variance</p>
          <p class="mt-1 text-sm font-bold tabular-nums {varianceColor(detail.variance)}">{Number(detail.variance) >= 0 ? "+" : ""}{fmtCFull(detail.variance)}</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Original Budget</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(detail.original_budget)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Approved Changes</p><p class="text-sm text-neutral-900 tabular-nums">{fmtCFull(detail.approved_changes)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Actual Cost</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtCFull(detail.actual_cost)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Forecast to Complete</p><p class="text-sm text-neutral-900 tabular-nums">{fmtCFull(detail.forecast_to_complete)}</p></div>
      </div>

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      <!-- Transactions -->
      <div class="border-t border-neutral-200 pt-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Transactions ({detail.transactions.length})</p>
        {#if detail.transactions.length > 0}
          <div class="space-y-2">
            {#each detail.transactions as txn}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3 flex items-center justify-between">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-neutral-200 text-neutral-600">{txn.transaction_type_display}</span>
                    <span class="text-xs text-neutral-500">{fmtDate(txn.transaction_date)}</span>
                  </div>
                  <p class="text-sm text-neutral-800 mt-0.5">{txn.reference || txn.description}</p>
                  {#if txn.vendor}<p class="text-xs text-neutral-500">{txn.vendor}</p>{/if}
                </div>
                <p class="text-sm font-bold tabular-nums text-neutral-900">{fmtCFull(txn.amount)}</p>
              </div>
            {/each}
          </div>
        {:else}
          <p class="text-sm text-neutral-400 text-center py-4">No transactions recorded.</p>
        {/if}
      </div>
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE BUDGET DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Add Budget Line" subtitle="Define a cost code with budget allocation" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={saveBudget} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <div class="grid grid-cols-3 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Code *</span><input bind:value={form.cost_code} placeholder="e.g. 2000" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label class="col-span-2"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description *</span><input bind:value={form.description} placeholder="e.g. Substructure" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Original Budget</span><input type="number" step="0.01" bind:value={form.original_budget} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Committed</span><input type="number" step="0.01" bind:value={form.committed} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Actual Cost</span><input type="number" step="0.01" bind:value={form.actual_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Forecast to Complete</span><input type="number" step="0.01" bind:value={form.forecast_to_complete} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillBudget} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Add Budget Line"}</button>
    </div>
  </form>
</DrawerShell>

<!-- ═══════════ ADD TRANSACTION DRAWER ═══════════ -->
<DrawerShell open={txnOpen} title="Record Transaction" subtitle="Log a commitment, invoice, payment, or transfer" width="max-w-md" onclose={() => (txnOpen = false)}>
  <form onsubmit={saveTxn} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Code *</span>
      <select bind:value={txnForm.cost_code_budget} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">Select</option>
        {#each budgets as b}<option value={String(b.id)}>{b.cost_code} — {b.description}</option>{/each}
      </select>
    </label>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span>
        <select bind:value={txnForm.transaction_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="commitment">Commitment (PO)</option>
          <option value="invoice">Invoice</option>
          <option value="payment">Payment</option>
          <option value="variation">Variation</option>
          <option value="transfer">Budget Transfer</option>
          <option value="contingency">Contingency</option>
        </select>
      </label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Amount *</span><input type="number" step="0.01" bind:value={txnForm.amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Reference</span><input bind:value={txnForm.reference} placeholder="PO #, Invoice #" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Date</span><DateInput bind:value={txnForm.transaction_date} /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Vendor</span><input bind:value={txnForm.vendor} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><input bind:value={txnForm.description} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (txnOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button type="submit" disabled={txnSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{txnSaving ? "Saving..." : "Record"}</button>
    </div>
  </form>
</DrawerShell>

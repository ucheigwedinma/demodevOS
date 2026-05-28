<script lang="ts">
  import { untrack } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    HeadcountSummaryResponse,
    HRBudgetStatus,
    HRPositionBudgetListItem,
    HRPositionBudgetWhatIfResponse,
    HRPositionBudgetSource,
    MasterDataEntry,
    PaginatedResponse,
  } from "$lib/types";

  let budgets = $state<HRPositionBudgetListItem[]>([]);
  let summary = $state<HeadcountSummaryResponse | null>(null);
  let totalCount = $state(0);
  let loading = $state(true);
  let summaryLoading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let filterYear = $state("");
  let filterStatus = $state("");
  let filterBudgetSource = $state("");
  let filterCurrency = $state("");
  let searchQuery = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let revisionMode = $state(false);
  let revisionReason = $state("");

  let form = $state({
    department: "" as string,
    position: "" as string,
    fiscal_period_label: "",
    fiscal_year: new Date().getFullYear(),
    budget_source: "corporate_overhead" as HRPositionBudgetSource,
    currency: "",
    fte: 1,
    statutory_benefits_rate: 15,
    allowances_rate: 10,
    local_tax_rate: 0,
    insurance_rate: 0,
    approved_headcount: 0,
    filled_headcount: 0,
    budget_amount: "",
    status: "draft" as HRBudgetStatus,
    notes: "",
  });

  let whatIfLoading = $state(false);
  let whatIfResult = $state<HRPositionBudgetWhatIfResponse | null>(null);
  let whatIfForm = $state({
    fiscal_year: "",
    department: "",
    position: "",
    additional_headcount: 2,
    per_head_cost: "",
    project_revenue: "",
    other_project_costs: "",
  });

  let departmentOptions = $state<{ id: number; name: string }[]>([]);
  let positionOptions = $state<{ id: number; title: string; code: string }[]>([]);
  let currencyOptions = $state<{ code: string; label: string }[]>([]);
  let expandedBudgetIds = $state<number[]>([]);

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<HRBudgetStatus, string> = {
    draft: "Draft",
    approved: "Approved",
    frozen: "Frozen",
  };

  const budgetSourceLabels: Record<HRPositionBudgetSource, string> = {
    corporate_overhead: "Corporate Overhead (Fixed)",
    project_funding: "Project Loan / Investor Fund (Variable)",
  };
  const budgetSources: HRPositionBudgetSource[] = ["corporate_overhead", "project_funding"];

  function normalizeCurrencyOptions(entries: MasterDataEntry[]): { code: string; label: string }[] {
    return entries
      .map((entry) => ({
        code: entry.code.toUpperCase(),
        label: entry.label || entry.code.toUpperCase(),
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  function formatByCurrency(amount: string | number, currencyCode: string | null | undefined): string {
    const value = Number(amount);
    if (!Number.isFinite(value)) return String(amount);
    const code = (currencyCode || "").toUpperCase();
    if (!code) return currency.format(value);
    try {
      return new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: code,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);
    } catch {
      return `${code} ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
  }

  function asNumber(value: string | number | null | undefined, fallback = 0): number {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function formatPercent(value: string | number | null | undefined): string {
    const parsed = asNumber(value, 0);
    return `${parsed.toFixed(2)}%`;
  }

  function heatPillClass(status: "green" | "yellow" | "red" | string): string {
    if (status === "red") return "bg-red-100 text-red-800";
    if (status === "yellow") return "bg-amber-100 text-amber-800";
    return "bg-emerald-100 text-emerald-800";
  }

  const burdenMultiplierPreview = $derived(
    (
      1 +
      (
        asNumber(form.statutory_benefits_rate, 0) +
        asNumber(form.allowances_rate, 0) +
        asNumber(form.local_tax_rate, 0) +
        asNumber(form.insurance_rate, 0)
      ) /
        100
    ).toFixed(4),
  );

  async function loadBudgetLookups() {
    try {
      const [deptRes, positionRes, currencyRes] = await Promise.all([
        api.get<{ results: { id: number; name: string }[] }>("/settings/departments/", { page_size: "200" }),
        api.get<{ results: { id: number; title: string; code: string }[] }>("/hr/positions/", {
          page_size: "500",
          status: "active",
        }),
        api.get<PaginatedResponse<MasterDataEntry>>("/settings/master-data/", {
          category: "currency",
          is_active: "true",
          page_size: "200",
        }),
      ]);

      departmentOptions = deptRes.results;
      positionOptions = positionRes.results;
      currencyOptions = normalizeCurrencyOptions(currencyRes.results ?? []);
      if (currencyOptions.length === 0) {
        currencyOptions = [{ code: currency.config.code, label: currency.config.code }];
      }
      if (!form.currency) {
        form.currency = currencyOptions[0]?.code ?? currency.config.code;
      }
    } catch {
      departmentOptions = [];
      positionOptions = [];
      currencyOptions = [{ code: currency.config.code, label: currency.config.code }];
      if (!form.currency) {
        form.currency = currency.config.code;
      }
    }
  }

  async function fetchBudgets() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (filterYear) params.fiscal_year = filterYear;
      if (filterStatus) params.status = filterStatus;
      if (filterBudgetSource) params.budget_source = filterBudgetSource;
      if (filterCurrency) params.currency = filterCurrency;
      if (searchQuery) params.search = searchQuery;

      const res = await api.get<PaginatedResponse<HRPositionBudgetListItem>>("/hr/position-budgets/", params);
      budgets = res.results;
      totalCount = res.count;
    } catch {
      budgets = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchSummary() {
    summaryLoading = true;
    try {
      const params: Record<string, string> = {};
      if (filterYear) params.fiscal_year = filterYear;
      if (filterCurrency) params.currency = filterCurrency;
      summary = await api.get<HeadcountSummaryResponse>("/hr/headcount-summary/", params);
    } catch {
      summary = null;
    } finally {
      summaryLoading = false;
    }
  }

  function resetForm() {
    form = {
      department: "",
      position: "",
      fiscal_period_label: "",
      fiscal_year: new Date().getFullYear(),
      budget_source: "corporate_overhead",
      currency: currencyOptions[0]?.code ?? currency.config.code,
      fte: 1,
      statutory_benefits_rate: 15,
      allowances_rate: 10,
      local_tax_rate: 0,
      insurance_rate: 0,
      approved_headcount: 0,
      filled_headcount: 0,
      budget_amount: "",
      status: "draft",
      notes: "",
    };
    fieldErrors = {};
    editingId = null;
    revisionMode = false;
    revisionReason = "";
  }

  async function openCreate() {
    resetForm();
    await loadBudgetLookups();
    showSlideOver = true;
  }

  async function openEdit(budget: HRPositionBudgetListItem) {
    resetForm();
    editingId = budget.id;
    revisionMode = budget.status === "approved" || budget.status === "frozen";
    revisionReason = "";
    form.department = String(budget.department);
    form.position = budget.position ? String(budget.position) : "";
    form.fiscal_period_label = budget.fiscal_period_label || "";
    form.fiscal_year = budget.fiscal_year;
    form.budget_source = budget.budget_source;
    form.currency = budget.currency;
    form.fte = asNumber(budget.fte, 1);
    form.statutory_benefits_rate = asNumber(budget.statutory_benefits_rate, 15);
    form.allowances_rate = asNumber(budget.allowances_rate, 10);
    form.local_tax_rate = asNumber(budget.local_tax_rate, 0);
    form.insurance_rate = asNumber(budget.insurance_rate, 0);
    form.approved_headcount = budget.approved_headcount;
    form.filled_headcount = budget.filled_headcount;
    form.budget_amount = budget.budget_amount;
    form.status = budget.status;

    try {
      const [, detail] = await Promise.all([
        loadBudgetLookups(),
        api.get<{ notes: string }>(`/hr/position-budgets/${budget.id}/`),
      ]);
      form.notes = detail.notes;
    } catch {
      // Keep already loaded values.
    }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        department: form.department ? Number(form.department) : undefined,
        fiscal_period_label: form.fiscal_period_label.trim(),
        fiscal_year: form.fiscal_year,
        budget_source: form.budget_source,
        currency: form.currency,
        fte: asNumber(form.fte, 1),
        statutory_benefits_rate: asNumber(form.statutory_benefits_rate, 15),
        allowances_rate: asNumber(form.allowances_rate, 10),
        local_tax_rate: asNumber(form.local_tax_rate, 0),
        insurance_rate: asNumber(form.insurance_rate, 0),
        approved_headcount: form.approved_headcount,
        filled_headcount: form.filled_headcount,
        budget_amount: form.budget_amount || "0",
        status: form.status,
        notes: form.notes,
      };
      if (form.position) payload.position = Number(form.position);

      if (isEditing && revisionMode) {
        if (!revisionReason.trim()) {
          fieldErrors = { reason: ["Provide a reason for this revision request."] };
          return;
        }
        await api.post("/hr/position-budget-revisions/", {
          budget: editingId,
          reason: revisionReason.trim(),
          proposed_changes: payload,
        });
        toast.success("Budget revision submitted for approval");
      } else if (isEditing) {
        await api.patch(`/hr/position-budgets/${editingId}/`, payload);
        toast.success("Budget record updated");
      } else {
        await api.post("/hr/position-budgets/", payload);
        toast.success("Budget record created");
      }

      showSlideOver = false;
      resetForm();
      fetchBudgets();
      fetchSummary();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        if (err.message) {
          toast.error(err.message);
        }
      } else {
        toast.error("Failed to save budget record");
      }
    } finally {
      saving = false;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchBudgets();
    }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchBudgets();
  }

  async function runWhatIfSimulator() {
    whatIfLoading = true;
    try {
      const payload: Record<string, string | number> = {
        additional_headcount: Math.max(1, asNumber(whatIfForm.additional_headcount, 1)),
      };
      if (whatIfForm.fiscal_year) payload.fiscal_year = Number(whatIfForm.fiscal_year);
      if (whatIfForm.department) payload.department = Number(whatIfForm.department);
      if (whatIfForm.position) payload.position = Number(whatIfForm.position);
      if (whatIfForm.per_head_cost) payload.per_head_cost = whatIfForm.per_head_cost;
      if (whatIfForm.project_revenue) payload.project_revenue = whatIfForm.project_revenue;
      if (whatIfForm.other_project_costs) payload.other_project_costs = whatIfForm.other_project_costs;
      if (filterCurrency) payload.currency = filterCurrency;

      whatIfResult = await api.post<HRPositionBudgetWhatIfResponse>("/hr/position-budgets/what-if/", payload);
    } catch (err) {
      whatIfResult = null;
      if (err instanceof ApiError && err.message) {
        toast.error(err.message);
      } else {
        toast.error("Failed to run what-if simulation");
      }
    } finally {
      whatIfLoading = false;
    }
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function isBudgetExpanded(id: number): boolean {
    return expandedBudgetIds.includes(id);
  }

  function toggleBudgetExpansion(id: number) {
    if (isBudgetExpanded(id)) {
      expandedBudgetIds = expandedBudgetIds.filter((budgetId) => budgetId !== id);
      return;
    }
    expandedBudgetIds = [...expandedBudgetIds, id];
  }

  function openHeadcountCount(budget: HRPositionBudgetListItem): number {
    const openCount = budget.approved_headcount - budget.filled_headcount;
    return openCount > 0 ? openCount : 0;
  }

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const BUDGET_SAMPLES = [
    {
      fiscal_period_label: "Zion Estate Project Phase 1",
      fiscal_year: 2026,
      budget_source: "project_funding" as HRPositionBudgetSource,
      fte: 1,
      statutory_benefits_rate: 15,
      allowances_rate: 10,
      local_tax_rate: 3,
      insurance_rate: 2,
      approved_headcount: 12,
      filled_headcount: 8,
      budget_amount: "960000",
      status: "approved" as HRBudgetStatus,
      notes: "Structural engineering team expansion for block package delivery.",
    },
    {
      fiscal_period_label: "Q2 2026",
      fiscal_year: 2026,
      budget_source: "corporate_overhead" as HRPositionBudgetSource,
      fte: 1,
      statutory_benefits_rate: 12,
      allowances_rate: 8,
      local_tax_rate: 2,
      insurance_rate: 1,
      approved_headcount: 6,
      filled_headcount: 6,
      budget_amount: "540000",
      status: "approved" as HRBudgetStatus,
      notes: "Sales and client success staffing envelope for off-plan campaigns.",
    },
    {
      fiscal_period_label: "Q3 2026",
      fiscal_year: 2026,
      budget_source: "project_funding" as HRPositionBudgetSource,
      fte: 0.5,
      statutory_benefits_rate: 10,
      allowances_rate: 12,
      local_tax_rate: 2,
      insurance_rate: 2,
      approved_headcount: 3,
      filled_headcount: 0,
      budget_amount: "420000",
      status: "draft" as HRBudgetStatus,
      notes: "Proposed SPV finance team, pending board approval.",
    },
  ];

  let budgetDevIdx = 0;
  function devFillBudget() {
    const sample = BUDGET_SAMPLES[budgetDevIdx % BUDGET_SAMPLES.length];
    budgetDevIdx++;
    form.fiscal_period_label = sample.fiscal_period_label;
    form.fiscal_year = sample.fiscal_year;
    form.budget_source = sample.budget_source;
    form.fte = sample.fte;
    form.statutory_benefits_rate = sample.statutory_benefits_rate;
    form.allowances_rate = sample.allowances_rate;
    form.local_tax_rate = sample.local_tax_rate;
    form.insurance_rate = sample.insurance_rate;
    form.approved_headcount = sample.approved_headcount;
    form.filled_headcount = sample.filled_headcount;
    form.budget_amount = sample.budget_amount;
    form.status = sample.status;
    form.notes = sample.notes;
    form.department =
      departmentOptions.length > 0 ? String(departmentOptions[budgetDevIdx % departmentOptions.length].id) : "";
    form.position = "";
    form.currency = currencyOptions[0]?.code ?? currency.config.code;
  }

  $effect(() => {
    untrack(() => {
      fetchBudgets();
      fetchSummary();
      loadBudgetLookups();
    });
  });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Position Budgeting</h1>
      <p class="mt-1 text-sm text-neutral-500">Financial guardrails for staffing plans and headcount cashflow.</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Budget
    </button>
  </div>

  {#if !summaryLoading && summary}
    <div class="grid grid-cols-3 gap-4 mb-8">
      <div class="bg-white border border-neutral-200 rounded-xl p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Approved Headcount</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1">{summary.totals.approved_headcount}</p>
      </div>
      <div class="bg-white border border-neutral-200 rounded-xl p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Filled Headcount</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1">{summary.totals.filled_headcount}</p>
      </div>
      <div class="bg-white border border-neutral-200 rounded-xl p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Headcount Budget</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1">
          {formatByCurrency(summary.totals.budget_amount, summary.currency || filterCurrency || currency.config.code)}
        </p>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-5 mb-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Budget vs Actual (BvA)</p>
          <p class="mt-1 text-sm text-neutral-600">Real-time staffing spend variance across committed and recruitment pipeline.</p>
        </div>
        <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold {summary.budget_vs_actual.variance_status === 'over_budget' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'}">
          {summary.budget_vs_actual.variance_status === "over_budget" ? "Over Budget" : "Buffer Available"}
        </span>
      </div>
      <div class="grid grid-cols-4 gap-3 mt-4">
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Budgeted</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">
            {formatByCurrency(summary.budget_vs_actual.budgeted, summary.currency || filterCurrency || currency.config.code)}
          </p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Committed</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">
            {formatByCurrency(summary.budget_vs_actual.committed, summary.currency || filterCurrency || currency.config.code)}
          </p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Pipeline</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">
            {formatByCurrency(summary.budget_vs_actual.pipeline, summary.currency || filterCurrency || currency.config.code)}
          </p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Variance</p>
          <p class="mt-1 text-sm font-semibold {summary.budget_vs_actual.variance_status === 'over_budget' ? 'text-red-700' : 'text-emerald-700'}">
            {formatByCurrency(summary.budget_vs_actual.variance, summary.currency || filterCurrency || currency.config.code)}
          </p>
        </div>
      </div>
    </div>

    <div class="grid gap-4 lg:grid-cols-2 mb-8">
      <section class="rounded-xl border border-neutral-200 bg-white p-4">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-neutral-900">Utilization Heatmap · Departments</h2>
          <p class="text-xs text-neutral-500">Committed + Pipeline vs Budgeted</p>
        </div>
        {#if summary.utilization_heatmap.departments.length === 0}
          <p class="mt-4 text-sm text-neutral-500">No department utilization data yet.</p>
        {:else}
          <div class="mt-3 overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-200 text-neutral-500 uppercase tracking-wide">
                  <th class="text-left py-2 font-medium">Department</th>
                  <th class="text-right py-2 font-medium">Utilization</th>
                  <th class="text-right py-2 font-medium">Heat</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each summary.utilization_heatmap.departments as item}
                  <tr>
                    <td class="py-2">
                      <p class="font-medium text-neutral-900">{item.department_name}</p>
                      <p class="text-[11px] text-neutral-500">
                        {formatByCurrency(item.committed, summary.currency || filterCurrency || currency.config.code)}
                        + {formatByCurrency(item.pipeline, summary.currency || filterCurrency || currency.config.code)}
                        / {formatByCurrency(item.budgeted, summary.currency || filterCurrency || currency.config.code)}
                      </p>
                    </td>
                    <td class="py-2 text-right font-medium text-neutral-800">{item.utilization_percent.toFixed(2)}%</td>
                    <td class="py-2 text-right">
                      <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold {heatPillClass(item.heat_status)}">
                        {item.heat_label}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-4">
        <div class="flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-neutral-900">Utilization Heatmap · Projects</h2>
          <p class="text-xs text-neutral-500">Project-funded staffing buckets</p>
        </div>
        {#if summary.utilization_heatmap.projects.length === 0}
          <p class="mt-4 text-sm text-neutral-500">No project utilization data yet.</p>
        {:else}
          <div class="mt-3 overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-200 text-neutral-500 uppercase tracking-wide">
                  <th class="text-left py-2 font-medium">Project / Phase</th>
                  <th class="text-right py-2 font-medium">Utilization</th>
                  <th class="text-right py-2 font-medium">Heat</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each summary.utilization_heatmap.projects as item}
                  <tr>
                    <td class="py-2">
                      <p class="font-medium text-neutral-900">{item.label}</p>
                      <p class="text-[11px] text-neutral-500">
                        {formatByCurrency(item.committed, summary.currency || filterCurrency || currency.config.code)}
                        + {formatByCurrency(item.pipeline, summary.currency || filterCurrency || currency.config.code)}
                        / {formatByCurrency(item.budgeted, summary.currency || filterCurrency || currency.config.code)}
                      </p>
                    </td>
                    <td class="py-2 text-right font-medium text-neutral-800">{item.utilization_percent.toFixed(2)}%</td>
                    <td class="py-2 text-right">
                      <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold {heatPillClass(item.heat_status)}">
                        {item.heat_label}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>
    </div>
  {/if}

  <section class="rounded-xl border border-neutral-200 bg-white p-5 mb-8">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-neutral-900">What-If Simulator</h2>
        <p class="mt-1 text-xs text-neutral-500">Model staffing scenarios and project-margin impact before approving headcount changes.</p>
      </div>
      <button
        onclick={runWhatIfSimulator}
        disabled={whatIfLoading}
        class="inline-flex items-center rounded-lg bg-neutral-900 px-3 py-2 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
      >
        {whatIfLoading ? "Running..." : "Run Simulation"}
      </button>
    </div>

    <div class="mt-4 grid gap-3 md:grid-cols-3">
      <label class="text-xs text-neutral-600">
        Fiscal Year
        <input
          type="number"
          min={2020}
          max={2035}
          bind:value={whatIfForm.fiscal_year}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </label>
      <label class="text-xs text-neutral-600">
        Department
        <select
          bind:value={whatIfForm.department}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All departments</option>
          {#each departmentOptions as dept}
            <option value={String(dept.id)}>{dept.name}</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-neutral-600">
        Position
        <select
          bind:value={whatIfForm.position}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">Auto-select position cost</option>
          {#each positionOptions as position}
            <option value={String(position.id)}>{position.title} ({position.code})</option>
          {/each}
        </select>
      </label>
      <label class="text-xs text-neutral-600">
        Additional Headcount
        <input
          type="number"
          min={1}
          bind:value={whatIfForm.additional_headcount}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </label>
      <label class="text-xs text-neutral-600">
        Per-Head Cost Override
        <input
          type="text"
          bind:value={whatIfForm.per_head_cost}
          placeholder="Optional"
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </label>
      <label class="text-xs text-neutral-600">
        Project Revenue
        <input
          type="text"
          bind:value={whatIfForm.project_revenue}
          placeholder="Optional"
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </label>
    </div>
    <label class="mt-3 block text-xs text-neutral-600">
      Other Project Costs
      <input
        type="text"
        bind:value={whatIfForm.other_project_costs}
        placeholder="Optional"
        class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
      />
    </label>

    {#if whatIfResult}
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Baseline</p>
          <p class="mt-1 text-xs text-neutral-600">Committed {formatByCurrency(whatIfResult.baseline.committed, whatIfResult.currency || filterCurrency || currency.config.code)}</p>
          <p class="text-xs text-neutral-600">Pipeline {formatByCurrency(whatIfResult.baseline.pipeline, whatIfResult.currency || filterCurrency || currency.config.code)}</p>
          <p class="text-xs text-neutral-600">Variance {formatByCurrency(whatIfResult.baseline.variance, whatIfResult.currency || filterCurrency || currency.config.code)}</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">
            Margin {whatIfResult.baseline.project_margin_percent === null ? "N/A" : `${whatIfResult.baseline.project_margin_percent.toFixed(2)}%`}
          </p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Scenario</p>
          <p class="mt-1 text-xs text-neutral-600">Additional Cost {formatByCurrency(whatIfResult.scenario.additional_cost, whatIfResult.currency || filterCurrency || currency.config.code)}</p>
          <p class="text-xs text-neutral-600">Committed {formatByCurrency(whatIfResult.scenario.committed, whatIfResult.currency || filterCurrency || currency.config.code)}</p>
          <p class="text-xs text-neutral-600">Variance {formatByCurrency(whatIfResult.scenario.variance, whatIfResult.currency || filterCurrency || currency.config.code)}</p>
          <p class="mt-1 text-sm font-semibold {whatIfResult.scenario.margin_delta_percent !== null && whatIfResult.scenario.margin_delta_percent < 0 ? 'text-red-700' : 'text-neutral-900'}">
            Margin {whatIfResult.scenario.project_margin_percent === null ? "N/A" : `${whatIfResult.scenario.project_margin_percent.toFixed(2)}%`}
            {#if whatIfResult.scenario.margin_delta_percent !== null}
              <span class="ml-2 text-xs font-medium {whatIfResult.scenario.margin_delta_percent < 0 ? 'text-red-600' : 'text-emerald-700'}">
                ({whatIfResult.scenario.margin_delta_percent > 0 ? "+" : ""}{whatIfResult.scenario.margin_delta_percent.toFixed(2)} pts)
              </span>
            {/if}
          </p>
        </div>
      </div>
    {/if}
  </section>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        stroke-width="1.5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
        />
      </svg>
      <input
        type="text"
        placeholder="Search period, department, position, source..."
        value={searchQuery}
        oninput={(e) => handleSearch(e.currentTarget.value)}
        class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </div>

    <select
      value={filterYear}
      onchange={(e) => {
        filterYear = e.currentTarget.value;
        currentPage = 1;
        fetchBudgets();
        fetchSummary();
      }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Years</option>
      {#each [2024, 2025, 2026, 2027, 2028] as y}
        <option value={String(y)}>FY {y}</option>
      {/each}
    </select>

    <select
      value={filterBudgetSource}
      onchange={(e) => {
        filterBudgetSource = e.currentTarget.value;
        currentPage = 1;
        fetchBudgets();
      }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Budget Sources</option>
      {#each budgetSources as source}
        <option value={source}>{budgetSourceLabels[source]}</option>
      {/each}
    </select>

    <select
      value={filterCurrency}
      onchange={(e) => {
        filterCurrency = e.currentTarget.value;
        currentPage = 1;
        fetchBudgets();
        fetchSummary();
      }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Currencies</option>
      {#each currencyOptions as option}
        <option value={option.code}>{option.code} - {option.label}</option>
      {/each}
    </select>

    <select
      value={filterStatus}
      onchange={(e) => {
        filterStatus = e.currentTarget.value;
        currentPage = 1;
        fetchBudgets();
      }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [key, label]}
        <option value={key}>{label}</option>
      {/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if budgets.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">
        {searchQuery || filterStatus || filterBudgetSource || filterCurrency
          ? "No budget records match your filters"
          : "No budget records yet"}
      </p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="px-3 py-3 text-center font-medium text-neutral-500 text-xs uppercase tracking-wider"> </th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Fiscal Period</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Budget Source</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Currency</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Approved</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">
              Total Headcount Budget
            </th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each budgets as budget}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-3 py-3.5 text-center">
                <button
                  type="button"
                  class="rounded p-1 text-neutral-500 hover:bg-neutral-200/70 hover:text-neutral-800 transition-colors"
                  aria-label={isBudgetExpanded(budget.id) ? "Collapse budget row" : "Expand budget row"}
                  onclick={() => toggleBudgetExpansion(budget.id)}
                >
                  <svg
                    class="h-4 w-4 transition-transform {isBudgetExpanded(budget.id) ? 'rotate-90' : ''}"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="2"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="m9 5 7 7-7 7" />
                  </svg>
                </button>
              </td>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{budget.department_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{budget.position_title ?? "All positions"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{budget.fiscal_period_label || `FY ${budget.fiscal_year}`}</td>
              <td class="px-5 py-3.5 text-neutral-600">{budget.budget_source_display}</td>
              <td class="px-5 py-3.5 text-center font-mono text-xs text-neutral-500">{budget.currency}</td>
              <td class="px-5 py-3.5 text-center text-neutral-700 font-medium">{budget.approved_headcount}</td>
              <td class="px-5 py-3.5 text-right text-neutral-700">{formatByCurrency(budget.budget_amount, budget.currency)}</td>
              <td class="px-5 py-3.5 text-center">
                <StatusBadge status={budget.status} label={statusLabels[budget.status] ?? budget.status} />
                <button
                  type="button"
                  onclick={() => openEdit(budget)}
                  class="mt-1 inline-flex text-[11px] font-semibold text-blue-700 hover:text-blue-800"
                >
                  {budget.status === "approved" || budget.status === "frozen" ? "Revise" : "Edit"}
                </button>
              </td>
            </tr>
            {#if isBudgetExpanded(budget.id)}
              <tr class="bg-neutral-50/60">
                <td colspan={9} class="px-5 py-4">
                  <div class="grid gap-3 md:grid-cols-2">
                    <section class="rounded-lg border border-neutral-200 bg-white p-3">
                      <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Position Financials</h3>
                      <div class="mt-2 text-xs text-neutral-600 space-y-1">
                        <p class="text-neutral-800">
                          {#if budget.base_salary_mid}
                            Base band: {formatByCurrency(budget.base_salary_min ?? budget.base_salary_mid, budget.salary_band_currency)} /
                            {formatByCurrency(budget.base_salary_mid, budget.salary_band_currency)} /
                            {formatByCurrency(budget.base_salary_max ?? budget.base_salary_mid, budget.salary_band_currency)}
                          {:else}
                            Base band: Not linked
                          {/if}
                        </p>
                        <p>FTE {budget.fte} · Multiplier {budget.burden_multiplier ?? "1.0000"}</p>
                        <p>
                          Statutory {formatPercent(budget.statutory_benefits_rate)}
                          · Allowances {formatPercent(budget.allowances_rate)}
                          · Local Tax {formatPercent(budget.local_tax_rate)}
                          · Insurance {formatPercent(budget.insurance_rate)}
                        </p>
                        <p class="font-medium text-neutral-700">
                          Fully burdened: {budget.fully_burdened_cost
                            ? formatByCurrency(budget.fully_burdened_cost, budget.salary_band_currency || budget.currency)
                            : "Not available"}
                        </p>
                        {#if budget.statutory_benefits_cost || budget.allowances_cost || budget.local_tax_cost || budget.insurance_cost}
                          <p class="text-neutral-500">
                            + Statutory {budget.statutory_benefits_cost
                              ? formatByCurrency(budget.statutory_benefits_cost, budget.salary_band_currency || budget.currency)
                              : "—"}
                            · Allowances {budget.allowances_cost
                              ? formatByCurrency(budget.allowances_cost, budget.salary_band_currency || budget.currency)
                              : "—"}
                            · Tax {budget.local_tax_cost
                              ? formatByCurrency(budget.local_tax_cost, budget.salary_band_currency || budget.currency)
                              : "—"}
                            · Insurance {budget.insurance_cost
                              ? formatByCurrency(budget.insurance_cost, budget.salary_band_currency || budget.currency)
                              : "—"}
                          </p>
                        {/if}
                      </div>
                    </section>
                    <section class="rounded-lg border border-neutral-200 bg-white p-3">
                      <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Headcount Breakdown</h3>
                      <div class="mt-3 grid grid-cols-3 gap-3">
                        <div class="rounded-md border border-neutral-200 p-2 text-center">
                          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Filled</p>
                          <p class="mt-1 text-base font-semibold text-neutral-900">{budget.filled_headcount}</p>
                        </div>
                        <div class="rounded-md border border-neutral-200 p-2 text-center">
                          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Open</p>
                          <p class="mt-1 text-base font-semibold text-neutral-900">{openHeadcountCount(budget)}</p>
                        </div>
                        <div class="rounded-md border border-neutral-200 p-2 text-center">
                          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Variance</p>
                          <p class="mt-1 text-base font-semibold {budget.variance > 0 ? 'text-neutral-900' : budget.variance < 0 ? 'text-red-600' : 'text-neutral-400'}">
                            {budget.variance > 0 ? "+" : ""}{budget.variance}
                          </p>
                        </div>
                      </div>
                    </section>
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>

    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} record{totalCount !== 1 ? "s" : ""}</span>
        <div class="flex items-center gap-1">
          <button
            onclick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &laquo;
          </button>
          {#each Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1) as page}
            <button
              onclick={() => goToPage(page)}
              class="px-2.5 py-1 rounded text-sm {page === currentPage ? 'bg-neutral-900 text-white' : 'hover:bg-neutral-100'}"
            >
              {page}
            </button>
          {/each}
          <button
            onclick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
            class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed"
          >
            &raquo;
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>

{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button
      class="absolute inset-0 bg-black/30 backdrop-blur-sm"
      onclick={() => {
        showSlideOver = false;
        resetForm();
      }}
      aria-label="Close"
    ></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">
          {#if isEditing && revisionMode}
            Submit Budget Revision
          {:else if isEditing}
            Edit Budget
          {:else}
            Create Budget
          {/if}
        </h2>
        <button
          onclick={() => {
            showSlideOver = false;
            resetForm();
          }}
          class="p-1 rounded hover:bg-neutral-100"
        >
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if revisionMode}
          <div class="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-xs text-blue-900">
            This budget is approved/frozen. Changes will be submitted as a formal revision request for approval.
          </div>
        {/if}

        <div>
          <label for="bud-dept" class="block text-sm font-medium text-neutral-700 mb-1">
            Department <span class="text-red-500">*</span>
          </label>
          <select
            id="bud-dept"
            bind:value={form.department}
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="">Select department</option>
            {#each departmentOptions as dept}
              <option value={String(dept.id)}>{dept.name}</option>
            {/each}
          </select>
          {#if fieldError("department")}
            <p class="mt-1 text-xs text-red-600">{fieldError("department")}</p>
          {/if}
        </div>

        <div>
          <label for="bud-position" class="block text-sm font-medium text-neutral-700 mb-1">Position Slot</label>
          <select
            id="bud-position"
            bind:value={form.position}
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="">All positions (department envelope)</option>
            {#each positionOptions as position}
              <option value={String(position.id)}>{position.title} ({position.code})</option>
            {/each}
          </select>
          {#if fieldError("position")}
            <p class="mt-1 text-xs text-red-600">{fieldError("position")}</p>
          {/if}
        </div>

        <div>
          <label for="bud-period" class="block text-sm font-medium text-neutral-700 mb-1">Fiscal Period</label>
          <input
            id="bud-period"
            type="text"
            bind:value={form.fiscal_period_label}
            placeholder="Q1 2026 or Zion Estate Project Phase 1"
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
          {#if fieldError("fiscal_period_label")}
            <p class="mt-1 text-xs text-red-600">{fieldError("fiscal_period_label")}</p>
          {/if}
        </div>

        <div>
          <label for="bud-fy" class="block text-sm font-medium text-neutral-700 mb-1">
            Fiscal Year <span class="text-red-500">*</span>
          </label>
          <input
            id="bud-fy"
            type="number"
            bind:value={form.fiscal_year}
            min={2020}
            max={2035}
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 font-mono"
          />
          {#if fieldError("fiscal_year")}
            <p class="mt-1 text-xs text-red-600">{fieldError("fiscal_year")}</p>
          {/if}
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="bud-source" class="block text-sm font-medium text-neutral-700 mb-1">
              Budget Source <span class="text-red-500">*</span>
            </label>
            <select
              id="bud-source"
              bind:value={form.budget_source}
              class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              {#each budgetSources as source}
                <option value={source}>{budgetSourceLabels[source]}</option>
              {/each}
            </select>
            {#if fieldError("budget_source")}
              <p class="mt-1 text-xs text-red-600">{fieldError("budget_source")}</p>
            {/if}
          </div>
          <div>
            <label for="bud-currency" class="block text-sm font-medium text-neutral-700 mb-1">
              Currency <span class="text-red-500">*</span>
            </label>
            <select
              id="bud-currency"
              bind:value={form.currency}
              class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              {#each currencyOptions as option}
                <option value={option.code}>{option.code} - {option.label}</option>
              {/each}
            </select>
            {#if fieldError("currency")}
              <p class="mt-1 text-xs text-red-600">{fieldError("currency")}</p>
            {/if}
          </div>
        </div>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50/60 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Position-Level Financial Inputs</p>
          <div class="mt-3 grid grid-cols-2 gap-3 md:grid-cols-5">
            <div>
              <label for="bud-fte" class="block text-xs font-medium text-neutral-700 mb-1">FTE</label>
              <input
                id="bud-fte"
                type="number"
                min={0.1}
                max={2}
                step={0.1}
                bind:value={form.fte}
                class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
              {#if fieldError("fte")}
                <p class="mt-1 text-xs text-red-600">{fieldError("fte")}</p>
              {/if}
            </div>
            <div>
              <label for="bud-statutory" class="block text-xs font-medium text-neutral-700 mb-1">Statutory %</label>
              <input
                id="bud-statutory"
                type="number"
                min={0}
                max={100}
                step={0.1}
                bind:value={form.statutory_benefits_rate}
                class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
              {#if fieldError("statutory_benefits_rate")}
                <p class="mt-1 text-xs text-red-600">{fieldError("statutory_benefits_rate")}</p>
              {/if}
            </div>
            <div>
              <label for="bud-allowances" class="block text-xs font-medium text-neutral-700 mb-1">Allowances %</label>
              <input
                id="bud-allowances"
                type="number"
                min={0}
                max={100}
                step={0.1}
                bind:value={form.allowances_rate}
                class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
              {#if fieldError("allowances_rate")}
                <p class="mt-1 text-xs text-red-600">{fieldError("allowances_rate")}</p>
              {/if}
            </div>
            <div>
              <label for="bud-local-tax" class="block text-xs font-medium text-neutral-700 mb-1">Local Tax %</label>
              <input
                id="bud-local-tax"
                type="number"
                min={0}
                max={100}
                step={0.1}
                bind:value={form.local_tax_rate}
                class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
              {#if fieldError("local_tax_rate")}
                <p class="mt-1 text-xs text-red-600">{fieldError("local_tax_rate")}</p>
              {/if}
            </div>
            <div>
              <label for="bud-insurance" class="block text-xs font-medium text-neutral-700 mb-1">Insurance %</label>
              <input
                id="bud-insurance"
                type="number"
                min={0}
                max={100}
                step={0.1}
                bind:value={form.insurance_rate}
                class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
              {#if fieldError("insurance_rate")}
                <p class="mt-1 text-xs text-red-600">{fieldError("insurance_rate")}</p>
              {/if}
            </div>
          </div>
          <p class="mt-2 text-xs text-neutral-600">
            Automation multiplier: <span class="font-semibold text-neutral-800">{burdenMultiplierPreview}x</span>
            (Base Salary x Multiplier x FTE)
          </p>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="bud-approved" class="block text-sm font-medium text-neutral-700 mb-1">Approved Headcount</label>
            <input
              id="bud-approved"
              type="number"
              min={0}
              bind:value={form.approved_headcount}
              class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
            />
          </div>
          <div>
            <label for="bud-filled" class="block text-sm font-medium text-neutral-700 mb-1">Filled Headcount</label>
            <input
              id="bud-filled"
              type="number"
              min={0}
              bind:value={form.filled_headcount}
              class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
            />
          </div>
        </div>

        <div>
          <label for="bud-amount" class="block text-sm font-medium text-neutral-700 mb-1">Total Headcount Budget</label>
          <input
            id="bud-amount"
            type="text"
            bind:value={form.budget_amount}
            placeholder="0.00"
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 font-mono"
          />
          {#if fieldError("budget_amount")}
            <p class="mt-1 text-xs text-red-600">{fieldError("budget_amount")}</p>
          {/if}
        </div>

        <div>
          <label for="bud-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
          <select
            id="bud-status"
            bind:value={form.status}
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            {#each Object.entries(statusLabels) as [key, label]}
              <option value={key}>{label}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="bud-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea
            id="bud-notes"
            bind:value={form.notes}
            rows={3}
            class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
          ></textarea>
        </div>

        {#if revisionMode}
          <div>
            <label for="bud-revision-reason" class="block text-sm font-medium text-neutral-700 mb-1">
              Revision Reason <span class="text-red-500">*</span>
            </label>
            <textarea
              id="bud-revision-reason"
              bind:value={revisionReason}
              rows={3}
              placeholder="Explain why this approved budget needs revision."
              class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
            ></textarea>
            {#if fieldError("reason")}
              <p class="mt-1 text-xs text-red-600">{fieldError("reason")}</p>
            {/if}
          </div>
        {/if}
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button
            onclick={devFillBudget}
            class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto"
          >
            Dev Fill
          </button>
        {/if}
        <button
          onclick={() => {
            showSlideOver = false;
            resetForm();
          }}
          class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto"
        >
          Cancel
        </button>
        <button
          onclick={handleSave}
          disabled={saving}
          class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {#if saving}
            Saving...
          {:else if isEditing && revisionMode}
            Submit Revision
          {:else if isEditing}
            Update
          {:else}
            Create
          {/if}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }

  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>

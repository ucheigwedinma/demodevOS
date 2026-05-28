<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    BudgetListItem,
    BudgetOverview,
    PaginatedResponse,
  } from "$lib/types";

  let loading = $state(true);
  let data = $state<BudgetListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let periodFilter = $state("");
  let sortValue = $state("-start_date");

  let overview = $state<BudgetOverview | null>(null);

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  let debounceTimer: ReturnType<typeof setTimeout>;

  async function fetchBudgets() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        ordering: sortValue,
      };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (periodFilter) params.period_type = periodFilter;

      const res = await api.get<PaginatedResponse<BudgetListItem>>(
        "/finance/budgets/",
        params
      );
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
    } finally {
      loading = false;
    }
  }

  async function fetchOverview() {
    try {
      overview = await api.get<BudgetOverview>("/finance/budgets/overview/");
    } catch {
      overview = null;
    }
  }

  function handleSearch(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    searchQuery = val;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchBudgets();
    }, 300);
  }

  function handleStatusFilter(e: Event) {
    statusFilter = (e.target as HTMLSelectElement).value;
    currentPage = 1;
    fetchBudgets();
  }

  function handlePeriodFilter(e: Event) {
    periodFilter = (e.target as HTMLSelectElement).value;
    currentPage = 1;
    fetchBudgets();
  }

  function handleSort(e: Event) {
    sortValue = (e.target as HTMLSelectElement).value;
    currentPage = 1;
    fetchBudgets();
  }

  function goToPage(p: number) {
    currentPage = p;
    fetchBudgets();
  }

  function formatCurrency(val: string | number): string {
    return currency.formatCompact(val);
  }

  function pctColor(pct: number, warningPct: number, tolerancePct: number): string {
    const exceededThreshold = 100 + tolerancePct;
    if (pct >= exceededThreshold) return "bg-red-500";
    if (pct >= warningPct) return "bg-amber-500";
    return "bg-neutral-800";
  }


  function periodLabel(pt: string): string {
    switch (pt) {
      case "annual": return "Annual";
      case "quarterly": return "Quarterly";
      case "monthly": return "Monthly";
      default: return pt;
    }
  }

  onMount(() => {
    fetchBudgets();
    fetchOverview();
  });
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Finance</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Budgets</h1>
      <p class="text-sm text-neutral-500 mt-1">Track financial budgets against actual spending</p>
    </div>
    <a
      href="/finance/budgets/new"
      class="inline-flex items-center gap-2 rounded-lg bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Budget
    </a>
  </div>

  <!-- KPI Strip -->
  {#if overview}
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
      <div class="bg-white rounded-xl border border-neutral-200 p-4 min-w-0">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Total Budgets</p>
        <p class="text-base sm:text-lg font-bold text-neutral-800 mt-1 leading-tight wrap-break-word">{overview.active_budgets}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4 min-w-0">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Total Budgeted</p>
        <p class="text-base sm:text-lg font-bold text-neutral-800 mt-1 leading-tight wrap-break-word">{formatCurrency(overview.total_budgeted)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4 min-w-0">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Total Spent</p>
        <p class="text-base sm:text-lg font-bold text-neutral-800 mt-1 leading-tight wrap-break-word">{formatCurrency(overview.total_spent)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4 min-w-0">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Overall Used</p>
        <p class="text-base sm:text-lg font-bold text-neutral-800 mt-1 leading-tight wrap-break-word">{Number(overview.pct_used).toFixed(1)}%</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4 min-w-0">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Warnings</p>
        <p class="text-base sm:text-lg font-bold text-amber-600 mt-1 leading-tight wrap-break-word">{overview.warning_count}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4 min-w-0">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Exceeded</p>
        <p class="text-base sm:text-lg font-bold text-red-600 mt-1 leading-tight wrap-break-word">{overview.exceeded_count}</p>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    <div class="px-5 py-4 border-b border-neutral-100 flex flex-wrap gap-3 items-center">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          type="text"
          placeholder="Search budgets..."
          value={searchQuery}
          oninput={handleSearch}
          class="w-full pl-9 pr-3 py-2 rounded-lg border border-neutral-200 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
      </div>

      <select onchange={handleStatusFilter} value={statusFilter} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
        <option value="">All Statuses</option>
        <option value="draft">Draft</option>
        <option value="active">Active</option>
        <option value="closed">Closed</option>
      </select>

      <select onchange={handlePeriodFilter} value={periodFilter} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
        <option value="">All Periods</option>
        <option value="annual">Annual</option>
        <option value="quarterly">Quarterly</option>
        <option value="monthly">Monthly</option>
      </select>

      <select onchange={handleSort} value={sortValue} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
        <option value="-start_date">Newest First</option>
        <option value="start_date">Oldest First</option>
        <option value="name">Name A-Z</option>
        <option value="-name">Name Z-A</option>
        <option value="-total_amount">Highest Budget</option>
      </select>
    </div>

    <!-- Table -->
    {#if loading}
      <div class="py-20 text-center text-sm text-neutral-400">Loading...</div>
    {:else if data.length === 0}
      <div class="py-20 text-center">
        <svg class="mx-auto w-10 h-10 text-neutral-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
        </svg>
        <p class="text-sm text-neutral-500">No budgets found</p>
        <a href="/finance/budgets/new" class="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-neutral-800 hover:underline">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Create your first budget
        </a>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 text-left">
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Name</th>
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Period</th>
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Status</th>
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Budgeted</th>
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Spent</th>
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide w-40">% Used</th>
              <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Lines</th>
            </tr>
          </thead>
          <tbody>
            {#each data as budget (budget.id)}
              {@const pct = Number(budget.pct_used)}
              {@const warningPct = Number(budget.warning_threshold_pct)}
              {@const tolerancePct = Number(budget.overspend_tolerance_pct)}
              <tr class="border-b border-neutral-50 hover:bg-neutral-50/50 transition-colors">
                <td class="px-5 py-3.5">
                  <a href="/finance/budgets/{budget.id}" class="font-medium text-neutral-800 hover:underline">
                    {budget.name}
                  </a>
                  <p class="text-xs text-neutral-400 mt-0.5">
                    {new Date(budget.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    &ndash;
                    {new Date(budget.end_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </p>
                </td>
                <td class="px-5 py-3.5 text-neutral-600">{periodLabel(budget.period_type)}</td>
                <td class="px-5 py-3.5">
                  <StatusBadge status={budget.status} />
                </td>
                <td class="px-5 py-3.5 text-right font-medium text-neutral-800 tabular-nums">{formatCurrency(budget.total_amount)}</td>
                <td class="px-5 py-3.5 text-right font-medium text-neutral-800 tabular-nums">{formatCurrency(budget.total_spent)}</td>
                <td class="px-5 py-3.5">
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all {pctColor(pct, warningPct, tolerancePct)}"
                        style="width: {Math.min(pct, 100)}%"
                      ></div>
                    </div>
                    <span class="text-xs font-medium text-neutral-600 tabular-nums w-12 text-right">{pct.toFixed(1)}%</span>
                  </div>
                </td>
                <td class="px-5 py-3.5 text-right text-neutral-500">{budget.line_item_count}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {#if totalPages > 1}
        <div class="px-5 py-4 border-t border-neutral-100 flex items-center justify-between">
          <p class="text-sm text-neutral-500">
            Showing {startItem} to {endItem} of {totalCount}
          </p>
          <div class="flex gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              class="px-3 py-1.5 rounded-lg border border-neutral-200 text-sm font-medium transition-colors hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            {#each Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              if (totalPages <= 7) return i + 1;
              if (currentPage <= 4) return i + 1;
              if (currentPage >= totalPages - 3) return totalPages - 6 + i;
              return currentPage - 3 + i;
            }) as p}
              <button
                onclick={() => goToPage(p)}
                class="w-9 h-9 rounded-lg text-sm font-medium transition-colors
                       {p === currentPage ? 'bg-neutral-800 text-white' : 'hover:bg-neutral-50 text-neutral-600'}"
              >
                {p}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              class="px-3 py-1.5 rounded-lg border border-neutral-200 text-sm font-medium transition-colors hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>

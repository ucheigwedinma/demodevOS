<script lang="ts">
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import type { BudgetListItem, PaginatedResponse } from "$lib/types";

  let loading = $state(true);
  let budgets = $state<BudgetListItem[]>([]);
  let error = $state("");

  function toAmount(value: string | number): number {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function varianceAmount(budget: BudgetListItem): number {
    return toAmount(budget.total_amount) - toAmount(budget.total_spent);
  }

  function variancePct(budget: BudgetListItem): number {
    const total = toAmount(budget.total_amount);
    if (total <= 0) return 0;
    return (varianceAmount(budget) / total) * 100;
  }

  function varianceTone(value: number): string {
    if (value < 0) return "text-red-600";
    if (value > 0) return "text-emerald-600";
    return "text-neutral-600";
  }

  const totalVariance = $derived(
    budgets.reduce((sum, budget) => sum + varianceAmount(budget), 0)
  );
  const overspentCount = $derived(
    budgets.filter((budget) => varianceAmount(budget) < 0).length
  );

  async function fetchVariance() {
    loading = true;
    error = "";
    try {
      const response = await api.get<PaginatedResponse<BudgetListItem>>(
        "/finance/budgets/",
        {
          ordering: "-updated_at",
          page_size: "100",
        }
      );
      budgets = response.results;
    } catch {
      budgets = [];
      error = "Failed to load variance analysis.";
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchVariance();
  });
</script>

<div>
  <div class="flex items-start justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-neutral-800">Variance Analysis</h1>
      <p class="text-sm text-neutral-500 mt-1">
        Compare project budget allocations against tracked spend.
      </p>
    </div>
    <a
      href="/finance/budgets"
      class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
    >
      Open Budgets
    </a>
  </div>

  <div class="grid grid-cols-1 gap-4 md:grid-cols-3 mb-6">
    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Tracked Budgets</p>
      <p class="mt-1 text-2xl font-bold text-neutral-800">{budgets.length}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Total Variance</p>
      <p class="mt-1 text-2xl font-bold {varianceTone(totalVariance)}">
        {currency.formatCompact(totalVariance)}
      </p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <p class="text-xs font-medium uppercase tracking-wide text-neutral-500">Overspent Budgets</p>
      <p class="mt-1 text-2xl font-bold text-red-600">{overspentCount}</p>
    </div>
  </div>

  <div class="overflow-x-auto rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="py-16 text-center text-sm text-neutral-500">Loading variance data...</div>
    {:else if error}
      <div class="py-16 text-center text-sm text-red-600">{error}</div>
    {:else if budgets.length === 0}
      <div class="py-16 text-center text-sm text-neutral-500">No budgets available for analysis.</div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 text-left">
            <th class="px-5 py-3 font-semibold text-xs uppercase tracking-wide text-neutral-500">Budget</th>
            <th class="px-5 py-3 font-semibold text-xs uppercase tracking-wide text-neutral-500 text-right">Budgeted</th>
            <th class="px-5 py-3 font-semibold text-xs uppercase tracking-wide text-neutral-500 text-right">Spent</th>
            <th class="px-5 py-3 font-semibold text-xs uppercase tracking-wide text-neutral-500 text-right">Variance</th>
            <th class="px-5 py-3 font-semibold text-xs uppercase tracking-wide text-neutral-500 text-right">Variance %</th>
          </tr>
        </thead>
        <tbody>
          {#each budgets as budget (budget.id)}
            {@const variance = varianceAmount(budget)}
            {@const variancePercent = variancePct(budget)}
            <tr class="border-b border-neutral-50">
              <td class="px-5 py-3.5">
                <a href="/finance/budgets/{budget.id}" class="font-medium text-neutral-800 hover:underline">
                  {budget.name}
                </a>
              </td>
              <td class="px-5 py-3.5 text-right tabular-nums text-neutral-800">
                {currency.formatCompact(budget.total_amount)}
              </td>
              <td class="px-5 py-3.5 text-right tabular-nums text-neutral-800">
                {currency.formatCompact(budget.total_spent)}
              </td>
              <td class="px-5 py-3.5 text-right tabular-nums font-semibold {varianceTone(variance)}">
                {currency.formatCompact(variance)}
              </td>
              <td class="px-5 py-3.5 text-right tabular-nums {varianceTone(variance)}">
                {variancePercent.toFixed(1)}%
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

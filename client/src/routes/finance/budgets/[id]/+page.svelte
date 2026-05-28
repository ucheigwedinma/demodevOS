<script lang="ts">
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { BudgetDetail, ReforecastSuggestion, PaginatedResponse } from "$lib/types";

  let loading = $state(true);
  let budget = $state<BudgetDetail | null>(null);
  let reforecasts = $state<ReforecastSuggestion[]>([]);
  let generatingReforecast = $state(false);
  let approvingId = $state<number | null>(null);
  let rejectingId = $state<number | null>(null);

  const budgetId = $derived($page.params.id);

  async function fetchBudget() {
    loading = true;
    try {
      budget = await api.get<BudgetDetail>(`/finance/budgets/${budgetId}/`);
    } catch {
      budget = null;
      toast.error("Failed to load budget.");
    } finally {
      loading = false;
    }
  }

  async function fetchReforecasts() {
    try {
      const res = await api.get<PaginatedResponse<ReforecastSuggestion>>(
        `/finance/budgets/${budgetId}/reforecasts/`
      );
      reforecasts = res.results;
    } catch {
      reforecasts = [];
    }
  }

  async function generateReforecast() {
    generatingReforecast = true;
    try {
      await api.post(`/finance/budgets/${budgetId}/generate-reforecast/`, {});
      toast.success("Reforecast suggestion generated.");
      await fetchReforecasts();
    } catch (err) {
      if (err instanceof ApiError) {
        const msgs = Object.values(err.fieldErrors).flat();
        toast.error(msgs.join(", ") || "Failed to generate reforecast.");
      } else {
        toast.error("Failed to generate reforecast.");
      }
    } finally {
      generatingReforecast = false;
    }
  }

  async function approveReforecast(rfId: number) {
    approvingId = rfId;
    try {
      await api.post(`/finance/budgets/${budgetId}/reforecasts/${rfId}/approve/`, {});
      toast.success("Reforecast approved and applied.");
      await Promise.all([fetchBudget(), fetchReforecasts()]);
    } catch {
      toast.error("Failed to approve reforecast.");
    } finally {
      approvingId = null;
    }
  }

  async function rejectReforecast(rfId: number) {
    rejectingId = rfId;
    try {
      await api.post(`/finance/budgets/${budgetId}/reforecasts/${rfId}/reject/`, {});
      toast.success("Reforecast rejected.");
      await fetchReforecasts();
    } catch {
      toast.error("Failed to reject reforecast.");
    } finally {
      rejectingId = null;
    }
  }

  function formatCurrency(val: string | number): string {
    return currency.formatCompact(val);
  }

  function pctColor(pct: number, budget: BudgetDetail): string {
    const exceeded = 100 + Number(budget.overspend_tolerance_pct);
    const warning = Number(budget.warning_threshold_pct);
    if (pct >= exceeded) return "bg-red-500";
    if (pct >= warning) return "bg-amber-500";
    return "bg-neutral-900";
  }

  function pctTextColor(pct: number, budget: BudgetDetail): string {
    const exceeded = 100 + Number(budget.overspend_tolerance_pct);
    const warning = Number(budget.warning_threshold_pct);
    if (pct >= exceeded) return "text-red-600";
    if (pct >= warning) return "text-amber-600";
    return "text-neutral-600";
  }


  $effect(() => {
    fetchBudget();
    fetchReforecasts();
  });
</script>

{#if loading}
  <div class="py-20 text-center text-sm text-neutral-400">Loading...</div>
{:else if !budget}
  <div class="py-20 text-center">
    <p class="text-sm text-neutral-500">Budget not found.</p>
    <a href="/finance/budgets" class="mt-3 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to Budgets</a>
  </div>
{:else}
  {@const overallPct = Number(budget.pct_used)}
  {@const totalBudgeted = Number(budget.total_amount)}
  {@const totalSpent = Number(budget.total_spent)}
  {@const remaining = totalBudgeted - totalSpent}

  <div>
    <!-- Header -->
    <div class="mb-6">
      <a href="/finance/budgets" class="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-3">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
        Back to Budgets
      </a>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-neutral-900">{budget.name}</h1>
          <StatusBadge status={budget.status} />
        </div>
        {#if budget.status === "active"}
          <button
            onclick={generateReforecast}
            disabled={generatingReforecast}
            class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:opacity-50"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
            </svg>
            {generatingReforecast ? "Generating..." : "Suggest Reforecast"}
          </button>
        {/if}
      </div>
      <p class="text-sm text-neutral-500 mt-1">
        {budget.period_type.charAt(0).toUpperCase() + budget.period_type.slice(1)} &middot;
        {new Date(budget.start_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
        &ndash;
        {new Date(budget.end_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
      </p>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Total Budgeted</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1">{formatCurrency(totalBudgeted)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Total Spent</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1">{formatCurrency(totalSpent)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">Remaining</p>
        <p class="text-2xl font-bold mt-1 {remaining < 0 ? 'text-red-600' : 'text-neutral-900'}">{formatCurrency(remaining)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs text-neutral-500 uppercase tracking-wide font-medium">% Used</p>
        <p class="text-2xl font-bold mt-1 {pctTextColor(overallPct, budget)}">{overallPct.toFixed(1)}%</p>
        <div class="mt-2 h-2 rounded-full bg-neutral-100 overflow-hidden">
          <div
            class="h-full rounded-full transition-all {pctColor(overallPct, budget)}"
            style="width: {Math.min(overallPct, 100)}%"
          ></div>
        </div>
      </div>
    </div>

    <!-- Line Items Table -->
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden mb-6">
      <div class="px-5 py-4 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wide">Line Items</h2>
      </div>

      {#if budget.line_items.length === 0}
        <div class="py-12 text-center text-sm text-neutral-400">No line items</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100 text-left">
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Account</th>
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Department</th>
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Cost Center</th>
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Budgeted</th>
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Actual</th>
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Variance</th>
                <th class="px-5 py-3 font-semibold text-neutral-500 text-xs uppercase tracking-wide w-44">% Used</th>
              </tr>
            </thead>
            <tbody>
              {#each budget.line_items as li (li.id)}
                {@const pct = Number(li.pct_used)}
                {@const budgeted = Number(li.budgeted_amount)}
                {@const actual = Number(li.actual_spent)}
                {@const variance = budgeted - actual}
                <tr class="border-b border-neutral-50 hover:bg-neutral-50/50 transition-colors">
                  <td class="px-5 py-3.5">
                    <span class="font-medium text-neutral-900">{li.account_code}</span>
                    <span class="text-neutral-500 ml-1">{li.account_name}</span>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600">{li.department_name || "—"}</td>
                  <td class="px-5 py-3.5 text-neutral-600">{li.cost_center_name || "—"}</td>
                  <td class="px-5 py-3.5 text-right font-medium text-neutral-900 tabular-nums">{formatCurrency(budgeted)}</td>
                  <td class="px-5 py-3.5 text-right font-medium text-neutral-900 tabular-nums">{formatCurrency(actual)}</td>
                  <td class="px-5 py-3.5 text-right font-medium tabular-nums {variance < 0 ? 'text-red-600' : 'text-neutral-600'}">
                    {variance < 0 ? '-' : ''}{formatCurrency(Math.abs(variance))}
                  </td>
                  <td class="px-5 py-3.5">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                        <div
                          class="h-full rounded-full transition-all {pctColor(pct, budget)}"
                          style="width: {Math.min(pct, 100)}%"
                        ></div>
                      </div>
                      <span class="text-xs font-medium tabular-nums w-12 text-right {pctTextColor(pct, budget)}">{pct.toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <!-- Reforecast Suggestions -->
    {#if reforecasts.length > 0}
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100">
          <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wide">Reforecast Suggestions</h2>
        </div>

        {#each reforecasts as rf (rf.id)}
          <div class="border-b border-neutral-100 last:border-b-0">
            <div class="px-5 py-4 flex items-center justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-neutral-900">
                    {new Date(rf.generated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })}
                  </span>
                  <StatusBadge status={rf.status} />
                </div>
                <p class="text-xs text-neutral-500 mt-0.5">{rf.reason}</p>
              </div>
              {#if rf.status === "pending"}
                <div class="flex items-center gap-2">
                  <button
                    onclick={() => rejectReforecast(rf.id)}
                    disabled={rejectingId === rf.id}
                    class="px-3 py-1.5 rounded-lg border border-neutral-200 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-50"
                  >
                    {rejectingId === rf.id ? "..." : "Reject"}
                  </button>
                  <button
                    onclick={() => approveReforecast(rf.id)}
                    disabled={approvingId === rf.id}
                    class="px-3 py-1.5 rounded-lg bg-neutral-900 text-xs font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-50"
                  >
                    {approvingId === rf.id ? "Applying..." : "Approve & Apply"}
                  </button>
                </div>
              {/if}
            </div>

            <!-- Reforecast line items table -->
            {#if rf.line_items.length > 0}
              <div class="overflow-x-auto border-t border-neutral-50">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-neutral-50 text-left bg-neutral-50/50">
                      <th class="px-5 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Account</th>
                      <th class="px-5 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Current</th>
                      <th class="px-5 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Actual Spent</th>
                      <th class="px-5 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Suggested</th>
                      <th class="px-5 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide text-right">Delta</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each rf.line_items as rli (rli.id)}
                      {@const delta = Number(rli.delta)}
                      <tr class="border-b border-neutral-50">
                        <td class="px-5 py-2.5">
                          <span class="font-medium text-neutral-900">{rli.account_code}</span>
                          <span class="text-neutral-500 ml-1">{rli.account_name}</span>
                        </td>
                        <td class="px-5 py-2.5 text-right tabular-nums text-neutral-600">{formatCurrency(rli.current_amount)}</td>
                        <td class="px-5 py-2.5 text-right tabular-nums text-neutral-600">{formatCurrency(rli.actual_spent)}</td>
                        <td class="px-5 py-2.5 text-right tabular-nums font-medium text-neutral-900">{formatCurrency(rli.suggested_amount)}</td>
                        <td class="px-5 py-2.5 text-right tabular-nums font-medium {delta > 0 ? 'text-emerald-600' : delta < 0 ? 'text-red-600' : 'text-neutral-400'}">
                          {delta > 0 ? '+' : ''}{formatCurrency(delta)}
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}

    <!-- Notes -->
    {#if budget.notes}
      <div class="bg-white rounded-xl border border-neutral-200 p-5 mt-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wide mb-2">Notes</h2>
        <p class="text-sm text-neutral-600 whitespace-pre-wrap">{budget.notes}</p>
      </div>
    {/if}
  </div>
{/if}

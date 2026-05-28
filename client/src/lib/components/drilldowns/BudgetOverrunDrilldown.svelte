<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { BudgetOverrunDrilldown } from "$lib/types";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import DrilldownPanel from "./DrilldownPanel.svelte";

  // Budget overrun is evaluated against each active Budget's own period
  // boundaries (set on the Budget record) and lifetime line-item actuals.
  // The board-metrics date filter is accepted for prop-signature parity but
  // does not narrow this view — each budget brings its own window.
  let {
    startDate = "",
    endDate = "",
    onclose,
  }: {
    startDate?: string;
    endDate?: string;
    onclose: () => void;
  } = $props();

  let data = $state<BudgetOverrunDrilldown | null>(null);
  let loading = $state(true);

  const dateFilterActive = $derived(Boolean(startDate || endDate));

  async function load() {
    loading = true;
    try {
      data = await api.get<BudgetOverrunDrilldown>("/analytics/drilldowns/budget-overrun/");
    } catch {
      toast.error("Load failed", "Could not load budget overrun drilldown.");
    }
    loading = false;
  }

  $effect(() => { load(); });

  function fmtCurrency(v: string): string {
    return currency.formatCompact(v);
  }
</script>

<DrilldownPanel title="Budget Overrun Frequency — Detail" {loading} {onclose}>
  {#if data}
    <div class="space-y-6">
      {#if dateFilterActive}
        <div class="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2 text-[11px] text-amber-800">
          Overrun frequency is evaluated against each budget's own period — the date filter on Board Metrics does not apply here.
        </div>
      {/if}
      <!-- Summary -->
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Total Budgeted</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtCurrency(data.summary.total_budgeted)}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Total Actual</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtCurrency(data.summary.total_actual)}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Net Overrun</p>
          <p class="text-sm font-semibold tabular-nums {Number(data.summary.net_overrun) > 0 ? 'text-red-700' : 'text-emerald-700'}">{fmtCurrency(data.summary.net_overrun)}</p>
        </div>
      </div>

      <!-- Per-budget chart -->
      {#if data.per_budget.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Overrun Frequency by Budget (%)</h4>
          <BarChart
            data={data.per_budget.map(b => ({ label: b.name.slice(0, 16), value: b.frequency_pct }))}
            formatValue={(d: number) => `${d}%`}
            colors={["#f43f5e"]}
            height={220}
          />
        </div>
      {/if}

      <!-- Worst line items -->
      {#if data.worst_line_items.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Worst Offending Line Items</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100 text-left text-neutral-400">
                  <th class="pb-2 pr-4 font-medium">Budget</th>
                  <th class="pb-2 pr-4 font-medium">Account</th>
                  <th class="pb-2 pr-4 font-medium text-right">Budgeted</th>
                  <th class="pb-2 pr-4 font-medium text-right">Actual</th>
                  <th class="pb-2 font-medium text-right">Overrun</th>
                </tr>
              </thead>
              <tbody>
                {#each data.worst_line_items as item}
                  <tr class="border-b border-neutral-50">
                    <td class="py-2 pr-4 text-neutral-700 font-medium truncate max-w-[120px]">{item.budget_name}</td>
                    <td class="py-2 pr-4 text-neutral-600">{item.account_code} {item.account_name}</td>
                    <td class="py-2 pr-4 text-right tabular-nums text-neutral-600">{fmtCurrency(item.budgeted)}</td>
                    <td class="py-2 pr-4 text-right tabular-nums text-neutral-600">{fmtCurrency(item.actual)}</td>
                    <td class="py-2 text-right tabular-nums text-red-700 font-semibold">+{item.overrun_pct}%</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</DrilldownPanel>

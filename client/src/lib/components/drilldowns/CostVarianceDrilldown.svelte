<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { CostVarianceDrilldown } from "$lib/types";
  import HorizontalBarChart from "$lib/components/charts/HorizontalBarChart.svelte";
  import DrilldownPanel from "./DrilldownPanel.svelte";

  // Cost variance is a cumulative state on each active Project (planned vs.
  // actual spend across all phases), not a stream of date-stamped events.
  // The board-metrics date filter is accepted for prop-signature parity with
  // the other drilldowns but does not narrow this view — surface that to the
  // user when a filter is active.
  let {
    startDate = "",
    endDate = "",
    onclose,
  }: {
    startDate?: string;
    endDate?: string;
    onclose: () => void;
  } = $props();

  let data = $state<CostVarianceDrilldown | null>(null);
  let loading = $state(true);

  const dateFilterActive = $derived(Boolean(startDate || endDate));

  async function load() {
    loading = true;
    try {
      data = await api.get<CostVarianceDrilldown>("/analytics/drilldowns/cost-variance/");
    } catch {
      toast.error("Load failed", "Could not load cost variance drilldown.");
    }
    loading = false;
  }

  $effect(() => { load(); });

  function fmtCurrency(v: string): string {
    return currency.formatCompact(v);
  }
</script>

<DrilldownPanel title="Cost Variance per Project — Detail" {loading} {onclose}>
  {#if data}
    <div class="space-y-6">
      {#if dateFilterActive}
        <div class="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2 text-[11px] text-amber-800">
          Cost variance is a cumulative position across active projects — the date filter on Board Metrics does not apply here.
        </div>
      {/if}
      <!-- Summary -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Total Planned</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtCurrency(data.summary.total_planned)}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Total Actual</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtCurrency(data.summary.total_actual)}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Worst Variance</p>
          <p class="text-sm font-semibold tabular-nums {data.summary.worst_variance_pct > 0 ? 'text-red-700' : 'text-emerald-700'}">{data.summary.worst_variance_pct > 0 ? '+' : ''}{data.summary.worst_variance_pct}%</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Best Variance</p>
          <p class="text-sm font-semibold tabular-nums {data.summary.best_variance_pct > 0 ? 'text-red-700' : 'text-emerald-700'}">{data.summary.best_variance_pct > 0 ? '+' : ''}{data.summary.best_variance_pct}%</p>
        </div>
      </div>

      <!-- Chart -->
      {#if data.per_project.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Variance by Project (%)</h4>
          <HorizontalBarChart
            data={data.per_project.slice(0, 10).map(p => ({ label: p.name.slice(0, 20), value: Math.abs(p.variance_pct) }))}
            colors={data.per_project.slice(0, 10).map(p => p.variance_pct > 0 ? "#ef4444" : "#10b981")}
            height={Math.max(200, data.per_project.slice(0, 10).length * 36)}
          />
        </div>
      {/if}

      <!-- Over budget table -->
      {#if data.over_budget_projects.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Over-Budget Projects</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100 text-left text-neutral-400">
                  <th class="pb-2 pr-4 font-medium">Project</th>
                  <th class="pb-2 pr-4 font-medium text-right">Planned</th>
                  <th class="pb-2 pr-4 font-medium text-right">Actual</th>
                  <th class="pb-2 font-medium text-right">Variance</th>
                </tr>
              </thead>
              <tbody>
                {#each data.over_budget_projects as p}
                  <tr class="border-b border-neutral-50">
                    <td class="py-2 pr-4 text-neutral-700 font-medium">{p.name}</td>
                    <td class="py-2 pr-4 text-right tabular-nums text-neutral-600">{fmtCurrency(p.planned)}</td>
                    <td class="py-2 pr-4 text-right tabular-nums text-neutral-600">{fmtCurrency(p.actual)}</td>
                    <td class="py-2 text-right tabular-nums text-red-700 font-semibold">+{p.variance_pct}%</td>
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

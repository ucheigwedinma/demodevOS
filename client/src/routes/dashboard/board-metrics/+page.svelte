<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { AnalyticsHealth, BoardKpiSnapshot } from "$lib/types";
  import DataFreshnessIndicator from "$lib/components/DataFreshnessIndicator.svelte";
  import ProcurementCycleDrilldown from "$lib/components/drilldowns/ProcurementCycleDrilldown.svelte";
  import CostVarianceDrilldown from "$lib/components/drilldowns/CostVarianceDrilldown.svelte";
  import VendorReliabilityDrilldown from "$lib/components/drilldowns/VendorReliabilityDrilldown.svelte";
  import EmergencyPurchasesDrilldown from "$lib/components/drilldowns/EmergencyPurchasesDrilldown.svelte";
  import BudgetOverrunDrilldown from "$lib/components/drilldowns/BudgetOverrunDrilldown.svelte";
  import ApprovalTimeDrilldown from "$lib/components/drilldowns/ApprovalTimeDrilldown.svelte";
  import DateInput from "$lib/components/DateInput.svelte";

  let data = $state<BoardKpiSnapshot | null>(null);
  let health = $state<AnalyticsHealth | null>(null);
  let loading = $state(true);
  let startDate = $state("");
  let endDate = $state("");
  let activeDrilldown = $state<string | null>(null);

  type DrilldownKey =
    | "procurement_cycle"
    | "cost_variance"
    | "vendor_reliability"
    | "emergency_purchases"
    | "budget_overrun"
    | "approval_time";

  function toggleDrilldown(key: DrilldownKey) {
    activeDrilldown = activeDrilldown === key ? null : key;
  }

  function fmtNumber(n: number, digits = 2): string {
    return Number(n || 0).toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  async function fetchBoardKpis() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      data = await api.get<BoardKpiSnapshot>("/analytics/board-kpis/", params);
    } catch {
      data = null;
      toast.error("Load failed", "Could not load board metrics.");
    }
    loading = false;
  }

  async function fetchHealth() {
    try {
      health = await api.get<AnalyticsHealth>("/analytics/health/");
    } catch {
      // Silently fail — freshness is supplementary
    }
  }

  $effect(() => {
    fetchBoardKpis();
    fetchHealth();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Board Metrics</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Executive KPI board across procurement, budget control, delivery and approvals.
          <span class="font-semibold text-red-600">Click a card to drill down.</span>
        </p>
        {#if health}
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <DataFreshnessIndicator
              label="Board KPIs"
              status={health.board_kpis.status}
              ageHours={health.board_kpis.age_hours}
            />
            <DataFreshnessIndicator
              label="Portfolio"
              status={health.portfolio.status}
              ageHours={health.portfolio.age_hours}
            />
          </div>
        {/if}
      </div>
      <div class="flex flex-wrap items-end gap-3">
        <label class="text-xs text-neutral-600">
          Start
          <DateInput bind:value={startDate} />
        </label>
        <label class="text-xs text-neutral-600">
          End
          <DateInput bind:value={endDate} />
        </label>
        <button
          onclick={fetchBoardKpis}
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          Apply
        </button>
      </div>
    </div>

    {#if data}
      <div class="text-xs text-neutral-500">
        Reporting window: {data.period.start_date} - {data.period.end_date} ({data.period.days} days)
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <!-- Procurement Cycle Time -->
        <button
          onclick={() => toggleDrilldown("procurement_cycle")}
          class="rounded-xl border px-4 py-4 text-left transition-all cursor-pointer
            {activeDrilldown === 'procurement_cycle'
              ? 'border-cyan-400 bg-cyan-50 shadow-md ring-1 ring-cyan-300'
              : 'border-cyan-200 bg-cyan-50/60 hover:shadow-md hover:border-cyan-300'}"
        >
          <p class="text-[11px] font-semibold text-cyan-800 uppercase tracking-wider">Procurement Cycle Time</p>
          <p class="mt-1 text-2xl font-bold text-cyan-900 tabular-nums">{fmtNumber(data.kpis.procurement_cycle_time_days.value)} days</p>
          <p class="text-xs text-cyan-800/80">{data.kpis.procurement_cycle_time_days.sample_size} completed PO cycles</p>
        </button>

        <!-- Cost Variance -->
        <button
          onclick={() => toggleDrilldown("cost_variance")}
          class="rounded-xl border px-4 py-4 text-left transition-all cursor-pointer
            {activeDrilldown === 'cost_variance'
              ? 'border-violet-400 bg-violet-50 shadow-md ring-1 ring-violet-300'
              : 'border-violet-200 bg-violet-50/60 hover:shadow-md hover:border-violet-300'}"
        >
          <p class="text-[11px] font-semibold text-violet-800 uppercase tracking-wider">Cost Variance per Project</p>
          <p class="mt-1 text-2xl font-bold tabular-nums {data.kpis.cost_variance_per_project_pct.value > 0 ? 'text-red-700' : 'text-emerald-700'}">
            {data.kpis.cost_variance_per_project_pct.value > 0 ? "+" : ""}{fmtNumber(data.kpis.cost_variance_per_project_pct.value)}%
          </p>
          <p class="text-xs text-violet-800/80">
            {data.kpis.cost_variance_per_project_pct.over_budget_projects} of {data.kpis.cost_variance_per_project_pct.project_count} over budget
          </p>
        </button>

        <!-- Vendor Reliability -->
        <button
          onclick={() => toggleDrilldown("vendor_reliability")}
          class="rounded-xl border px-4 py-4 text-left transition-all cursor-pointer
            {activeDrilldown === 'vendor_reliability'
              ? 'border-emerald-400 bg-emerald-50 shadow-md ring-1 ring-emerald-300'
              : 'border-emerald-200 bg-emerald-50/60 hover:shadow-md hover:border-emerald-300'}"
        >
          <p class="text-[11px] font-semibold text-emerald-800 uppercase tracking-wider">Vendor Reliability Score</p>
          <p class="mt-1 text-2xl font-bold text-emerald-900 tabular-nums">{fmtNumber(data.kpis.vendor_reliability_score.value, 1)}/100</p>
          <p class="text-xs text-emerald-800/80">{data.kpis.vendor_reliability_score.vendor_count} active vendors</p>
        </button>

        <!-- Emergency Purchases -->
        <button
          onclick={() => toggleDrilldown("emergency_purchases")}
          class="rounded-xl border px-4 py-4 text-left transition-all cursor-pointer
            {activeDrilldown === 'emergency_purchases'
              ? 'border-amber-400 bg-amber-50 shadow-md ring-1 ring-amber-300'
              : 'border-amber-200 bg-amber-50/60 hover:shadow-md hover:border-amber-300'}"
        >
          <p class="text-[11px] font-semibold text-amber-800 uppercase tracking-wider">Emergency Purchases</p>
          <p class="mt-1 text-2xl font-bold text-amber-900 tabular-nums">{fmtNumber(data.kpis.emergency_purchases_pct.value)}%</p>
          <p class="text-xs text-amber-800/80">
            {data.kpis.emergency_purchases_pct.emergency_count} of {data.kpis.emergency_purchases_pct.total_requisitions} requisitions
          </p>
        </button>

        <!-- Budget Overrun -->
        <button
          onclick={() => toggleDrilldown("budget_overrun")}
          class="rounded-xl border px-4 py-4 text-left transition-all cursor-pointer
            {activeDrilldown === 'budget_overrun'
              ? 'border-rose-400 bg-rose-50 shadow-md ring-1 ring-rose-300'
              : 'border-rose-200 bg-rose-50/60 hover:shadow-md hover:border-rose-300'}"
        >
          <p class="text-[11px] font-semibold text-rose-800 uppercase tracking-wider">Budget Overrun Frequency</p>
          <p class="mt-1 text-2xl font-bold text-rose-900 tabular-nums">{fmtNumber(data.kpis.budget_overrun_frequency_pct.value)}%</p>
          <p class="text-xs text-rose-800/80">
            {data.kpis.budget_overrun_frequency_pct.overrun_items} of {data.kpis.budget_overrun_frequency_pct.tracked_items} tracked lines
          </p>
        </button>

        <!-- Approval Time -->
        <button
          onclick={() => toggleDrilldown("approval_time")}
          class="rounded-xl border px-4 py-4 text-left transition-all cursor-pointer
            {activeDrilldown === 'approval_time'
              ? 'border-indigo-400 bg-indigo-50 shadow-md ring-1 ring-indigo-300'
              : 'border-indigo-200 bg-indigo-50/60 hover:shadow-md hover:border-indigo-300'}"
        >
          <p class="text-[11px] font-semibold text-indigo-800 uppercase tracking-wider">Average Approval Time</p>
          <p class="mt-1 text-2xl font-bold text-indigo-900 tabular-nums">{fmtNumber(data.kpis.average_approval_time_hours.value)} hrs</p>
          <p class="text-xs text-indigo-800/80">{data.kpis.average_approval_time_hours.completed_workflows} completed workflows</p>
        </button>
      </div>

      <!-- Drilldown Panel -->
      {#if activeDrilldown === "procurement_cycle"}
        <ProcurementCycleDrilldown {startDate} {endDate} onclose={() => activeDrilldown = null} />
      {:else if activeDrilldown === "cost_variance"}
        <CostVarianceDrilldown {startDate} {endDate} onclose={() => activeDrilldown = null} />
      {:else if activeDrilldown === "vendor_reliability"}
        <VendorReliabilityDrilldown {startDate} {endDate} onclose={() => activeDrilldown = null} />
      {:else if activeDrilldown === "emergency_purchases"}
        <EmergencyPurchasesDrilldown {startDate} {endDate} onclose={() => activeDrilldown = null} />
      {:else if activeDrilldown === "budget_overrun"}
        <BudgetOverrunDrilldown {startDate} {endDate} onclose={() => activeDrilldown = null} />
      {:else if activeDrilldown === "approval_time"}
        <ApprovalTimeDrilldown {startDate} {endDate} onclose={() => activeDrilldown = null} />
      {/if}
    {:else}
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-8 text-center">
        <p class="text-sm text-neutral-500">No board metrics are available for this filter range.</p>
      </div>
    {/if}
  </div>
{/if}

<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface ProjectSummary { id: number; name: string; start_date: string | null; target_end_date: string | null; budget: string | null; }
  interface TradeBreakdown { project: string; headcount: number; }
  interface TradeSummary { trade: string; total_headcount: number; project_breakdown: TradeBreakdown[]; project_count: number; }
  interface EquipmentConflict { equipment: string; project_a: string; dates_a: string; project_b: string; dates_b: string; }
  interface Alert { type: string; severity: string; message: string; trade?: string; equipment?: string; projects: string[]; }
  interface OptimizationData {
    projects: ProjectSummary[];
    trade_summary: TradeSummary[];
    equipment_conflicts: EquipmentConflict[];
    alerts: Alert[];
  }

  let loading = $state(true);
  let data = $state<OptimizationData | null>(null);

  const criticalAlerts = $derived(data?.alerts.filter(a => a.severity === "critical") || []);
  const warningAlerts = $derived(data?.alerts.filter(a => a.severity === "warning") || []);
  const totalHeadcount = $derived(data?.trade_summary.reduce((s, t) => s + t.total_headcount, 0) || 0);
  const totalTrades = $derived(data?.trade_summary.length || 0);
  const totalProjects = $derived(data?.projects.length || 0);
  const totalConflicts = $derived(data?.equipment_conflicts.length || 0);

  // Heatmap: trade × project matrix
  const heatmapProjects = $derived.by(() => {
    if (!data) return [] as string[];
    const names = new Set<string>();
    for (const ts of data.trade_summary) {
      for (const pb of ts.project_breakdown) names.add(pb.project);
    }
    return [...names].sort();
  });

  function getHeatmapValue(trade: TradeSummary, projectName: string): number {
    const entry = trade.project_breakdown.find(p => p.project === projectName);
    return entry?.headcount || 0;
  }

  function heatmapColor(value: number, max: number): string {
    if (value === 0) return "bg-neutral-50 text-neutral-300";
    const intensity = max > 0 ? value / max : 0;
    if (intensity > 0.7) return "bg-red-100 text-red-800 font-bold";
    if (intensity > 0.4) return "bg-amber-100 text-amber-800 font-semibold";
    return "bg-emerald-50 text-emerald-700";
  }

  const maxHeadcount = $derived(
    data ? Math.max(...data.trade_summary.flatMap(t => t.project_breakdown.map(p => p.headcount)), 1) : 1
  );

  async function loadData() {
    loading = true;
    try {
      data = await api.get<OptimizationData>("/projects/resource-optimization/");
    } catch {
      toast.error("Load failed", "Could not load resource optimization data.");
    } finally { loading = false; }
  }

  onMount(() => { loadData(); });
</script>

<svelte:head><title>Resource Optimization | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Project Planning</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Resource Optimization</h1>
    <p class="mt-1 text-sm text-neutral-500">Cross-project workforce and equipment allocation. Detect over-allocation and conflicts across all active projects.</p>
  </div>

  {#if loading}
    <p class="py-20 text-center text-sm text-neutral-400">Loading...</p>
  {:else if data}

    <!-- KPI Strip -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Active Projects</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{totalProjects}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Trades Deployed</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{totalTrades}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total Headcount</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{totalHeadcount}</p>
      </div>
      <div class="rounded-xl border {totalConflicts > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} p-4 text-center">
        <p class="text-[9px] font-semibold {totalConflicts > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Equipment Conflicts</p>
        <p class="mt-1 text-2xl font-bold {totalConflicts > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{totalConflicts}</p>
      </div>
      <div class="rounded-xl border {criticalAlerts.length > 0 ? 'border-red-200 bg-red-50' : warningAlerts.length > 0 ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'} p-4 text-center">
        <p class="text-[9px] font-semibold {criticalAlerts.length > 0 ? 'text-red-400' : warningAlerts.length > 0 ? 'text-amber-400' : 'text-emerald-400'} uppercase tracking-wider">Alerts</p>
        <p class="mt-1 text-2xl font-bold {criticalAlerts.length > 0 ? 'text-red-700' : warningAlerts.length > 0 ? 'text-amber-700' : 'text-emerald-700'} tabular-nums">{data.alerts.length}</p>
      </div>
    </div>

    <!-- Alerts Panel -->
    {#if data.alerts.length > 0}
      <section class="rounded-xl border {criticalAlerts.length > 0 ? 'border-red-200' : 'border-amber-200'} overflow-hidden">
        <div class="border-b {criticalAlerts.length > 0 ? 'border-red-100 bg-red-50' : 'border-amber-100 bg-amber-50'} px-5 py-3">
          <h3 class="text-[10px] font-semibold {criticalAlerts.length > 0 ? 'text-red-500' : 'text-amber-500'} uppercase tracking-widest">
            Over-Allocation Alerts ({data.alerts.length})
          </h3>
        </div>
        <div class="divide-y divide-neutral-100 bg-white">
          {#each data.alerts as alert}
            <div class="flex items-start gap-3 px-5 py-3">
              <span class="mt-0.5 inline-block h-2 w-2 rounded-full flex-shrink-0 {alert.severity === 'critical' ? 'bg-red-500' : 'bg-amber-500'}"></span>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-neutral-900">{alert.message}</p>
                <div class="mt-1 flex flex-wrap gap-1">
                  {#each alert.projects as proj}
                    <span class="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-medium text-neutral-600">{proj}</span>
                  {/each}
                </div>
              </div>
              <span class="rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase {alert.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}">{alert.severity}</span>
            </div>
          {/each}
        </div>
      </section>
    {:else}
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
        <p class="text-sm font-medium text-emerald-700">No resource conflicts or over-allocations detected.</p>
        <p class="mt-1 text-xs text-emerald-500">All resources are optimally allocated across projects.</p>
      </div>
    {/if}

    <!-- Cross-Project Heatmap -->
    {#if data.trade_summary.length > 0 && heatmapProjects.length > 0}
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Cross-Project Resource Heatmap (Trade x Project)</h3>
        </div>
        <div class="overflow-x-auto p-4">
          <table class="w-full text-sm">
            <thead>
              <tr>
                <th class="px-3 py-2 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Trade / Skill</th>
                {#each heatmapProjects as proj}
                  <th class="px-3 py-2 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider max-w-[120px] truncate" title={proj}>{proj}</th>
                {/each}
                <th class="px-3 py-2 text-center text-[10px] font-semibold text-neutral-900 uppercase tracking-wider">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.trade_summary as trade}
                <tr class="hover:bg-neutral-50">
                  <td class="px-3 py-2.5 text-sm font-medium text-neutral-900">{trade.trade}</td>
                  {#each heatmapProjects as proj}
                    {@const val = getHeatmapValue(trade, proj)}
                    <td class="px-3 py-2.5 text-center">
                      <span class="inline-block min-w-[32px] rounded-md px-2 py-1 text-xs tabular-nums {heatmapColor(val, maxHeadcount)}">
                        {val || "—"}
                      </span>
                    </td>
                  {/each}
                  <td class="px-3 py-2.5 text-center text-sm font-bold text-neutral-900 tabular-nums">{trade.total_headcount}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    <!-- Equipment Conflicts Detail -->
    {#if data.equipment_conflicts.length > 0}
      <section class="rounded-xl border border-red-200 bg-white overflow-hidden">
        <div class="border-b border-red-100 bg-red-50 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-red-500 uppercase tracking-widest">Equipment Scheduling Conflicts ({data.equipment_conflicts.length})</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Equipment</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project A</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Dates A</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project B</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Dates B</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.equipment_conflicts as conflict}
                <tr class="hover:bg-red-50/50">
                  <td class="px-4 py-2.5 font-medium text-neutral-900">{conflict.equipment}</td>
                  <td class="px-4 py-2.5 text-neutral-700">{conflict.project_a}</td>
                  <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{conflict.dates_a}</td>
                  <td class="px-4 py-2.5 text-neutral-700">{conflict.project_b}</td>
                  <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{conflict.dates_b}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    <!-- Active Projects -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Active Projects ({data.projects.length})</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100">
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Start</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Target End</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Budget</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each data.projects as proj}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-2.5 font-medium text-neutral-900">{proj.name}</td>
                <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{proj.start_date || "—"}</td>
                <td class="px-4 py-2.5 text-neutral-500 tabular-nums">{proj.target_end_date || "—"}</td>
                <td class="px-4 py-2.5 text-right font-semibold text-neutral-900 tabular-nums">
                  {proj.budget ? currency.formatCompact(proj.budget) : "—"}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

  {/if}
</div>

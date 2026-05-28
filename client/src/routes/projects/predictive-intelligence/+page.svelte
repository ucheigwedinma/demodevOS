<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface ProjectForecast {
    id: number; name: string; start_date: string | null; target_end_date: string | null;
    total_tasks: number; completed_tasks: number; overdue_tasks: number;
    completion_pct: number; overdue_pct: number;
    days_elapsed: number; days_planned: number;
    projected_total_days: number; projected_end_delta: number;
    budget: number; actual_cost: number;
    cpi: number; spi: number;
    cost_at_completion: number; cost_variance: number;
    risk_level: "critical" | "at_risk" | "on_track";
  }
  interface HistoricalPerf { category: string; tasks_completed: number; avg_delta_days: number; overrun_rate_pct: number; }
  interface Recommendation { project: string; type: string; severity: string; title: string; detail: string; action: string; }
  interface IntelData {
    project_forecasts: ProjectForecast[];
    historical_performance: HistoricalPerf[];
    recommendations: Recommendation[];
    generated_at: string;
  }

  let loading = $state(true);
  let data = $state<IntelData | null>(null);

  const criticalCount = $derived(data?.project_forecasts.filter(p => p.risk_level === "critical").length || 0);
  const atRiskCount = $derived(data?.project_forecasts.filter(p => p.risk_level === "at_risk").length || 0);
  const onTrackCount = $derived(data?.project_forecasts.filter(p => p.risk_level === "on_track").length || 0);
  const avgSpi = $derived(data && data.project_forecasts.length > 0
    ? +(data.project_forecasts.reduce((s, p) => s + p.spi, 0) / data.project_forecasts.length).toFixed(2)
    : 0);
  const avgCpi = $derived(data && data.project_forecasts.length > 0
    ? +(data.project_forecasts.reduce((s, p) => s + p.cpi, 0) / data.project_forecasts.length).toFixed(2)
    : 0);

  function riskColor(level: string): string {
    if (level === "critical") return "bg-red-500";
    if (level === "at_risk") return "bg-amber-500";
    return "bg-emerald-500";
  }
  function riskBorder(level: string): string {
    if (level === "critical") return "border-red-200";
    if (level === "at_risk") return "border-amber-200";
    return "border-emerald-200";
  }
  function riskBg(level: string): string {
    if (level === "critical") return "bg-red-50";
    if (level === "at_risk") return "bg-amber-50";
    return "bg-emerald-50";
  }
  function riskText(level: string): string {
    if (level === "critical") return "text-red-700";
    if (level === "at_risk") return "text-amber-700";
    return "text-emerald-700";
  }
  function riskLabel(level: string): string {
    if (level === "critical") return "Critical";
    if (level === "at_risk") return "At Risk";
    return "On Track";
  }
  function spiColor(spi: number): string {
    if (spi < 0.8) return "text-red-700";
    if (spi < 0.95) return "text-amber-700";
    return "text-emerald-700";
  }
  function cpiColor(cpi: number): string {
    if (cpi < 0.8) return "text-red-700";
    if (cpi < 0.95) return "text-amber-700";
    return "text-emerald-700";
  }
  function fmt(n: number): string {
    if (n == null || Number.isNaN(n)) return "--";
    return currency.formatCompact(n);
  }
  function sevColor(sev: string): { bg: string; text: string; border: string } {
    if (sev === "critical") return { bg: "bg-red-50", text: "text-red-700", border: "border-red-200" };
    if (sev === "warning") return { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" };
    return { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" };
  }

  async function loadData() {
    loading = true;
    try {
      data = await api.get<IntelData>("/projects/predictive-intelligence/");
    } catch { toast.error("Load failed", "Could not load predictive intelligence data."); }
    finally { loading = false; }
  }

  onMount(() => { loadData(); });
</script>

<svelte:head><title>Predictive Intelligence | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Projects</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Predictive Intelligence</h1>
      <p class="mt-1 text-sm text-neutral-500">Forecast delays before they occur. Powered by historical patterns and live project telemetry.</p>
    </div>
    {#if data}
      <div class="flex items-center gap-2 rounded-full border border-neutral-200 bg-white/80 px-4 py-2 text-xs text-neutral-500" style="backdrop-filter: blur(12px)">
        <span class="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
        Generated {data.generated_at}
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-32">
      <div class="flex flex-col items-center gap-3">
        <div class="h-8 w-8 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div>
        <p class="text-sm text-neutral-400">Analysing project telemetry...</p>
      </div>
    </div>
  {:else if data}

    <!-- Portfolio Health Ribbon -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-6">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Projects</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{data.project_forecasts.length}</p>
      </div>
      <div class="rounded-xl border border-red-200 bg-red-50/80 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-red-400 uppercase tracking-wider">Critical</p>
        <p class="mt-1 text-2xl font-bold text-red-700 tabular-nums">{criticalCount}</p>
      </div>
      <div class="rounded-xl border border-amber-200 bg-amber-50/80 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-amber-400 uppercase tracking-wider">At Risk</p>
        <p class="mt-1 text-2xl font-bold text-amber-700 tabular-nums">{atRiskCount}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50/80 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-emerald-400 uppercase tracking-wider">On Track</p>
        <p class="mt-1 text-2xl font-bold text-emerald-700 tabular-nums">{onTrackCount}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Avg SPI</p>
        <p class="mt-1 text-2xl font-bold {spiColor(avgSpi)} tabular-nums">{avgSpi}</p>
        <p class="text-[9px] text-neutral-400">Schedule Performance</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Avg CPI</p>
        <p class="mt-1 text-2xl font-bold {cpiColor(avgCpi)} tabular-nums">{avgCpi}</p>
        <p class="text-[9px] text-neutral-400">Cost Performance</p>
      </div>
    </div>

    <!-- Recommendations -->
    {#if data.recommendations.length > 0}
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden" style="backdrop-filter: blur(10px)">
        <div class="border-b border-neutral-100 bg-linear-to-r from-neutral-50 to-white px-5 py-3 flex items-center justify-between">
          <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">AI Recommendations ({data.recommendations.length})</h3>
          <span class="rounded-full bg-indigo-100 border border-indigo-200 px-2.5 py-0.5 text-[9px] font-semibold text-indigo-700">Auto-generated</span>
        </div>
        <div class="divide-y divide-neutral-50">
          {#each data.recommendations as rec}
            {@const sc = sevColor(rec.severity)}
            <div class="px-5 py-4 hover:bg-neutral-50/50 transition-colors">
              <div class="flex items-start gap-3">
                <div class="mt-1 shrink-0">
                  {#if rec.severity === "critical"}
                    <span class="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 text-red-600">
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
                    </span>
                  {:else if rec.severity === "warning"}
                    <span class="flex h-6 w-6 items-center justify-center rounded-full bg-amber-100 text-amber-600">
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                    </span>
                  {:else}
                    <span class="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-600">
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" /></svg>
                    </span>
                  {/if}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="text-sm font-semibold text-neutral-900">{rec.title}</span>
                    <span class="rounded-full {sc.bg} {sc.border} border px-2 py-0.5 text-[9px] font-semibold {sc.text} uppercase">{rec.severity}</span>
                  </div>
                  <p class="text-xs text-neutral-600 mb-2">{rec.detail}</p>
                  <div class="flex items-center gap-2">
                    <span class="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 text-[10px] font-medium text-neutral-600">{rec.project}</span>
                    <span class="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-0.5 text-[10px] font-medium text-indigo-700">{rec.type}</span>
                  </div>
                  <div class="mt-2 rounded-lg border border-emerald-200 bg-emerald-50/50 px-3 py-2">
                    <p class="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mb-0.5">Recommended Action</p>
                    <p class="text-xs text-emerald-800">{rec.action}</p>
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Project Forecast Cards -->
    <section>
      <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Project Forecasts</h3>
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {#each data.project_forecasts as pf}
          <div class="rounded-xl border {riskBorder(pf.risk_level)} bg-white overflow-hidden shadow-sm hover:shadow-md transition-shadow" style="backdrop-filter: blur(10px)">
            <!-- Card Header -->
            <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-100 {riskBg(pf.risk_level)}">
              <div class="flex items-center gap-2 min-w-0">
                <span class="inline-block h-2.5 w-2.5 rounded-full {riskColor(pf.risk_level)} shrink-0"></span>
                <h4 class="text-sm font-semibold text-neutral-900 truncate">{pf.name}</h4>
              </div>
              <span class="rounded-full {riskBg(pf.risk_level)} border {riskBorder(pf.risk_level)} px-2.5 py-0.5 text-[9px] font-bold {riskText(pf.risk_level)} uppercase shrink-0">{riskLabel(pf.risk_level)}</span>
            </div>

            <!-- Completion Progress -->
            <div class="px-4 pt-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-[10px] font-semibold text-neutral-500 uppercase">Completion</span>
                <span class="text-sm font-bold text-neutral-900 tabular-nums">{pf.completion_pct}%</span>
              </div>
              <div class="h-2 rounded-full bg-neutral-100 overflow-hidden">
                <div class="h-full rounded-full transition-all duration-500 {pf.risk_level === 'critical' ? 'bg-red-500' : pf.risk_level === 'at_risk' ? 'bg-amber-500' : 'bg-emerald-500'}" style="width: {pf.completion_pct}%"></div>
              </div>
              <div class="flex items-center justify-between mt-1">
                <span class="text-[10px] text-neutral-400">{pf.completed_tasks}/{pf.total_tasks} tasks</span>
                {#if pf.overdue_tasks > 0}
                  <span class="text-[10px] font-semibold text-red-500">{pf.overdue_tasks} overdue</span>
                {/if}
              </div>
            </div>

            <!-- Performance Indices -->
            <div class="grid grid-cols-2 gap-px bg-neutral-100 mx-4 mt-3 rounded-lg overflow-hidden">
              <div class="bg-white px-3 py-2.5 text-center">
                <p class="text-[9px] font-semibold text-neutral-400 uppercase">SPI</p>
                <p class="text-lg font-bold {spiColor(pf.spi)} tabular-nums">{pf.spi}</p>
                <p class="text-[9px] text-neutral-400">{pf.spi >= 1 ? 'Ahead' : pf.spi >= 0.95 ? 'On time' : 'Behind'}</p>
              </div>
              <div class="bg-white px-3 py-2.5 text-center">
                <p class="text-[9px] font-semibold text-neutral-400 uppercase">CPI</p>
                <p class="text-lg font-bold {cpiColor(pf.cpi)} tabular-nums">{pf.cpi}</p>
                <p class="text-[9px] text-neutral-400">{pf.cpi >= 1 ? 'Under budget' : pf.cpi >= 0.95 ? 'On budget' : 'Over budget'}</p>
              </div>
            </div>

            <!-- Schedule Forecast -->
            <div class="px-4 py-3 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-neutral-500">Planned Duration</span>
                <span class="text-xs font-semibold text-neutral-900 tabular-nums">{pf.days_planned}d</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-neutral-500">Projected Duration</span>
                <span class="text-xs font-semibold {pf.projected_end_delta > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">
                  {pf.projected_total_days}d
                  {#if pf.projected_end_delta !== 0}
                    <span class="text-[10px]">({pf.projected_end_delta > 0 ? '+' : ''}{pf.projected_end_delta}d)</span>
                  {/if}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-neutral-500">Est. Cost at Completion</span>
                <span class="text-xs font-semibold {pf.cost_variance > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">
                  {fmt(pf.cost_at_completion)}
                  {#if pf.cost_variance !== 0}
                    <span class="text-[10px]">({pf.cost_variance > 0 ? '+' : ''}{fmt(pf.cost_variance)})</span>
                  {/if}
                </span>
              </div>
            </div>

            <!-- Timeline Bar -->
            <div class="px-4 pb-3">
              <div class="flex items-center gap-2 text-[9px] text-neutral-400">
                <span>{pf.start_date || '—'}</span>
                <div class="flex-1 h-px bg-neutral-200 relative">
                  {#if pf.days_planned > 0}
                    <div class="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-neutral-300" style="width: 100%"></div>
                    <div class="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full {riskColor(pf.risk_level)}" style="width: {Math.min(100, pf.days_elapsed / pf.days_planned * 100)}%"></div>
                  {/if}
                </div>
                <span>{pf.target_end_date || '—'}</span>
              </div>
            </div>
          </div>
        {/each}
      </div>
    </section>

    <!-- Historical Performance Patterns -->
    {#if data.historical_performance.length > 0}
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden" style="backdrop-filter: blur(10px)">
        <div class="border-b border-neutral-100 bg-linear-to-r from-neutral-50 to-white px-5 py-3">
          <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">Historical Performance Patterns</h3>
          <p class="mt-0.5 text-[10px] text-neutral-400">Based on {data.historical_performance.reduce((s, h) => s + h.tasks_completed, 0)} completed tasks across all projects.</p>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Category</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Tasks</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Avg Delta</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Overrun Rate</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Trend</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.historical_performance as hp}
                <tr class="hover:bg-neutral-50/50">
                  <td class="px-5 py-3 font-medium text-neutral-900">{hp.category}</td>
                  <td class="px-5 py-3 text-center text-neutral-600 tabular-nums">{hp.tasks_completed}</td>
                  <td class="px-5 py-3 text-center tabular-nums {hp.avg_delta_days > 0 ? 'text-red-600 font-semibold' : hp.avg_delta_days < 0 ? 'text-emerald-600 font-semibold' : 'text-neutral-500'}">
                    {hp.avg_delta_days > 0 ? '+' : ''}{hp.avg_delta_days}d
                  </td>
                  <td class="px-5 py-3 text-center">
                    <span class="inline-block min-w-[48px] rounded-full px-2.5 py-0.5 text-[10px] font-semibold tabular-nums
                      {hp.overrun_rate_pct > 50 ? 'bg-red-100 text-red-700' :
                       hp.overrun_rate_pct > 25 ? 'bg-amber-100 text-amber-700' :
                       'bg-emerald-100 text-emerald-700'}">
                      {hp.overrun_rate_pct}%
                    </span>
                  </td>
                  <td class="px-5 py-3">
                    <!-- Visual bar -->
                    <div class="flex items-center gap-2">
                      <div class="h-1.5 rounded-full bg-neutral-100 w-20 overflow-hidden">
                        <div class="h-full rounded-full {hp.overrun_rate_pct > 50 ? 'bg-red-400' : hp.overrun_rate_pct > 25 ? 'bg-amber-400' : 'bg-emerald-400'}" style="width: {Math.min(100, hp.overrun_rate_pct)}%"></div>
                      </div>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {:else}
      <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-8 text-center">
        <p class="text-sm text-neutral-500">No historical data yet. Complete tasks with due dates to build performance patterns.</p>
      </div>
    {/if}

  {/if}
</div>

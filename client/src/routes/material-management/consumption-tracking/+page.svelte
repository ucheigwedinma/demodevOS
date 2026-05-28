<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface MaterialVariance { material: string; boq_value: string; issued_value: string; variance_pct: number; variance_amount: string; status: string; }
  interface CategoryConsumption { category: string; total_value: string; total_qty: string; count: number; }
  interface ProjectConsumption { project_id: number; project_name: string; total_value: string; total_qty: string; tx_count: number; }
  interface RecentTx { id: number; item_name: string; item_category: string; warehouse_name: string; project_name: string; quantity: string; total_cost: string; transaction_date: string; reference_number: string; notes: string; }
  interface PVAEntry { material: string; work_package: string; project: string; planned_qty: string; actual_qty: string; unit: string; variance_qty: string; variance_pct: number; planned_value: string; actual_value: string; status: string; }
  interface CrewEntry { crew: string; issue_count: number; total_value: string; total_qty: string; cost_per_issue: number; efficiency_score: number; rating: string; top_materials: { name: string; qty: string }[]; }
  interface YieldEntry { material: string; category: string; total_issued: string; issue_count: number; yield_per_issue: number; total_value: string; }
  interface DashboardData {
    overall_variance_pct: number; wastage_value: string; total_issued: string; boq_baseline: string;
    high_risk_material: MaterialVariance | null; productivity_score: number;
    material_variances: MaterialVariance[]; category_consumption: CategoryConsumption[];
    project_consumption: ProjectConsumption[]; recent_transactions: RecentTx[];
    pva_ledger: PVAEntry[];
    crew_leaderboard: { leaderboard: CrewEntry[]; yields: YieldEntry[] };
  }

  let loading = $state(true);
  let data = $state<DashboardData | null>(null);
  let varianceFilter = $state<"all" | "over" | "under" | "on_track">("all");

  // Variance badge color helper (Green < 2%, Orange 2-7%, Red > 7%)
  function varianceBadge(pct: number): { bg: string; text: string; border: string; label: string } {
    const abs = Math.abs(pct);
    if (abs <= 2) return { bg: "bg-emerald-100", text: "text-emerald-700", border: "border-emerald-300", label: "On Track" };
    if (abs <= 7) return { bg: "bg-amber-100", text: "text-amber-700", border: "border-amber-300", label: pct > 0 ? "Caution" : "Saving" };
    return { bg: "bg-red-100", text: "text-red-700", border: "border-red-300", label: pct > 0 ? "Critical" : "Major Saving" };
  }

  // Chart data: cumulative planned vs actual over time
  const chartData = $derived.by(() => {
    if (!data || !data.recent_transactions.length) return null;

    // Group transactions by date, accumulate
    const dateMap = new Map<string, number>();
    const sortedTxs = [...data.recent_transactions].sort((a, b) => a.transaction_date.localeCompare(b.transaction_date));

    let cumulative = 0;
    for (const tx of sortedTxs) {
      cumulative += Number(tx.total_cost || 0);
      dateMap.set(tx.transaction_date, cumulative);
    }

    const dates = [...dateMap.keys()];
    const actualValues = [...dateMap.values()];
    const maxActual = Math.max(...actualValues, 1);

    // Planned line: linear interpolation from 0 to BoQ baseline
    const baseline = Number(data.boq_baseline || 0);
    const plannedValues = dates.map((_, i) => baseline * ((i + 1) / dates.length));

    return { dates, actualValues, plannedValues, maxActual, baseline };
  });

  // Investigation slide-over
  let showInvestigation = $state(false);
  let investigationEntry = $state<PVAEntry | null>(null);
  let investigationSaving = $state(false);
  let invForm = $state({
    root_cause: "other", severity: "medium", supervisor_notes: "", corrective_action: "",
  });
  let invPhoto = $state<File | null>(null);

  const ROOT_CAUSES = [
    { value: "theft", label: "Theft / Pilferage", icon: "🔒", color: "text-red-700 bg-red-50" },
    { value: "poor_workmanship", label: "Poor Workmanship", icon: "🔨", color: "text-amber-700 bg-amber-50" },
    { value: "design_change", label: "Design Change", icon: "📐", color: "text-blue-700 bg-blue-50" },
    { value: "spillage", label: "Spillage / Breakage", icon: "💧", color: "text-orange-700 bg-orange-50" },
    { value: "measurement_error", label: "Measurement Error", icon: "📏", color: "text-violet-700 bg-violet-50" },
    { value: "soil_conditions", label: "Site Conditions", icon: "🏗️", color: "text-yellow-700 bg-yellow-50" },
    { value: "rework", label: "Rework / Remedial", icon: "🔄", color: "text-pink-700 bg-pink-50" },
    { value: "weather", label: "Weather Damage", icon: "🌧️", color: "text-cyan-700 bg-cyan-50" },
    { value: "other", label: "Other", icon: "📋", color: "text-neutral-700 bg-neutral-50" },
  ];

  function openInvestigation(entry: PVAEntry) {
    investigationEntry = entry;
    invForm = { root_cause: "other", severity: entry.variance_pct > 20 ? "critical" : entry.variance_pct > 10 ? "high" : "medium", supervisor_notes: "", corrective_action: "" };
    invPhoto = null;
    showInvestigation = true;
  }

  async function submitInvestigation() {
    if (!investigationEntry || !invForm.supervisor_notes.trim()) {
      toast.error("Required", "Supervisor notes are mandatory.");
      return;
    }
    investigationSaving = true;
    try {
      const res = await api.post<{ id: number }>("/material-issues/variance-investigations/", {
        project: data?.project_consumption[0]?.project_id || null,
        material_name: investigationEntry.material,
        work_package: investigationEntry.work_package,
        root_cause: invForm.root_cause,
        severity: invForm.severity,
        planned_quantity: Number(investigationEntry.planned_qty),
        actual_quantity: Number(investigationEntry.actual_qty),
        variance_quantity: Number(investigationEntry.variance_qty),
        variance_pct: investigationEntry.variance_pct,
        unit: investigationEntry.unit,
        supervisor_notes: invForm.supervisor_notes,
        corrective_action: invForm.corrective_action,
        financial_impact: Math.abs(Number(investigationEntry.actual_value) - Number(investigationEntry.planned_value)),
      });

      // Upload photo if provided
      if (invPhoto && res.id) {
        const fd = new FormData();
        fd.append("image", invPhoto);
        fd.append("caption", `Variance evidence — ${investigationEntry.material}`);
        await fetch(`/api/material-issues/variance-investigations/${res.id}/upload-photo/`, {
          method: "POST",
          headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
          body: fd,
        });
      }

      toast.success("Investigation Filed", `Root cause recorded: ${ROOT_CAUSES.find(r => r.value === invForm.root_cause)?.label || invForm.root_cause}`);
      showInvestigation = false;
    } catch { toast.error("Failed", "Could not file investigation."); }
    finally { investigationSaving = false; }
  }

  const filteredVariances = $derived.by(() => {
    if (!data) return [];
    if (varianceFilter === "all") return data.material_variances;
    return data.material_variances.filter(v => v.status === varianceFilter);
  });

  let flagging = $state<string | null>(null);

  async function flagForAudit(entry: PVAEntry) {
    flagging = entry.material;
    try {
      // Create a variance investigation with "under_review" status to notify QS
      await api.post("/material-issues/variance-investigations/", {
        project: data?.project_consumption[0]?.project_id || null,
        material_name: entry.material,
        work_package: entry.work_package,
        root_cause: "other",
        severity: entry.variance_pct > 20 ? "critical" : "high",
        status: "escalated",
        planned_quantity: Number(entry.planned_qty),
        actual_quantity: Number(entry.actual_qty),
        variance_quantity: Number(entry.variance_qty),
        variance_pct: entry.variance_pct,
        unit: entry.unit,
        supervisor_notes: `Flagged for QS audit — unexplained ${entry.variance_pct}% variance on ${entry.material} (${entry.work_package}).`,
        financial_impact: Math.abs(Number(entry.actual_value) - Number(entry.planned_value)),
      });
      toast.success("Flagged", `${entry.material} flagged for QS audit. Notification sent.`);
    } catch { toast.error("Failed", "Could not flag for audit."); }
    finally { flagging = null; }
  }

  async function loadData() {
    loading = true;
    try {
      data = await api.get<DashboardData>("/material-issues/consumption-tracking/");
    } catch { toast.error("Load failed", "Could not load consumption tracking data."); }
    finally { loading = false; }
  }

  onMount(() => { loadData(); });
</script>

<svelte:head><title>Consumption Tracking | developerOS</title></svelte:head>

<div class="space-y-5">
  <!-- Header -->
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Material Management</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Consumption Tracking</h1>
    <p class="mt-1 text-sm text-neutral-500">Audit engine — compare what was issued vs what was actually consumed against the BoQ baseline.</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20"><div class="h-7 w-7 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div></div>
  {:else if data}

    <!-- Consumption Efficiency HUD -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <!-- Overall Variance Index -->
      <div class="rounded-xl border-2 {data.overall_variance_pct > 5 ? 'border-amber-300' : data.overall_variance_pct < -5 ? 'border-emerald-300' : 'border-neutral-200'} p-4 text-center bg-linear-to-br {data.overall_variance_pct > 5 ? 'from-amber-50 to-orange-50' : data.overall_variance_pct < -5 ? 'from-emerald-50 to-teal-50' : 'from-white to-neutral-50'}" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold {data.overall_variance_pct > 5 ? 'text-amber-500' : data.overall_variance_pct < -5 ? 'text-emerald-500' : 'text-neutral-400'} uppercase tracking-wider">Overall Variance</p>
        <p class="mt-1 text-3xl font-black {data.overall_variance_pct > 5 ? 'text-amber-700' : data.overall_variance_pct < -5 ? 'text-emerald-700' : 'text-neutral-900'} tabular-nums">
          {data.overall_variance_pct > 0 ? '+' : ''}{data.overall_variance_pct}%
        </p>
        <p class="text-[9px] {data.overall_variance_pct > 5 ? 'text-amber-400' : 'text-neutral-400'}">vs BoQ baseline</p>
      </div>

      <!-- Wastage Value -->
      <div class="rounded-xl border-2 {Number(data.wastage_value) > 0 ? 'border-red-300' : 'border-emerald-300'} p-4 text-center bg-linear-to-br {Number(data.wastage_value) > 0 ? 'from-red-50 to-rose-50' : 'from-emerald-50 to-green-50'}" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold {Number(data.wastage_value) > 0 ? 'text-red-400' : 'text-emerald-400'} uppercase tracking-wider">Wastage Value</p>
        <p class="mt-1 text-xl font-black {Number(data.wastage_value) > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">{currency.format(Number(data.wastage_value))}</p>
        <p class="text-[9px] {Number(data.wastage_value) > 0 ? 'text-red-400' : 'text-emerald-400'}">over-consumption cost</p>
      </div>

      <!-- High-Risk Material -->
      <div class="rounded-xl border-2 border-orange-200 bg-linear-to-br from-orange-50 to-amber-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-orange-400 uppercase tracking-wider">High-Risk Material</p>
        {#if data.high_risk_material}
          <p class="mt-1 text-sm font-black text-orange-900 truncate" title={data.high_risk_material.material}>{data.high_risk_material.material}</p>
          <span class="inline-block mt-1 rounded-full bg-linear-to-r {data.high_risk_material.variance_pct > 0 ? 'from-amber-200 to-orange-200 text-orange-800' : 'from-emerald-200 to-teal-200 text-emerald-800'} px-3 py-0.5 text-[9px] font-bold tabular-nums">
            {data.high_risk_material.variance_pct > 0 ? '+' : ''}{data.high_risk_material.variance_pct}%
          </span>
        {:else}
          <p class="mt-1 text-sm text-orange-300">No variance data</p>
        {/if}
      </div>

      <!-- Productivity Score -->
      <div class="rounded-xl border-2 border-emerald-300 bg-linear-to-br from-emerald-50 to-teal-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-emerald-500 uppercase tracking-wider">Productivity Score</p>
        <p class="mt-1 text-2xl font-black text-emerald-700 tabular-nums">{currency.format(data.productivity_score)}</p>
        <p class="text-[9px] text-emerald-400">material value / man-hour</p>
      </div>
    </div>

    <!-- Issued vs BoQ Summary Bar -->
    <div class="rounded-xl border border-neutral-200 bg-white/80 p-4" style="backdrop-filter: blur(10px)">
      <div class="flex items-center justify-between mb-2">
        <span class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Issued vs BoQ Baseline</span>
        <span class="text-xs text-neutral-500">
          {currency.format(Number(data.total_issued))} / {currency.format(Number(data.boq_baseline))}
        </span>
      </div>
      {#if true}
        {@const pct = Number(data.boq_baseline) > 0 ? Math.min(150, Number(data.total_issued) / Number(data.boq_baseline) * 100) : 0}
        <div class="h-3 rounded-full bg-neutral-100 overflow-hidden relative">
          <!-- BoQ baseline marker at 100% -->
          <div class="absolute top-0 bottom-0 w-0.5 bg-neutral-400 z-10" style="left: {Math.min(100, 100 / (pct || 100) * 100)}%"></div>
          <div class="h-full rounded-full transition-all {pct > 105 ? 'bg-red-500' : pct > 95 ? 'bg-amber-500' : 'bg-emerald-500'}" style="width: {Math.min(100, pct)}%"></div>
        </div>
        <div class="flex items-center justify-between mt-1 text-[9px] text-neutral-400">
          <span>0%</span>
          <span class="font-semibold text-neutral-600">BoQ Baseline (100%)</span>
          <span>{Math.round(pct)}% consumed</span>
        </div>
      {/if}
    </div>

    <!-- Cumulative Planned vs Actual Chart -->
    {#if chartData && chartData.dates.length >= 2}
      {#each [{ maxVal: Math.max(chartData.baseline, chartData.maxActual, 1), cW: 700, cH: 200, pL: 60, pR: 20, pT: 20, pB: 30 }] as c}
      {@const plotW = c.cW - c.pL - c.pR}
      {@const plotH = c.cH - c.pT - c.pB}

      <section class="rounded-xl border-2 border-neutral-200 bg-white/90 overflow-hidden" style="backdrop-filter: blur(12px)">
        <div class="border-b border-neutral-100 bg-linear-to-r from-neutral-50 to-white px-5 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-base">📈</span>
            <h3 class="text-[10px] font-black text-neutral-700 uppercase tracking-widest">Cumulative Consumption — Planned vs Actual</h3>
          </div>
          <div class="flex items-center gap-4 text-[9px]">
            <span class="flex items-center gap-1.5"><span class="inline-block h-2 w-4 rounded-full bg-emerald-500"></span> <span class="text-neutral-500 font-semibold">Planned (BoQ)</span></span>
            <span class="flex items-center gap-1.5"><span class="inline-block h-2 w-4 rounded-full bg-red-500"></span> <span class="text-neutral-500 font-semibold">Actual (Issued)</span></span>
          </div>
        </div>
        <div class="p-5 overflow-x-auto">
          <svg viewBox="0 0 {c.cW} {c.cH}" class="w-full" style="min-width: 500px; height: 200px;">
            <!-- Grid lines -->
            {#each [0, 0.25, 0.5, 0.75, 1] as frac}
              <line x1={c.pL} y1={c.pT + plotH * (1 - frac)} x2={c.pL + plotW} y2={c.pT + plotH * (1 - frac)} stroke="#f0f0f0" stroke-width="1" />
              <text x={c.pL - 8} y={c.pT + plotH * (1 - frac) + 3} text-anchor="end" fill="#a3a3a3" font-size="8" font-family="Raleway" font-weight="600">{currency.formatAbbreviated(c.maxVal * frac)}</text>
            {/each}

            <!-- Planned line (emerald, dashed) -->
            <polyline
              fill="none"
              stroke="#10b981"
              stroke-width="2"
              stroke-dasharray="6,3"
              points={chartData.dates.map((_, i) => {
                const x = c.pL + (i / (chartData.dates.length - 1)) * plotW;
                const y = c.pT + plotH * (1 - chartData.plannedValues[i] / c.maxVal);
                return `${x},${y}`;
              }).join(" ")}
            />
            <!-- Planned area (emerald, subtle) -->
            <polygon
              fill="rgba(16,185,129,0.06)"
              points={`${c.pL},${c.pT + plotH} ` + chartData.dates.map((_, i) => {
                const x = c.pL + (i / (chartData.dates.length - 1)) * plotW;
                const y = c.pT + plotH * (1 - chartData.plannedValues[i] / c.maxVal);
                return `${x},${y}`;
              }).join(" ") + ` ${c.pL + plotW},${c.pT + plotH}`}
            />

            <!-- Actual line (red/amber, solid) -->
            <polyline
              fill="none"
              stroke="#ef4444"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              points={chartData.dates.map((_, i) => {
                const x = c.pL + (i / (chartData.dates.length - 1)) * plotW;
                const y = c.pT + plotH * (1 - chartData.actualValues[i] / c.maxVal);
                return `${x},${y}`;
              }).join(" ")}
            />
            <!-- Actual area (red, subtle) -->
            <polygon
              fill="rgba(239,68,68,0.06)"
              points={`${c.pL},${c.pT + plotH} ` + chartData.dates.map((_, i) => {
                const x = c.pL + (i / (chartData.dates.length - 1)) * plotW;
                const y = c.pT + plotH * (1 - chartData.actualValues[i] / c.maxVal);
                return `${x},${y}`;
              }).join(" ") + ` ${c.pL + plotW},${c.pT + plotH}`}
            />

            <!-- Actual data points -->
            {#each chartData.dates as _, i}
              {@const x = c.pL + (i / (chartData.dates.length - 1)) * plotW}
              {@const y = c.pT + plotH * (1 - chartData.actualValues[i] / c.maxVal)}
              <circle cx={x} cy={y} r="3.5" fill="white" stroke="#ef4444" stroke-width="2" />
            {/each}

            <!-- Date labels -->
            {#each chartData.dates as date, i}
              {#if i % Math.max(1, Math.floor(chartData.dates.length / 6)) === 0 || i === chartData.dates.length - 1}
                {@const x = c.pL + (i / (chartData.dates.length - 1)) * plotW}
                <text x={x} y={c.cH - 5} text-anchor="middle" fill="#a3a3a3" font-size="7" font-family="Raleway" font-weight="500">
                  {date.slice(5)}
                </text>
              {/if}
            {/each}

            <!-- Baseline marker -->
            {#if true}
              {@const baselineY = c.pT + plotH * (1 - chartData.baseline / c.maxVal)}
              <line x1={c.pL} y1={baselineY} x2={c.pL + plotW} y2={baselineY} stroke="#10b981" stroke-width="1" stroke-dasharray="2,2" opacity="0.5" />
              <text x={c.pL + plotW + 4} y={baselineY + 3} fill="#10b981" font-size="7" font-weight="700">BoQ</text>
            {/if}
          </svg>
        </div>
      </section>
      {/each}
    {/if}

    <!-- PVA Ledger (Planned vs Actual) -->
    {#if data.pva_ledger.length > 0}
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-200 bg-neutral-100/80 px-5 py-3 flex items-center justify-between">
          <div>
            <h3 class="text-[10px] font-bold text-neutral-700 uppercase tracking-widest">Planned vs. Actual Ledger</h3>
            <p class="text-[9px] text-neutral-500 mt-0.5">Quantity-level comparison against BoQ baseline per material and work package.</p>
          </div>
          <span class="text-[10px] text-neutral-400">{data.pva_ledger.length} items tracked</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200 bg-neutral-100/80">
                <th class="px-4 py-2.5 text-left text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Material Item</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Work Package</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Planned (BoQ)</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-bold text-neutral-900 uppercase tracking-wider">Actual (Issued)</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Burn Rate</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Variance</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-bold text-neutral-700 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.pva_ledger as entry}
                {@const varQty = Number(entry.variance_qty)}
                {@const burnPct = Number(entry.planned_qty) > 0 ? Math.min(150, Number(entry.actual_qty) / Number(entry.planned_qty) * 100) : 0}
                {@const circumference = 2 * Math.PI * 14}
                {@const dashOffset = circumference - (Math.min(100, burnPct) / 100) * circumference}
                {@const gaugeColor = burnPct > 100 ? '#ef4444' : burnPct > 80 ? '#f59e0b' : '#10b981'}
                {@const frostedRed = entry.variance_pct > 5}
                <tr class="{entry.status === 'investigate' || entry.status === 'at_risk' ? 'cursor-pointer' : ''} hover:bg-neutral-50/80 transition-colors {frostedRed ? '' : entry.status === 'at_risk' ? 'bg-amber-50/20' : ''}"
                  style="{frostedRed ? 'background: rgba(254,202,202,0.15); box-shadow: inset 0 0 20px rgba(239,68,68,0.06);' : ''}"
                  onclick={() => { if (entry.status === 'investigate' || entry.status === 'at_risk') openInvestigation(entry); }}>
                  <!-- Material Item -->
                  <td class="px-4 py-3">
                    <p class="font-bold text-neutral-900" style="font-family: Raleway, sans-serif; font-weight: 500;">{entry.material}</p>
                    <p class="text-[9px] text-neutral-400 mt-0.5">{entry.project}</p>
                  </td>
                  <!-- Work Package -->
                  <td class="px-4 py-3">
                    <span class="rounded-md bg-neutral-100 border border-neutral-200 px-2 py-0.5 text-[10px] font-medium text-neutral-700 capitalize">{entry.work_package.replace(/_/g, " ")}</span>
                  </td>
                  <!-- Planned -->
                  <td class="px-4 py-3 text-right tabular-nums text-neutral-600" style="font-family: Raleway, sans-serif; font-weight: 500;">
                    <span>{Number(entry.planned_qty).toLocaleString()}</span>
                    <span class="text-[9px] text-neutral-400 ml-0.5">{entry.unit}</span>
                  </td>
                  <!-- Actual (Bold) -->
                  <td class="px-4 py-3 text-right tabular-nums" style="font-family: Raleway, sans-serif; font-weight: 700;">
                    <span class="text-neutral-900 text-base">{Number(entry.actual_qty).toLocaleString()}</span>
                    <span class="text-[9px] text-neutral-400 ml-0.5">{entry.unit}</span>
                  </td>
                  <!-- Burn Rate Gauge -->
                  <td class="px-4 py-3">
                    <div class="flex justify-center">
                      <div class="relative" style="width: 36px; height: 36px;">
                        <svg viewBox="0 0 36 36" class="w-full h-full -rotate-90">
                          <circle cx="18" cy="18" r="14" fill="none" stroke="#f5f5f5" stroke-width="3" />
                          <circle cx="18" cy="18" r="14" fill="none" stroke={gaugeColor} stroke-width="3"
                            stroke-dasharray={String(circumference)} stroke-dashoffset={String(dashOffset)}
                            stroke-linecap="round" class="transition-all duration-500" />
                        </svg>
                        <div class="absolute inset-0 flex items-center justify-center">
                          <span class="text-[8px] font-black tabular-nums" style="color: {gaugeColor}">{Math.round(burnPct)}</span>
                        </div>
                      </div>
                    </div>
                  </td>
                  <!-- Variance with dynamic badge -->
                  <td class="px-4 py-3 text-right">
                    {#if true}
                      {@const badge = varianceBadge(entry.variance_pct)}
                      <span class="font-black tabular-nums text-sm {varQty > 0 ? 'text-red-700' : varQty < 0 ? 'text-emerald-700' : 'text-neutral-500'}">
                        {varQty > 0 ? `(${Math.abs(varQty).toLocaleString()})` : varQty < 0 ? Math.abs(varQty).toLocaleString() : '—'}
                      </span>
                      {#if entry.variance_pct !== 0}
                        <span class="inline-block mt-1 rounded-full {badge.bg} {badge.text} border {badge.border} px-2 py-0.5 text-[8px] font-bold tabular-nums">
                          {varQty > 0 ? '+' : ''}{entry.variance_pct}% · {badge.label}
                        </span>
                      {/if}
                    {/if}
                  </td>
                  <!-- Status -->
                  <td class="px-4 py-3 text-center">
                    {#if entry.status === "investigate"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-linear-to-r from-red-100 to-rose-100 border border-red-200 px-2.5 py-1 text-[9px] font-bold text-red-700 shadow-sm">
                        <span class="inline-block h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
                        Investigate
                      </span>
                    {:else if entry.status === "at_risk"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-linear-to-r from-amber-100 to-orange-100 border border-amber-200 px-2.5 py-1 text-[9px] font-bold text-amber-700">
                        <span class="inline-block h-2 w-2 rounded-full bg-amber-500"></span>
                        At Risk
                      </span>
                    {:else if entry.status === "optimized"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-linear-to-r from-emerald-100 to-teal-100 border border-emerald-200 px-2.5 py-1 text-[9px] font-bold text-emerald-700">
                        <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
                        Optimized
                      </span>
                    {:else}
                      <span class="inline-flex items-center gap-1 rounded-full bg-neutral-100 border border-neutral-200 px-2.5 py-1 text-[9px] font-semibold text-neutral-500">
                        <span class="inline-block h-2 w-2 rounded-full bg-neutral-400"></span>
                        On Track
                      </span>
                    {/if}
                  </td>
                  <!-- Action -->
                  <td class="px-4 py-3 text-center" onclick={(e) => e.stopPropagation()}>
                    {#if entry.status === "investigate" || entry.status === "at_risk"}
                      <div class="flex justify-center gap-1">
                        <button onclick={() => openInvestigation(entry)} class="rounded-md bg-amber-100 border border-amber-200 px-2 py-1 text-[9px] font-bold text-amber-700 hover:bg-amber-200 transition-colors" title="Investigate root cause">
                          Investigate
                        </button>
                        <button onclick={() => flagForAudit(entry)} disabled={flagging === entry.material}
                          class="rounded-md bg-red-100 border border-red-200 px-2 py-1 text-[9px] font-bold text-red-700 hover:bg-red-200 transition-colors" title="Flag for QS audit">
                          {flagging === entry.material ? "..." : "Flag"}
                        </button>
                      </div>
                    {:else if entry.status === "optimized"}
                      <span class="text-[9px] text-emerald-500 font-semibold">Savings</span>
                    {:else}
                      <span class="text-[9px] text-neutral-300">—</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    <!-- Material Variance Table -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between">
        <h3 class="text-[10px] font-bold text-neutral-500 uppercase tracking-widest">Material Variance Analysis ({filteredVariances.length})</h3>
        <div class="flex gap-1">
          {#each [["all", "All"], ["over", "Over"], ["under", "Under"], ["on_track", "On Track"]] as [val, label]}
            <button onclick={() => { varianceFilter = val as any; }}
              class="rounded-md px-2.5 py-1 text-[9px] font-semibold transition-colors {varianceFilter === val ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'}">
              {label}
            </button>
          {/each}
        </div>
      </div>

      {#if filteredVariances.length === 0}
        <div class="p-6 text-center text-sm text-neutral-400">No variance data available.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-neutral-100 bg-neutral-50/50">
              <th class="px-4 py-2.5 text-left text-[10px] font-bold text-neutral-600 uppercase">Material</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-bold text-neutral-600 uppercase">BoQ Estimate</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-bold text-neutral-600 uppercase">Issued</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-bold text-neutral-600 uppercase">Variance</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-bold text-neutral-600 uppercase">Status</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-bold text-neutral-600 uppercase">Trend</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-50">
              {#each filteredVariances as v}
                <tr class="hover:bg-neutral-50 {v.status === 'over' ? 'bg-red-50/20' : ''}">
                  <td class="px-4 py-3 font-semibold text-neutral-900">{v.material}</td>
                  <td class="px-4 py-3 text-right tabular-nums text-neutral-600">{currency.format(Number(v.boq_value))}</td>
                  <td class="px-4 py-3 text-right tabular-nums font-semibold text-neutral-900">{currency.format(Number(v.issued_value))}</td>
                  <td class="px-4 py-3 text-right tabular-nums font-bold {v.variance_pct > 0 ? 'text-red-700' : v.variance_pct < 0 ? 'text-emerald-700' : 'text-neutral-500'}">
                    {v.variance_pct > 0 ? '+' : ''}{v.variance_pct}%
                    <span class="block text-[9px] font-normal text-neutral-400">{currency.format(Math.abs(Number(v.variance_amount)))}</span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <div class="inline-flex items-center gap-1.5">
                      <span class="inline-block h-2 w-2 rounded-full {v.status === 'over' ? 'bg-red-500' : v.status === 'under' ? 'bg-emerald-500' : 'bg-neutral-400'}"></span>
                      <span class="text-[10px] font-semibold {v.status === 'over' ? 'text-red-700' : v.status === 'under' ? 'text-emerald-700' : 'text-neutral-500'}">{v.status === 'over' ? 'Over' : v.status === 'under' ? 'Under' : 'On Track'}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3">
                    <div class="h-1.5 w-16 rounded-full bg-neutral-100 overflow-hidden">
                      {#if v.variance_pct > 0}
                        <div class="h-full rounded-full bg-red-400" style="width: {Math.min(100, v.variance_pct * 2)}%"></div>
                      {:else if v.variance_pct < 0}
                        <div class="h-full rounded-full bg-emerald-400" style="width: {Math.min(100, Math.abs(v.variance_pct) * 2)}%"></div>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <!-- Productivity & Crew Analysis -->
    {#if data.crew_leaderboard.leaderboard.length > 0 || data.crew_leaderboard.yields.length > 0}
      <div class="grid gap-4 md:grid-cols-2">
        <!-- Crew Leaderboard -->
        {#if data.crew_leaderboard.leaderboard.length > 0}
          <section class="rounded-xl border-2 border-indigo-200 bg-linear-to-br from-indigo-50/80 to-violet-50/50 overflow-hidden" style="backdrop-filter: blur(10px)">
            <div class="border-b border-indigo-200 bg-linear-to-r from-indigo-100/80 to-violet-100/50 px-5 py-3 flex items-center gap-2">
              <span class="text-base">🏆</span>
              <h3 class="text-[10px] font-black text-indigo-800 uppercase tracking-widest">Crew Leaderboard</h3>
            </div>
            <div class="p-4 space-y-3">
              {#each data.crew_leaderboard.leaderboard as crew, rank}
                {@const ratingColors = { highly_productive: { bg: "from-emerald-50 to-teal-50", border: "border-emerald-300", text: "text-emerald-700", badge: "bg-gradient-to-r from-emerald-500 to-teal-500 text-white", label: "Highly Productive" }, productive: { bg: "from-blue-50 to-indigo-50", border: "border-blue-200", text: "text-blue-700", badge: "bg-blue-100 text-blue-700", label: "Productive" }, needs_improvement: { bg: "from-amber-50 to-orange-50", border: "border-amber-300", text: "text-amber-700", badge: "bg-amber-100 text-amber-700", label: "Needs Improvement" } }}
                {@const rc = ratingColors[crew.rating as keyof typeof ratingColors] || ratingColors.productive}
                <div class="rounded-xl border-2 {rc.border} bg-linear-to-br {rc.bg} p-3.5">
                  <div class="flex items-center gap-3">
                    <!-- Rank Medal -->
                    <div class="shrink-0 flex items-center justify-center h-9 w-9 rounded-full {rank === 0 ? 'bg-linear-to-br from-yellow-400 to-amber-500 text-white shadow-lg' : rank === 1 ? 'bg-linear-to-br from-neutral-300 to-neutral-400 text-white' : rank === 2 ? 'bg-linear-to-br from-amber-600 to-amber-700 text-white' : 'bg-neutral-200 text-neutral-600'} font-black text-sm">
                      {rank + 1}
                    </div>

                    <div class="flex-1 min-w-0">
                      <div class="flex items-center justify-between">
                        <p class="text-sm font-bold {rc.text}">{crew.crew}</p>
                        <span class="rounded-full {rc.badge} px-2.5 py-0.5 text-[8px] font-bold shadow-sm">{rc.label}</span>
                      </div>

                      <!-- Efficiency bar -->
                      <div class="mt-2 flex items-center gap-2">
                        <div class="flex-1 h-2.5 rounded-full bg-white/60 overflow-hidden">
                          <div class="h-full rounded-full transition-all duration-700 {crew.efficiency_score >= 80 ? 'bg-linear-to-r from-emerald-400 to-teal-500' : crew.efficiency_score >= 50 ? 'bg-linear-to-r from-blue-400 to-indigo-500' : 'bg-linear-to-r from-amber-400 to-orange-500'}" style="width: {crew.efficiency_score}%"></div>
                        </div>
                        <span class="text-xs font-black tabular-nums {rc.text}">{crew.efficiency_score}%</span>
                      </div>

                      <!-- Stats row -->
                      <div class="flex items-center gap-3 mt-1.5 text-[9px]">
                        <span class="{rc.text}">{crew.issue_count} issues</span>
                        <span class="text-neutral-400">|</span>
                        <span class="{rc.text}">{currency.format(Number(crew.total_value))} consumed</span>
                        <span class="text-neutral-400">|</span>
                        <span class="{rc.text}">{currency.format(crew.cost_per_issue)}/issue</span>
                      </div>

                      <!-- Top materials -->
                      {#if crew.top_materials.length > 0}
                        <div class="flex gap-1 mt-1.5">
                          {#each crew.top_materials as mat}
                            <span class="rounded-md bg-white/70 border border-white/50 px-1.5 py-0.5 text-[8px] font-semibold text-neutral-600">{mat.name}: {mat.qty}</span>
                          {/each}
                        </div>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </section>
        {/if}

        <!-- Yield Calculations -->
        {#if data.crew_leaderboard.yields.length > 0}
          <section class="rounded-xl border-2 border-teal-200 bg-linear-to-br from-teal-50/80 to-emerald-50/50 overflow-hidden" style="backdrop-filter: blur(10px)">
            <div class="border-b border-teal-200 bg-linear-to-r from-teal-100/80 to-emerald-100/50 px-5 py-3 flex items-center gap-2">
              <span class="text-base">📊</span>
              <h3 class="text-[10px] font-black text-teal-800 uppercase tracking-widest">Actual Yield Analysis</h3>
            </div>
            <div class="p-4">
              <div class="space-y-2">
                {#each data.crew_leaderboard.yields as y}
                  <div class="rounded-xl border border-teal-200 bg-white/70 p-3 flex items-center gap-3 hover:bg-white transition-colors">
                    <!-- Yield circle -->
                    <div class="shrink-0 flex items-center justify-center h-11 w-11 rounded-full bg-linear-to-br from-teal-400 to-emerald-500 text-white shadow-md">
                      <span class="text-xs font-black tabular-nums">{y.yield_per_issue}</span>
                    </div>

                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-bold text-teal-900">{y.material}</p>
                      <div class="flex items-center gap-3 mt-0.5 text-[9px]">
                        <span class="text-teal-600 capitalize">{y.category.replace(/_/g, " ")}</span>
                        <span class="text-neutral-300">|</span>
                        <span class="text-teal-600">{Number(y.total_issued).toLocaleString()} units issued</span>
                        <span class="text-neutral-300">|</span>
                        <span class="text-teal-600">{y.issue_count} draws</span>
                      </div>
                    </div>

                    <div class="text-right shrink-0">
                      <p class="text-[9px] font-semibold text-teal-500 uppercase">Per Issue</p>
                      <p class="text-sm font-black text-teal-800 tabular-nums">{y.yield_per_issue} units</p>
                    </div>
                  </div>
                {/each}
              </div>

              {#if data.crew_leaderboard.yields.length > 3}
                <p class="text-[9px] text-teal-400 text-center mt-3">Showing top {data.crew_leaderboard.yields.length} materials by volume</p>
              {/if}
            </div>
          </section>
        {/if}
      </div>
    {/if}

    <!-- Category + Project + Recent Transactions -->
    <div class="grid gap-4 md:grid-cols-3">
      <!-- Category Consumption -->
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
          <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">By Category</h3>
        </div>
        <div class="divide-y divide-neutral-50 px-4">
          {#each data.category_consumption as cat}
            <div class="py-2.5 flex items-center justify-between">
              <span class="text-xs text-neutral-700 capitalize font-medium">{cat.category.replace(/_/g, " ")}</span>
              <span class="text-xs font-bold text-neutral-900 tabular-nums">{currency.format(Number(cat.total_value))}</span>
            </div>
          {:else}
            <div class="py-4 text-center text-xs text-neutral-400">No data</div>
          {/each}
        </div>
      </div>

      <!-- Project Consumption -->
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
          <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">By Project</h3>
        </div>
        <div class="divide-y divide-neutral-50 px-4">
          {#each data.project_consumption as pc}
            <div class="py-2.5">
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-900 font-medium truncate">{pc.project_name}</span>
                <span class="text-xs font-bold text-neutral-900 tabular-nums shrink-0 ml-2">{currency.format(Number(pc.total_value))}</span>
              </div>
              <p class="text-[9px] text-neutral-400 mt-0.5">{pc.tx_count} transactions</p>
            </div>
          {:else}
            <div class="py-4 text-center text-xs text-neutral-400">No data</div>
          {/each}
        </div>
      </div>

      <!-- Recent Transactions -->
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
          <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Recent Consumption</h3>
        </div>
        <div class="divide-y divide-neutral-50 max-h-72 overflow-y-auto">
          {#each data.recent_transactions as tx}
            <div class="px-4 py-2.5">
              <div class="flex items-center justify-between">
                <span class="text-xs font-medium text-neutral-900 truncate">{tx.item_name}</span>
                <span class="text-xs font-bold text-red-700 tabular-nums shrink-0">-{tx.quantity}</span>
              </div>
              <div class="flex items-center justify-between mt-0.5 text-[9px] text-neutral-400">
                <span>{tx.project_name} | {tx.warehouse_name}</span>
                <span class="tabular-nums">{tx.transaction_date}</span>
              </div>
            </div>
          {:else}
            <div class="py-4 text-center text-xs text-neutral-400">No transactions</div>
          {/each}
        </div>
      </div>
    </div>

  {/if}
</div>

<!-- Variance Investigation Slide-over -->
{#if showInvestigation && investigationEntry}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex justify-end bg-black/40" style="backdrop-filter: blur(15px)" onclick={() => { showInvestigation = false; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-lg bg-white/95 shadow-2xl overflow-y-auto" style="backdrop-filter: blur(20px); border-left: 1px solid rgba(200,200,200,0.3);" onclick={(e) => e.stopPropagation()}>
      <!-- Header with gradient accent -->
      <div class="bg-linear-to-r from-amber-600 via-orange-600 to-red-600 px-6 py-5">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-bold text-white">Variance Investigation</h2>
            <p class="text-sm text-amber-100 mt-1 font-medium">{investigationEntry.material}</p>
            <div class="flex gap-2 mt-2">
              <span class="rounded-full bg-white/20 border border-white/30 px-2.5 py-0.5 text-[10px] font-bold text-white capitalize">{investigationEntry.work_package.replace(/_/g, " ")}</span>
              <span class="rounded-full bg-white/20 border border-white/30 px-2.5 py-0.5 text-[10px] font-bold text-white">{investigationEntry.variance_pct > 0 ? '+' : ''}{investigationEntry.variance_pct}% variance</span>
            </div>
          </div>
          <button onclick={() => { showInvestigation = false; }} class="rounded-lg p-1.5 text-white/70 hover:bg-white/20 hover:text-white" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <div class="p-6 space-y-5">
        <!-- Variance Summary Cards -->
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-xl bg-linear-to-br from-neutral-50 to-neutral-100 border border-neutral-200 p-3 text-center">
            <p class="text-[8px] font-bold text-neutral-400 uppercase">Planned</p>
            <p class="text-base font-bold text-neutral-900 tabular-nums">{Number(investigationEntry.planned_qty).toLocaleString()}</p>
            <p class="text-[9px] text-neutral-500">{investigationEntry.unit}</p>
          </div>
          <div class="rounded-xl bg-linear-to-br from-red-50 to-amber-50 border border-amber-200 p-3 text-center">
            <p class="text-[8px] font-bold text-amber-500 uppercase">Actual</p>
            <p class="text-base font-bold text-amber-800 tabular-nums">{Number(investigationEntry.actual_qty).toLocaleString()}</p>
            <p class="text-[9px] text-amber-600">{investigationEntry.unit}</p>
          </div>
          <div class="rounded-xl bg-linear-to-br {Number(investigationEntry.variance_qty) > 0 ? 'from-red-50 to-red-100 border-red-200' : 'from-emerald-50 to-emerald-100 border-emerald-200'} border p-3 text-center">
            <p class="text-[8px] font-bold {Number(investigationEntry.variance_qty) > 0 ? 'text-red-400' : 'text-emerald-400'} uppercase">Excess</p>
            <p class="text-base font-bold {Number(investigationEntry.variance_qty) > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">{Math.abs(Number(investigationEntry.variance_qty)).toLocaleString()}</p>
            <p class="text-[9px] {Number(investigationEntry.variance_qty) > 0 ? 'text-red-500' : 'text-emerald-500'}">{investigationEntry.unit}</p>
          </div>
        </div>

        <!-- Root Cause Selection (visual cards) -->
        <div>
          <label class="block text-xs font-bold text-neutral-800 mb-2">Wastage Categorization *</label>
          <div class="grid grid-cols-3 gap-2">
            {#each ROOT_CAUSES as cause}
              <button type="button" onclick={() => { invForm.root_cause = cause.value; }}
                class="rounded-xl border-2 p-3 text-center transition-all {invForm.root_cause === cause.value ? 'border-amber-500 bg-amber-50 shadow-md ring-2 ring-amber-200' : 'border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-sm'}">
                <span class="text-lg">{cause.icon}</span>
                <p class="text-[9px] font-bold mt-1 {invForm.root_cause === cause.value ? 'text-amber-800' : 'text-neutral-600'}">{cause.label}</p>
              </button>
            {/each}
          </div>
        </div>

        <!-- Severity -->
        <div>
          <label class="block text-xs font-bold text-neutral-800 mb-2">Severity Level</label>
          <div class="flex gap-2">
            {#each [["low", "Low", "bg-emerald-500"], ["medium", "Medium", "bg-amber-500"], ["high", "High", "bg-orange-500"], ["critical", "Critical", "bg-red-500"]] as [val, label, color]}
              <button type="button" onclick={() => { invForm.severity = val; }}
                class="flex-1 rounded-lg border-2 py-2.5 text-xs font-bold text-center transition-all {invForm.severity === val ? `border-neutral-900 ${color} text-white shadow-md` : 'border-neutral-200 text-neutral-500 hover:border-neutral-300'}">
                {label}
              </button>
            {/each}
          </div>
        </div>

        <!-- Photo Evidence -->
        <div>
          <label class="block text-xs font-bold text-neutral-800 mb-2">Photo Evidence</label>
          <input type="file" accept="image/*" capture="environment"
            class="hidden" id="variance-photo-input"
            onchange={(e) => { invPhoto = (e.target as HTMLInputElement).files?.[0] || null; }}
          />
          <button type="button" onclick={() => document.getElementById("variance-photo-input")?.click()}
            class="w-full rounded-xl border-2 border-dashed {invPhoto ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50/30'} p-4 text-center hover:border-amber-400 transition-colors">
            {#if invPhoto}
              <span class="text-emerald-700 font-semibold text-sm">{invPhoto.name}</span>
              <p class="text-[9px] text-emerald-500 mt-1">Click to change photo</p>
            {:else}
              <svg class="mx-auto h-7 w-7 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" /></svg>
              <p class="text-xs text-amber-600 font-medium mt-1">Capture or upload site photo</p>
              <p class="text-[9px] text-amber-400">Show area of over-consumption</p>
            {/if}
          </button>
        </div>

        <!-- Supervisor Notes -->
        <div>
          <label class="block text-xs font-bold text-neutral-800 mb-2">Supervisor Notes *</label>
          <textarea bind:value={invForm.supervisor_notes} rows="3"
            placeholder="Explain the variance... e.g. 'Unexpected soil porosity required deeper blinding — additional 30 bags consumed for foundation stabilisation'"
            class="w-full rounded-xl border-2 border-neutral-200 px-4 py-3 text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 resize-none"
            style="font-family: Raleway, sans-serif; font-weight: 300;"></textarea>
          <p class="text-[9px] text-neutral-400 mt-1">This is a mandatory field — justify the over-consumption.</p>
        </div>

        <!-- Corrective Action -->
        <div>
          <label class="block text-xs font-bold text-neutral-800 mb-2">Corrective Action Plan</label>
          <textarea bind:value={invForm.corrective_action} rows="2"
            placeholder="Preventive measures for future phases..."
            class="w-full rounded-xl border-2 border-neutral-200 px-4 py-3 text-sm focus:outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100 resize-none"></textarea>
        </div>

        <!-- Financial Impact -->
        <div class="rounded-xl bg-linear-to-r from-red-50 via-amber-50 to-orange-50 border border-amber-200 p-4">
          <p class="text-[9px] font-bold text-amber-600 uppercase tracking-widest">Financial Impact</p>
          <p class="text-xl font-bold text-amber-800 tabular-nums mt-1">
            {currency.format(Math.abs(Number(investigationEntry.actual_value) - Number(investigationEntry.planned_value)))}
          </p>
          <p class="text-[9px] text-amber-500 mt-0.5">excess cost from over-consumption</p>
        </div>

        <!-- Submit -->
        <div class="sticky bottom-0 bg-white/95 border-t border-neutral-100 -mx-6 px-6 py-4 flex gap-3" style="backdrop-filter: blur(10px)">
          <button onclick={() => { showInvestigation = false; }} class="flex-1 rounded-xl border-2 border-neutral-200 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
          <button onclick={submitInvestigation} disabled={investigationSaving}
            class="flex-1 rounded-xl bg-linear-to-r from-amber-600 to-orange-600 py-3 text-sm font-bold text-white hover:from-amber-700 hover:to-orange-700 disabled:opacity-50 shadow-lg">
            {investigationSaving ? "Filing..." : "File Investigation"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

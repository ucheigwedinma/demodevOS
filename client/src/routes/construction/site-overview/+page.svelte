<script lang="ts">
  import { api } from "$lib/api";
  import AreaChart from "$lib/components/charts/AreaChart.svelte";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
  import GroupedBarChart from "$lib/components/charts/GroupedBarChart.svelte";
  import HorizontalBarChart from "$lib/components/charts/HorizontalBarChart.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    ConstructionContractorPerformanceBand,
    ConstructionSiteOverview,
    ProjectExecutionInspectionStatus,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const today = new Date();
  const todayIso = toDateInput(today);
  const defaultStartIso = toDateInput(new Date(today.getTime() - 1000 * 60 * 60 * 24 * 90));

  let loading = $state(true);
  let refreshing = $state(false);
  let data = $state<ConstructionSiteOverview | null>(null);
  let selectedProject = $state("");
  let startDate = $state(defaultStartIso);
  let endDate = $state(todayIso);

  function toDateInput(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function fmtCount(value: number): string {
    return value.toLocaleString("en-US");
  }

  function fmtPercent(value: number, fractionDigits = 1): string {
    return `${value.toFixed(fractionDigits)}%`;
  }

  function fmtSignedDays(value: number): string {
    const sign = value > 0 ? "+" : "";
    return `${sign}${value.toFixed(1)}d`;
  }

  function fmtCurrency(value: number): string {
    return currency.formatAbbreviated(value);
  }

  function fmtAxisCurrency(value: number): string {
    return currency.formatAbbreviated(value);
  }

  function fmtDateTick(value: unknown): string {
    if (!(value instanceof Date)) return "";
    return value.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function fmtMonth(isoDate: string): string {
    const d = new Date(`${isoDate}T00:00:00`);
    if (Number.isNaN(d.getTime())) return isoDate;
    return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  }

  function inspectionStatusLabel(status: ProjectExecutionInspectionStatus): string {
    const labels: Record<ProjectExecutionInspectionStatus, string> = {
      planned: "Planned",
      in_progress: "In Progress",
      passed: "Passed",
      failed: "Failed",
      blocked: "Blocked",
      closed: "Closed",
    };
    return labels[status] ?? status;
  }

  function contractorBandLabel(band: ConstructionContractorPerformanceBand): string {
    const labels: Record<ConstructionContractorPerformanceBand, string> = {
      strong: "Strong",
      watch: "Watch",
      weak: "Weak",
    };
    return labels[band] ?? band;
  }

  function contractorBandClass(band: ConstructionContractorPerformanceBand): string {
    if (band === "strong") return "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300";
    if (band === "weak") return "bg-rose-100 text-rose-800 ring-1 ring-rose-300";
    return "bg-amber-100 text-amber-800 ring-1 ring-amber-300";
  }

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {
      start_date: startDate,
      end_date: endDate,
    };
    if (selectedProject) {
      params.project = selectedProject;
    }
    return params;
  }

  async function fetchOverview(silent = false) {
    if (silent) {
      refreshing = true;
    } else {
      loading = true;
    }

    try {
      const payload = await api.get<ConstructionSiteOverview>(
        "/projects/construction/site-overview/",
        buildParams(),
      );
      data = payload;

      if (!selectedProject && payload.filters.project) {
        selectedProject = String(payload.filters.project);
      }
      if (!startDate) startDate = payload.filters.start_date;
      if (!endDate) endDate = payload.filters.end_date;
    } catch {
      data = null;
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  $effect(() => {
    fetchOverview();
  });

  function applyFilters() {
    fetchOverview(true);
  }

  function resetFilters() {
    selectedProject = "";
    startDate = defaultStartIso;
    endDate = todayIso;
    fetchOverview(true);
  }

  const progressCurveData = $derived.by(() => {
    if (!data) return [];
    return data.widgets.progress_curve.map((row) => ({
      x: new Date(`${row.date}T00:00:00`),
      y: row.progress_percent,
    }));
  });

  const costVsBudgetData = $derived.by(() => {
    if (!data) return [];
    return data.widgets.cost_vs_budget.map((row) => ({
      label: row.project_name,
      value1: row.planned,
      value2: row.actual,
    }));
  });

  const labourDistributionData = $derived.by(() => {
    if (!data) return [];
    return data.widgets.labour_distribution
      .filter((row) => row.count > 0)
      .map((row) => ({ label: row.label, value: row.count }));
  });

  const materialConsumptionData = $derived.by(() => {
    if (!data) return [];
    return data.widgets.material_consumption.map((row) => ({
      label: fmtMonth(row.period),
      value: row.amount,
    }));
  });

  const safetyIndexData = $derived.by(() => {
    if (!data) return [];
    return data.widgets.safety_index.map((row) => ({
      x: new Date(`${row.period}T00:00:00`),
      y: row.index,
    }));
  });

  const inspectionStatusData = $derived.by(() => {
    if (!data) return [];
    return data.widgets.inspection_status
      .filter((row) => row.count > 0)
      .map((row) => ({
        label: inspectionStatusLabel(row.status),
        value: row.count,
      }));
  });

  const kpiCardBaseClass =
    "rounded-xl border p-4 shadow-sm transition-colors hover:shadow-md";
  const kpiLabelClass = "text-[10px] font-semibold text-neutral-600 uppercase tracking-wider";
  const kpiValueClass = "mt-1 text-xl font-bold text-neutral-900 tabular-nums";
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !data}
  <div class="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
    <p class="text-sm font-medium text-red-700">Could not load Construction Site Overview.</p>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex flex-wrap items-start justify-between gap-4 w-full">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-400">Construction</p>
          <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Site Overview</h1>
          <p class="mt-1 text-sm text-neutral-500">Simplify construction project planning, scheduling, and site coordination</p>
        </div>
        <button
          onclick={() => fetchOverview(true)}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <label class="text-xs text-neutral-500">
          Project
          <select
            bind:value={selectedProject}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          >
            <option value="">All projects</option>
            {#each data.projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs text-neutral-500">
          Start date
          <DateInput bind:value={startDate} />
        </label>

        <label class="text-xs text-neutral-500">
          End date
          <DateInput bind:value={endDate} />
        </label>

        <div class="flex items-end gap-2">
          <button
            onclick={applyFilters}
            class="flex-1 rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Apply
          </button>
          <button
            onclick={resetFilters}
            class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Reset
          </button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      <div class={`${kpiCardBaseClass} border-cyan-100 bg-linear-to-br from-white to-cyan-50`}>
        <p class={kpiLabelClass}>Project Progress</p>
        <p class={kpiValueClass}>{fmtPercent(data.kpis.project_progress_percent)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-blue-100 bg-linear-to-br from-white to-blue-50`}>
        <p class={kpiLabelClass}>Schedule Variance</p>
        <p class={kpiValueClass}>{fmtSignedDays(data.kpis.schedule_variance_days)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-violet-100 bg-linear-to-br from-white to-violet-50`}>
        <p class={kpiLabelClass}>Cost Variance</p>
        <p class={kpiValueClass}>{fmtCurrency(data.kpis.cost_variance_amount)}</p>
        <p class="mt-0.5 text-[11px] text-slate-600">{fmtPercent(data.kpis.cost_variance_percent)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-amber-100 bg-linear-to-br from-white to-amber-50`}>
        <p class={kpiLabelClass}>Open RFIs</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.open_rfis)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-lime-100 bg-linear-to-br from-white to-lime-50`}>
        <p class={kpiLabelClass}>Pending Inspections</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.pending_inspections)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-rose-100 bg-linear-to-br from-white to-rose-50`}>
        <p class={kpiLabelClass}>Safety Incidents</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.safety_incidents)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-emerald-100 bg-linear-to-br from-white to-emerald-50`}>
        <p class={kpiLabelClass}>Material Shortages</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.material_shortages)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-fuchsia-100 bg-linear-to-br from-white to-fuchsia-50`}>
        <p class={kpiLabelClass}>Workforce Count</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.workforce_count)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-indigo-100 bg-linear-to-br from-white to-indigo-50`}>
        <p class={kpiLabelClass}>Equipment Utilization</p>
        <p class={kpiValueClass}>{fmtPercent(data.kpis.equipment_utilization_percent)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-purple-100 bg-linear-to-br from-white to-purple-50`}>
        <p class={kpiLabelClass}>Quality Issues</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.quality_issues)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-orange-100 bg-linear-to-br from-white to-orange-50`}>
        <p class={kpiLabelClass}>Delayed Tasks</p>
        <p class={kpiValueClass}>{fmtCount(data.kpis.delayed_tasks)}</p>
      </div>

      <div class={`${kpiCardBaseClass} border-sky-100 bg-linear-to-br from-white to-sky-50`}>
        <p class={kpiLabelClass}>Contractor Performance</p>
        <div class="mt-1 flex items-center gap-2">
          <p class={kpiValueClass}>{fmtPercent(data.kpis.contractor_performance_score)}</p>
          <span class={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${contractorBandClass(data.kpis.contractor_performance_band)}`}>
            {contractorBandLabel(data.kpis.contractor_performance_band)}
          </span>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div class="rounded-2xl border border-sky-100 bg-linear-to-br from-white to-sky-50 p-5 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-800">Progress Curve</h3>
        <div class="rounded-xl bg-white/95 p-3">
          <AreaChart
            data={progressCurveData}
            xKey="x"
            yKey="y"
            color="#0284c7"
            formatX={fmtDateTick}
            formatY={(value) => fmtPercent(Number(value), 0)}
            height={300}
          />
        </div>
      </div>

      <div class="rounded-2xl border border-indigo-100 bg-linear-to-br from-white to-indigo-50 p-5 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-800">Cost vs Budget</h3>
        <div class="rounded-xl bg-white/95 p-3">
          <GroupedBarChart
            data={costVsBudgetData}
            labelKey="label"
            value1Key="value1"
            value2Key="value2"
            label1="Budget"
            label2="Actual"
            color1="#818cf8"
            color2="#4f46e5"
            formatValue={fmtCurrency}
            formatAxisValue={fmtAxisCurrency}
            height={320}
          />
        </div>
      </div>

      <div class="rounded-2xl border border-fuchsia-100 bg-linear-to-br from-white to-fuchsia-50 p-5 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-800">Labour Distribution</h3>
        <div class="rounded-xl bg-white/95 p-3">
          <DonutChart
            data={labourDistributionData}
            labelKey="label"
            valueKey="value"
            centerLabel="Headcount"
            centerValue={fmtCount(data.kpis.workforce_count)}
            colors={["#ec4899", "#d946ef", "#a855f7", "#f97316", "#f59e0b", "#06b6d4", "#3b82f6", "#14b8a6"]}
            size={210}
          />
        </div>
      </div>

      <div class="rounded-2xl border border-amber-100 bg-linear-to-br from-white to-amber-50 p-5 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-800">Material Consumption</h3>
        <div class="rounded-xl bg-white/95 p-3">
          <BarChart
            data={materialConsumptionData}
            labelKey="label"
            valueKey="value"
            colors={["#f97316", "#fb7185", "#f59e0b", "#84cc16", "#22c55e", "#06b6d4"]}
            formatValue={fmtAxisCurrency}
            height={300}
          />
        </div>
      </div>

      <div class="rounded-2xl border border-emerald-100 bg-linear-to-br from-white to-emerald-50 p-5 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-800">Safety Index</h3>
        <div class="rounded-xl bg-white/95 p-3">
          <AreaChart
            data={safetyIndexData}
            xKey="x"
            yKey="y"
            color="#059669"
            formatX={fmtDateTick}
            formatY={(value) => fmtPercent(Number(value), 0)}
            height={300}
          />
        </div>
      </div>

      <div class="rounded-2xl border border-purple-100 bg-linear-to-br from-white to-purple-50 p-5 shadow-sm">
        <h3 class="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-800">Inspection Status</h3>
        <div class="rounded-xl bg-white/95 p-3">
          <HorizontalBarChart
            data={inspectionStatusData}
            labelKey="label"
            valueKey="value"
            colors={["#7c3aed", "#a855f7", "#d946ef", "#4f46e5", "#0891b2", "#0d9488"]}
            formatValue={(value) => fmtCount(value)}
            height={300}
          />
        </div>
      </div>
    </div>
  </div>
{/if}

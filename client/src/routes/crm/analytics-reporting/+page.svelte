<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    CRMAnalyticsAutomationRunResult,
    CRMAnalyticsReportingOverview,
  } from "$lib/types";

  const sourcePageSize = 8;
  const agentPageSize = 8;

  let loading = $state(true);
  let overviewError = $state<string | null>(null);
  let refreshing = $state(false);
  let runningWeeklyReport = $state(false);
  let checkingPipelineDrop = $state(false);
  let syncingProjectInsights = $state(false);
  let syncingProcurementInsights = $state(false);

  let windowDays = $state("90");
  let lookbackDays = $state("7");
  let overview = $state<CRMAnalyticsReportingOverview | null>(null);
  let sourcePage = $state(1);
  let agentPage = $state(1);

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtMoney(value: unknown): string {
    return currency.format(toNumber(value));
  }

  function fmtPct(value: number | null | undefined): string {
    if (value === null || value === undefined) return "--";
    return `${value.toFixed(1)}%`;
  }

  function fmtDays(value: number | null | undefined): string {
    if (value === null || value === undefined) return "--";
    return `${value} days`;
  }

  function fmtLabel(value: string | null | undefined): string {
    if (!value) return "--";
    return value.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "--";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "--";
    return dt.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function pageNumbers(current: number, total: number): number[] {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let page = start; page <= end; page += 1) pages.push(page);
    return pages;
  }

  const sourceRows = $derived(overview?.lead_source_performance ?? []);
  const sourceTotalPages = $derived(Math.max(1, Math.ceil(sourceRows.length / sourcePageSize)));
  const sourcePageRows = $derived.by(() => {
    const start = (sourcePage - 1) * sourcePageSize;
    return sourceRows.slice(start, start + sourcePageSize);
  });
  const sourcePageNumbers = $derived.by(() => pageNumbers(sourcePage, sourceTotalPages));

  const agentRows = $derived(overview?.agent_performance ?? []);
  const agentTotalPages = $derived(Math.max(1, Math.ceil(agentRows.length / agentPageSize)));
  const agentPageRows = $derived.by(() => {
    const start = (agentPage - 1) * agentPageSize;
    return agentRows.slice(start, start + agentPageSize);
  });
  const agentPageNumbers = $derived.by(() => pageNumbers(agentPage, agentTotalPages));
  const projectsIntegration = $derived(
    overview?.projects_integration ?? {
      last_synced_at: null,
      demand_insight_count: 0,
      high_demand_insight_count: 0,
      top_demand_areas: [],
      high_demand_areas: [],
    },
  );
  const procurementIntegration = $derived(
    overview?.procurement_integration ?? {
      last_synced_at: null,
      bulk_demand_insight_count: 0,
      furnishing_package_count: 0,
      add_on_package_count: 0,
      triggered_areas: [],
      package_recommendations: [],
    },
  );

  $effect(() => {
    sourceRows.length;
    if (sourcePage > sourceTotalPages) sourcePage = sourceTotalPages;
  });

  $effect(() => {
    agentRows.length;
    if (agentPage > agentTotalPages) agentPage = agentTotalPages;
  });

  async function fetchOverview() {
    if (!loading) refreshing = true;
    overviewError = null;
    try {
      overview = await api.get<CRMAnalyticsReportingOverview>("/crm/analytics-reporting/overview/", {
        window_days: windowDays,
        lookback_days: lookbackDays,
      });
    } catch (err) {
      console.error("[crm/analytics-reporting]", err);
      overview = null;
      overviewError = err instanceof Error ? err.message : "Could not load CRM analytics and reporting.";
      toast.error("Load failed", "Could not load CRM analytics and reporting.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function refreshOverview() {
    sourcePage = 1;
    agentPage = 1;
    await fetchOverview();
  }

  async function runWeeklyReport() {
    if (runningWeeklyReport) return;
    runningWeeklyReport = true;
    try {
      const result = await api.post<CRMAnalyticsAutomationRunResult>(
        "/crm/analytics-reporting/run-weekly-report/",
        { window_days: Number(windowDays) },
      );
      if (result.skipped) {
        toast.info("Weekly report skipped", result.reason || "No management recipients found.");
      } else {
        toast.success(
          "Weekly report sent",
          `${result.notifications_sent} notifications, ${result.emails_sent} emails.`,
        );
      }
    } catch (err) {
      console.error("[crm/analytics-reporting]", err);
      toast.error("Run failed", "Could not trigger weekly report automation.");
    } finally {
      runningWeeklyReport = false;
    }
  }

  async function checkPipelineDrop() {
    if (checkingPipelineDrop) return;
    checkingPipelineDrop = true;
    try {
      const result = await api.post<CRMAnalyticsAutomationRunResult>(
        "/crm/analytics-reporting/check-pipeline-drop/",
        { lookback_days: Number(lookbackDays) },
      );
      if (result.alert_triggered) {
        const dropPercent = result.pipeline_drop?.drop_percent ?? 0;
        toast.warning(
          "Pipeline drop alert triggered",
          `Drop detected at ${dropPercent.toFixed(1)}%. Management has been notified.`,
        );
      } else {
        toast.info("Pipeline healthy", "No alert triggered for the selected lookback period.");
      }
      await fetchOverview();
    } catch (err) {
      console.error("[crm/analytics-reporting]", err);
      toast.error("Run failed", "Could not evaluate pipeline drop automation.");
    } finally {
      checkingPipelineDrop = false;
    }
  }

  async function syncProjectDemandInsights() {
    if (syncingProjectInsights) return;
    syncingProjectInsights = true;
    try {
      const result = await api.post<CRMAnalyticsAutomationRunResult>(
        "/crm/analytics-reporting/sync-project-demand-insights/",
        { window_days: Number(windowDays), force: true },
      );
      if (result.skipped) {
        toast.info("Project demand sync skipped", result.reason || "No demand data available in this window.");
      } else {
        const triggered = result.high_demand_triggered ?? 0;
        toast.success(
          "Project demand insights synced",
          `${result.insights_upserted ?? 0} insights updated, ${triggered} high-demand triggers.`,
        );
      }
      await fetchOverview();
    } catch (err) {
      console.error("[crm/analytics-reporting]", err);
      toast.error("Run failed", "Could not sync CRM demand insights to Projects.");
    } finally {
      syncingProjectInsights = false;
    }
  }

  async function syncProcurementDemandInsights() {
    if (syncingProcurementInsights) return;
    syncingProcurementInsights = true;
    try {
      const result = await api.post<CRMAnalyticsAutomationRunResult>(
        "/crm/analytics-reporting/sync-procurement-demand-insights/",
        { window_days: Number(windowDays), force: true },
      );
      if (result.skipped) {
        toast.info("Procurement demand sync skipped", result.reason || "No demand data available in this window.");
      } else {
        const triggered = result.package_triggers ?? 0;
        toast.success(
          "Procurement demand insights synced",
          `${result.insights_upserted ?? 0} insights updated, ${triggered} package triggers.`,
        );
      }
      await fetchOverview();
    } catch (err) {
      console.error("[crm/analytics-reporting]", err);
      toast.error("Run failed", "Could not sync CRM demand insights to Procurement.");
    } finally {
      syncingProcurementInsights = false;
    }
  }

  function goToSourcePage(page: number) {
    if (page < 1 || page > sourceTotalPages || page === sourcePage) return;
    sourcePage = page;
  }

  function goToAgentPage(page: number) {
    if (page < 1 || page > agentTotalPages || page === agentPage) return;
    agentPage = page;
  }

  onMount(() => {
    void fetchOverview();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-teal-600">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Analytics & Reporting</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Strategic insight workspace for conversion, velocity, revenue forecast, source quality, and agent output.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <label class="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-600">
        Window
        <select
          bind:value={windowDays}
          onchange={refreshOverview}
          class="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-700"
        >
          <option value="30">30 days</option>
          <option value="60">60 days</option>
          <option value="90">90 days</option>
          <option value="180">180 days</option>
          <option value="365">365 days</option>
        </select>
      </label>
      <label class="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-600">
        Drop Lookback
        <select
          bind:value={lookbackDays}
          onchange={refreshOverview}
          class="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-700"
        >
          <option value="3">3 days</option>
          <option value="7">7 days</option>
          <option value="14">14 days</option>
          <option value="21">21 days</option>
          <option value="30">30 days</option>
        </select>
      </label>
      <button
        onclick={refreshOverview}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50"
        disabled={refreshing}
      >
        {refreshing ? "Refreshing..." : "Refresh"}
      </button>
      <button
        onclick={runWeeklyReport}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        disabled={runningWeeklyReport}
      >
        {runningWeeklyReport ? "Sending..." : "Send Weekly Report"}
      </button>
      <button
        onclick={checkPipelineDrop}
        class="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-100 disabled:opacity-50"
        disabled={checkingPipelineDrop}
      >
        {checkingPipelineDrop ? "Checking..." : "Check Pipeline Drop"}
      </button>
      <button
        onclick={syncProjectDemandInsights}
        class="rounded-lg border border-sky-300 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-800 hover:bg-sky-100 disabled:opacity-50"
        disabled={syncingProjectInsights}
      >
        {syncingProjectInsights ? "Syncing..." : "Sync Project Insights"}
      </button>
      <button
        onclick={syncProcurementDemandInsights}
        class="rounded-lg border border-rose-300 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-800 hover:bg-rose-100 disabled:opacity-50"
        disabled={syncingProcurementInsights}
      >
        {syncingProcurementInsights ? "Syncing..." : "Sync Procurement Insights"}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else if overviewError}
    <DataStateBanner
      title="Couldn't load CRM analytics"
      message={overviewError}
      onretry={fetchOverview}
    />
  {:else if !overview}
    <div class="rounded-xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center text-sm text-neutral-500">
      Analytics data is unavailable right now.
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-7">
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Conversion Rate</p>
        <p class="mt-2 text-base font-semibold text-neutral-900">{fmtPct(overview.summary.conversion_rate)}</p>
      </div>
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Sales Velocity</p>
        <p class="mt-2 text-base font-semibold text-neutral-900">{fmtDays(overview.summary.sales_velocity_days)}</p>
      </div>
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Weighted Forecast</p>
        <p class="mt-2 text-base font-semibold text-neutral-900 tabular-nums">{fmtMoney(overview.summary.weighted_forecast)}</p>
      </div>
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Lead Sources</p>
        <p class="mt-2 text-base font-semibold text-neutral-900">{overview.lead_source_performance.length}</p>
      </div>
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Agents Tracked</p>
        <p class="mt-2 text-base font-semibold text-neutral-900">{overview.agent_performance.length}</p>
      </div>
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Campaign ROI</p>
        <p class="mt-2 text-base font-semibold text-neutral-900">{fmtPct(overview.campaign_performance.roi_percent)}</p>
      </div>
      <div class="rounded-xl border border-[#b8dfd9] bg-[#eaf8f5] p-4">
        <p class="text-[11px] font-medium uppercase tracking-wide text-neutral-500">Generated Leads</p>
        <p class="mt-2 text-base font-semibold text-neutral-900">{overview.campaign_performance.generated_leads}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-700">Conversion Rates</h2>
          <span class="text-xs text-neutral-500">Window: {overview.window_days} days</span>
        </div>
        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="rounded-lg border border-[#efc4d8] bg-[#fff0f6] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Overall</p>
            <p class="mt-1 text-base font-semibold text-neutral-900">{fmtPct(overview.conversion_rates.overall_conversion_rate)}</p>
          </div>
          <div class="rounded-lg border border-[#efc4d8] bg-[#fff0f6] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Qualified+</p>
            <p class="mt-1 text-base font-semibold text-neutral-900">{fmtPct(overview.conversion_rates.qualified_conversion_rate)}</p>
          </div>
          <div class="rounded-lg border border-[#efc4d8] bg-[#fff0f6] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Win Rate</p>
            <p class="mt-1 text-base font-semibold text-neutral-900">{fmtPct(overview.conversion_rates.win_rate)}</p>
          </div>
        </div>
        <div class="mt-4 overflow-x-auto">
          <table class="w-full min-w-[620px]">
            <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Stage Path</th>
                <th class="px-3 py-2 text-right">Eligible</th>
                <th class="px-3 py-2 text-right">Progressed</th>
                <th class="px-3 py-2 text-right">Conversion</th>
                <th class="px-3 py-2 text-right">Avg Days</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each overview.conversion_rates.stage_conversion as row}
                <tr class="text-sm text-neutral-700">
                  <td class="px-3 py-3 font-medium text-neutral-900">{row.label}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.eligible_count}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.progressed_count}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.conversion_rate)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtDays(row.avg_days_to_progress)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-700">Sales Velocity & Revenue Forecast</h2>
        <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div class="rounded-lg border border-[#d8c3f2] bg-[#f4eefe] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Avg Days To Close</p>
            <p class="mt-1 text-base font-semibold text-neutral-900">{fmtDays(overview.sales_velocity.avg_days_to_close)}</p>
          </div>
          <div class="rounded-lg border border-[#d8c3f2] bg-[#f4eefe] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Deals / Month</p>
            <p class="mt-1 text-base font-semibold text-neutral-900 tabular-nums">{overview.sales_velocity.deals_per_month}</p>
          </div>
          <div class="rounded-lg border border-[#d8c3f2] bg-[#f4eefe] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Pipeline Value</p>
            <p class="mt-1 text-base font-semibold text-neutral-900 tabular-nums">{fmtMoney(overview.revenue_forecast.pipeline_value)}</p>
          </div>
          <div class="rounded-lg border border-[#d8c3f2] bg-[#f4eefe] px-3 py-2">
            <p class="text-[11px] uppercase tracking-wide text-neutral-500">Closed Won Value</p>
            <p class="mt-1 text-base font-semibold text-neutral-900 tabular-nums">{fmtMoney(overview.revenue_forecast.closed_won_value)}</p>
          </div>
        </div>
        <div class="mt-4 overflow-x-auto">
          <table class="w-full min-w-[620px]">
            <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Stage</th>
                <th class="px-3 py-2 text-right">Deals</th>
                <th class="px-3 py-2 text-right">Deal Value</th>
                <th class="px-3 py-2 text-right">Weighted</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if overview.revenue_forecast.stage_breakdown.length === 0}
                <tr>
                  <td colspan="4" class="px-3 py-10 text-center text-sm text-neutral-500">No forecast stage data.</td>
                </tr>
              {:else}
                {#each overview.revenue_forecast.stage_breakdown as row}
                  <tr class="text-sm text-neutral-700">
                    <td class="px-3 py-3 font-medium text-neutral-900">{row.stage}</td>
                    <td class="px-3 py-3 text-right tabular-nums">{row.count}</td>
                    <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.deal_value)}</td>
                    <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.weighted_value)}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-5 py-4">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-700">Lead Source Performance</h2>
      </div>
      <div class="overflow-x-auto p-5">
        <table class="w-full min-w-[1020px]">
          <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="px-3 py-2">Source</th>
              <th class="px-3 py-2 text-right">Leads</th>
              <th class="px-3 py-2 text-right">Won</th>
              <th class="px-3 py-2 text-right">Conversion</th>
              <th class="px-3 py-2 text-right">Avg Score</th>
              <th class="px-3 py-2 text-right">Pipeline Value</th>
              <th class="px-3 py-2 text-right">Weighted Forecast</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#if sourcePageRows.length === 0}
              <tr>
                <td colspan="7" class="px-3 py-10 text-center text-sm text-neutral-500">No lead-source performance data.</td>
              </tr>
            {:else}
              {#each sourcePageRows as row}
                <tr class="text-sm text-neutral-700">
                  <td class="px-3 py-3 font-medium text-neutral-900">{row.source_name}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.total_leads}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.won_leads}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.conversion_rate)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.average_score.toFixed(1)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.pipeline_value)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.weighted_forecast)}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-5 py-3">
        <p class="text-sm text-neutral-500">
          Showing {sourceRows.length === 0 ? 0 : (sourcePage - 1) * sourcePageSize + 1}&ndash;{Math.min(sourcePage * sourcePageSize, sourceRows.length)} of {sourceRows.length}
        </p>
        {#if sourceTotalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToSourcePage(sourcePage - 1)}
              disabled={sourcePage <= 1}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            {#each sourcePageNumbers as pageNo}
              <button
                onclick={() => goToSourcePage(pageNo)}
                class="rounded-lg border px-3 py-1.5 text-sm transition-colors {pageNo === sourcePage ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50'}"
              >
                {pageNo}
              </button>
            {/each}
            <button
              onclick={() => goToSourcePage(sourcePage + 1)}
              disabled={sourcePage >= sourceTotalPages}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        {/if}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-5 py-4">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-700">Agent Performance</h2>
      </div>
      <div class="overflow-x-auto p-5">
        <table class="w-full min-w-[1200px]">
          <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="px-3 py-2">Agent</th>
              <th class="px-3 py-2 text-right">Total Leads</th>
              <th class="px-3 py-2 text-right">Won</th>
              <th class="px-3 py-2 text-right">Conversion</th>
              <th class="px-3 py-2 text-right">Avg Days To Close</th>
              <th class="px-3 py-2 text-right">Activities</th>
              <th class="px-3 py-2 text-right">Pipeline Value</th>
              <th class="px-3 py-2 text-right">Weighted Forecast</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#if agentPageRows.length === 0}
              <tr>
                <td colspan="8" class="px-3 py-10 text-center text-sm text-neutral-500">No agent performance data.</td>
              </tr>
            {:else}
              {#each agentPageRows as row}
                <tr class="text-sm text-neutral-700">
                  <td class="px-3 py-3 font-medium text-neutral-900">{row.agent_name}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.total_leads}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.won_leads}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.conversion_rate)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtDays(row.avg_days_to_close)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.activity_count}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.pipeline_value)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.weighted_forecast)}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-5 py-3">
        <p class="text-sm text-neutral-500">
          Showing {agentRows.length === 0 ? 0 : (agentPage - 1) * agentPageSize + 1}&ndash;{Math.min(agentPage * agentPageSize, agentRows.length)} of {agentRows.length}
        </p>
        {#if agentTotalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToAgentPage(agentPage - 1)}
              disabled={agentPage <= 1}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            {#each agentPageNumbers as pageNo}
              <button
                onclick={() => goToAgentPage(pageNo)}
                class="rounded-lg border px-3 py-1.5 text-sm transition-colors {pageNo === agentPage ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 text-neutral-700 hover:bg-neutral-50'}"
              >
                {pageNo}
              </button>
            {/each}
            <button
              onclick={() => goToAgentPage(agentPage + 1)}
              disabled={agentPage >= agentTotalPages}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        {/if}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-5 py-4">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-700">Campaign Performance Feed</h2>
      </div>
      <div class="grid grid-cols-2 gap-3 p-5 lg:grid-cols-6">
        <div class="rounded-lg border border-[#f3cdb4] bg-[#fff2e9] px-3 py-2">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Total Campaigns</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{overview.campaign_performance.total_campaigns}</p>
        </div>
        <div class="rounded-lg border border-[#f3cdb4] bg-[#fff2e9] px-3 py-2">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Running</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{overview.campaign_performance.running_campaigns}</p>
        </div>
        <div class="rounded-lg border border-[#f3cdb4] bg-[#fff2e9] px-3 py-2">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Completed</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{overview.campaign_performance.completed_campaigns}</p>
        </div>
        <div class="rounded-lg border border-[#f3cdb4] bg-[#fff2e9] px-3 py-2">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Generated Leads</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{overview.campaign_performance.generated_leads}</p>
        </div>
        <div class="rounded-lg border border-[#f3cdb4] bg-[#fff2e9] px-3 py-2">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Total Spend</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{fmtMoney(overview.campaign_performance.total_spend)}</p>
        </div>
        <div class="rounded-lg border border-[#f3cdb4] bg-[#fff2e9] px-3 py-2">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Total Revenue</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900 tabular-nums">{fmtMoney(overview.campaign_performance.total_revenue)}</p>
        </div>
      </div>
      <div class="overflow-x-auto border-t border-neutral-200 p-5">
        <table class="w-full min-w-[1160px]">
          <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="px-3 py-2">Campaign</th>
              <th class="px-3 py-2">Type</th>
              <th class="px-3 py-2">Channel</th>
              <th class="px-3 py-2 text-right">Recipients</th>
              <th class="px-3 py-2 text-right">Generated Leads</th>
              <th class="px-3 py-2 text-right">Delivery</th>
              <th class="px-3 py-2 text-right">Open</th>
              <th class="px-3 py-2 text-right">Click</th>
              <th class="px-3 py-2 text-right">Spend</th>
              <th class="px-3 py-2 text-right">Revenue</th>
              <th class="px-3 py-2 text-right">ROI</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#if overview.campaign_performance.campaigns.length === 0}
              <tr>
                <td colspan="11" class="px-3 py-10 text-center text-sm text-neutral-500">No campaign performance records in this window.</td>
              </tr>
            {:else}
              {#each overview.campaign_performance.campaigns as row}
                <tr class="text-sm text-neutral-700">
                  <td class="px-3 py-3 font-medium text-neutral-900">{row.name}</td>
                  <td class="px-3 py-3">{fmtLabel(row.campaign_type)}</td>
                  <td class="px-3 py-3">{fmtLabel(row.channel)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.total_recipients}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{row.auto_created_leads_count}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.delivery_rate)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.open_rate)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.click_rate)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.spend_amount)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtMoney(row.revenue_attributed)}</td>
                  <td class="px-3 py-3 text-right tabular-nums">{fmtPct(row.roi_percent)}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-700">Automation Status</h2>
      <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-[#f2de97] bg-[#fffbe8] px-3 py-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Weekly Report</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">
            Auto-send to management every Monday at 8:00 AM UTC.
          </p>
        </div>
        <div class="rounded-lg border border-[#f2de97] bg-[#fffbe8] px-3 py-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">Pipeline Drop</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">
            {overview.pipeline_drop_monitor.is_alert ? "Alert condition currently met" : "No current alert condition"}
          </p>
          <p class="mt-1 text-xs text-neutral-500">
            Drop: {fmtPct(overview.pipeline_drop_monitor.drop_percent)} over {overview.pipeline_drop_monitor.lookback_days} days.
          </p>
          <p class="mt-0.5 text-xs text-neutral-500">
            Current vs previous additions: {overview.pipeline_drop_monitor.current_additions_count} vs {overview.pipeline_drop_monitor.previous_additions_count}
          </p>
        </div>
        <div class="rounded-lg border border-[#f2de97] bg-[#fffbe8] px-3 py-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">CRM -> Projects</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">
            {projectsIntegration.high_demand_insight_count} high-demand development insights active.
          </p>
          <p class="mt-1 text-xs text-neutral-500">
            Demand insights: {projectsIntegration.demand_insight_count}
          </p>
          {#if projectsIntegration.last_synced_at}
            <p class="mt-0.5 text-xs text-neutral-500">
              Last sync: {fmtDateTime(projectsIntegration.last_synced_at)}
            </p>
          {/if}
          {#if projectsIntegration.high_demand_areas.length > 0}
            <p class="mt-1 text-xs text-neutral-600">
              Areas: {projectsIntegration.high_demand_areas.map((item) => item.area_name).join(", ")}
            </p>
          {/if}
        </div>
        <div class="rounded-lg border border-[#f2de97] bg-[#fffbe8] px-3 py-3">
          <p class="text-[11px] uppercase tracking-wide text-neutral-500">CRM -> Procurement</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">
            {procurementIntegration.furnishing_package_count + procurementIntegration.add_on_package_count} package insights active.
          </p>
          <p class="mt-1 text-xs text-neutral-500">
            Bulk demand: {procurementIntegration.bulk_demand_insight_count}
          </p>
          <p class="mt-0.5 text-xs text-neutral-500">
            Furnishing: {procurementIntegration.furnishing_package_count} | Add-ons: {procurementIntegration.add_on_package_count}
          </p>
          {#if procurementIntegration.last_synced_at}
            <p class="mt-0.5 text-xs text-neutral-500">
              Last sync: {fmtDateTime(procurementIntegration.last_synced_at)}
            </p>
          {/if}
          {#if procurementIntegration.triggered_areas.length > 0}
            <p class="mt-1 text-xs text-neutral-600">
              Areas: {procurementIntegration.triggered_areas.join(", ")}
            </p>
          {/if}
        </div>
      </div>
    </section>
  {/if}
</div>

<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { BoardKpiSnapshot, FinanceCashFlow, FinanceOverview, PortfolioAnalytics } from "$lib/types";

  const TARGETS = {
    vendor_reliability: 85,
    budget_overrun_pct: 10,
    approval_hours: 24,
    procurement_cycle_days: 18,
    emergency_purchases_pct: 8,
  } as const;

  let loading = $state(true);
  let refreshing = $state(false);
  let board = $state<BoardKpiSnapshot | null>(null);
  let previousBoard = $state<BoardKpiSnapshot | null>(null);
  let portfolio = $state<PortfolioAnalytics | null>(null);
  let finance = $state<FinanceOverview | null>(null);
  let cashFlow = $state<FinanceCashFlow | null>(null);
  let requestSeq = 0;

  function clamp(value: number, min = 0, max = 100): number {
    return Math.min(Math.max(value, min), max);
  }

  function toNumber(value: number | string | null | undefined): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatCount(value: number): string {
    return Math.round(value).toLocaleString("en-US");
  }

  function formatMoney(value: number): string {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value);
  }

  function formatPercent(value: number, digits = 1): string {
    return `${value.toFixed(digits)}%`;
  }

  function formatSignedPercent(value: number, digits = 1): string {
    const sign = value > 0 ? "+" : "";
    return `${sign}${value.toFixed(digits)}%`;
  }

  function titleCase(value: string): string {
    return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  const TREND_CHART = {
    width: 560,
    height: 220,
    padLeft: 40,
    padRight: 16,
    padTop: 16,
    padBottom: 28,
  } as const;

  const DONUT_COLORS = ["#0891b2", "#4f46e5", "#16a34a", "#d97706", "#dc2626", "#7c3aed"] as const;

  function dateOnly(value: Date): string {
    const y = value.getFullYear();
    const m = String(value.getMonth() + 1).padStart(2, "0");
    const d = String(value.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function previousWindow(period: { start_date: string; end_date: string }): { start_date: string; end_date: string } {
    const dayMs = 24 * 60 * 60 * 1000;
    const start = new Date(`${period.start_date}T00:00:00`);
    const end = new Date(`${period.end_date}T00:00:00`);
    const days = Math.max(1, Math.round((end.getTime() - start.getTime()) / dayMs) + 1);
    const prevEnd = new Date(start.getTime() - dayMs);
    const prevStart = new Date(prevEnd.getTime() - (days - 1) * dayMs);
    return {
      start_date: dateOnly(prevStart),
      end_date: dateOnly(prevEnd),
    };
  }

  function attainmentScore(snapshot: BoardKpiSnapshot | null): number {
    if (!snapshot) return 0;

    const vendor = clamp(toNumber(snapshot.kpis.vendor_reliability_score.value));
    const budget = clamp((TARGETS.budget_overrun_pct / Math.max(toNumber(snapshot.kpis.budget_overrun_frequency_pct.value), 0.01)) * 100);
    const approval = clamp((TARGETS.approval_hours / Math.max(toNumber(snapshot.kpis.average_approval_time_hours.value), 0.01)) * 100);
    const emergency = clamp((TARGETS.emergency_purchases_pct / Math.max(toNumber(snapshot.kpis.emergency_purchases_pct.value), 0.01)) * 100);

    return (vendor + budget + approval + emergency) / 4;
  }

  function velocityScore(snapshot: BoardKpiSnapshot | null): number {
    if (!snapshot) return 0;
    const approval = clamp((TARGETS.approval_hours / Math.max(toNumber(snapshot.kpis.average_approval_time_hours.value), 0.01)) * 100);
    const procurement = clamp((TARGETS.procurement_cycle_days / Math.max(toNumber(snapshot.kpis.procurement_cycle_time_days.value), 0.01)) * 100);
    return (approval + procurement) / 2;
  }

  function reworkRate(snapshot: BoardKpiSnapshot | null): number {
    if (!snapshot) return 0;
    const budgetOverrun = clamp(toNumber(snapshot.kpis.budget_overrun_frequency_pct.value));
    const emergency = clamp(toNumber(snapshot.kpis.emergency_purchases_pct.value));
    return (budgetOverrun + emergency) / 2;
  }

  async function loadDashboard(manual = false) {
    const seq = ++requestSeq;
    loading = board === null && portfolio === null && !manual;
    refreshing = manual;

    try {
      const [boardPayload, portfolioPayload, financePayload, cashFlowPayload] = await Promise.all([
        api.get<BoardKpiSnapshot>("/analytics/board-kpis/"),
        api.get<PortfolioAnalytics>("/analytics/portfolio/"),
        api.get<FinanceOverview>("/finance/overview/").catch(() => null),
        api.get<FinanceCashFlow>("/finance/cash-flow/", { year: String(new Date().getFullYear()) }).catch(() => null),
      ]);

      const previousRange = previousWindow(boardPayload.period);
      let previousPayload: BoardKpiSnapshot | null = null;
      try {
        previousPayload = await api.get<BoardKpiSnapshot>("/analytics/board-kpis/", previousRange);
      } catch {
        previousPayload = null;
      }

      if (seq !== requestSeq) return;
      board = boardPayload;
      portfolio = portfolioPayload;
      finance = financePayload;
      cashFlow = cashFlowPayload;
      previousBoard = previousPayload;
    } catch {
      if (seq !== requestSeq) return;
      board = null;
      portfolio = null;
      finance = null;
      cashFlow = null;
      previousBoard = null;
      toast.error("Load failed", "Could not load KPI monitor.");
    } finally {
      if (seq !== requestSeq) return;
      loading = false;
      refreshing = false;
    }
  }

  onMount(() => {
    void loadDashboard(false);
  });

  const activeUsers = $derived.by(() => portfolio?.hr_summary.active_employees ?? 0);
  const activeProjects = $derived.by(() => board?.kpis.cost_variance_per_project_pct.project_count ?? 0);
  const currentRevenue = $derived.by(() => toNumber(portfolio?.crm_summary.converted_value ?? 0));
  const targetVsActual = $derived.by(() => attainmentScore(board));

  const growthRate = $derived.by(() => {
    if (!board || !previousBoard) return null;
    const current = attainmentScore(board);
    const previous = attainmentScore(previousBoard);
    if (Math.abs(previous) < 0.001) return null;
    return ((current - previous) / previous) * 100;
  });

  const currentVelocity = $derived.by(() => velocityScore(board));
  const velocityDelta = $derived.by(() => {
    if (!previousBoard) return null;
    return currentVelocity - velocityScore(previousBoard);
  });
  const avgApprovalHours = $derived.by(() => toNumber(board?.kpis.average_approval_time_hours.value ?? 0));
  const procurementCycleDays = $derived.by(() => toNumber(board?.kpis.procurement_cycle_time_days.value ?? 0));

  const qualityPerfectRate = $derived.by(() => clamp(100 - reworkRate(board)));
  const qualityReworkRate = $derived.by(() => clamp(reworkRate(board)));
  const qualityDelta = $derived.by(() => {
    if (!previousBoard) return null;
    const previousPerfectRate = clamp(100 - reworkRate(previousBoard));
    return qualityPerfectRate - previousPerfectRate;
  });

  const SPEND_TONES = [
    "bg-indigo-500",
    "bg-cyan-500",
    "bg-emerald-500",
    "bg-amber-500",
    "bg-rose-500",
  ] as const;

  const vendorSpend = $derived.by(() => {
    const rows = (cashFlow?.expense_by_vendor ?? [])
      .map((row, index) => ({
        label: row.label || "Unattributed",
        value: toNumber(row.value),
        tone: SPEND_TONES[index % SPEND_TONES.length],
      }))
      .filter((row) => row.value > 0)
      .sort((a, b) => b.value - a.value);

    const totalShown = rows.reduce((sum, row) => sum + row.value, 0);
    const totalExpenses = toNumber(cashFlow?.total_expenses ?? 0);
    const otherValue = Math.max(0, totalExpenses - totalShown);

    const shareBase = totalExpenses > 0 ? totalExpenses : totalShown;
    const ranked = rows.map((row) => ({
      ...row,
      share: shareBase > 0 ? (row.value / shareBase) * 100 : 0,
    }));

    if (otherValue > 0 && shareBase > 0) {
      ranked.push({
        label: "Other vendors",
        value: otherValue,
        tone: "bg-neutral-400",
        share: (otherValue / shareBase) * 100,
      });
    }

    return ranked;
  });

  const monthlyBurnRate = $derived.by(() => {
    if (!cashFlow) return 0;
    const expenses = cashFlow.monthly_flow
      .map((row) => toNumber(row.expenses))
      .filter((value) => value > 0);
    if (expenses.length === 0) return 0;
    const trailing = expenses.slice(-3);
    const base = trailing.length > 0 ? trailing : expenses;
    return base.reduce((sum, value) => sum + value, 0) / base.length;
  });

  const closedDeals = $derived.by(() => portfolio?.crm_summary.converted_reservations ?? 0);
  const closedValue = $derived.by(() => toNumber(portfolio?.crm_summary.converted_value ?? 0));
  const avgDealValue = $derived.by(() => (closedDeals > 0 ? closedValue / closedDeals : 0));
  const activePipeline = $derived.by(() => {
    const leads = portfolio?.crm_summary.active_leads ?? 0;
    const reservations = portfolio?.crm_summary.active_reservations ?? 0;
    return leads + reservations;
  });
  const funnelTotal = $derived.by(() => activePipeline + closedDeals);
  const closeRate = $derived.by(() => (funnelTotal > 0 ? (closedDeals / funnelTotal) * 100 : null));

  const budgetRemainingPct = $derived.by(() => clamp(toNumber(cashFlow?.budget_pct_remaining ?? 0)));
  const budgetUsedPct = $derived.by(() => clamp(100 - budgetRemainingPct));
  const burnRunwayMonths = $derived.by(() => {
    const burn = monthlyBurnRate;
    const balance = toNumber(cashFlow?.net_balance ?? 0);
    if (burn <= 0 || balance <= 0) return null;
    return balance / burn;
  });

  const trendMax = $derived.by(() => {
    if (!cashFlow || cashFlow.monthly_flow.length === 0) return 1;
    return Math.max(
      ...cashFlow.monthly_flow.flatMap((row) => [toNumber(row.income), toNumber(row.expenses)]),
      1,
    );
  });

  const trendPoints = $derived.by(() => {
    if (!cashFlow || cashFlow.monthly_flow.length === 0) return [];
    const innerWidth = TREND_CHART.width - TREND_CHART.padLeft - TREND_CHART.padRight;
    const innerHeight = TREND_CHART.height - TREND_CHART.padTop - TREND_CHART.padBottom;
    const count = cashFlow.monthly_flow.length;
    return cashFlow.monthly_flow.map((row, index) => {
      const x = count > 1
        ? TREND_CHART.padLeft + (index / (count - 1)) * innerWidth
        : TREND_CHART.padLeft + innerWidth / 2;
      const income = toNumber(row.income);
      const expenses = toNumber(row.expenses);
      const incomeY = TREND_CHART.padTop + (1 - income / trendMax) * innerHeight;
      const expenseY = TREND_CHART.padTop + (1 - expenses / trendMax) * innerHeight;
      return {
        month: row.month,
        income,
        expenses,
        x,
        incomeY,
        expenseY,
      };
    });
  });

  const incomeLinePoints = $derived.by(() => trendPoints.map((point) => `${point.x},${point.incomeY}`).join(" "));
  const expenseLinePoints = $derived.by(() => trendPoints.map((point) => `${point.x},${point.expenseY}`).join(" "));

  const distributionRows = $derived.by(() => {
    const rows = (portfolio?.type_distribution ?? [])
      .slice()
      .sort((a, b) => b.count - a.count);
    const total = rows.reduce((sum, row) => sum + row.count, 0);
    return rows.map((row, index) => ({
      label: titleCase(row.type),
      count: row.count,
      totalValue: toNumber(row.total_value),
      share: total > 0 ? (row.count / total) * 100 : 0,
      color: DONUT_COLORS[index % DONUT_COLORS.length],
    }));
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !board || !portfolio}
  <div class="rounded-xl border border-neutral-200 bg-white px-6 py-10 text-center">
    <p class="text-sm text-neutral-600">KPI monitor is unavailable right now.</p>
    <button
      type="button"
      onclick={() => loadDashboard(true)}
      class="mt-3 rounded-lg border border-neutral-300 bg-white px-4 py-2 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">KPI Monitor</h1>
        <p class="mt-1 text-sm text-neutral-500">Top-down command view of current status, target attainment, and growth trajectory.</p>
      </div>
      <button
        type="button"
        onclick={() => loadDashboard(true)}
        class="rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
      >
        {refreshing ? "Refreshing..." : "Refresh"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-4 sm:p-5">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">North Star Metrics</h2>
        <span class="rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] font-semibold text-neutral-600">Header Level</span>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <article class="rounded-xl border border-cyan-200 bg-cyan-50/60 p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-800">Current Status</p>
          <p class="mt-1 text-2xl font-bold text-cyan-900 tabular-nums">{formatCount(activeUsers)}</p>
          <p class="mt-1 text-[11px] text-cyan-800/80">Active users</p>
        </article>

        <article class="rounded-xl border border-violet-200 bg-violet-50/60 p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-violet-800">Current Status</p>
          <p class="mt-1 text-2xl font-bold text-violet-900 tabular-nums">{formatMoney(currentRevenue)}</p>
          <p class="mt-1 text-[11px] text-violet-800/80">Current revenue (converted)</p>
        </article>

        <article class="rounded-xl border border-emerald-200 bg-emerald-50/60 p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-800">Current Status</p>
          <p class="mt-1 text-2xl font-bold text-emerald-900 tabular-nums">{formatCount(activeProjects)}</p>
          <p class="mt-1 text-[11px] text-emerald-800/80">Active project count</p>
        </article>

        <article class="rounded-xl border border-amber-200 bg-amber-50/60 p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-800">Target vs Actual</p>
          <p class="mt-1 text-2xl font-bold text-amber-900 tabular-nums">{formatPercent(targetVsActual)}</p>
          <p class="mt-1 text-[11px] text-amber-800/80">Monthly goal attainment</p>
        </article>

        <article class="rounded-xl border border-neutral-300 bg-neutral-50 p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-700">Growth Rate</p>
          <p class="mt-1 text-2xl font-bold tabular-nums {growthRate !== null && growthRate < 0 ? 'text-rose-700' : 'text-neutral-900'}">
            {growthRate === null ? "--" : formatSignedPercent(growthRate)}
          </p>
          <p class="mt-1 text-[11px] text-neutral-600">Compared to previous period</p>
        </article>
      </div>
    </section>

    <section class="grid gap-4 xl:grid-cols-12">
      <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Velocity / Efficiency</h2>
          <span class="rounded-full bg-cyan-50 px-2 py-0.5 text-[10px] font-semibold text-cyan-700">
            {formatPercent(currentVelocity)}
          </span>
        </div>
        <p class="text-xs text-neutral-500">Task execution speed proxy based on approval and procurement cycle times.</p>

        <div class="mt-4 h-2.5 overflow-hidden rounded-full bg-neutral-200">
          <div class="h-full rounded-full bg-cyan-500" style="width: {currentVelocity}%;"></div>
        </div>
        <div class="mt-2 flex items-center justify-between text-[11px]">
          <span class="text-neutral-500">Trend vs previous period</span>
          <span class="font-semibold {velocityDelta !== null && velocityDelta < 0 ? 'text-rose-700' : 'text-emerald-700'}">
            {velocityDelta === null ? "--" : formatSignedPercent(velocityDelta)}
          </span>
        </div>

        <div class="mt-4 grid grid-cols-2 gap-2">
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
            <p class="text-[10px] uppercase tracking-wider text-neutral-500">Avg Approval Time</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{avgApprovalHours.toFixed(1)}h</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
            <p class="text-[10px] uppercase tracking-wider text-neutral-500">Procurement Cycle</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{procurementCycleDays.toFixed(1)}d</p>
          </div>
        </div>
      </article>

      <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Spend by Vendor</h2>
          <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-600">Top outflows · YTD</span>
        </div>
        <p class="text-xs text-neutral-500">Realised cash outflows by vendor for the current period — share of total expenses paid.</p>

        {#if vendorSpend.length === 0}
          <div class="mt-4 rounded-lg border border-dashed border-neutral-200 bg-neutral-50 px-4 py-5 text-sm text-neutral-500">
            No vendor payments recorded for this period.
          </div>
        {:else}
          <div class="mt-4 space-y-3">
            {#each vendorSpend as row}
              <div>
                <div class="mb-1.5 flex items-center justify-between text-[11px]">
                  <span class="truncate font-medium text-neutral-700">{row.label}</span>
                  <span class="tabular-nums text-neutral-600">{formatPercent(row.share)}</span>
                </div>
                <div class="h-2 overflow-hidden rounded-full bg-neutral-200">
                  <div class="h-full rounded-full {row.tone}" style="width: {Math.max(4, row.share)}%;"></div>
                </div>
                <div class="mt-1 flex items-center justify-between text-[10px] text-neutral-500">
                  <span>Paid this period</span>
                  <span class="tabular-nums">{formatMoney(row.value)}</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </article>

      <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
        <div class="mb-3 flex items-center justify-between gap-2">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Quality / Error Rate</h2>
          <span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
            Perfect: {formatPercent(qualityPerfectRate)}
          </span>
        </div>
        <p class="text-xs text-neutral-500">Share of outcomes that clear without rework versus those requiring intervention.</p>

        <div class="mt-4 h-3 overflow-hidden rounded-full bg-neutral-200">
          <div class="flex h-full w-full">
            <div class="h-full bg-emerald-500" style="width: {qualityPerfectRate}%;"></div>
            <div class="h-full bg-rose-500" style="width: {qualityReworkRate}%;"></div>
          </div>
        </div>
        <div class="mt-2 flex items-center justify-between text-[11px]">
          <span class="text-neutral-600">Rework rate</span>
          <span class="font-semibold text-rose-700">{formatPercent(qualityReworkRate)}</span>
        </div>
        <div class="mt-1 flex items-center justify-between text-[11px]">
          <span class="text-neutral-600">Vendor reliability</span>
          <span class="font-semibold text-neutral-900">{formatPercent(toNumber(board.kpis.vendor_reliability_score.value))}</span>
        </div>
        <div class="mt-1 flex items-center justify-between text-[11px]">
          <span class="text-neutral-600">Trend vs previous period</span>
          <span class="font-semibold {qualityDelta !== null && qualityDelta < 0 ? 'text-rose-700' : 'text-emerald-700'}">
            {qualityDelta === null ? "--" : formatSignedPercent(qualityDelta)}
          </span>
        </div>
      </article>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-4 sm:p-5">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Financial &amp; Cost Tracking</h2>
        <span class="rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] font-semibold text-neutral-600">Lean Infrastructure</span>
      </div>

      {#if !cashFlow}
        <div class="rounded-lg border border-dashed border-neutral-200 bg-neutral-50 px-4 py-5 text-sm text-neutral-500">
          Cash-flow feed unavailable. Financial widgets will appear once finance data is accessible.
        </div>
      {:else}
        <div class="grid gap-4 xl:grid-cols-12">
          <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-700">Burn Rate</h3>
              <span class="rounded-full bg-rose-50 px-2 py-0.5 text-[10px] font-semibold text-rose-700">Monthly Recurring</span>
            </div>
            <p class="mt-2 text-2xl font-bold text-neutral-900 tabular-nums">{formatMoney(monthlyBurnRate)}</p>
            <p class="mt-1 text-[11px] text-neutral-500">Average recurring cost over the latest 3 expense months.</p>
            <div class="mt-3 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Total annualized spend</span>
              <span class="font-semibold text-neutral-900 tabular-nums">{formatMoney(monthlyBurnRate * 12)}</span>
            </div>
            <div class="mt-1 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Runway at current burn</span>
              <span class="font-semibold text-neutral-900 tabular-nums">
                {burnRunwayMonths === null ? "--" : `${burnRunwayMonths.toFixed(1)} mo`}
              </span>
            </div>
          </article>

          <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-700">Sales Funnel Economics</h3>
              <span class="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">CRM · YTD</span>
            </div>
            <div class="mt-3 grid grid-cols-2 gap-2">
              <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p class="text-[10px] uppercase tracking-wider text-neutral-500">Avg Deal Value</p>
                <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{formatMoney(avgDealValue)}</p>
              </div>
              <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p class="text-[10px] uppercase tracking-wider text-neutral-500">Closed Deals</p>
                <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{formatCount(closedDeals)}</p>
              </div>
            </div>
            <div class="mt-3 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Closed revenue</span>
              <span class="font-semibold text-neutral-900 tabular-nums">{formatMoney(closedValue)}</span>
            </div>
            <div class="mt-1 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Active pipeline</span>
              <span class="font-semibold text-neutral-900 tabular-nums">{formatCount(activePipeline)}</span>
            </div>
            <div class="mt-1 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Close rate</span>
              <span class="font-semibold tabular-nums {closeRate !== null && closeRate >= 20 ? 'text-emerald-700' : closeRate !== null && closeRate >= 10 ? 'text-amber-700' : 'text-rose-700'}">
                {closeRate === null ? "--" : formatPercent(closeRate)}
              </span>
            </div>
          </article>

          <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-700">Budget Remaining</h3>
              <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold
                {budgetRemainingPct > 50
                  ? 'bg-emerald-50 text-emerald-700'
                  : budgetRemainingPct > 20
                    ? 'bg-amber-50 text-amber-700'
                    : 'bg-rose-50 text-rose-700'}"
              >
                {formatPercent(budgetRemainingPct)}
              </span>
            </div>
            <p class="mt-2 text-[11px] text-neutral-500">Share of allocated funds still available for this period.</p>
            <div class="mt-4 h-3 overflow-hidden rounded-full bg-neutral-200">
              <div
                class="h-full rounded-full
                  {budgetRemainingPct > 50
                    ? 'bg-emerald-500'
                    : budgetRemainingPct > 20
                      ? 'bg-amber-500'
                      : 'bg-rose-500'}"
                style="width: {budgetRemainingPct}%;"
              ></div>
            </div>
            <div class="mt-2 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Used</span>
              <span class="font-semibold text-neutral-900 tabular-nums">{formatPercent(budgetUsedPct)}</span>
            </div>
            <div class="mt-1 flex items-center justify-between text-[11px]">
              <span class="text-neutral-600">Remaining</span>
              <span class="font-semibold text-neutral-900 tabular-nums">{formatPercent(budgetRemainingPct)}</span>
            </div>
          </article>
        </div>
      {/if}
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-4 sm:p-5">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Trend Analysis</h2>
        <span class="rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] font-semibold text-neutral-600">Visuals</span>
      </div>

      <div class="grid gap-4 xl:grid-cols-12">
        <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-8">
          <div class="mb-3 flex items-center justify-between gap-2">
            <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-700">Time-Series Line Chart</h3>
            <div class="flex items-center gap-3 text-[10px] font-medium text-neutral-500">
              <span class="inline-flex items-center gap-1">
                <span class="h-2 w-2 rounded-full bg-cyan-500"></span>Income
              </span>
              <span class="inline-flex items-center gap-1">
                <span class="h-2 w-2 rounded-full bg-amber-500"></span>Expenses
              </span>
            </div>
          </div>
          <p class="text-xs text-neutral-500">Track seasonal dips and sudden spikes across monthly financial movement.</p>

          {#if trendPoints.length === 0}
            <div class="mt-4 rounded-lg border border-dashed border-neutral-200 bg-neutral-50 px-4 py-5 text-sm text-neutral-500">
              No monthly trend data available.
            </div>
          {:else}
            <div class="mt-4 overflow-x-auto">
              <svg
                class="w-full min-w-[520px]"
                viewBox="0 0 {TREND_CHART.width} {TREND_CHART.height}"
                preserveAspectRatio="xMidYMid meet"
              >
                {#each [0, 0.25, 0.5, 0.75, 1] as tick}
                  {@const y = TREND_CHART.padTop + (1 - tick) * (TREND_CHART.height - TREND_CHART.padTop - TREND_CHART.padBottom)}
                  <line
                    x1={TREND_CHART.padLeft}
                    y1={y}
                    x2={TREND_CHART.width - TREND_CHART.padRight}
                    y2={y}
                    stroke="#f1f5f9"
                    stroke-width="1"
                  />
                  <text x={TREND_CHART.padLeft - 8} y={y + 3} text-anchor="end" class="fill-neutral-400 text-[9px]">
                    {formatMoney(trendMax * tick)}
                  </text>
                {/each}

                <polyline
                  points={incomeLinePoints}
                  fill="none"
                  stroke="#06b6d4"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
                <polyline
                  points={expenseLinePoints}
                  fill="none"
                  stroke="#f59e0b"
                  stroke-width="2.5"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />

                {#each trendPoints as point}
                  <circle cx={point.x} cy={point.incomeY} r="2.8" fill="#06b6d4">
                    <title>{point.month} income: {formatMoney(point.income)}</title>
                  </circle>
                  <circle cx={point.x} cy={point.expenseY} r="2.8" fill="#f59e0b">
                    <title>{point.month} expenses: {formatMoney(point.expenses)}</title>
                  </circle>
                  <text
                    x={point.x}
                    y={TREND_CHART.height - 8}
                    text-anchor="middle"
                    class="fill-neutral-400 text-[9px]"
                  >
                    {point.month}
                  </text>
                {/each}
              </svg>
            </div>
          {/if}
        </article>

        <article class="rounded-xl border border-neutral-200 bg-white p-4 xl:col-span-4">
          <div class="mb-3 flex items-center justify-between gap-2">
            <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-700">Distribution Donut</h3>
            <span class="text-[10px] font-medium text-neutral-500">Project Type Ratio</span>
          </div>
          <p class="text-xs text-neutral-500">Category distribution snapshot by portfolio type count.</p>

          {#if distributionRows.length === 0}
            <div class="mt-4 rounded-lg border border-dashed border-neutral-200 bg-neutral-50 px-4 py-5 text-sm text-neutral-500">
              No distribution data available.
            </div>
          {:else}
            {@const donutRadius = 52}
            {@const donutCirc = 2 * Math.PI * donutRadius}
            <div class="mt-4 flex items-start gap-4">
              <div class="relative h-[140px] w-[140px] shrink-0">
                <svg viewBox="0 0 140 140" class="-rotate-90">
                  <circle cx="70" cy="70" r={donutRadius} fill="none" stroke="#e5e7eb" stroke-width="20" />
                  {#each distributionRows as row, index}
                    {@const arc = (row.share / 100) * donutCirc}
                    {@const prior = distributionRows.slice(0, index).reduce((sum, item) => sum + item.share, 0)}
                    <circle
                      cx="70"
                      cy="70"
                      r={donutRadius}
                      fill="none"
                      stroke={row.color}
                      stroke-width="20"
                      stroke-dasharray="{Math.max(arc - 1.5, 0)} {donutCirc}"
                      stroke-dashoffset={-(prior / 100) * donutCirc}
                    >
                      <title>{row.label}: {formatPercent(row.share)} ({row.count})</title>
                    </circle>
                  {/each}
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <span class="text-xl font-bold text-neutral-900 tabular-nums">
                    {formatCount(distributionRows.reduce((sum, row) => sum + row.count, 0))}
                  </span>
                  <span class="text-[10px] uppercase tracking-wider text-neutral-500">Total</span>
                </div>
              </div>

              <div class="min-w-0 flex-1 space-y-2">
                {#each distributionRows.slice(0, 5) as row}
                  <div class="flex items-center justify-between gap-2 text-[11px]">
                    <span class="inline-flex min-w-0 items-center gap-1.5">
                      <span class="h-2 w-2 rounded-full" style="background: {row.color};"></span>
                      <span class="truncate text-neutral-700">{row.label}</span>
                    </span>
                    <span class="tabular-nums font-semibold text-neutral-900">{formatPercent(row.share)}</span>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        </article>
      </div>
    </section>
  </div>
{/if}

<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CustomDashboard,
    FinanceCashFlow,
    FinanceOverview,
    PortfolioAnalytics,
    BoardKpiSnapshot,
  } from "$lib/types";
  import WidgetRenderer from "$lib/components/dashboard/WidgetRenderer.svelte";
  import { getRequiredDataSources, type WidgetDataSource } from "$lib/dashboard/widget-catalog";

  let dashboards = $state<CustomDashboard[]>([]);
  let activeDashboard = $state<CustomDashboard | null>(null);
  let portfolioData = $state<PortfolioAnalytics | null>(null);
  let boardKpiData = $state<BoardKpiSnapshot | null>(null);
  let financeData = $state<FinanceOverview | null>(null);
  let cashFlowData = $state<FinanceCashFlow | null>(null);
  let loading = $state(true);
  let widgetDataLoading = $state(false);

  // Track in-flight fetches per source so concurrent loads (e.g. fast tab
  // switching) coalesce instead of issuing duplicate requests.
  const inFlight: Partial<Record<WidgetDataSource, Promise<void>>> = {};

  function loadPortfolio(): Promise<void> {
    if (portfolioData !== null) return Promise.resolve();
    if (inFlight.portfolio) return inFlight.portfolio;
    const p = api
      .get<PortfolioAnalytics>("/analytics/portfolio/")
      .then((r) => { portfolioData = r; })
      .catch(() => { portfolioData = null; })
      .finally(() => { delete inFlight.portfolio; });
    inFlight.portfolio = p;
    return p;
  }

  function loadBoardKpi(): Promise<void> {
    if (boardKpiData !== null) return Promise.resolve();
    if (inFlight.board_kpi) return inFlight.board_kpi;
    const p = api
      .get<BoardKpiSnapshot>("/analytics/board-kpis/")
      .then((r) => { boardKpiData = r; })
      .catch(() => { boardKpiData = null; })
      .finally(() => { delete inFlight.board_kpi; });
    inFlight.board_kpi = p;
    return p;
  }

  function loadFinance(): Promise<void> {
    if (financeData !== null) return Promise.resolve();
    if (inFlight.finance) return inFlight.finance;
    const p = api
      .get<FinanceOverview>("/finance/overview/")
      .then((r) => { financeData = r; })
      .catch(() => { financeData = null; })
      .finally(() => { delete inFlight.finance; });
    inFlight.finance = p;
    return p;
  }

  function loadCashFlow(): Promise<void> {
    if (cashFlowData !== null) return Promise.resolve();
    if (inFlight.finance_cash_flow) return inFlight.finance_cash_flow;
    const year = new Date().getFullYear();
    const p = api
      .get<FinanceCashFlow>(`/finance/cash-flow/?year=${year}`)
      .then((r) => { cashFlowData = r; })
      .catch(() => { cashFlowData = null; })
      .finally(() => { delete inFlight.finance_cash_flow; });
    inFlight.finance_cash_flow = p;
    return p;
  }

  async function ensureDataSources(needed: Set<WidgetDataSource>) {
    const promises: Promise<void>[] = [];
    if (needed.has("portfolio") && portfolioData === null) promises.push(loadPortfolio());
    if (needed.has("board_kpi") && boardKpiData === null) promises.push(loadBoardKpi());
    if (needed.has("finance") && financeData === null) promises.push(loadFinance());
    if (needed.has("finance_cash_flow") && cashFlowData === null) promises.push(loadCashFlow());
    if (promises.length === 0) return;
    widgetDataLoading = true;
    try {
      await Promise.all(promises);
    } finally {
      widgetDataLoading = false;
    }
  }

  async function load() {
    loading = true;
    try {
      const dashes = await api.get<CustomDashboard[]>("/analytics/dashboards/");
      if (!Array.isArray(dashes)) {
        throw new Error(`Expected array, got ${typeof dashes}`);
      }
      dashboards = dashes;
      activeDashboard = dashes.find((d) => d.is_default) ?? dashes[0] ?? null;
    } catch (err) {
      console.error("Failed to load custom dashboards:", err);
      toast.error("Load failed", "Could not load dashboards.");
    }
    loading = false;
  }

  async function deleteDashboard(id: number) {
    try {
      await api.delete(`/analytics/dashboards/${id}/`);
      dashboards = dashboards.filter((d) => d.id !== id);
      if (activeDashboard?.id === id) {
        activeDashboard = dashboards[0] ?? null;
      }
      toast.success("Deleted", "Dashboard removed.");
    } catch {
      toast.error("Error", "Could not delete dashboard.");
    }
  }

  onMount(() => {
    void load();
  });

  // Lazy-load only the data sources the active dashboard's widgets need.
  // Re-runs when the user switches between dashboard tabs.
  $effect(() => {
    if (!activeDashboard) return;
    const needed = getRequiredDataSources(activeDashboard.layout);
    void ensureDataSources(needed);
  });

  // Compute max row from layout for grid height
  function gridRows(dash: CustomDashboard): number {
    if (!dash.layout.length) return 4;
    return Math.max(
      ...dash.layout.map((w) => w.position.y + w.position.h),
      4
    );
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Custom Dashboards</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Your personalized analytics dashboards.
        </p>
      </div>
      <a
        href="/dashboard/custom/builder"
        class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
        </svg>
        New Dashboard
      </a>
    </div>

    {#if dashboards.length === 0}
      <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50/50 px-8 py-16 text-center">
        <svg class="mx-auto w-10 h-10 text-neutral-300 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
        </svg>
        <p class="text-sm text-neutral-500 mb-4">No custom dashboards yet.</p>
        <a
          href="/dashboard/custom/builder"
          class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          Create your first dashboard
        </a>
      </div>
    {:else}
      <!-- Dashboard tabs -->
      <div class="flex items-center gap-2 border-b border-neutral-200 pb-px overflow-x-auto">
        {#each dashboards as dash}
          <button
            onclick={() => (activeDashboard = dash)}
            class="shrink-0 rounded-t-lg px-4 py-2 text-sm font-medium transition-colors
              {activeDashboard?.id === dash.id
                ? 'bg-white border border-b-white border-neutral-200 text-neutral-900 -mb-px'
                : 'text-neutral-500 hover:text-neutral-700'}"
          >
            {dash.name}
            {#if dash.is_default}
              <span class="ml-1 text-[9px] text-neutral-400 uppercase">default</span>
            {/if}
          </button>
        {/each}
      </div>

      <!-- Active dashboard grid -->
      {#if activeDashboard}
        <div class="flex items-center justify-between">
          <p class="text-xs text-neutral-400">
            {activeDashboard.layout.length} widget{activeDashboard.layout.length !== 1 ? "s" : ""}
          </p>
          <div class="flex items-center gap-2">
            <a
              href="/dashboard/custom/builder?id={activeDashboard.id}"
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
            >
              Edit
            </a>
            <button
              onclick={() => activeDashboard && deleteDashboard(activeDashboard.id)}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
            >
              Delete
            </button>
          </div>
        </div>

        {#if activeDashboard.layout.length > 0}
          <div class="relative">
            {#if widgetDataLoading}
              <div class="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-white/60 backdrop-blur-[1px]">
                <div class="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 shadow-sm">
                  <span class="inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-neutral-300 border-t-neutral-700"></span>
                  Loading widgets…
                </div>
              </div>
            {/if}
            <div
              class="grid gap-4"
              style="grid-template-columns: repeat(12, 1fr); grid-template-rows: repeat({gridRows(activeDashboard)}, 80px);"
            >
              {#each activeDashboard.layout as widget}
                <div
                  style="grid-column: {widget.position.x + 1} / span {widget.position.w}; grid-row: {widget.position.y + 1} / span {widget.position.h};"
                >
                  <WidgetRenderer config={widget} {portfolioData} {boardKpiData} {financeData} {cashFlowData} />
                </div>
              {/each}
            </div>
          </div>
        {:else}
          <div class="rounded-xl border border-dashed border-neutral-300 bg-neutral-50/50 px-8 py-12 text-center">
            <p class="text-sm text-neutral-500">This dashboard has no widgets. <a href="/dashboard/custom/builder?id={activeDashboard.id}" class="text-neutral-900 font-medium hover:underline">Edit it</a> to add some.</p>
          </div>
        {/if}
      {/if}
    {/if}
  </div>
{/if}

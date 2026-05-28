<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    BoardKpiSnapshot,
    CustomDashboard,
    FinanceCashFlow,
    FinanceOverview,
    PortfolioAnalytics,
    WidgetConfig,
    WidgetType,
  } from "$lib/types";
  import WidgetPicker from "$lib/components/dashboard/WidgetPicker.svelte";
  import WidgetCanvas from "$lib/components/dashboard/WidgetCanvas.svelte";
  import { getDefaultSize } from "$lib/dashboard/widget-catalog";

  let dashboardName = $state("My Dashboard");
  let isDefault = $state(false);
  let widgets = $state<WidgetConfig[]>([]);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let loading = $state(true);

  // Preview data — used by WidgetCanvas to render live previews of each
  // widget while the user is arranging the layout. Loaded in parallel with
  // the existing-dashboard fetch; failures are silent (preview falls back
  // to the renderer's "data unavailable" placeholder).
  let portfolioData = $state<PortfolioAnalytics | null>(null);
  let boardKpiData = $state<BoardKpiSnapshot | null>(null);
  let financeData = $state<FinanceOverview | null>(null);
  let cashFlowData = $state<FinanceCashFlow | null>(null);

  // Find the next available position
  function nextPosition(w: number, h: number): { x: number; y: number; w: number; h: number } {
    if (widgets.length === 0) return { x: 0, y: 0, w, h };

    // Find the max y + h to place below existing widgets
    const maxBottom = Math.max(...widgets.map((wg) => wg.position.y + wg.position.h));

    // Try to fit in the current row first
    const lastRow = widgets.filter((wg) => wg.position.y + wg.position.h === maxBottom);
    const rightEdge = lastRow.length
      ? Math.max(...lastRow.map((wg) => wg.position.x + wg.position.w))
      : 0;

    if (rightEdge + w <= 12) {
      // Fits in the same row
      const rowY = lastRow.length ? lastRow[0].position.y : 0;
      return { x: rightEdge, y: rowY, w, h };
    }

    // New row
    return { x: 0, y: maxBottom, w, h };
  }

  function addWidget(widgetType: WidgetType, kpiKey?: string) {
    const size = getDefaultSize(widgetType);
    const pos = nextPosition(size.w, size.h);
    widgets = [
      ...widgets,
      {
        widget_type: widgetType,
        ...(kpiKey ? { kpi_key: kpiKey } : {}),
        position: pos,
        config: {},
      },
    ];
  }

  function removeWidget(index: number) {
    widgets = widgets.filter((_, i) => i !== index);
  }

  async function save() {
    saving = true;
    try {
      const payload = {
        name: dashboardName,
        is_default: isDefault,
        layout: widgets,
      };
      if (editingId) {
        await api.put(`/analytics/dashboards/${editingId}/`, payload);
        toast.success("Saved", "Dashboard updated.");
      } else {
        await api.post("/analytics/dashboards/", payload);
        toast.success("Created", "Dashboard created.");
      }
      goto("/dashboard/custom");
    } catch {
      toast.error("Save failed", "Could not save dashboard.");
    }
    saving = false;
  }

  async function loadPreviewData() {
    const year = new Date().getFullYear();
    const [portfolio, board, finance, cashFlow] = await Promise.allSettled([
      api.get<PortfolioAnalytics>("/analytics/portfolio/"),
      api.get<BoardKpiSnapshot>("/analytics/board-kpis/"),
      api.get<FinanceOverview>("/finance/overview/"),
      api.get<FinanceCashFlow>(`/finance/cash-flow/?year=${year}`),
    ]);
    if (portfolio.status === "fulfilled") portfolioData = portfolio.value;
    if (board.status === "fulfilled") boardKpiData = board.value;
    if (finance.status === "fulfilled") financeData = finance.value;
    if (cashFlow.status === "fulfilled") cashFlowData = cashFlow.value;
  }

  // Load existing dashboard if editing
  async function loadExisting() {
    const urlId = $page.url.searchParams.get("id");
    if (!urlId) {
      loading = false;
      return;
    }
    try {
      const dash = await api.get<CustomDashboard>(`/analytics/dashboards/${urlId}/`);
      editingId = dash.id;
      dashboardName = dash.name;
      isDefault = dash.is_default;
      widgets = dash.layout;
    } catch {
      toast.error("Load failed", "Could not load dashboard for editing.");
    }
    loading = false;
  }

  onMount(() => {
    void loadExisting();
    void loadPreviewData();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="flex gap-6 min-h-[calc(100vh-120px)]">
    <!-- Sidebar: Widget Picker — fixed-height column with an independently
         scrollable picker so the canvas preview stays in view as the user
         browses the (37-entry) widget catalog. -->
    <div class="w-64 shrink-0">
      <div class="sticky top-4 flex flex-col gap-4 h-[calc(100vh-2rem)]">
        <div class="shrink-0">
          <a href="/dashboard/custom" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">&larr; Back to dashboards</a>
          <h1 class="mt-2 text-lg font-bold text-neutral-800">
            {editingId ? "Edit" : "Build"} Dashboard
          </h1>
        </div>

        <!-- Name + Default -->
        <div class="space-y-3 shrink-0">
          <label class="block">
            <span class="text-xs font-medium text-neutral-600">Name</span>
            <input
              type="text"
              bind:value={dashboardName}
              class="mt-1 block w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400"
              placeholder="Dashboard name"
            />
          </label>
          <label class="flex items-center gap-2 text-xs text-neutral-600">
            <input type="checkbox" bind:checked={isDefault} class="rounded border-neutral-300" />
            Set as default dashboard
          </label>
        </div>

        <hr class="border-neutral-100 shrink-0" />

        <!-- Widget picker — scrolls independently so the canvas stays visible. -->
        <div class="min-h-0 flex-1 overflow-y-auto pr-1 -mr-1">
          <WidgetPicker onadd={addWidget} />
        </div>

        <hr class="border-neutral-100 shrink-0" />

        <button
          onclick={save}
          disabled={saving || !dashboardName.trim() || widgets.length === 0}
          class="shrink-0 w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? "Saving..." : editingId ? "Update Dashboard" : "Save Dashboard"}
        </button>
      </div>
    </div>

    <!-- Canvas -->
    <div class="flex-1 min-w-0">
      <div class="mb-3 flex items-center justify-between">
        <p class="text-[11px] uppercase tracking-[0.3em] text-neutral-400">Layout preview</p>
        <p class="text-[11px] text-neutral-500">
          Drag header to move · drag corner to resize · 12-column grid
        </p>
      </div>
      <WidgetCanvas bind:widgets {portfolioData} {boardKpiData} {financeData} {cashFlowData} onremove={removeWidget} />
    </div>
  </div>
{/if}

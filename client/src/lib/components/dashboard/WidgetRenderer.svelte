<script lang="ts">
  import type {
    WidgetConfig,
    PortfolioAnalytics,
    BoardKpiSnapshot,
    FinanceOverview,
    FinanceCashFlow,
  } from "$lib/types";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
  import AreaChart from "$lib/components/charts/AreaChart.svelte";
  import HorizontalBarChart from "$lib/components/charts/HorizontalBarChart.svelte";
  import { currency } from "$lib/stores/currency.svelte";

  let {
    config,
    portfolioData = null,
    boardKpiData = null,
    financeData = null,
    cashFlowData = null,
  }: {
    config: WidgetConfig;
    portfolioData?: PortfolioAnalytics | null;
    boardKpiData?: BoardKpiSnapshot | null;
    financeData?: FinanceOverview | null;
    cashFlowData?: FinanceCashFlow | null;
  } = $props();

  function fmtN(n: number, digits = 2): string {
    return Number(n || 0).toLocaleString("en-US", { maximumFractionDigits: digits });
  }

  function fmtCount(n: number): string {
    return Number(n || 0).toLocaleString("en-US");
  }

  function fmtCurrency(v: string | number): string {
    return currency.formatCompact(v);
  }

  function titleCase(input: string): string {
    return input.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function toNumber(v: string | number | null | undefined): number {
    const n = Number(v ?? 0);
    return Number.isFinite(n) ? n : 0;
  }

  // Static class map — Tailwind 4's scanner only picks up class names that
  // appear verbatim in source. Building "border-{color}-400" at runtime would
  // be purged in production. Each accent class is written out in full so the
  // scanner sees the literal string.
  const KPI_BORDER_CLASS = {
    cyan: "border-l-4 border-cyan-400",
    violet: "border-l-4 border-violet-400",
    emerald: "border-l-4 border-emerald-400",
    amber: "border-l-4 border-amber-400",
    rose: "border-l-4 border-rose-400",
    indigo: "border-l-4 border-indigo-400",
  } as const;

  type KpiAccent = keyof typeof KPI_BORDER_CLASS;

  const KPI_META: Record<string, { label: string; accent: KpiAccent; format: (v: Record<string, any>) => string; sub: (v: Record<string, any>) => string }> = {
    procurement_cycle_time_days: {
      label: "Procurement Cycle Time",
      accent: "cyan",
      format: (v) => `${fmtN(v.value)} days`,
      sub: (v) => `${v.sample_size} PO cycles`,
    },
    cost_variance_per_project_pct: {
      label: "Cost Variance",
      accent: "violet",
      format: (v) => `${v.value > 0 ? "+" : ""}${fmtN(v.value)}%`,
      sub: (v) => `${v.over_budget_projects} of ${v.project_count} over budget`,
    },
    vendor_reliability_score: {
      label: "Vendor Reliability",
      accent: "emerald",
      format: (v) => `${fmtN(v.value, 1)}/100`,
      sub: (v) => `${v.vendor_count} vendors`,
    },
    emergency_purchases_pct: {
      label: "Emergency Purchases",
      accent: "amber",
      format: (v) => `${fmtN(v.value)}%`,
      sub: (v) => `${v.emergency_count} of ${v.total_requisitions}`,
    },
    budget_overrun_frequency_pct: {
      label: "Budget Overrun",
      accent: "rose",
      format: (v) => `${fmtN(v.value)}%`,
      sub: (v) => `${v.overrun_items} of ${v.tracked_items} lines`,
    },
    average_approval_time_hours: {
      label: "Approval Time",
      accent: "indigo",
      format: (v) => `${fmtN(v.value)} hrs`,
      sub: (v) => `${v.completed_workflows} workflows`,
    },
  };
</script>

<div class="h-full rounded-xl border border-neutral-200 bg-white overflow-hidden">
  {#if config.widget_type === "board_kpi_card" && boardKpiData && config.kpi_key}
    {@const kpiKey = config.kpi_key as keyof typeof boardKpiData.kpis}
    {@const kpiValue = boardKpiData.kpis[kpiKey]}
    {@const meta = KPI_META[config.kpi_key]}
    {#if meta && kpiValue}
      <div class="px-4 py-4 h-full flex flex-col justify-center {KPI_BORDER_CLASS[meta.accent]}">
        <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">{meta.label}</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{meta.format(kpiValue)}</p>
        <p class="text-xs text-neutral-400">{meta.sub(kpiValue)}</p>
      </div>
    {/if}

  {:else if config.widget_type === "portfolio_kpi_summary" && portfolioData}
    <div class="px-4 py-3 space-y-2">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Portfolio Summary</p>
      <div class="grid grid-cols-3 gap-2 text-xs">
        <div>
          <p class="text-neutral-400">Properties</p>
          <p class="font-semibold text-neutral-900">{portfolioData.kpis.property_count}</p>
        </div>
        <div>
          <p class="text-neutral-400">Total Value</p>
          <p class="font-semibold text-neutral-900 tabular-nums">{fmtCurrency(portfolioData.kpis.total_value)}</p>
        </div>
        <div>
          <p class="text-neutral-400">Unrealized Gain</p>
          <p class="font-semibold text-neutral-900 tabular-nums">{fmtCurrency(portfolioData.kpis.unrealized_gain)}</p>
        </div>
      </div>
    </div>

  {:else if config.widget_type === "portfolio_type_distribution" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Type Distribution</p>
      <DonutChart
        data={portfolioData.type_distribution.map(t => ({ label: t.type, value: t.count }))}
        size={180}
        centerLabel="types"
        centerValue={String(portfolioData.type_distribution.length)}
      />
    </div>

  {:else if config.widget_type === "portfolio_classification" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Classification Breakdown</p>
      <BarChart
        data={portfolioData.classification_breakdown.map(c => ({ label: c.classification, value: c.count }))}
        height={180}
      />
    </div>

  {:else if config.widget_type === "portfolio_valuation_history" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Valuation History</p>
      {#if portfolioData.valuation_history.length > 1}
        <AreaChart
          data={portfolioData.valuation_history.map(v => ({ x: new Date(v.month), y: Number(v.total_value) }))}
          formatX={(d) => (d as Date).toLocaleDateString("en-US", { month: "short" })}
          formatY={(d) => fmtCurrency(String(d))}
          height={180}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">Not enough data</p>
      {/if}
    </div>

  {:else if config.widget_type === "portfolio_unit_occupancy" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Unit Occupancy</p>
      <HorizontalBarChart
        data={portfolioData.unit_occupancy.map(u => ({ label: u.status, value: u.count }))}
        height={Math.max(120, portfolioData.unit_occupancy.length * 32)}
      />
    </div>

  {:else if config.widget_type === "portfolio_budget_summary" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Project Budget Summary</p>
      <div class="space-y-1.5 max-h-[200px] overflow-y-auto">
        {#each portfolioData.project_budget_summary.slice(0, 5) as p}
          <div class="flex items-center justify-between text-xs">
            <span class="text-neutral-700 truncate mr-2">{p.name}</span>
            <span class="tabular-nums text-neutral-500 shrink-0">{fmtCurrency(p.total_actual)} / {fmtCurrency(p.total_planned)}</span>
          </div>
        {/each}
      </div>
    </div>

  {:else if config.widget_type === "portfolio_construction_budget_burn" && portfolioData}
    {@const planned = portfolioData.project_budget_summary.reduce((sum, row) => sum + toNumber(row.total_planned), 0)}
    {@const actual = portfolioData.project_budget_summary.reduce((sum, row) => sum + toNumber(row.total_actual), 0)}
    {@const burnRate = planned > 0 ? (actual / planned) * 100 : 0}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Construction Budget Burn</p>
      <p class="mt-1 text-xl font-bold text-rose-700 tabular-nums">{burnRate.toFixed(1)}%</p>
      <div class="mt-2 h-2 overflow-hidden rounded-full bg-rose-100">
        <div class="h-full rounded-full bg-rose-500" style="width: {Math.min(100, Math.max(0, burnRate))}%"></div>
      </div>
      <p class="mt-2 text-xs text-neutral-500">
        Planned {fmtCurrency(String(planned))} · Actual {fmtCurrency(String(actual))}
      </p>
    </div>

  {:else if config.widget_type === "portfolio_property_inventory" && portfolioData}
    {@const inventory = portfolioData.unit_occupancy.reduce(
      (acc, row) => {
        const key = row.status.toLowerCase();
        const count = row.count ?? 0;
        acc.total += count;
        if (key === "available") acc.available += count;
        if (key === "reserved") acc.reserved += count;
        if (key === "sold") acc.sold += count;
        if (key === "leased") acc.leased += count;
        return acc;
      },
      { total: 0, available: 0, reserved: 0, sold: 0, leased: 0 },
    )}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Property Inventory</p>
      <p class="mt-1 text-xl font-bold text-lime-700 tabular-nums">{inventory.total}</p>
      <p class="mt-2 text-xs text-neutral-500">
        {inventory.available} available · {inventory.reserved} reserved · {inventory.sold} sold
      </p>
      <p class="mt-1 text-xs text-neutral-400">{inventory.leased} leased</p>
    </div>

  {:else if config.widget_type === "portfolio_procurement_commitments" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Procurement Commitments</p>
      <p class="mt-1 text-xl font-bold text-amber-700 tabular-nums">
        {fmtCurrency(portfolioData.procurement_summary.committed_amount)}
      </p>
      <p class="mt-2 text-xs text-neutral-500">
        {portfolioData.procurement_summary.open_commitments} open PO commitments
      </p>
      <p class="mt-1 text-xs text-neutral-400">
        {portfolioData.procurement_summary.overdue_deliveries} overdue · {portfolioData.procurement_summary.pending_requisitions} pending reqs
      </p>
    </div>

  {:else if config.widget_type === "portfolio_rental_occupancy" && portfolioData}
    {@const totalUnits = portfolioData.unit_occupancy.reduce((sum, row) => sum + (row.count ?? 0), 0)}
    {@const leasedUnits = portfolioData.unit_occupancy
      .filter((row) => row.status.toLowerCase() === "leased")
      .reduce((sum, row) => sum + (row.count ?? 0), 0)}
    {@const occupancy = totalUnits > 0 ? (leasedUnits / totalUnits) * 100 : 0}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Rental Occupancy</p>
      <p class="mt-1 text-xl font-bold text-cyan-700 tabular-nums">{occupancy.toFixed(1)}%</p>
      <div class="mt-2 h-2 overflow-hidden rounded-full bg-cyan-100">
        <div class="h-full rounded-full bg-cyan-500" style="width: {Math.min(100, Math.max(0, occupancy))}%"></div>
      </div>
      <p class="mt-2 text-xs text-neutral-500">{leasedUnits} leased out of {totalUnits} units</p>
    </div>

  {:else if config.widget_type === "portfolio_maintenance_backlog" && portfolioData}
    {@const totalBacklog = (portfolioData.facility_summary.open_work_orders ?? 0) + (portfolioData.facility_summary.open_service_requests ?? 0)}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Maintenance Backlog</p>
      <p class="mt-1 text-xl font-bold text-orange-700 tabular-nums">{totalBacklog}</p>
      <p class="mt-2 text-xs text-neutral-500">
        {portfolioData.facility_summary.open_work_orders} work orders · {portfolioData.facility_summary.open_service_requests} service requests
      </p>
      <p class="mt-1 text-xs text-neutral-400">
        {portfolioData.facility_summary.urgent_work_orders} urgent · {portfolioData.facility_summary.pending_inspections} pending inspections
      </p>
    </div>

  {:else if config.widget_type === "portfolio_cash_flow_forecast" && financeData}
    {@const baseline = toNumber(financeData.total_receivable) - toNumber(financeData.total_payable)}
    {@const recentIn = financeData.recent_invoices.reduce((sum, row) => sum + toNumber(row.total_amount), 0)}
    {@const recentOut = financeData.recent_bills.reduce((sum, row) => sum + toNumber(row.total_amount), 0)}
    {@const avgMonthlyNet = (recentIn - recentOut) / 3}
    {@const now = new Date()}
    {@const series = [0, 1, 2, 3].map((step) => ({
      x: new Date(now.getFullYear(), now.getMonth() + step, 1),
      y: baseline + avgMonthlyNet * step,
    }))}
    <div class="px-4 py-3">
      <div class="mb-2 flex items-center justify-between">
        <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Cash Flow Forecast</p>
        <span class="text-[10px] text-neutral-400">90 days</span>
      </div>
      <p class="text-xl font-bold text-blue-700 tabular-nums">{fmtCurrency(String(baseline + avgMonthlyNet * 3))}</p>
      <p class="mt-1 text-xs text-neutral-500">
        Avg monthly net {avgMonthlyNet >= 0 ? "+" : ""}{fmtCurrency(String(avgMonthlyNet))}
      </p>
      <div class="mt-2">
        <AreaChart
          data={series}
          formatX={(d) => (d as Date).toLocaleDateString("en-US", { month: "short" })}
          formatY={(d) => fmtCurrency(String(d))}
          color="#2563eb"
          height={140}
        />
      </div>
    </div>

  {:else if (config.widget_type === "portfolio_top_appreciating" || config.widget_type === "portfolio_top_depreciating") && portfolioData}
    {@const items = config.widget_type === "portfolio_top_appreciating" ? portfolioData.top_appreciating : portfolioData.top_depreciating}
    {@const title = config.widget_type === "portfolio_top_appreciating" ? "Top Appreciating" : "Top Depreciating"}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">{title}</p>
      <div class="space-y-1.5">
        {#each items.slice(0, 5) as prop}
          <div class="flex items-center justify-between text-xs">
            <span class="text-neutral-700 truncate mr-2">{prop.name}</span>
            <span class="tabular-nums font-semibold shrink-0 {Number(prop.gain_pct) >= 0 ? 'text-emerald-700' : 'text-red-700'}">
              {Number(prop.gain_pct) > 0 ? "+" : ""}{prop.gain_pct}%
            </span>
          </div>
        {/each}
      </div>
    </div>

  {:else if config.widget_type === "portfolio_encumbrance" && portfolioData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Encumbrances</p>
      {#if portfolioData.encumbrance_summary.by_type.length > 0}
        <DonutChart
          data={portfolioData.encumbrance_summary.by_type.map(e => ({ label: e.type, value: Number(e.total_amount) }))}
          size={180}
          centerLabel="total"
          centerValue={fmtCurrency(portfolioData.encumbrance_summary.total_amount)}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No encumbrances</p>
      {/if}
    </div>

  <!-- ── Portfolio scalar KPIs ────────────────────────────────────── -->
  {:else if config.widget_type === "portfolio_total_acquisition" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-cyan-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Total Acquisition Cost</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(portfolioData.kpis.total_acquisition)}</p>
      <p class="text-xs text-neutral-400">Across {portfolioData.kpis.property_count} properties</p>
    </div>

  {:else if config.widget_type === "portfolio_total_area" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-violet-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Total Area</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtN(toNumber(portfolioData.kpis.total_area_sqft), 0)} sqft</p>
      <p class="text-xs text-neutral-400">{portfolioData.kpis.property_count} properties</p>
    </div>

  {:else if config.widget_type === "portfolio_avg_price_per_sqft" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-emerald-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Avg $/sqft</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(portfolioData.kpis.avg_price_per_sqft)}</p>
      <p class="text-xs text-neutral-400">Portfolio average</p>
    </div>

  <!-- ── Operations cards ─────────────────────────────────────────── -->
  {:else if config.widget_type === "hr_active_headcount" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-indigo-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Active Headcount</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCount(portfolioData.hr_summary.active_employees)}</p>
      <p class="text-xs text-neutral-400">{fmtCount(portfolioData.hr_summary.employees_on_leave)} on leave</p>
    </div>

  {:else if config.widget_type === "hr_open_vacancies" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-amber-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Open Vacancies</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCount(portfolioData.hr_summary.open_vacancies)}</p>
      <p class="text-xs text-neutral-400">Staffing gap: {fmtCount(portfolioData.hr_summary.staffing_gap)}</p>
    </div>

  {:else if config.widget_type === "tenant_active_count" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-cyan-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Active Tenants</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCount(portfolioData.tenant_summary.active_tenants)}</p>
      <p class="text-xs text-neutral-400">{fmtCount(portfolioData.tenant_summary.open_tenant_requests)} open requests</p>
    </div>

  {:else if config.widget_type === "crm_active_leads" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-rose-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Active Leads</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCount(portfolioData.crm_summary.active_leads)}</p>
      <p class="text-xs text-neutral-400">{fmtCount(portfolioData.crm_summary.active_reservations)} live reservations</p>
    </div>

  {:else if config.widget_type === "crm_closed_reservations" && portfolioData}
    <div class="px-4 py-4 h-full flex flex-col justify-center border-l-4 border-emerald-400">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Closed Reservations</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCount(portfolioData.crm_summary.converted_reservations)}</p>
      <p class="text-xs text-neutral-400">{fmtCurrency(portfolioData.crm_summary.converted_value)} converted value</p>
    </div>

  <!-- ── Finance status & lists ──────────────────────────────────── -->
  {:else if config.widget_type === "finance_bills_by_status" && financeData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Bills by Status</p>
      {#if financeData.bills_by_status.length > 0}
        <DonutChart
          data={financeData.bills_by_status.map(s => ({ label: titleCase(s.status), value: s.count }))}
          size={180}
          centerLabel="bills"
          centerValue={fmtCount(financeData.bills_by_status.reduce((a, b) => a + b.count, 0))}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No bills</p>
      {/if}
    </div>

  {:else if config.widget_type === "finance_invoices_by_status" && financeData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Invoices by Status</p>
      {#if financeData.invoices_by_status.length > 0}
        <DonutChart
          data={financeData.invoices_by_status.map(s => ({ label: titleCase(s.status), value: s.count }))}
          size={180}
          centerLabel="invoices"
          centerValue={fmtCount(financeData.invoices_by_status.reduce((a, b) => a + b.count, 0))}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No invoices</p>
      {/if}
    </div>

  {:else if config.widget_type === "finance_recent_invoices" && financeData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Recent Invoices</p>
      {#if financeData.recent_invoices.length > 0}
        <div class="space-y-1.5 max-h-[230px] overflow-y-auto">
          {#each financeData.recent_invoices.slice(0, 6) as inv}
            <div class="flex items-center justify-between text-xs">
              <span class="min-w-0 truncate text-neutral-700 mr-2">
                <span class="font-semibold">{inv.invoice_number}</span>
                <span class="text-neutral-400">· {inv.customer_name}</span>
              </span>
              <span class="shrink-0 tabular-nums text-neutral-600">{fmtCurrency(inv.total_amount)}</span>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No recent invoices</p>
      {/if}
    </div>

  {:else if config.widget_type === "finance_recent_bills" && financeData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Recent Bills</p>
      {#if financeData.recent_bills.length > 0}
        <div class="space-y-1.5 max-h-[230px] overflow-y-auto">
          {#each financeData.recent_bills.slice(0, 6) as bill}
            <div class="flex items-center justify-between text-xs">
              <span class="min-w-0 truncate text-neutral-700 mr-2">
                <span class="font-semibold">{bill.bill_number}</span>
                <span class="text-neutral-400">· {bill.vendor_name}</span>
              </span>
              <span class="shrink-0 tabular-nums text-neutral-600">{fmtCurrency(bill.total_amount)}</span>
            </div>
          {/each}
        </div>
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No recent bills</p>
      {/if}
    </div>

  <!-- ── Cash-flow widgets (FinanceCashFlow source) ──────────────── -->
  {:else if config.widget_type === "cashflow_top_customers" && cashFlowData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Top Customers by Revenue</p>
      {#if cashFlowData.income_by_customer.length > 0}
        <HorizontalBarChart
          data={cashFlowData.income_by_customer.slice(0, 5).map(c => ({ label: c.label || "—", value: toNumber(c.value) }))}
          height={Math.max(120, cashFlowData.income_by_customer.slice(0, 5).length * 32)}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No revenue this period</p>
      {/if}
    </div>

  {:else if config.widget_type === "cashflow_top_vendors" && cashFlowData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Top Vendors by Spend</p>
      {#if cashFlowData.expense_by_vendor.length > 0}
        <HorizontalBarChart
          data={cashFlowData.expense_by_vendor.slice(0, 5).map(v => ({ label: v.label || "—", value: toNumber(v.value) }))}
          height={Math.max(120, cashFlowData.expense_by_vendor.slice(0, 5).length * 32)}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No spend this period</p>
      {/if}
    </div>

  {:else if config.widget_type === "cashflow_monthly_trend" && cashFlowData}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">Monthly Cash Flow ({cashFlowData.year})</p>
      {#if cashFlowData.monthly_flow.length > 0}
        <AreaChart
          data={cashFlowData.monthly_flow.map((m, i) => ({ x: new Date(cashFlowData.year, i, 1), y: toNumber(m.income) - toNumber(m.expenses) }))}
          formatX={(d) => (d as Date).toLocaleDateString("en-US", { month: "short" })}
          formatY={(d) => fmtCurrency(String(d))}
          color="#2563eb"
          height={180}
        />
      {:else}
        <p class="text-xs text-neutral-400 py-8 text-center">No monthly data</p>
      {/if}
    </div>

  {:else if config.widget_type === "cashflow_annual_totals" && cashFlowData}
    <div class="px-4 py-3 space-y-2">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Annual Income vs Expenses ({cashFlowData.year})</p>
      <div class="grid grid-cols-3 gap-2 text-xs">
        <div>
          <p class="text-neutral-400">Income</p>
          <p class="font-semibold text-emerald-700 tabular-nums">{fmtCurrency(cashFlowData.total_income)}</p>
        </div>
        <div>
          <p class="text-neutral-400">Expenses</p>
          <p class="font-semibold text-rose-700 tabular-nums">{fmtCurrency(cashFlowData.total_expenses)}</p>
        </div>
        <div>
          <p class="text-neutral-400">Net</p>
          <p class="font-semibold tabular-nums {toNumber(cashFlowData.net_balance) >= 0 ? 'text-emerald-700' : 'text-rose-700'}">
            {fmtCurrency(cashFlowData.net_balance)}
          </p>
        </div>
      </div>
    </div>

  {:else if config.widget_type === "cashflow_budget_remaining" && cashFlowData}
    {@const remaining = Math.max(0, Math.min(100, cashFlowData.budget_pct_remaining ?? 0))}
    {@const tone = remaining > 50 ? "emerald" : remaining > 20 ? "amber" : "rose"}
    <div class="px-4 py-3">
      <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Budget Remaining</p>
      <p class="mt-1 text-xl font-bold tabular-nums {tone === 'emerald' ? 'text-emerald-700' : tone === 'amber' ? 'text-amber-700' : 'text-rose-700'}">
        {remaining.toFixed(1)}%
      </p>
      <div class="mt-2 h-2 overflow-hidden rounded-full bg-neutral-100">
        <div
          class="h-full rounded-full {tone === 'emerald' ? 'bg-emerald-500' : tone === 'amber' ? 'bg-amber-500' : 'bg-rose-500'}"
          style="width: {remaining}%;"
        ></div>
      </div>
      <p class="mt-2 text-xs text-neutral-500">{(100 - remaining).toFixed(1)}% used</p>
    </div>

  {:else}
    <div class="px-4 py-8 text-center">
      <p class="text-xs text-neutral-400">Widget data unavailable</p>
    </div>
  {/if}
</div>

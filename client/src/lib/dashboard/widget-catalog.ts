import type { WidgetType, WidgetConfig } from "$lib/types";

export type WidgetGroup = "board_kpi" | "portfolio" | "finance" | "operations";
export type WidgetDataSource = "portfolio" | "board_kpi" | "finance" | "finance_cash_flow";

export interface WidgetTypeDefaults {
  typeLabel: string;
  defaultSize: { w: number; h: number };
  dataSource: WidgetDataSource;
}

/**
 * Single source of truth for widget type metadata used across the
 * custom-dashboard builder, picker, renderer, and viewer.
 *
 * `typeLabel` is the human-friendly name shown in the builder's per-widget
 * row (where it is augmented with the kpi_key when present). `defaultSize`
 * is the grid footprint applied when the widget is first added.
 * `dataSource` indicates which API payload the widget needs at render time
 * — used by the custom-dashboard viewer to lazy-load only what the active
 * layout actually requires.
 */
export const WIDGET_TYPE_DEFAULTS: Record<WidgetType, WidgetTypeDefaults> = {
  board_kpi_card: { typeLabel: "Board KPI", defaultSize: { w: 4, h: 2 }, dataSource: "board_kpi" },
  portfolio_kpi_summary: { typeLabel: "Portfolio Summary", defaultSize: { w: 6, h: 2 }, dataSource: "portfolio" },
  portfolio_type_distribution: { typeLabel: "Type Distribution", defaultSize: { w: 6, h: 4 }, dataSource: "portfolio" },
  portfolio_classification: { typeLabel: "Classification", defaultSize: { w: 6, h: 4 }, dataSource: "portfolio" },
  portfolio_valuation_history: { typeLabel: "Valuation History", defaultSize: { w: 6, h: 4 }, dataSource: "portfolio" },
  portfolio_unit_occupancy: { typeLabel: "Unit Occupancy", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_budget_summary: { typeLabel: "Project Budget", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_construction_budget_burn: { typeLabel: "Construction Budget Burn", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_property_inventory: { typeLabel: "Property Inventory", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_procurement_commitments: { typeLabel: "Procurement Commitments", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_rental_occupancy: { typeLabel: "Rental Occupancy", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_maintenance_backlog: { typeLabel: "Maintenance Backlog", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_cash_flow_forecast: { typeLabel: "Cash Flow Forecast", defaultSize: { w: 6, h: 4 }, dataSource: "finance" },
  portfolio_top_appreciating: { typeLabel: "Top Appreciating", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_top_depreciating: { typeLabel: "Top Depreciating", defaultSize: { w: 6, h: 3 }, dataSource: "portfolio" },
  portfolio_encumbrance: { typeLabel: "Encumbrances", defaultSize: { w: 6, h: 4 }, dataSource: "portfolio" },

  portfolio_total_acquisition: { typeLabel: "Total Acquisition Cost", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },
  portfolio_total_area: { typeLabel: "Total Area", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },
  portfolio_avg_price_per_sqft: { typeLabel: "Avg Price per sqft", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },

  hr_active_headcount: { typeLabel: "Active Headcount", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },
  hr_open_vacancies: { typeLabel: "Open Vacancies", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },
  tenant_active_count: { typeLabel: "Active Tenants", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },
  crm_active_leads: { typeLabel: "Active Leads", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },
  crm_closed_reservations: { typeLabel: "Closed Reservations", defaultSize: { w: 4, h: 2 }, dataSource: "portfolio" },

  finance_bills_by_status: { typeLabel: "Bills by Status", defaultSize: { w: 6, h: 4 }, dataSource: "finance" },
  finance_invoices_by_status: { typeLabel: "Invoices by Status", defaultSize: { w: 6, h: 4 }, dataSource: "finance" },
  finance_recent_invoices: { typeLabel: "Recent Invoices", defaultSize: { w: 6, h: 4 }, dataSource: "finance" },
  finance_recent_bills: { typeLabel: "Recent Bills", defaultSize: { w: 6, h: 4 }, dataSource: "finance" },

  cashflow_top_customers: { typeLabel: "Top Customers by Revenue", defaultSize: { w: 6, h: 4 }, dataSource: "finance_cash_flow" },
  cashflow_top_vendors: { typeLabel: "Top Vendors by Spend", defaultSize: { w: 6, h: 4 }, dataSource: "finance_cash_flow" },
  cashflow_monthly_trend: { typeLabel: "Monthly Cash Flow", defaultSize: { w: 12, h: 4 }, dataSource: "finance_cash_flow" },
  cashflow_annual_totals: { typeLabel: "Annual Income vs Expenses", defaultSize: { w: 6, h: 3 }, dataSource: "finance_cash_flow" },
  cashflow_budget_remaining: { typeLabel: "Budget Remaining", defaultSize: { w: 6, h: 3 }, dataSource: "finance_cash_flow" },
};

export interface WidgetCatalogEntry {
  type: WidgetType;
  kpiKey?: string;
  /** Picker-button label. For board KPI cards this is per-KPI; otherwise it matches typeLabel. */
  label: string;
  group: WidgetGroup;
}

/**
 * Addable widget options shown in the builder's picker. Each entry maps
 * 1:1 to a button the user can click. Most entries inherit their label
 * from `WIDGET_TYPE_DEFAULTS[type].typeLabel`; board-KPI entries override
 * it with the specific KPI name since one type spawns six options.
 */
export const WIDGET_CATALOG: WidgetCatalogEntry[] = [
  { type: "board_kpi_card", kpiKey: "procurement_cycle_time_days", label: "Procurement Cycle Time", group: "board_kpi" },
  { type: "board_kpi_card", kpiKey: "cost_variance_per_project_pct", label: "Cost Variance", group: "board_kpi" },
  { type: "board_kpi_card", kpiKey: "vendor_reliability_score", label: "Vendor Reliability", group: "board_kpi" },
  { type: "board_kpi_card", kpiKey: "emergency_purchases_pct", label: "Emergency Purchases", group: "board_kpi" },
  { type: "board_kpi_card", kpiKey: "budget_overrun_frequency_pct", label: "Budget Overrun", group: "board_kpi" },
  { type: "board_kpi_card", kpiKey: "average_approval_time_hours", label: "Approval Time", group: "board_kpi" },

  { type: "portfolio_kpi_summary", label: WIDGET_TYPE_DEFAULTS.portfolio_kpi_summary.typeLabel, group: "portfolio" },
  { type: "portfolio_type_distribution", label: WIDGET_TYPE_DEFAULTS.portfolio_type_distribution.typeLabel, group: "portfolio" },
  { type: "portfolio_classification", label: WIDGET_TYPE_DEFAULTS.portfolio_classification.typeLabel, group: "portfolio" },
  { type: "portfolio_valuation_history", label: WIDGET_TYPE_DEFAULTS.portfolio_valuation_history.typeLabel, group: "portfolio" },
  { type: "portfolio_unit_occupancy", label: WIDGET_TYPE_DEFAULTS.portfolio_unit_occupancy.typeLabel, group: "portfolio" },
  { type: "portfolio_budget_summary", label: WIDGET_TYPE_DEFAULTS.portfolio_budget_summary.typeLabel, group: "portfolio" },
  { type: "portfolio_construction_budget_burn", label: WIDGET_TYPE_DEFAULTS.portfolio_construction_budget_burn.typeLabel, group: "portfolio" },
  { type: "portfolio_property_inventory", label: WIDGET_TYPE_DEFAULTS.portfolio_property_inventory.typeLabel, group: "portfolio" },
  { type: "portfolio_procurement_commitments", label: WIDGET_TYPE_DEFAULTS.portfolio_procurement_commitments.typeLabel, group: "portfolio" },
  { type: "portfolio_rental_occupancy", label: WIDGET_TYPE_DEFAULTS.portfolio_rental_occupancy.typeLabel, group: "portfolio" },
  { type: "portfolio_maintenance_backlog", label: WIDGET_TYPE_DEFAULTS.portfolio_maintenance_backlog.typeLabel, group: "portfolio" },
  { type: "portfolio_cash_flow_forecast", label: WIDGET_TYPE_DEFAULTS.portfolio_cash_flow_forecast.typeLabel, group: "portfolio" },
  { type: "portfolio_top_appreciating", label: WIDGET_TYPE_DEFAULTS.portfolio_top_appreciating.typeLabel, group: "portfolio" },
  { type: "portfolio_top_depreciating", label: WIDGET_TYPE_DEFAULTS.portfolio_top_depreciating.typeLabel, group: "portfolio" },
  { type: "portfolio_encumbrance", label: WIDGET_TYPE_DEFAULTS.portfolio_encumbrance.typeLabel, group: "portfolio" },

  { type: "portfolio_total_acquisition", label: WIDGET_TYPE_DEFAULTS.portfolio_total_acquisition.typeLabel, group: "portfolio" },
  { type: "portfolio_total_area", label: WIDGET_TYPE_DEFAULTS.portfolio_total_area.typeLabel, group: "portfolio" },
  { type: "portfolio_avg_price_per_sqft", label: WIDGET_TYPE_DEFAULTS.portfolio_avg_price_per_sqft.typeLabel, group: "portfolio" },

  { type: "hr_active_headcount", label: WIDGET_TYPE_DEFAULTS.hr_active_headcount.typeLabel, group: "operations" },
  { type: "hr_open_vacancies", label: WIDGET_TYPE_DEFAULTS.hr_open_vacancies.typeLabel, group: "operations" },
  { type: "tenant_active_count", label: WIDGET_TYPE_DEFAULTS.tenant_active_count.typeLabel, group: "operations" },
  { type: "crm_active_leads", label: WIDGET_TYPE_DEFAULTS.crm_active_leads.typeLabel, group: "operations" },
  { type: "crm_closed_reservations", label: WIDGET_TYPE_DEFAULTS.crm_closed_reservations.typeLabel, group: "operations" },

  { type: "finance_bills_by_status", label: WIDGET_TYPE_DEFAULTS.finance_bills_by_status.typeLabel, group: "finance" },
  { type: "finance_invoices_by_status", label: WIDGET_TYPE_DEFAULTS.finance_invoices_by_status.typeLabel, group: "finance" },
  { type: "finance_recent_invoices", label: WIDGET_TYPE_DEFAULTS.finance_recent_invoices.typeLabel, group: "finance" },
  { type: "finance_recent_bills", label: WIDGET_TYPE_DEFAULTS.finance_recent_bills.typeLabel, group: "finance" },

  { type: "cashflow_top_customers", label: WIDGET_TYPE_DEFAULTS.cashflow_top_customers.typeLabel, group: "finance" },
  { type: "cashflow_top_vendors", label: WIDGET_TYPE_DEFAULTS.cashflow_top_vendors.typeLabel, group: "finance" },
  { type: "cashflow_monthly_trend", label: WIDGET_TYPE_DEFAULTS.cashflow_monthly_trend.typeLabel, group: "finance" },
  { type: "cashflow_annual_totals", label: WIDGET_TYPE_DEFAULTS.cashflow_annual_totals.typeLabel, group: "finance" },
  { type: "cashflow_budget_remaining", label: WIDGET_TYPE_DEFAULTS.cashflow_budget_remaining.typeLabel, group: "finance" },
];

export function getDefaultSize(type: WidgetType): { w: number; h: number } {
  return WIDGET_TYPE_DEFAULTS[type]?.defaultSize ?? { w: 4, h: 2 };
}

export function getTypeLabel(type: WidgetType): string {
  return WIDGET_TYPE_DEFAULTS[type]?.typeLabel ?? String(type);
}

/**
 * Returns the unique set of API data sources required to render the given
 * layout. Used by the custom-dashboard viewer to skip unused payloads.
 */
export function getRequiredDataSources(
  layout: Pick<WidgetConfig, "widget_type">[],
): Set<WidgetDataSource> {
  const needed = new Set<WidgetDataSource>();
  for (const widget of layout) {
    const source = WIDGET_TYPE_DEFAULTS[widget.widget_type]?.dataSource;
    if (source) needed.add(source);
  }
  return needed;
}

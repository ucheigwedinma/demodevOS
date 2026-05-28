<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";

  type TenantRowStatus = "active" | "overdue" | "notice_given" | "pending_move_in" | "inactive" | "moved_out";
  type OccupancyUnitStatus = "occupied" | "vacant_ready" | "notice_given" | "under_maintenance";
  type TenancyTypeKey = "residential" | "commercial";
  type DebtStatusKey = "clear" | "outstanding" | "overdue";

  interface TenantDashboardOverview {
    generated_at: string;
    portfolio_scope: {
      properties_count: number;
      active_tenants: number;
      total_units: number;
    };
    occupancy: {
      rate: number;
      occupied_units: number;
      total_units: number;
    };
    arrears: {
      total: string;
      overdue_invoices: number;
      customers_in_arrears: number;
    };
    monthly_revenue: {
      collections_total: string;
      target_total: string;
      attainment_pct: number | null;
      period_start: string;
      period_end: string;
    };
    maintenance: {
      open_work_orders: number;
      urgent_open_work_orders: number;
    };
    lease_expirations: {
      count: number;
      window_days: number;
      soonest_date: string | null;
    };
  }

  interface TenantMasterListRow {
    id: number;
    tenant_name: string;
    unit_label: string;
    property_name: string;
    property_location: string;
    lease_expiry: string | null;
    balance: string;
    status_key: TenantRowStatus;
    status_label: string;
    tenancy_type_key: TenancyTypeKey;
    tenancy_type_label: string;
    debt_status_key: DebtStatusKey;
    debt_status_label: string;
  }

  interface OccupancyUnitCard {
    id: number;
    tenant_profile_id: number | null;
    unit_number: string;
    floor: number | null;
    space_label: string;
    location_description: string;
    tenant_name: string;
    balance: string;
    lease_expiry: string | null;
    status_key: OccupancyUnitStatus;
    status_label: string;
    open_work_orders: number;
  }

  interface OccupancyPropertyGroup {
    property_id: number;
    property_name: string;
    totals: Record<OccupancyUnitStatus, number>;
    units: OccupancyUnitCard[];
  }

  interface TenantDashboardLayout {
    generated_at: string;
    master_list: TenantMasterListRow[];
    filters: {
      property_locations: string[];
      tenancy_types: Array<{ value: TenancyTypeKey; label: string }>;
      debt_statuses: Array<{ value: DebtStatusKey; label: string }>;
    };
    occupancy_vacancy: {
      totals: Record<OccupancyUnitStatus, number>;
      properties: OccupancyPropertyGroup[];
    };
  }

  interface TenantCollectionTrendPoint {
    label: string;
    month_start: string;
    collections_total: string;
  }

  interface TenantAgingBucket {
    key: string;
    label: string;
    total: string;
    count: number;
  }

  interface TenantPropertyIncomeComparison {
    property_id: number;
    property_name: string;
    income_collected: string;
    maintenance_cost: string;
    net: string;
  }

  interface TenantRevenueAnalytics {
    generated_at: string;
    collection_trend: {
      months: TenantCollectionTrendPoint[];
      total_collections: string;
      peak_collections: string;
      average_collections: string;
    };
    aging_buckets: {
      total_overdue: string;
      overdue_invoices: number;
      buckets: TenantAgingBucket[];
    };
    expense_vs_income: {
      period_start: string;
      period_end: string;
      rent_collected_total: string;
      maintenance_cost_total: string;
      net_operating_total: string;
      expense_ratio_pct: number | null;
      property_breakdown: TenantPropertyIncomeComparison[];
    };
  }

  interface TenantCommunicationEntry {
    id: number | string;
    interaction_type: string;
    interaction_type_display: string;
    channel: string;
    channel_display: string;
    direction: string;
    direction_display: string;
    status: string;
    status_display: string;
    subject: string;
    message: string;
    metadata: Record<string, unknown>;
    happened_at: string;
    author_name: string;
  }

  interface TenantIntelligenceDetail {
    generated_at: string;
    tenant: {
      id: number;
      name: string;
      status: TenantRowStatus;
      status_label: string;
      tenant_type: string;
      tenant_type_display: string;
      property_name: string;
      unit_label: string;
      lease_start_date: string | null;
      lease_end_date: string | null;
      move_in_date: string | null;
      move_out_date: string | null;
      current_balance: string;
      overdue_balance: string;
    };
    payment_reliability: {
      score: number;
      label: string;
      summary: string;
      total_invoices: number;
      paid_on_time: number;
      paid_late: number;
      overdue_invoices: number;
      current_balance: string;
      overdue_balance: string;
    };
    lease_timeline: {
      start_date: string | null;
      end_date: string | null;
      elapsed_days: number;
      remaining_days: number;
      total_days: number;
      elapsed_pct: number;
      status_label: string;
    };
    communication_log: TenantCommunicationEntry[];
    contact: {
      email: string;
      phone: string;
    };
    quick_actions: {
      can_generate_invoice: boolean;
      can_send_payment_reminder: boolean;
      can_initiate_eviction_notice: boolean;
    };
  }

  interface TenantActionResult {
    detail: string;
    generated_count?: number;
    delivery_count?: number;
    notification_count?: number;
    successful_dispatches?: number;
    skipped?: Array<{ tenant_id: number; tenant_name: string; reason: string }>;
  }

  const cardShellClass =
    "relative overflow-hidden rounded-xl border border-slate-200/75 bg-white/64 p-5 shadow-[0_18px_52px_-34px_rgba(15,23,42,0.28)] backdrop-blur-xl";
  const reliabilityStars = [1, 2, 3, 4, 5];

  const masterListStatusOptions: Array<{ value: "all" | TenantRowStatus; label: string }> = [
    { value: "all", label: "All statuses" },
    { value: "overdue", label: "Overdue" },
    { value: "notice_given", label: "Notice Given" },
    { value: "active", label: "Active" },
    { value: "pending_move_in", label: "Pending Move In" },
    { value: "inactive", label: "Inactive" },
    { value: "moved_out", label: "Moved Out" },
  ];

  const occupancyLegend: Array<{ key: OccupancyUnitStatus; label: string }> = [
    { key: "occupied", label: "Occupied" },
    { key: "vacant_ready", label: "Vacant" },
    { key: "notice_given", label: "Notice Given" },
    { key: "under_maintenance", label: "Under Maintenance" },
  ];

  let loading = $state(true);
  let refreshing = $state(false);
  let overview = $state<TenantDashboardOverview | null>(null);
  let layout = $state<TenantDashboardLayout | null>(null);
  let revenueAnalytics = $state<TenantRevenueAnalytics | null>(null);
  let tenantSearch = $state("");
  let tenantStatusFilter = $state<"all" | TenantRowStatus>("all");
  let propertyLocationFilter = $state<"all" | string>("all");
  let tenancyTypeFilter = $state<"all" | TenancyTypeKey>("all");
  let debtStatusFilter = $state<"all" | DebtStatusKey>("all");
  let selectedTenantIds = $state<number[]>([]);
  let showManagementLayoutDrawer = $state(false);
  let showBulkActionDrawer = $state(false);
  let bulkActionMode = $state<"service_charge" | "holiday_announcement">("service_charge");
  let bulkActionSubmitting = $state(false);
  let bulkInvoiceForm = $state({
    description: "Monthly service charge",
    amount: "",
    due_in_days: "7",
    notes: "",
    send_notifications: true,
  });
  let bulkAnnouncementForm = $state({
    subject: "Holiday announcement",
    message: "",
    delivery_mode: "all_available",
  });
  let showIntelligenceDrawer = $state(false);
  let selectedTenantId = $state<number | null>(null);
  let intelligenceLoading = $state(false);
  let intelligenceError = $state("");
  let intelligenceAction = $state<"generate_invoice" | "send_payment_reminder" | "initiate_eviction_notice" | null>(null);
  let tenantIntelligence = $state<TenantIntelligenceDetail | null>(null);

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtInt(value: unknown): string {
    return toNumber(value).toLocaleString("en-US");
  }

  function fmtPct(value: number | null | undefined): string {
    if (value === null || value === undefined) return "--";
    return `${value.toFixed(1)}%`;
  }

  function fmtMoney(value: string | number | null | undefined): string {
    const parsed = Number(value ?? 0);
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: "NGN",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(parsed) ? parsed : 0);
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function clampPct(value: number | null | undefined): number {
    return Math.max(0, Math.min(toNumber(value), 100));
  }

  function parseApiMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string" && error.data.detail) return error.data.detail;
      if (typeof error.data.message === "string" && error.data.message) return error.data.message;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  function csvCell(value: unknown): string {
    const text = String(value ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    return `"${text.replace(/"/g, '""')}"`;
  }

  function csvRow(values: unknown[]): string {
    return values.map((value) => csvCell(value)).join(",");
  }

  function masterListBadgeClass(statusKey: TenantRowStatus): string {
    switch (statusKey) {
      case "active":
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
      case "overdue":
        return "border-rose-200 bg-rose-50 text-rose-700";
      case "notice_given":
        return "border-rose-200 bg-rose-50 text-rose-700";
      case "pending_move_in":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "moved_out":
        return "border-slate-200 bg-slate-100 text-slate-600";
      default:
        return "border-neutral-200 bg-neutral-100 text-neutral-600";
    }
  }

  function occupancyLegendClass(statusKey: OccupancyUnitStatus): string {
    switch (statusKey) {
      case "occupied":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "notice_given":
        return "border-orange-200 bg-orange-50 text-orange-700";
      case "under_maintenance":
        return "border-sky-200 bg-sky-50 text-sky-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  }

  function occupancyTileClass(statusKey: OccupancyUnitStatus): string {
    switch (statusKey) {
      case "occupied":
        return "border-emerald-200/80 bg-linear-to-br from-emerald-100 via-emerald-50 to-white text-emerald-950";
      case "notice_given":
        return "border-orange-200/80 bg-linear-to-br from-orange-100 via-amber-50 to-white text-orange-950";
      case "under_maintenance":
        return "border-sky-200/80 bg-linear-to-br from-sky-100 via-blue-50 to-white text-sky-950";
      default:
        return "border-slate-200/80 bg-linear-to-br from-slate-100 via-white to-slate-50 text-slate-900";
    }
  }

  function occupancyStatusLabel(unit: OccupancyUnitCard): string {
    return unit.status_key === "vacant_ready" ? "Vacant" : unit.status_label;
  }

  function occupancyCardTitle(unit: OccupancyUnitCard): string {
    if (unit.tenant_name) {
      return unit.space_label || unit.location_description || "Occupied unit";
    }
    if (unit.status_key === "under_maintenance") return "Maintenance hold";
    return "Available to assign";
  }

  function occupancyCardSubtitle(unit: OccupancyUnitCard): string {
    if (unit.tenant_name) {
      if (unit.space_label && unit.location_description && unit.location_description !== unit.space_label) {
        return unit.location_description;
      }
      if (unit.status_key === "notice_given" && unit.lease_expiry) {
        return `Lease ${fmtDate(unit.lease_expiry)}`;
      }
      return "";
    }
    if (unit.status_key === "under_maintenance") return "Temporarily unavailable";
    return "";
  }

  function occupancyCardMeta(unit: OccupancyUnitCard): string {
    if (unit.tenant_name) {
      if (toNumber(unit.balance) > 0) return "Arrears flagged";
      if (unit.status_key === "notice_given") return "Move-out soon";
      return "Current";
    }
    if (unit.open_work_orders > 0) {
      return `${fmtInt(unit.open_work_orders)} work order${unit.open_work_orders === 1 ? "" : "s"}`;
    }
    if (unit.status_key === "under_maintenance") return "Maintenance";
    return "Ready";
  }

  function occupancyCardMetaClass(unit: OccupancyUnitCard): string {
    if (unit.tenant_name && toNumber(unit.balance) > 0) {
      return "border-rose-200 bg-rose-50 text-rose-700";
    }
    if (unit.tenant_name && unit.status_key === "notice_given") {
      return "border-orange-200 bg-orange-50 text-orange-700";
    }
    if (unit.tenant_name) {
      return "border-white/60 bg-white/72 text-slate-700";
    }
    if (unit.open_work_orders > 0 || unit.status_key === "under_maintenance") {
      return "border-sky-200 bg-sky-50 text-sky-700";
    }
    return "border-slate-200 bg-white/72 text-slate-700";
  }

  function reliabilityBadgeClass(score: number): string {
    if (score >= 5) return "border-emerald-200 bg-emerald-50 text-emerald-700";
    if (score === 4) return "border-teal-200 bg-teal-50 text-teal-700";
    if (score === 3) return "border-amber-200 bg-amber-50 text-amber-700";
    if (score === 2) return "border-orange-200 bg-orange-50 text-orange-700";
    return "border-rose-200 bg-rose-50 text-rose-700";
  }

  function communicationStatusClass(statusKey: string): string {
    switch (statusKey) {
      case "sent":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "queued":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "failed":
        return "border-rose-200 bg-rose-50 text-rose-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  }

  function communicationChannelClass(channel: string): string {
    switch (channel) {
      case "email":
        return "border-violet-200 bg-violet-50 text-violet-700";
      case "whatsapp":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "phone":
        return "border-amber-200 bg-amber-50 text-amber-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  }

  function debtStatusBadgeClass(statusKey: DebtStatusKey): string {
    switch (statusKey) {
      case "overdue":
        return "border-rose-200 bg-rose-50 text-rose-700";
      case "outstanding":
        return "border-rose-200 bg-rose-50 text-rose-700";
      default:
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
    }
  }

  function tenancyTypeBadgeClass(typeKey: TenancyTypeKey): string {
    if (typeKey === "commercial") return "border-violet-200 bg-violet-50 text-violet-700";
    return "border-sky-200 bg-sky-50 text-sky-700";
  }

  function agingBucketClass(bucketKey: string): string {
    switch (bucketKey) {
      case "current":
        return "border-amber-200 bg-amber-50 text-amber-800";
      case "overdue_30":
        return "border-orange-200 bg-orange-50 text-orange-800";
      case "overdue_60":
        return "border-rose-200 bg-rose-50 text-rose-800";
      default:
        return "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-800";
    }
  }

  function collectionTrendPoints(months: TenantCollectionTrendPoint[]): string {
    if (months.length === 0) return "";
    const chartWidth = 360;
    const chartHeight = 180;
    const paddingX = 20;
    const paddingTop = 20;
    const paddingBottom = 24;
    const usableWidth = chartWidth - paddingX * 2;
    const usableHeight = chartHeight - paddingTop - paddingBottom;
    const maxValue = Math.max(...months.map((month) => toNumber(month.collections_total)), 1);
    const step = months.length === 1 ? 0 : usableWidth / (months.length - 1);

    return months
      .map((month, index) => {
        const value = toNumber(month.collections_total);
        const x = paddingX + step * index;
        const y = paddingTop + (usableHeight - (value / maxValue) * usableHeight);
        return `${x},${y}`;
      })
      .join(" ");
  }

  function collectionTrendAreaPoints(months: TenantCollectionTrendPoint[]): string {
    if (months.length === 0) return "";
    const linePoints = collectionTrendPoints(months);
    if (!linePoints) return "";
    const chartHeight = 180;
    const baseline = chartHeight - 24;
    const paddingX = 20;
    const chartWidth = 360;
    const lastX = months.length === 1 ? paddingX : chartWidth - paddingX;
    return `${paddingX},${baseline} ${linePoints} ${lastX},${baseline}`;
  }

  function comparisonBarWidth(value: string | number, total: string | number): number {
    const totalNumber = toNumber(total);
    if (totalNumber <= 0) return 0;
    return Math.max(0, Math.min((toNumber(value) / totalNumber) * 100, 100));
  }

  function filteredMasterList(): TenantMasterListRow[] {
    const rows = layout?.master_list ?? [];
    const query = tenantSearch.trim().toLowerCase();
    return rows.filter((row) => {
      if (tenantStatusFilter !== "all" && row.status_key !== tenantStatusFilter) return false;
      if (propertyLocationFilter !== "all" && row.property_location !== propertyLocationFilter) return false;
      if (tenancyTypeFilter !== "all" && row.tenancy_type_key !== tenancyTypeFilter) return false;
      if (debtStatusFilter !== "all" && row.debt_status_key !== debtStatusFilter) return false;
      if (!query) return true;
      return [
        row.tenant_name,
        row.unit_label,
        row.property_name,
        row.property_location,
        row.status_label,
        row.tenancy_type_label,
        row.debt_status_label,
      ].some((value) => value.toLowerCase().includes(query));
    });
  }

  function selectedTenantRows(): TenantMasterListRow[] {
    const selectedSet = new Set(selectedTenantIds);
    return (layout?.master_list ?? []).filter((row) => selectedSet.has(row.id));
  }

  function visibleTenantIds(): number[] {
    return filteredMasterList().map((row) => row.id);
  }

  function isTenantSelected(tenantId: number): boolean {
    return selectedTenantIds.includes(tenantId);
  }

  function areAllVisibleTenantsSelected(): boolean {
    const visibleIds = visibleTenantIds();
    if (visibleIds.length === 0) return false;
    return visibleIds.every((tenantId) => selectedTenantIds.includes(tenantId));
  }

  function toggleTenantSelection(tenantId: number) {
    if (selectedTenantIds.includes(tenantId)) {
      selectedTenantIds = selectedTenantIds.filter((id) => id !== tenantId);
      return;
    }
    selectedTenantIds = [...selectedTenantIds, tenantId];
  }

  function setVisibleTenantSelection(selected: boolean) {
    const visibleIds = visibleTenantIds();
    if (!selected) {
      selectedTenantIds = selectedTenantIds.filter((tenantId) => !visibleIds.includes(tenantId));
      return;
    }
    selectedTenantIds = Array.from(new Set([...selectedTenantIds, ...visibleIds]));
  }

  function clearSelectedTenants() {
    selectedTenantIds = [];
  }

  function openManagementLayoutDrawer() {
    showManagementLayoutDrawer = true;
  }

  function closeManagementLayoutDrawer() {
    showManagementLayoutDrawer = false;
  }

  function openBulkActionDrawer(mode: "service_charge" | "holiday_announcement") {
    if (selectedTenantIds.length === 0) return;
    showManagementLayoutDrawer = false;
    bulkActionMode = mode;
    showBulkActionDrawer = true;
  }

  function closeBulkActionDrawer() {
    showBulkActionDrawer = false;
    bulkActionSubmitting = false;
  }

  function resetBulkForms() {
    bulkInvoiceForm = {
      description: "Monthly service charge",
      amount: "",
      due_in_days: "7",
      notes: "",
      send_notifications: true,
    };
    bulkAnnouncementForm = {
      subject: "Holiday announcement",
      message: "",
      delivery_mode: "all_available",
    };
  }

  async function fetchDashboard() {
    if (!loading) refreshing = true;
    const results = await Promise.allSettled([
      api.get<TenantDashboardOverview>("/tenants/dashboard/overview/"),
      api.get<TenantDashboardLayout>("/tenants/dashboard/layout/"),
      api.get<TenantRevenueAnalytics>("/tenants/dashboard/revenue-analytics/"),
    ]);

    const [overviewResult, layoutResult, revenueAnalyticsResult] = results;
    const failedSections: string[] = [];

    if (overviewResult.status === "fulfilled") {
      overview = overviewResult.value;
    } else {
      overview = null;
      failedSections.push("portfolio health");
    }

    if (layoutResult.status === "fulfilled") {
      layout = layoutResult.value;
    } else {
      layout = null;
      failedSections.push("management layout");
    }

    if (revenueAnalyticsResult.status === "fulfilled") {
      revenueAnalytics = revenueAnalyticsResult.value;
    } else {
      revenueAnalytics = null;
      failedSections.push("revenue and aging analytics");
    }

    if (failedSections.length === 1) {
      toast.error("Load failed", `Could not load ${failedSections[0]} for the tenants dashboard.`);
    } else if (failedSections.length > 1) {
      toast.error("Load failed", "Could not load the tenants dashboard.");
    }

    loading = false;
    refreshing = false;
  }

  async function fetchTenantIntelligence(tenantId: number) {
    intelligenceLoading = true;
    intelligenceError = "";

    try {
      const detail = await api.get<TenantIntelligenceDetail>(`/tenants/profiles/${tenantId}/intelligence/`);
      if (selectedTenantId !== tenantId) return;
      tenantIntelligence = detail;
    } catch (error) {
      if (selectedTenantId !== tenantId) return;
      tenantIntelligence = null;
      intelligenceError = parseApiMessage(error, "Could not load tenant intelligence.");
      toast.error("Load failed", intelligenceError);
    } finally {
      if (selectedTenantId === tenantId) {
        intelligenceLoading = false;
      }
    }
  }

  async function openTenantIntelligence(tenantId: number) {
    selectedTenantId = tenantId;
    showManagementLayoutDrawer = false;
    showIntelligenceDrawer = true;
    tenantIntelligence = null;
    await fetchTenantIntelligence(tenantId);
  }

  function closeTenantIntelligence() {
    showIntelligenceDrawer = false;
    selectedTenantId = null;
    tenantIntelligence = null;
    intelligenceError = "";
    intelligenceLoading = false;
    intelligenceAction = null;
  }

  async function runTenantAction(
    actionKey: "generate_invoice" | "send_payment_reminder" | "initiate_eviction_notice",
    endpoint: string,
    successTitle: string,
    fallbackError: string
  ) {
    if (!selectedTenantId) return;
    const tenantId = selectedTenantId;

    intelligenceAction = actionKey;
    try {
      const result = await api.post<TenantActionResult>(`/tenants/profiles/${tenantId}/${endpoint}/`, {});
      toast.success(successTitle, result.detail || successTitle);
      if (selectedTenantId === tenantId) {
        await fetchTenantIntelligence(tenantId);
      }
      await fetchDashboard();
    } catch (error) {
      toast.error("Action failed", parseApiMessage(error, fallbackError));
    } finally {
      intelligenceAction = null;
    }
  }

  async function generateInvoice() {
    await runTenantAction(
      "generate_invoice",
      "generate-invoice",
      "Invoice generated",
      "Could not generate draft invoice."
    );
  }

  async function sendPaymentReminder() {
    await runTenantAction(
      "send_payment_reminder",
      "send-payment-reminder",
      "Reminder sent",
      "Could not send tenant payment reminder."
    );
  }

  async function initiateEvictionNotice() {
    await runTenantAction(
      "initiate_eviction_notice",
      "initiate-eviction-notice",
      "Eviction notice initiated",
      "Could not initiate eviction notice."
    );
  }

  async function submitBulkAction() {
    if (selectedTenantIds.length === 0) {
      toast.error("No tenants selected", "Select one or more tenants first.");
      return;
    }

    bulkActionSubmitting = true;
    try {
      let result: TenantActionResult;
      if (bulkActionMode === "service_charge") {
        result = await api.post<TenantActionResult>("/tenants/profiles/bulk-service-charge/", {
          tenant_ids: selectedTenantIds,
          description: bulkInvoiceForm.description,
          amount: bulkInvoiceForm.amount,
          due_in_days: bulkInvoiceForm.due_in_days,
          notes: bulkInvoiceForm.notes,
          send_notifications: bulkInvoiceForm.send_notifications,
        });
        toast.success(
          "Service charge blast complete",
          result.detail || `Generated ${result.generated_count ?? 0} invoice(s).`
        );
      } else {
        result = await api.post<TenantActionResult>("/tenants/profiles/bulk-holiday-announcement/", {
          tenant_ids: selectedTenantIds,
          subject: bulkAnnouncementForm.subject,
          message: bulkAnnouncementForm.message,
          delivery_mode: bulkAnnouncementForm.delivery_mode,
        });
        toast.success(
          "Holiday announcement sent",
          result.detail || `Processed ${result.delivery_count ?? 0} dispatches.`
        );
      }

      clearSelectedTenants();
      closeBulkActionDrawer();
      resetBulkForms();
      await fetchDashboard();
    } catch (error) {
      toast.error("Bulk action failed", parseApiMessage(error, "Could not complete the bulk action."));
    } finally {
      bulkActionSubmitting = false;
    }
  }

  function exportPortfolioReport() {
    if (!overview && !layout && !revenueAnalytics) {
      toast.error("Export unavailable", "Load the tenants dashboard before exporting the portfolio report.");
      return;
    }

    const rows: string[] = [];
    const exportedAt = new Date().toISOString();
    const visibleRows = filteredMasterList();

    rows.push(csvRow(["Portfolio Report", "Generated At", exportedAt]));
    rows.push("");

    if (overview) {
      rows.push(csvRow(["Portfolio Health"]));
      rows.push(csvRow(["Metric", "Value", "Notes"]));
      rows.push(
        csvRow([
          "Occupancy Rate",
          fmtPct(overview.occupancy.rate),
          `${fmtInt(overview.occupancy.occupied_units)} occupied of ${fmtInt(overview.occupancy.total_units)} units`,
        ])
      );
      rows.push(
        csvRow([
          "Total Arrears",
          fmtMoney(overview.arrears.total),
          `${fmtInt(overview.arrears.overdue_invoices)} overdue invoices / ${fmtInt(overview.arrears.customers_in_arrears)} tenants in arrears`,
        ])
      );
      rows.push(
        csvRow([
          "Monthly Revenue",
          fmtMoney(overview.monthly_revenue.collections_total),
          `Target ${fmtMoney(overview.monthly_revenue.target_total)} / attainment ${fmtPct(overview.monthly_revenue.attainment_pct)}`,
        ])
      );
      rows.push(
        csvRow([
          "Open Work Orders",
          fmtInt(overview.maintenance.open_work_orders),
          `${fmtInt(overview.maintenance.urgent_open_work_orders)} urgent / high priority`,
        ])
      );
      rows.push(
        csvRow([
          "Lease Expirations",
          fmtInt(overview.lease_expirations.count),
          `Within ${fmtInt(overview.lease_expirations.window_days)} days / soonest ${fmtDate(overview.lease_expirations.soonest_date)}`,
        ])
      );
      rows.push("");
    }

    if (layout) {
      rows.push(csvRow(["Tenant Master List - Current View"]));
      rows.push(csvRow(["Tenant Name", "Unit", "Property", "Location", "Lease Expiry", "Balance", "Status", "Debt Status", "Tenancy Type"]));
      if (visibleRows.length === 0) {
        rows.push(csvRow(["No tenant rows match the current filters."]));
      } else {
        for (const row of visibleRows) {
          rows.push(
            csvRow([
              row.tenant_name,
              row.unit_label,
              row.property_name,
              row.property_location,
              fmtDate(row.lease_expiry),
              fmtMoney(row.balance),
              row.status_label,
              row.debt_status_label,
              row.tenancy_type_label,
            ])
          );
        }
      }
      rows.push("");

      rows.push(csvRow(["Occupancy & Vacancy"]));
      rows.push(csvRow(["Property", "Occupied", "Vacant / Ready", "Notice Given", "Under Maintenance"]));
      for (const property of layout.occupancy_vacancy.properties) {
        rows.push(
          csvRow([
            property.property_name,
            fmtInt(property.totals.occupied),
            fmtInt(property.totals.vacant_ready),
            fmtInt(property.totals.notice_given),
            fmtInt(property.totals.under_maintenance),
          ])
        );
      }
      rows.push("");
    }

    if (revenueAnalytics) {
      rows.push(csvRow(["Collection Trend"]));
      rows.push(csvRow(["Month", "Collections"]));
      for (const month of revenueAnalytics.collection_trend.months) {
        rows.push(csvRow([month.label, fmtMoney(month.collections_total)]));
      }
      rows.push("");

      rows.push(csvRow(["Aging Buckets"]));
      rows.push(csvRow(["Bucket", "Total", "Invoice Count"]));
      for (const bucket of revenueAnalytics.aging_buckets.buckets) {
        rows.push(csvRow([bucket.label, fmtMoney(bucket.total), fmtInt(bucket.count)]));
      }
      rows.push("");

      rows.push(csvRow(["Expense vs. Income"]));
      rows.push(csvRow(["Property", "Rent Collected", "Maintenance Cost", "Net"]));
      for (const property of revenueAnalytics.expense_vs_income.property_breakdown) {
        rows.push(
          csvRow([
            property.property_name,
            fmtMoney(property.income_collected),
            fmtMoney(property.maintenance_cost),
            fmtMoney(property.net),
          ])
        );
      }
      rows.push("");
    }

    const csvContent = `\ufeff${rows.join("\n")}`;
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const dateStamp = new Date().toISOString().slice(0, 10);

    link.href = url;
    link.download = `tenant-portfolio-report-${dateStamp}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast.success("Portfolio report exported", "The tenants portfolio report download has started.");
  }

  $effect(() => {
    const availableIds = new Set((layout?.master_list ?? []).map((row) => row.id));
    const nextSelected = selectedTenantIds.filter((tenantId) => availableIds.has(tenantId));
    if (nextSelected.length !== selectedTenantIds.length) {
      selectedTenantIds = nextSelected;
    }
  });

  $effect(() => {
    if (showBulkActionDrawer && selectedTenantIds.length === 0) {
      showBulkActionDrawer = false;
    }
  });

  $effect(() => {
    fetchDashboard();
  });

  const live = useLiveKpis(
    ["Lease"],
    fetchDashboard,
    { debounceMs: 3000 },
  );
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div class="space-y-3">
      <div>
        <div class="flex items-center gap-2">
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-orange-700">Tenants</p>
          <LiveBadge refreshing={live.refreshing} />
        </div>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-slate-800">Dashboard</h1>
        <p class="mt-2 max-w-3xl text-sm text-slate-600">
          Portfolio-wide oversight for occupancy, lease risk, collections, and maintenance pressure across managed properties.
        </p>
      </div>

      {#if overview}
        <div class="flex flex-wrap gap-2">
          <span class="inline-flex items-center rounded-full border border-white/70 bg-white/70 px-3 py-1 text-xs font-medium text-slate-700 shadow-sm backdrop-blur">
            Properties {fmtInt(overview.portfolio_scope.properties_count)}
          </span>
          <span class="inline-flex items-center rounded-full border border-white/70 bg-white/70 px-3 py-1 text-xs font-medium text-slate-700 shadow-sm backdrop-blur">
            Active Tenants {fmtInt(overview.portfolio_scope.active_tenants)}
          </span>
          <span class="inline-flex items-center rounded-full border border-white/70 bg-white/70 px-3 py-1 text-xs font-medium text-slate-700 shadow-sm backdrop-blur">
            Units Tracked {fmtInt(overview.portfolio_scope.total_units)}
          </span>
        </div>
      {/if}

      {#if overview?.generated_at || layout?.generated_at}
        <p class="text-xs text-slate-500">Last refreshed: {fmtDateTime(overview?.generated_at ?? layout?.generated_at)}</p>
      {/if}
    </div>

    <div class="flex items-center gap-2 self-start lg:self-auto">
      <button
        type="button"
        onclick={exportPortfolioReport}
        class="inline-flex items-center gap-2 rounded-xl border border-sky-200/80 bg-[linear-gradient(135deg,rgba(240,249,255,0.96),rgba(245,243,255,0.94))] px-4 py-2.5 text-sm font-semibold text-slate-900 shadow-[0_16px_38px_-30px_rgba(14,116,144,0.26)] backdrop-blur transition hover:border-sky-300 hover:shadow-[0_20px_44px_-28px_rgba(14,116,144,0.32)]"
      >
        <svg class="h-4 w-4 text-sky-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0 4-4m-4 4-4-4M4 17.5v.5A2 2 0 0 0 6 20h12a2 2 0 0 0 2-2v-.5" />
        </svg>
        Export Portfolio Report
      </button>

      <button
        type="button"
        onclick={fetchDashboard}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/70 bg-white/72 text-slate-700 shadow-sm backdrop-blur hover:border-slate-300 hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing tenants dashboard" : "Refresh tenants dashboard"}
        title={refreshing ? "Refreshing tenants dashboard" : "Refresh tenants dashboard"}
      >
        <svg
          class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003"
          />
        </svg>
      </button>
    </div>
  </div>

  <section class="relative overflow-hidden rounded-xl border border-slate-200/80 bg-[radial-gradient(circle_at_top_left,rgba(125,211,252,0.1),transparent_40%),radial-gradient(circle_at_top_right,rgba(196,181,253,0.1),transparent_38%),linear-gradient(180deg,rgba(255,255,255,0.97),rgba(248,250,252,0.95))] p-5 shadow-[0_26px_72px_-50px_rgba(15,23,42,0.24)]">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Portfolio Health</p>
        <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Top Summary</h2>
        <p class="mt-1 text-sm text-slate-600">
          Big-picture portfolio health across occupancy, collections, maintenance load, and lease rollover risk.
        </p>
      </div>
    </div>

    {#if loading}
      <div class="mt-5 rounded-lg border border-dashed border-slate-300 bg-white/65 p-10 text-center text-sm text-slate-500 backdrop-blur">
        Loading portfolio health...
      </div>
    {:else if !overview}
      <div class="mt-5 rounded-lg border border-red-200 bg-red-50/90 p-6 text-sm text-red-700">
        Tenants portfolio health is unavailable right now.
      </div>
    {:else}
      <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <article class={cardShellClass}>
          <div class="absolute inset-0 bg-linear-to-br from-sky-100/36 via-white/8 to-cyan-100/24"></div>
          <div class="relative">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-800">Occupancy Rate</p>
            <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-950">{fmtPct(overview.occupancy.rate)}</p>
            <p class="mt-2 text-sm text-slate-600">
              {fmtInt(overview.occupancy.occupied_units)} occupied of {fmtInt(overview.occupancy.total_units)} units.
            </p>
            <div class="mt-4 h-2 overflow-hidden rounded-full bg-white/65">
              <div
                class="h-full rounded-full bg-linear-to-r from-sky-500 to-cyan-400 transition-all"
                style={`width: ${Math.max(0, Math.min(toNumber(overview.occupancy.rate), 100))}%`}
              ></div>
            </div>
          </div>
        </article>

        <article class={`${cardShellClass} text-white`}>
          <div class="absolute inset-0 bg-linear-to-br from-[#bc5a1d] via-[#e96b3b] to-[#d96a2f]"></div>
          <div class="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.18),transparent_52%)]"></div>
          <div class="relative">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-orange-100">Total Arrears</p>
            <p class="mt-4 text-2xl font-semibold tracking-tight text-white">{fmtMoney(overview.arrears.total)}</p>
            <div class="mt-3 flex flex-wrap gap-2 text-xs text-orange-50">
              <span class="rounded-full border border-white/25 bg-white/10 px-2.5 py-1">
                {fmtInt(overview.arrears.overdue_invoices)} overdue invoices
              </span>
              <span class="rounded-full border border-white/25 bg-white/10 px-2.5 py-1">
                {fmtInt(overview.arrears.customers_in_arrears)} customers in arrears
              </span>
            </div>
          </div>
        </article>

        <article class={cardShellClass}>
          <div class="absolute inset-0 bg-linear-to-br from-emerald-100/36 via-white/8 to-teal-100/24"></div>
          <div class="relative">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-800">Monthly Revenue</p>
            <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-950">
              {fmtMoney(overview.monthly_revenue.collections_total)}
            </p>
            <p class="mt-2 text-sm text-slate-600">
              vs target {fmtMoney(overview.monthly_revenue.target_total)}
            </p>
            <div class="mt-4 flex items-center justify-between text-xs text-slate-500">
              <span>{fmtDate(overview.monthly_revenue.period_start)} - {fmtDate(overview.monthly_revenue.period_end)}</span>
              <span class="font-semibold text-emerald-700">{fmtPct(overview.monthly_revenue.attainment_pct)} attained</span>
            </div>
            <div class="mt-2 h-2 overflow-hidden rounded-full bg-white/70">
              <div
                class="h-full rounded-full bg-linear-to-r from-emerald-500 to-teal-400 transition-all"
                style={`width: ${Math.max(0, Math.min(toNumber(overview.monthly_revenue.attainment_pct), 100))}%`}
              ></div>
            </div>
          </div>
        </article>

        <article class={cardShellClass}>
          <div class="absolute inset-0 bg-linear-to-br from-amber-100/34 via-white/8 to-indigo-100/22"></div>
          <div class="relative">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-indigo-800">Open Work Orders</p>
            <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-950">
              {fmtInt(overview.maintenance.open_work_orders)}
            </p>
            <p class="mt-2 text-sm text-slate-600">
              Unresolved maintenance requests across the managed portfolio.
            </p>
            <div class="mt-4 inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
              {fmtInt(overview.maintenance.urgent_open_work_orders)} urgent / high priority
            </div>
          </div>
        </article>

        <article class={cardShellClass}>
          <div class="absolute inset-0 bg-linear-to-br from-violet-100/34 via-white/8 to-fuchsia-100/22"></div>
          <div class="relative">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-800">Lease Expirations</p>
            <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-950">
              {fmtInt(overview.lease_expirations.count)}
            </p>
            <p class="mt-2 text-sm text-slate-600">
              Active leases ending within the next {fmtInt(overview.lease_expirations.window_days)} days.
            </p>
            <div class="mt-4 rounded-2xl border border-violet-200/70 bg-white/65 px-3 py-2 text-xs text-violet-900 backdrop-blur-sm">
              Soonest expiry: <span class="font-semibold">{fmtDate(overview.lease_expirations.soonest_date)}</span>
            </div>
          </div>
        </article>
      </div>
    {/if}
  </section>

  <section class="relative overflow-hidden rounded-xl border border-slate-200/80 bg-[radial-gradient(circle_at_top_left,rgba(196,181,253,0.09),transparent_40%),radial-gradient(circle_at_bottom_right,rgba(251,191,36,0.08),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.97),rgba(248,250,252,0.95))] p-5 shadow-[0_26px_72px_-50px_rgba(15,23,42,0.24)]">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">Management Layout Grid</p>
        <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Master List + Occupancy Drawer</h2>
        <p class="mt-1 text-sm text-slate-600">
          The tenant master list and occupancy view now open in a dedicated drawer so this dashboard stays easier to scan.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <p class="text-xs text-slate-500">Green = occupied, grey = vacant, orange = notice given, blue = under maintenance.</p>
        <button
          type="button"
          onclick={openManagementLayoutDrawer}
          class="inline-flex items-center rounded-full border border-violet-200 bg-white px-4 py-2 text-xs font-semibold text-violet-700 transition hover:border-violet-300 hover:bg-violet-50"
        >
          Open management grid
        </button>
      </div>
    </div>

    {#if loading}
      <div class="mt-5 rounded-[24px] border border-dashed border-slate-300 bg-white/65 p-10 text-center text-sm text-slate-500 backdrop-blur">
        Loading management layout grid...
      </div>
    {:else if !layout}
      <div class="mt-5 rounded-[24px] border border-red-200 bg-red-50/90 p-6 text-sm text-red-700">
        Tenant management layout is unavailable right now.
      </div>
    {:else}
      <div class="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1.08fr)_minmax(300px,0.92fr)]">
        <article class="rounded-xl border border-white/70 bg-white/68 p-5 shadow-[0_20px_56px_-38px_rgba(15,23,42,0.24)] backdrop-blur-xl">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Master Ledger Access</p>
              <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Open the full control surface when you need it</h3>
              <p class="mt-2 max-w-2xl text-sm text-slate-600">
                Search tenants, manage bulk actions, and drill into the occupancy map from a dedicated drawer instead of keeping the whole grid on the page.
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                Rows {fmtInt(filteredMasterList().length)}
              </span>
              <span class="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                Selected {fmtInt(selectedTenantIds.length)}
              </span>
            </div>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-3">
            <div class="rounded-xl border border-white/80 bg-white/80 p-4 shadow-sm">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Overdue</p>
              <p class="mt-2 text-xl font-semibold text-orange-700">
                {fmtInt(layout.master_list.filter((row) => row.status_key === "overdue").length)}
              </p>
            </div>
            <div class="rounded-xl border border-white/80 bg-white/80 p-4 shadow-sm">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Notice Given</p>
              <p class="mt-2 text-xl font-semibold text-orange-700">
                {fmtInt(layout.master_list.filter((row) => row.status_key === "notice_given").length)}
              </p>
            </div>
            <div class="rounded-xl border border-white/80 bg-white/80 p-4 shadow-sm">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Properties Mapped</p>
              <p class="mt-2 text-xl font-semibold text-slate-950">
                {fmtInt(layout.occupancy_vacancy.properties.length)}
              </p>
            </div>
          </div>
        </article>

        <article class="rounded-xl border border-white/70 bg-white/68 p-5 shadow-[0_20px_56px_-38px_rgba(15,23,42,0.24)] backdrop-blur-xl">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Occupancy Snapshot</p>
          <div class="mt-4 flex flex-wrap gap-2">
            {#each occupancyLegend as item}
              <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${occupancyLegendClass(item.key)}`}>
                {item.label} {fmtInt(layout.occupancy_vacancy.totals[item.key] ?? 0)}
              </span>
            {/each}
          </div>
          <p class="mt-4 text-sm text-slate-600">
            Open the drawer to browse the full visual grid, tenant selection states, and the linked intelligence actions.
          </p>
        </article>
      </div>
    {/if}
  </section>

  <section class="relative overflow-hidden rounded-xl border border-slate-200/80 bg-[radial-gradient(circle_at_top_left,rgba(16,185,129,0.08),transparent_38%),radial-gradient(circle_at_top_right,rgba(251,146,60,0.1),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.97),rgba(248,250,252,0.95))] p-5 shadow-[0_26px_72px_-50px_rgba(15,23,42,0.24)]">
    <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Revenue &amp; Aging Analytics</p>
        <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Money in Flight</h2>
        <p class="mt-1 text-sm text-slate-600">
          Rolling collections, overdue debt pressure, and maintenance cost drag across the managed tenant portfolio.
        </p>
      </div>
    </div>

    {#if loading}
      <div class="mt-5 rounded-[24px] border border-dashed border-slate-300 bg-white/65 p-10 text-center text-sm text-slate-500 backdrop-blur">
        Loading revenue and aging analytics...
      </div>
    {:else if !revenueAnalytics}
      <div class="mt-5 rounded-[24px] border border-red-200 bg-red-50/90 p-6 text-sm text-red-700">
        Revenue and aging analytics are unavailable right now.
      </div>
    {:else}
      <div class="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.22fr)_minmax(340px,0.98fr)]">
        <article class="rounded-xl border border-white/70 bg-white/66 p-5 shadow-[0_24px_60px_-36px_rgba(15,23,42,0.4)] backdrop-blur-xl">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">Collection Trend</p>
              <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Revenue over the last 6 months</h3>
            </div>
            <div class="text-right">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Collected</p>
              <p class="mt-1 text-xl font-semibold tracking-tight text-emerald-700">
                {fmtMoney(revenueAnalytics.collection_trend.total_collections)}
              </p>
            </div>
          </div>

          <div class="mt-5 rounded-xl border border-emerald-100/80 bg-[linear-gradient(180deg,rgba(236,253,245,0.88),rgba(255,255,255,0.94))] p-4">
            <svg viewBox="0 0 360 180" class="h-52 w-full" role="img" aria-label="Collection trend over the last six months">
              <defs>
                <linearGradient id="tenantCollectionsArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#10b981" stop-opacity="0.32"></stop>
                  <stop offset="100%" stop-color="#10b981" stop-opacity="0.04"></stop>
                </linearGradient>
              </defs>
              <line x1="20" y1="156" x2="340" y2="156" stroke="#bbf7d0" stroke-width="1.2" stroke-dasharray="4 4"></line>
              <line x1="20" y1="110" x2="340" y2="110" stroke="#d1fae5" stroke-width="1" stroke-dasharray="4 5"></line>
              <line x1="20" y1="64" x2="340" y2="64" stroke="#ecfdf5" stroke-width="1" stroke-dasharray="4 5"></line>
              <polygon points={collectionTrendAreaPoints(revenueAnalytics.collection_trend.months)} fill="url(#tenantCollectionsArea)"></polygon>
              <polyline
                points={collectionTrendPoints(revenueAnalytics.collection_trend.months)}
                fill="none"
                stroke="#059669"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
              ></polyline>
            </svg>

            <div class="mt-2 grid grid-cols-3 gap-3 sm:grid-cols-6">
              {#each revenueAnalytics.collection_trend.months as month}
                <div class="rounded-[20px] border border-white/75 bg-white/82 px-3 py-2 text-center shadow-sm">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">{month.label}</p>
                  <p class="mt-1 text-sm font-semibold text-slate-950">{fmtMoney(month.collections_total)}</p>
                </div>
              {/each}
            </div>
          </div>

          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <div class="rounded-[24px] border border-white/70 bg-white/78 p-4 shadow-sm">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Peak Month</p>
              <p class="mt-2 text-xl font-semibold text-slate-950">{fmtMoney(revenueAnalytics.collection_trend.peak_collections)}</p>
            </div>
            <div class="rounded-[24px] border border-white/70 bg-white/78 p-4 shadow-sm">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Average Monthly Collection</p>
              <p class="mt-2 text-xl font-semibold text-slate-950">{fmtMoney(revenueAnalytics.collection_trend.average_collections)}</p>
            </div>
          </div>
        </article>

        <div class="space-y-5">
          <article class="rounded-xl border border-white/70 bg-white/66 p-5 shadow-[0_24px_60px_-36px_rgba(15,23,42,0.4)] backdrop-blur-xl">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-orange-700">Aging Buckets</p>
                <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Debt by age band</h3>
              </div>
              <div class="text-right">
                <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Total Overdue</p>
                <p class="mt-1 text-xl font-semibold tracking-tight text-orange-700">
                  {fmtMoney(revenueAnalytics.aging_buckets.total_overdue)}
                </p>
              </div>
            </div>

            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              {#each revenueAnalytics.aging_buckets.buckets as bucket}
                <div class={`rounded-[24px] border p-4 ${agingBucketClass(bucket.key)}`}>
                  <p class="text-[11px] font-semibold uppercase tracking-[0.18em]">{bucket.label}</p>
                  <p class="mt-3 text-xl font-semibold">{fmtMoney(bucket.total)}</p>
                  <p class="mt-2 text-xs opacity-80">{fmtInt(bucket.count)} overdue invoice{bucket.count === 1 ? "" : "s"}</p>
                </div>
              {/each}
            </div>
          </article>

          <article class="rounded-xl border border-white/70 bg-white/66 p-5 shadow-[0_24px_60px_-36px_rgba(15,23,42,0.4)] backdrop-blur-xl">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Expense vs. Income</p>
                <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Maintenance cost drag vs rent collected</h3>
              </div>
              <p class="text-xs text-slate-500">
                {fmtDate(revenueAnalytics.expense_vs_income.period_start)} - {fmtDate(revenueAnalytics.expense_vs_income.period_end)}
              </p>
            </div>

            <div class="mt-4 grid gap-3 sm:grid-cols-3">
              <div class="rounded-[24px] border border-emerald-200/75 bg-emerald-50/80 p-4">
                <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-700">Rent Collected</p>
                <p class="mt-2 text-xl font-semibold text-emerald-700">
                  {fmtMoney(revenueAnalytics.expense_vs_income.rent_collected_total)}
                </p>
              </div>
              <div class="rounded-[24px] border border-orange-200/75 bg-orange-50/80 p-4">
                <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-orange-700">Maintenance Cost</p>
                <p class="mt-2 text-xl font-semibold text-orange-700">
                  {fmtMoney(revenueAnalytics.expense_vs_income.maintenance_cost_total)}
                </p>
              </div>
              <div class="rounded-[24px] border border-slate-200/75 bg-white/85 p-4">
                <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Net Operating</p>
                <p class={`mt-2 text-xl font-semibold ${toNumber(revenueAnalytics.expense_vs_income.net_operating_total) >= 0 ? "text-slate-950" : "text-rose-700"}`}>
                  {fmtMoney(revenueAnalytics.expense_vs_income.net_operating_total)}
                </p>
                <p class="mt-2 text-xs text-slate-500">
                  Expense ratio {fmtPct(revenueAnalytics.expense_vs_income.expense_ratio_pct)}
                </p>
              </div>
            </div>

            <div class="mt-4 space-y-3">
              {#if revenueAnalytics.expense_vs_income.property_breakdown.length === 0}
                <div class="rounded-[24px] border border-dashed border-slate-300 bg-white/75 p-6 text-sm text-slate-500">
                  No property-level income or maintenance cost activity was recorded in this period.
                </div>
              {:else}
                {#each revenueAnalytics.expense_vs_income.property_breakdown as property}
                  <div class="rounded-[24px] border border-white/75 bg-white/82 p-4 shadow-sm">
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <p class="text-sm font-semibold text-slate-950">{property.property_name}</p>
                      <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${toNumber(property.net) >= 0 ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-rose-200 bg-rose-50 text-rose-700"}`}>
                        Net {fmtMoney(property.net)}
                      </span>
                    </div>

                    <div class="mt-3 space-y-3">
                      <div>
                        <div class="flex items-center justify-between text-xs font-medium text-slate-500">
                          <span>Income</span>
                          <span>{fmtMoney(property.income_collected)}</span>
                        </div>
                        <div class="mt-1 h-2 overflow-hidden rounded-full bg-slate-200/70">
                          <div
                            class="h-full rounded-full bg-linear-to-r from-emerald-500 to-teal-400"
                            style={`width: ${comparisonBarWidth(property.income_collected, Math.max(toNumber(property.income_collected), toNumber(property.maintenance_cost), 1))}%`}
                          ></div>
                        </div>
                      </div>

                      <div>
                        <div class="flex items-center justify-between text-xs font-medium text-slate-500">
                          <span>Maintenance Cost</span>
                          <span>{fmtMoney(property.maintenance_cost)}</span>
                        </div>
                        <div class="mt-1 h-2 overflow-hidden rounded-full bg-slate-200/70">
                          <div
                            class="h-full rounded-full bg-linear-to-r from-orange-500 to-amber-400"
                            style={`width: ${comparisonBarWidth(property.maintenance_cost, Math.max(toNumber(property.income_collected), toNumber(property.maintenance_cost), 1))}%`}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                {/each}
              {/if}
            </div>
          </article>
        </div>
      </div>
    {/if}
  </section>
</div>

{#if showManagementLayoutDrawer}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/38 backdrop-blur-[2px]"
      onclick={closeManagementLayoutDrawer}
      aria-label="Close management layout panel"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-384">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.99),rgba(248,250,252,0.98))] shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.38)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">Management Layout Grid</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Tenant Master List + Occupancy View</h2>
            <p class="mt-2 text-sm text-slate-600">
              Search, select, blast, and review occupancy without crowding the main dashboard surface.
            </p>
          </div>
          <button
            type="button"
            onclick={closeManagementLayoutDrawer}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close management layout panel"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-5">
          {#if loading}
            <div class="rounded-[24px] border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
              Loading management layout grid...
            </div>
          {:else if !layout}
            <div class="rounded-[24px] border border-red-200 bg-red-50/90 p-6 text-sm text-red-700">
              Tenant management layout is unavailable right now.
            </div>
          {:else}
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">Management Layout Grid</p>
                <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Tenant Master List + Occupancy View</h3>
                <p class="mt-1 text-sm text-slate-600">
                  A dense tenant control table paired with a visual map of occupied, vacant, notice, and maintenance units.
                </p>
              </div>
              <p class="text-xs text-slate-500">Green = occupied, grey = vacant, orange = notice given, blue = under maintenance.</p>
            </div>

            <div class="mt-5 grid gap-5 2xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.95fr)]">
              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_20px_60px_-36px_rgba(15,23,42,0.18)]">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <h3 class="text-sm font-semibold uppercase tracking-wider text-slate-400">Main View</h3>
                    <p class="mt-1 text-sm font-bold tracking-wide text-neutral-800 uppercase">Tenant Master List</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                      Rows {fmtInt(filteredMasterList().length)}
                    </span>
                    <span class="inline-flex items-center rounded-full border border-orange-200 bg-orange-50 px-3 py-1 text-xs font-medium text-orange-700">
                      Overdue {fmtInt(layout.master_list.filter((row) => row.status_key === "overdue").length)}
                    </span>
                    <span class="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                      Notice {fmtInt(layout.master_list.filter((row) => row.status_key === "notice_given").length)}
                    </span>
                    <button
                      type="button"
                      onclick={() => openBulkActionDrawer("service_charge")}
                      disabled={selectedTenantIds.length === 0}
                      class="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700 transition hover:border-sky-300 disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      Service Charge Blast
                    </button>
                    <button
                      type="button"
                      onclick={() => openBulkActionDrawer("holiday_announcement")}
                      disabled={selectedTenantIds.length === 0}
                      class="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700 transition hover:border-violet-300 disabled:cursor-not-allowed disabled:opacity-55"
                    >
                      Holiday Announcement
                    </button>
                  </div>
                </div>

                {#if selectedTenantIds.length > 0}
                  <div class="mt-4 flex flex-wrap items-center gap-2 rounded-[22px] border border-slate-200/80 bg-slate-50/90 px-4 py-3 shadow-sm">
                    <span class="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                      Selected {fmtInt(selectedTenantIds.length)}
                    </span>
                    <span class="text-xs text-slate-500">Choose a blast action to invoice or message the selected tenants.</span>
                    <button
                      type="button"
                      onclick={clearSelectedTenants}
                      class="ml-auto inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-700 transition hover:border-slate-300"
                    >
                      Clear selection
                    </button>
                  </div>
                {/if}

                <div class="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1.4fr)_repeat(4,minmax(0,0.85fr))]">
                  <label class="flex-1">
                    <span class="sr-only">Search tenants</span>
                    <input
                      bind:value={tenantSearch}
                      type="search"
                      placeholder="Search tenant, unit, property..."
                      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm placeholder:text-slate-400 focus:border-slate-300 focus:outline-none"
                    />
                  </label>
                  <label class="sm:w-52">
                    <span class="sr-only">Filter tenant status</span>
                    <select
                      bind:value={tenantStatusFilter}
                      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none"
                    >
                      {#each masterListStatusOptions as option}
                        <option value={option.value}>{option.label}</option>
                      {/each}
                    </select>
                  </label>

                  <label>
                    <span class="sr-only">Filter property location</span>
                    <select
                      bind:value={propertyLocationFilter}
                      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none"
                    >
                      <option value="all">All locations</option>
                      {#each layout.filters.property_locations as location}
                        <option value={location}>{location}</option>
                      {/each}
                    </select>
                  </label>

                  <label>
                    <span class="sr-only">Filter tenancy type</span>
                    <select
                      bind:value={tenancyTypeFilter}
                      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none"
                    >
                      <option value="all">All tenancy types</option>
                      {#each layout.filters.tenancy_types as option}
                        <option value={option.value}>{option.label}</option>
                      {/each}
                    </select>
                  </label>

                  <label>
                    <span class="sr-only">Filter debt status</span>
                    <select
                      bind:value={debtStatusFilter}
                      class="w-full rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none"
                    >
                      <option value="all">All debt statuses</option>
                      {#each layout.filters.debt_statuses as option}
                        <option value={option.value}>{option.label}</option>
                      {/each}
                    </select>
                  </label>
                </div>

                <div class="mt-4 overflow-hidden rounded-[24px] border border-slate-200 bg-white">
                  <div class="max-h-[68vh] overflow-auto">
                    <table class="min-w-full border-separate border-spacing-0 text-sm">
                      <thead class="sticky top-0 z-10 bg-white/95 backdrop-blur">
                        <tr class="text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                          <th class="w-12 px-4 py-3">
                            <input
                              type="checkbox"
                              checked={areAllVisibleTenantsSelected()}
                              onchange={(event) => setVisibleTenantSelection((event.currentTarget as HTMLInputElement).checked)}
                              class="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                              aria-label="Select all visible tenants"
                            />
                          </th>
                          <th class="px-4 py-3">Tenant Name</th>
                          <th class="px-4 py-3">Unit</th>
                          <th class="px-4 py-3">Property</th>
                          <th class="px-4 py-3">Lease Expiry</th>
                          <th class="px-4 py-3 text-right">Balance</th>
                          <th class="px-4 py-3">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {#if filteredMasterList().length === 0}
                          <tr>
                            <td colspan="7" class="px-4 py-8 text-center text-sm text-slate-500">
                              No tenant rows match the current search and status filter.
                            </td>
                          </tr>
                        {:else}
                          {#each filteredMasterList() as row, index}
                            <tr class={`group text-slate-700 transition-all duration-200 ${index % 2 === 0 ? "bg-white" : "bg-slate-50/72"} hover:bg-slate-50 hover:[backdrop-filter:blur(10px)] hover:[box-shadow:inset_0_0_0_1px_rgba(226,232,240,0.9)]`}>
                              <td class="border-t border-slate-100 px-4 py-3 align-top transition-colors group-hover:border-slate-200">
                                <input
                                  type="checkbox"
                                  checked={isTenantSelected(row.id)}
                                  onchange={() => toggleTenantSelection(row.id)}
                                  class="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                                  aria-label={`Select ${row.tenant_name}`}
                                />
                              </td>
                              <td class="border-t border-slate-100 px-4 py-3 align-top transition-colors group-hover:border-slate-200">
                                <button
                                  type="button"
                                  onclick={() => openTenantIntelligence(row.id)}
                                  class="group flex flex-col items-start text-left"
                                >
                                  <span class="font-semibold text-slate-950 transition group-hover:text-sky-700">{row.tenant_name}</span>
                                  <span class="mt-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400 transition group-hover:text-sky-600">
                                    Open intelligence
                                  </span>
                                </button>
                              </td>
                              <td class="border-t border-slate-100 px-4 py-3 align-top font-medium text-slate-800 transition-colors group-hover:border-slate-200">
                                <div>{row.unit_label}</div>
                                <div class={`mt-2 inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tenancyTypeBadgeClass(row.tenancy_type_key)}`}>
                                  {row.tenancy_type_label}
                                </div>
                              </td>
                              <td class="border-t border-slate-100 px-4 py-3 align-top transition-colors group-hover:border-slate-200">
                                <div class="font-medium text-slate-900">{row.property_name}</div>
                                <div class="mt-1 text-xs text-slate-500">{row.property_location}</div>
                              </td>
                              <td class="border-t border-slate-100 px-4 py-3 align-top whitespace-nowrap transition-colors group-hover:border-slate-200">{fmtDate(row.lease_expiry)}</td>
                              <td class={`border-t border-slate-100 px-4 py-3 align-top text-right font-semibold whitespace-nowrap transition-colors group-hover:border-slate-200 ${toNumber(row.balance) > 0 ? "text-orange-700" : "text-slate-700"}`}>
                                {fmtMoney(row.balance)}
                              </td>
                              <td class="border-t border-slate-100 px-4 py-3 align-top transition-colors group-hover:border-slate-200">
                                <div class="flex flex-col items-start gap-2">
                                  <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${masterListBadgeClass(row.status_key)}`}>
                                    {row.status_label}
                                  </span>
                                  <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${debtStatusBadgeClass(row.debt_status_key)}`}>
                                    {row.debt_status_label}
                                  </span>
                                </div>
                              </td>
                            </tr>
                          {/each}
                        {/if}
                      </tbody>
                    </table>
                  </div>
                </div>
              </section>

              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_18px_50px_-34px_rgba(15,23,42,0.18)]">
                <div class="flex flex-col gap-3">
                  <div>
                    <h3 class="text-sm font-semibold uppercase tracking-wider text-slate-400">Secondary View</h3>
                    <p class="mt-1 text-sm font-bold tracking-wide text-neutral-800 uppercase">Occupancy &amp; Vacancy</p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    {#each occupancyLegend as item}
                      <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${occupancyLegendClass(item.key)}`}>
                        {item.label} {fmtInt(layout.occupancy_vacancy.totals[item.key] ?? 0)}
                      </span>
                    {/each}
                  </div>
                </div>

                <div class="mt-4 space-y-4">
                  {#each layout.occupancy_vacancy.properties as property}
                    <article class="rounded-lg border border-slate-200 bg-slate-50/50 p-4 shadow-sm">
                      <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <p class="text-xs font-semibold text-slate-900">{property.property_name}</p>
                          <p class="mt-1 text-xs text-slate-500">{fmtInt(property.units.length)} units visualized</p>
                        </div>
                        <div class="flex flex-wrap gap-2">
                          {#if property.totals.occupied > 0}
                            <span class="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                              Occupied {fmtInt(property.totals.occupied)}
                            </span>
                          {/if}
                          {#if property.totals.notice_given > 0}
                            <span class="rounded-full border border-orange-200 bg-orange-50 px-2.5 py-1 text-[11px] font-semibold text-orange-700">
                              Notice {fmtInt(property.totals.notice_given)}
                            </span>
                          {/if}
                          {#if property.totals.under_maintenance > 0}
                            <span class="rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700">
                              Maintenance {fmtInt(property.totals.under_maintenance)}
                            </span>
                          {/if}
                          {#if property.totals.vacant_ready > 0}
                            <span class="rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-700">
                              Vacant {fmtInt(property.totals.vacant_ready)}
                            </span>
                          {/if}
                        </div>
                      </div>

                      <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
                        {#each property.units as unit}
                          <!-- svelte-ignore a11y_no_static_element_interactions -->
                          <div
                            role={unit.tenant_profile_id ? "button" : undefined}
                            onclick={unit.tenant_profile_id ? () => openTenantIntelligence(unit.tenant_profile_id!) : undefined}
                            onkeydown={unit.tenant_profile_id ? (e) => { if (e.key === "Enter" || e.key === " ") openTenantIntelligence(unit.tenant_profile_id!); } : undefined}
                            class="min-h-[112px] rounded-lg border px-3 pb-3 pt-5 text-left shadow-[inset_0_1px_0_rgba(255,255,255,0.45)] {occupancyTileClass(unit.status_key)} {unit.tenant_profile_id ? 'cursor-pointer transition hover:-translate-y-0.5 hover:shadow-[0_18px_36px_-24px,rgba(14,116,144,0.35)]' : ''}"
                          >
                            <div class="mt-1 flex items-start justify-between gap-2">
                              <div class="pt-1">
                                <p class="text-sm font-semibold">{unit.unit_number}</p>
                                <p class="mt-1 text-[11px] uppercase tracking-[0.18em] opacity-70">
                                  {unit.floor !== null ? `Floor ${unit.floor}` : "Unit"}
                                </p>
                              </div>
                              <span class="rounded-full border border-white/50 bg-white/55 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
                                {occupancyStatusLabel(unit)}
                              </span>
                            </div>
                            <div class="mt-3 flex min-h-[3.8rem] flex-col gap-2">
                              <p class="truncate text-sm font-semibold leading-tight" title={occupancyCardTitle(unit)}>
                                {occupancyCardTitle(unit)}
                              </p>
                              {#if occupancyCardSubtitle(unit)}
                                <p class="truncate text-[11px] uppercase tracking-[0.18em] opacity-70" title={occupancyCardSubtitle(unit)}>
                                  {occupancyCardSubtitle(unit)}
                                </p>
                              {/if}
                            </div>
                            <div class="mt-3 flex items-center justify-between gap-2">
                              <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${occupancyCardMetaClass(unit)}`}>
                                {occupancyCardMeta(unit)}
                              </span>
                              {#if unit.tenant_profile_id}
                                <svg class="h-4 w-4 text-sky-800/70" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                                  <path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6" />
                                </svg>
                              {/if}
                            </div>
                          </div>
                        {/each}
                      </div>
                    </article>
                  {/each}
                </div>
              </section>
            </div>
          {/if}
        </div>
      </div>
    </aside>
  </div>
{/if}

{#if showBulkActionDrawer}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/38 backdrop-blur-[2px]"
      onclick={closeBulkActionDrawer}
      aria-label="Close bulk actions panel"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-2xl">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.97))] shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.38)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">5. UI / UX Features For Admin</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">
              {bulkActionMode === "service_charge" ? "Service Charge Blast" : "Holiday Announcement Blast"}
            </h2>
            <p class="mt-2 text-sm text-slate-600">
              Apply the action to {fmtInt(selectedTenantIds.length)} selected tenant{selectedTenantIds.length === 1 ? "" : "s"}.
            </p>
          </div>
          <button
            type="button"
            onclick={closeBulkActionDrawer}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close bulk actions panel"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-5">
          <div class="space-y-4">
            <section class="rounded-xl border border-slate-200/80 bg-white p-4 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  onclick={() => (bulkActionMode = "service_charge")}
                  class={`inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold transition ${bulkActionMode === "service_charge" ? "border-sky-200 bg-sky-50 text-sky-700" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"}`}
                >
                  Blast Service Charge Invoices
                </button>
                <button
                  type="button"
                  onclick={() => (bulkActionMode = "holiday_announcement")}
                  class={`inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold transition ${bulkActionMode === "holiday_announcement" ? "border-violet-200 bg-violet-50 text-violet-700" : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"}`}
                >
                  Blast Holiday Announcement
                </button>
              </div>

              <div class="mt-4 rounded-xl border border-slate-200/80 bg-slate-50/80 p-4 shadow-sm">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                    Selected {fmtInt(selectedTenantIds.length)}
                  </span>
                  <span class="text-xs text-slate-500">The bulk action will only run for the selected tenants below.</span>
                </div>
                <div class="mt-3 flex flex-wrap gap-2">
                  {#each selectedTenantRows() as row}
                    <span class="inline-flex items-center rounded-full border border-white/80 bg-white px-3 py-1 text-xs font-medium text-slate-700 shadow-sm">
                      {row.tenant_name} · {row.property_name}
                    </span>
                  {/each}
                </div>
              </div>
            </section>

            {#if bulkActionMode === "service_charge"}
              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Bulk Service Charge</p>
                <div class="mt-4 grid gap-4 sm:grid-cols-2">
                  <label class="sm:col-span-2">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Line Item Description</span>
                    <input
                      bind:value={bulkInvoiceForm.description}
                      type="text"
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      placeholder="Monthly service charge"
                    />
                  </label>

                  <label>
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Amount</span>
                    <input
                      bind:value={bulkInvoiceForm.amount}
                      type="number"
                      min="0"
                      step="0.01"
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      placeholder="125000.00"
                    />
                  </label>

                  <label>
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Due In Days</span>
                    <input
                      bind:value={bulkInvoiceForm.due_in_days}
                      type="number"
                      min="0"
                      step="1"
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                    />
                  </label>

                  <label class="sm:col-span-2">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notes</span>
                    <textarea
                      bind:value={bulkInvoiceForm.notes}
                      rows="4"
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      placeholder="Optional note to include on the invoice email."
                    ></textarea>
                  </label>
                </div>

                <label class="mt-4 flex items-center gap-3 rounded-xl border border-slate-200/80 bg-slate-50/80 px-4 py-3 text-sm text-slate-700 shadow-sm">
                  <input bind:checked={bulkInvoiceForm.send_notifications} type="checkbox" class="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500" />
                  <span>Notify tenants by email immediately after generating the invoices where contact email exists.</span>
                </label>
              </section>
            {:else}
              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Bulk Holiday Announcement</p>
                <div class="mt-4 grid gap-4">
                  <label>
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Subject</span>
                    <input
                      bind:value={bulkAnnouncementForm.subject}
                      type="text"
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      placeholder="Holiday announcement"
                    />
                  </label>

                  <label>
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Message</span>
                    <textarea
                      bind:value={bulkAnnouncementForm.message}
                      rows="6"
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      placeholder="Share holiday closures, reduced service windows, or portfolio-wide notices."
                    ></textarea>
                  </label>

                  <label>
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Delivery Mode</span>
                    <select
                      bind:value={bulkAnnouncementForm.delivery_mode}
                      class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                    >
                      <option value="all_available">All available channels</option>
                      <option value="email_only">Email only</option>
                      <option value="whatsapp_only">WhatsApp only</option>
                    </select>
                  </label>
                </div>
              </section>
            {/if}
          </div>
        </div>

        <div class="flex items-center justify-between gap-3 border-t border-slate-200/80 px-5 py-4">
          <button
            type="button"
            onclick={closeBulkActionDrawer}
            class="inline-flex items-center rounded-2xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
          >
            Cancel
          </button>
          <button
            type="button"
            onclick={submitBulkAction}
            disabled={bulkActionSubmitting || selectedTenantIds.length === 0}
            class="inline-flex items-center rounded-2xl border border-slate-900 bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-55"
          >
            {#if bulkActionSubmitting}
              Processing...
            {:else if bulkActionMode === "service_charge"}
              Blast service charge invoices
            {:else}
              Blast holiday announcement
            {/if}
          </button>
        </div>
      </div>
    </aside>
  </div>
{/if}

{#if showIntelligenceDrawer}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/38 backdrop-blur-[2px]"
      onclick={closeTenantIntelligence}
      aria-label="Close tenant intelligence panel"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-176">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.97))] shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.38)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">Tenant Intelligence</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">
              {tenantIntelligence?.tenant.name ?? "Tenant Detail"}
            </h2>
            <p class="mt-2 text-sm text-slate-600">
              Payment behavior, lease timeline, communication history, and fast recovery actions.
            </p>
          </div>
          <button
            type="button"
            onclick={closeTenantIntelligence}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close tenant intelligence panel"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-5">
          {#if intelligenceLoading}
            <div class="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-sm text-slate-500">
              Loading tenant intelligence...
            </div>
          {:else if intelligenceError}
            <div class="rounded-xl border border-rose-200 bg-rose-50/90 p-6 text-sm text-rose-700">
              {intelligenceError}
            </div>
          {:else if tenantIntelligence}
            <div class="space-y-4">
              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                <div class="flex flex-col gap-4">
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div class="flex flex-wrap items-center gap-2">
                        <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${masterListBadgeClass(tenantIntelligence.tenant.status)}`}>
                          {tenantIntelligence.tenant.status_label}
                        </span>
                        <span class="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                          {tenantIntelligence.tenant.tenant_type_display}
                        </span>
                      </div>
                      <p class="mt-3 text-base font-semibold text-slate-950">
                        {tenantIntelligence.tenant.property_name} / {tenantIntelligence.tenant.unit_label}
                      </p>
                      <p class="mt-1 text-sm text-slate-600">
                        Current balance {fmtMoney(tenantIntelligence.tenant.current_balance)}
                        {#if toNumber(tenantIntelligence.tenant.overdue_balance) > 0}
                          <span class="font-semibold text-orange-700"> • Overdue {fmtMoney(tenantIntelligence.tenant.overdue_balance)}</span>
                        {/if}
                      </p>
                    </div>

                    <div class="flex flex-wrap gap-2">
                      {#if tenantIntelligence.contact.email}
                        <span class="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
                          {tenantIntelligence.contact.email}
                        </span>
                      {/if}
                      {#if tenantIntelligence.contact.phone}
                        <span class="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                          {tenantIntelligence.contact.phone}
                        </span>
                      {/if}
                    </div>
                  </div>
                </div>
              </section>

              <section class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
                <article class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-700">Payment Reliability Score</p>
                      <div class="mt-3 flex items-center gap-1.5 text-amber-500">
                        {#each reliabilityStars as star}
                          <svg
                            class={`h-6 w-6 ${star <= tenantIntelligence.payment_reliability.score ? "fill-current" : "fill-white/0 stroke-current opacity-35"}`}
                            viewBox="0 0 24 24"
                            stroke-width="1.6"
                            aria-hidden="true"
                          >
                            <path
                              stroke-linecap="round"
                              stroke-linejoin="round"
                              d="m12 3.75 2.67 5.41 5.97.87-4.32 4.21 1.02 5.95L12 17.39l-5.34 2.81 1.02-5.95-4.32-4.21 5.97-.87L12 3.75Z"
                            />
                          </svg>
                        {/each}
                      </div>
                      <p class="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
                        {tenantIntelligence.payment_reliability.score}/5
                      </p>
                      <p class="mt-2 text-sm text-slate-600">{tenantIntelligence.payment_reliability.summary}</p>
                    </div>
                    <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${reliabilityBadgeClass(tenantIntelligence.payment_reliability.score)}`}>
                      {tenantIntelligence.payment_reliability.label}
                    </span>
                  </div>

                  <div class="mt-4 grid gap-3 sm:grid-cols-2">
                    <div class="rounded-[22px] border border-emerald-200/70 bg-emerald-50/80 p-3">
                      <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-emerald-700">On Time</p>
                      <p class="mt-2 text-xl font-semibold text-slate-950">
                        {fmtInt(tenantIntelligence.payment_reliability.paid_on_time)}
                      </p>
                    </div>
                    <div class="rounded-[22px] border border-orange-200/70 bg-orange-50/80 p-3">
                      <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-orange-700">Late / Overdue</p>
                      <p class="mt-2 text-xl font-semibold text-slate-950">
                        {fmtInt(tenantIntelligence.payment_reliability.paid_late + tenantIntelligence.payment_reliability.overdue_invoices)}
                      </p>
                    </div>
                    <div class="rounded-[22px] border border-slate-200/70 bg-white/80 p-3">
                      <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Invoices Reviewed</p>
                      <p class="mt-2 text-xl font-semibold text-slate-950">
                        {fmtInt(tenantIntelligence.payment_reliability.total_invoices)}
                      </p>
                    </div>
                    <div class="rounded-[22px] border border-rose-200/70 bg-rose-50/80 p-3">
                      <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-rose-700">Overdue Balance</p>
                      <p class="mt-2 text-xl font-semibold text-rose-700">
                        {fmtMoney(tenantIntelligence.payment_reliability.overdue_balance)}
                      </p>
                    </div>
                  </div>
                </article>

                <article class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Lease Timeline</p>
                  <div class="mt-4">
                    <div class="flex items-center justify-between text-xs font-medium text-slate-500">
                      <span>{fmtDate(tenantIntelligence.lease_timeline.start_date)}</span>
                      <span>{tenantIntelligence.lease_timeline.status_label}</span>
                      <span>{fmtDate(tenantIntelligence.lease_timeline.end_date)}</span>
                    </div>
                    <div class="mt-3 h-3 overflow-hidden rounded-full bg-slate-200/70">
                      <div
                        class="h-full rounded-full bg-linear-to-r from-sky-500 via-cyan-400 to-violet-400 transition-all"
                        style={`width: ${clampPct(tenantIntelligence.lease_timeline.elapsed_pct)}%`}
                      ></div>
                    </div>
                    <div class="mt-4 grid gap-3 sm:grid-cols-3">
                      <div class="rounded-[22px] border border-slate-200/70 bg-white/80 p-3">
                        <p class="text-xs font-regular uppercase tracking-tight text-slate-500">Elapsed</p>
                        <p class="mt-2 text-md font-semibold text-slate-900">{fmtInt(tenantIntelligence.lease_timeline.elapsed_days)} days</p>
                      </div>
                      <div class="rounded-[22px] border border-slate-200/70 bg-white/80 p-3">
                        <p class="text-xs font-regular uppercase tracking-tight text-slate-500">Remaining</p>
                        <p class="mt-2 text-md font-semibold text-slate-900">{fmtInt(tenantIntelligence.lease_timeline.remaining_days)} days</p>
                      </div>
                      <div class="rounded-[22px] border border-slate-200/70 bg-white/80 p-3">
                        <p class="text-xs font-regular uppercase tracking-tight text-slate-500">Total Term</p>
                        <p class="mt-2 text-md font-semibold text-slate-900">{fmtInt(tenantIntelligence.lease_timeline.total_days)} days</p>
                      </div>
                    </div>
                  </div>
                </article>
              </section>

              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Communication Log</p>
                    <h3 class="mt-2 text-lg font-semibold tracking-tight text-slate-950">Recent interactions</h3>
                  </div>
                  <p class="text-xs text-slate-500">Latest notes, outreach, and recovery activity for this tenant.</p>
                </div>

                <div class="mt-4 space-y-3">
                  {#if tenantIntelligence.communication_log.length === 0}
                    <div class="rounded-[24px] border border-dashed border-slate-300 bg-white/75 p-6 text-sm text-slate-500">
                      No communication history has been recorded yet.
                    </div>
                  {:else}
                    {#each tenantIntelligence.communication_log as entry}
                      <article class="rounded-[24px] border border-white/75 bg-white/78 p-4 shadow-sm backdrop-blur">
                        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div class="flex flex-wrap items-center gap-2">
                              <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${communicationChannelClass(entry.channel)}`}>
                                {entry.channel_display}
                              </span>
                              <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${communicationStatusClass(entry.status)}`}>
                                {entry.status_display}
                              </span>
                            </div>
                            <p class="mt-3 text-sm font-semibold text-slate-950">{entry.subject || entry.interaction_type_display}</p>
                            <p class="mt-2 text-sm leading-6 text-slate-600">{entry.message}</p>
                          </div>
                          <div class="text-right text-xs text-slate-500">
                            <p>{fmtDateTime(entry.happened_at)}</p>
                            {#if entry.author_name}
                              <p class="mt-1 font-medium text-slate-600">{entry.author_name}</p>
                            {/if}
                          </div>
                        </div>
                      </article>
                    {/each}
                  {/if}
                </div>
              </section>

              <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-fuchsia-700">Quick Actions</p>
                    <h3 class="mt-2 text-lg font-semibold tracking-tight text-slate-950">Recovery and billing shortcuts</h3>
                  </div>
                  <p class="text-xs text-slate-500">Fast actions for invoicing, collection follow-up, and escalation.</p>
                </div>

                <div class="mt-4 grid gap-3">
                  <button
                    type="button"
                    onclick={generateInvoice}
                    disabled={!tenantIntelligence.quick_actions.can_generate_invoice || intelligenceAction !== null}
                    class="flex items-center justify-between rounded-[24px] border border-sky-200/80 bg-linear-to-r from-sky-50 to-white px-4 py-4 text-left shadow-sm transition hover:border-sky-300 disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    <div>
                      <p class="text-sm font-semibold text-slate-950">Generate Invoice</p>
                      <p class="mt-1 text-sm text-slate-600">Create a draft receivables invoice from the latest tenant billing pattern.</p>
                    </div>
                    <span class="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                      {intelligenceAction === "generate_invoice" ? "Running..." : "Run"}
                    </span>
                  </button>

                  <button
                    type="button"
                    onclick={sendPaymentReminder}
                    disabled={!tenantIntelligence.quick_actions.can_send_payment_reminder || intelligenceAction !== null}
                    class="flex items-center justify-between rounded-[24px] border border-emerald-200/80 bg-linear-to-r from-emerald-50 to-white px-4 py-4 text-left shadow-sm transition hover:border-emerald-300 disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    <div>
                      <p class="text-sm font-semibold text-slate-950">Send Payment Reminder</p>
                      <p class="mt-1 text-sm text-slate-600">Dispatch reminder outreach through email and WhatsApp where tenant contacts exist.</p>
                    </div>
                    <span class="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                      {intelligenceAction === "send_payment_reminder" ? "Running..." : "Run"}
                    </span>
                  </button>

                  <button
                    type="button"
                    onclick={initiateEvictionNotice}
                    disabled={!tenantIntelligence.quick_actions.can_initiate_eviction_notice || intelligenceAction !== null}
                    class="flex items-center justify-between rounded-[24px] border border-rose-200/80 bg-linear-to-r from-rose-50 to-white px-4 py-4 text-left shadow-sm transition hover:border-rose-300 disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    <div>
                      <p class="text-sm font-semibold text-slate-950">Initiate Eviction Notice</p>
                      <p class="mt-1 text-sm text-slate-600">Record escalation, set a move-out target, and issue formal notice where email is available.</p>
                    </div>
                    <span class="text-xs font-semibold uppercase tracking-[0.18em] text-rose-700">
                      {intelligenceAction === "initiate_eviction_notice" ? "Running..." : "Run"}
                    </span>
                  </button>
                </div>
              </section>
            </div>
          {/if}
        </div>
      </div>
    </aside>
  </div>
{/if}

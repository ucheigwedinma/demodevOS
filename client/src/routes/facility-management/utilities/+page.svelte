<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse } from "$lib/types";

  type UtilitiesTab = "meters" | "readings" | "billing" | "analytics";
  type UtilityType = "electricity" | "water" | "gas" | "diesel" | "solar";
  type UtilityBillStatus = "draft" | "issued" | "overdue" | "paid" | "disputed" | "cancelled";

  interface FacilityLookupItem {
    id: number;
    facility_code: string;
    property_name: string;
  }

  interface VendorLookupItem {
    id: number;
    label: string;
    category: string;
  }

  interface MeterLookupItem {
    id: number;
    facility: number | null;
    facility_code: string;
    property_name: string;
    meter_number: string;
    utility_type: UtilityType;
    utility_type_display: string;
    unit_of_measure: string;
    is_active: boolean;
  }

  interface UtilityMeterListItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    vendor: number | null;
    vendor_name: string;
    meter_number: string;
    utility_type: UtilityType;
    utility_type_display: string;
    unit_of_measure: string;
    location_label: string;
    provider_name: string;
    installed_at: string | null;
    is_smart_meter: boolean;
    is_active: boolean;
    last_reading_at: string | null;
    latest_reading_value: string | null;
    total_readings: number;
    open_anomalies: number;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface UtilityReadingListItem {
    id: number;
    meter: number;
    meter_number: string;
    utility_type: UtilityType;
    utility_type_display: string;
    unit_of_measure: string;
    property_name: string;
    facility: number | null;
    facility_code: string;
    reading_at: string;
    reading_date: string;
    reading_value: string;
    consumption_delta: string;
    entered_by: number | null;
    entered_by_name: string;
    is_estimated: boolean;
    is_anomaly: boolean;
    anomaly_reason: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface UtilityBillListItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    meter: number | null;
    meter_number: string;
    vendor: number | null;
    vendor_name: string;
    finance_bill: number | null;
    finance_bill_number: string;
    provider_name: string;
    utility_type: UtilityType;
    utility_type_display: string;
    bill_number: string;
    billing_period_start: string;
    billing_period_end: string;
    issue_date: string;
    due_date: string;
    usage_quantity: string;
    unit_rate: string;
    subtotal: string;
    tax_amount: string;
    total_amount: string;
    amount_paid: string;
    balance_due: string;
    status: UtilityBillStatus;
    status_display: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface MonthlyTrendItem {
    month: string | null;
    electricity_kwh: string;
    water_m3: string;
    gas_m3: string;
    diesel_liters: string;
    carbon_kg_co2e: string;
  }

  interface CostBreakdownItem {
    utility_type: UtilityType;
    total_amount: string;
    usage_quantity: string;
    count: number;
  }

  interface SustainabilityWatchItem {
    property_id: number;
    property_name: string;
    facility_code: string;
    carbon_kg_co2e: string;
    energy_total: string;
    water_m3: string;
  }

  interface UtilitiesOverview {
    generated_at: string;
    kpis: {
      active_meters: number;
      smart_meters: number;
      readings_logged_30d: number;
      anomalous_readings: number;
      utility_cost_30d: string;
      overdue_bills: number;
      electricity_kwh_30d: string;
      water_m3_30d: string;
      gas_m3_30d: string;
      diesel_liters_30d: string;
      carbon_kg_co2e_30d: string;
      energy_intensity_per_1000_sqft: string;
      water_intensity_per_1000_sqft: string;
      sustainability_score: number;
      energy_change_vs_previous_pct: number | null;
    };
    meter_type_breakdown: Array<{ utility_type: UtilityType; count: number }>;
    billing_status_breakdown: Array<{ status: UtilityBillStatus; count: number }>;
    monthly_consumption_trend: MonthlyTrendItem[];
    cost_breakdown: CostBreakdownItem[];
    anomaly_watchlist: UtilityReadingListItem[];
    recent_readings_watchlist: UtilityReadingListItem[];
    overdue_bill_watchlist: UtilityBillListItem[];
    sustainability_watchlist: SustainabilityWatchItem[];
  }

  interface UtilitiesLookupsResponse {
    facilities: FacilityLookupItem[];
    vendors: VendorLookupItem[];
    meters: MeterLookupItem[];
  }

  interface WorkflowSyncResult {
    meters_synced: number;
    readings_synced: number;
    anomalies_flagged: number;
    consumption_days_synced: number;
    bills_synced: number;
    finance_bills_synced: number;
    overdue_bills: number;
  }

  const tabs: { key: UtilitiesTab; label: string }[] = [
    { key: "meters", label: "Utilities Tracking" },
    { key: "readings", label: "Meter Readings" },
    { key: "billing", label: "Utility Billing" },
    { key: "analytics", label: "Analytics & Sustainability" },
  ];

  const utilityTypeOptions: { value: UtilityType; label: string }[] = [
    { value: "electricity", label: "Electricity" },
    { value: "water", label: "Water" },
    { value: "gas", label: "Gas" },
    { value: "diesel", label: "Diesel" },
  ];

  const billStatusOptions: { value: UtilityBillStatus; label: string }[] = [
    { value: "overdue", label: "Overdue" },
    { value: "issued", label: "Issued" },
    { value: "paid", label: "Paid" },
    { value: "draft", label: "Draft" },
    { value: "disputed", label: "Disputed" },
    { value: "cancelled", label: "Cancelled" },
  ];

  let activeTab = $state<UtilitiesTab>("meters");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingWorkflows = $state(false);

  let overview = $state<UtilitiesOverview | null>(null);
  let meters = $state<UtilityMeterListItem[]>([]);
  let readings = $state<UtilityReadingListItem[]>([]);
  let bills = $state<UtilityBillListItem[]>([]);

  let facilitiesLookup = $state<FacilityLookupItem[]>([]);
  let vendorsLookup = $state<VendorLookupItem[]>([]);
  let metersLookup = $state<MeterLookupItem[]>([]);

  let meterSearch = $state("");
  let meterFacilityFilter = $state("");
  let meterUtilityFilter = $state("");

  let readingSearch = $state("");
  let readingFacilityFilter = $state("");
  let readingUtilityFilter = $state("");
  let readingAnomalyFilter = $state("");

  let billSearch = $state("");
  let billFacilityFilter = $state("");
  let billUtilityFilter = $state("");
  let billStatusFilter = $state("");

  let showMeterDrawer = $state(false);
  let showReadingDrawer = $state(false);
  let showBillDrawer = $state(false);

  let meterSaving = $state(false);
  let readingSaving = $state(false);
  let billSaving = $state(false);

  let meterForm = $state({
    facility: "",
    vendor: "",
    meter_number: "",
    utility_type: "electricity" as UtilityType,
    unit_of_measure: "",
    location_label: "",
    provider_name: "",
    installed_at: "",
    is_smart_meter: true,
    is_active: true,
    notes: "",
  });

  let readingForm = $state({
    facility: "",
    meter: "",
    reading_at: nextDateTimeInput(),
    reading_value: "",
    is_estimated: false,
    notes: "",
  });

  let billForm = $state({
    facility: "",
    meter: "",
    vendor: "",
    provider_name: "",
    utility_type: "electricity" as UtilityType,
    bill_number: "",
    billing_period_start: todayInput(-30),
    billing_period_end: todayInput(),
    issue_date: todayInput(),
    due_date: todayInput(14),
    usage_quantity: "",
    unit_rate: "",
    subtotal: "",
    tax_amount: "",
    notes: "",
  });

  function todayInput(offsetDays = 0): string {
    const value = new Date();
    value.setDate(value.getDate() + offsetDays);
    return value.toISOString().slice(0, 10);
  }

  function nextDateTimeInput(offsetHours = 0): string {
    const value = new Date();
    value.setHours(value.getHours() + offsetHours);
    const offset = value.getTimezoneOffset();
    const local = new Date(value.getTime() - offset * 60 * 1000);
    return local.toISOString().slice(0, 16);
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillMeter() {
    const types: UtilityType[] = ["electricity", "water", "gas", "diesel", "solar"];
    const type = types[Math.floor(Math.random() * types.length)];
    const units: Record<string, string> = { electricity: "kWh", water: "m³", gas: "m³", diesel: "litres", solar: "kWh" };
    meterForm.meter_number = `MTR-${Math.floor(Math.random() * 9000) + 1000}`;
    meterForm.utility_type = type;
    meterForm.unit_of_measure = units[type] || "kWh";
    meterForm.location_label = ["Main building entry", "Basement plant room", "Rooftop solar array", "Generator house", "Ground floor utility closet"][Math.floor(Math.random() * 5)];
    meterForm.provider_name = ["Ikeja Electric", "Lagos Water Corp", "Shell Gas", "Total Energies", "Eko Electricity"][Math.floor(Math.random() * 5)];
    meterForm.installed_at = todayInput(-90);
    meterForm.is_smart_meter = Math.random() > 0.3;
    meterForm.is_active = true;
    meterForm.notes = `${type.charAt(0).toUpperCase() + type.slice(1)} meter installed for facility monitoring.`;
    if (facilitiesLookup.length > 0 && !meterForm.facility) meterForm.facility = String(facilitiesLookup[0].id);
    if (vendorsLookup.length > 0 && !meterForm.vendor) meterForm.vendor = String(vendorsLookup[0].id);
  }

  function devFillReading() {
    readingForm.reading_at = nextDateTimeInput();
    readingForm.reading_value = String(Math.floor(Math.random() * 50000) + 1000);
    readingForm.is_estimated = Math.random() > 0.8;
    readingForm.notes = readingForm.is_estimated ? "Estimated reading due to meter access issue." : "Regular scheduled reading.";
    if (facilitiesLookup.length > 0 && !readingForm.facility) readingForm.facility = String(facilitiesLookup[0].id);
    if (metersLookup.length > 0 && !readingForm.meter) readingForm.meter = String(metersLookup[0].id);
  }

  function devFillBill() {
    const types: UtilityType[] = ["electricity", "water", "gas", "diesel", "solar"];
    const type = types[Math.floor(Math.random() * types.length)];
    const qty = Math.floor(Math.random() * 5000) + 500;
    const rate = Math.floor(Math.random() * 50) + 10;
    const subtotal = qty * rate;
    const tax = Math.floor(subtotal * 0.075);
    billForm.utility_type = type;
    billForm.bill_number = `UTL-${Math.floor(Math.random() * 9000) + 1000}`;
    billForm.provider_name = ["Ikeja Electric", "Lagos Water Corp", "Shell Gas"][Math.floor(Math.random() * 3)];
    billForm.billing_period_start = todayInput(-30);
    billForm.billing_period_end = todayInput();
    billForm.issue_date = todayInput();
    billForm.due_date = todayInput(14);
    billForm.usage_quantity = String(qty);
    billForm.unit_rate = String(rate);
    billForm.subtotal = String(subtotal);
    billForm.tax_amount = String(tax);
    billForm.notes = `${type.charAt(0).toUpperCase() + type.slice(1)} bill for the current billing cycle.`;
    if (facilitiesLookup.length > 0 && !billForm.facility) billForm.facility = String(facilitiesLookup[0].id);
    if (metersLookup.length > 0 && !billForm.meter) billForm.meter = String(metersLookup[0].id);
    if (vendorsLookup.length > 0 && !billForm.vendor) billForm.vendor = String(vendorsLookup[0].id);
  }

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtInt(value: unknown): string {
    return toNumber(value).toLocaleString("en-US");
  }

  function fmtMoney(value: string | number | null | undefined): string {
    return toNumber(value).toLocaleString("en-US", {
      style: "currency",
      currency: "NGN",
      maximumFractionDigits: 2,
    });
  }

  function fmtQty(value: string | number | null | undefined, unit = ""): string {
    const amount = toNumber(value);
    const formatted = amount.toLocaleString("en-US", {
      minimumFractionDigits: amount % 1 === 0 ? 0 : 2,
      maximumFractionDigits: 2,
    });
    return unit ? `${formatted} ${unit}` : formatted;
  }

  function fmtPercent(value: number | null | undefined): string {
    if (value === null || value === undefined) return "--";
    return `${Number(value).toFixed(1)}%`;
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

  function fmtMonth(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", {
      month: "short",
      year: "numeric",
    });
  }

  function fmtLabel(value: string): string {
    return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function parseApiMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string") return error.data.detail;
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ");
      if (fieldMessage) return fieldMessage;
    }
    return fallback;
  }

  function utilityBadgeClass(value: UtilityType): string {
    switch (value) {
      case "electricity":
        return "border-amber-200 bg-amber-50 text-amber-700";
      case "water":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "gas":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "diesel":
        return "border-orange-200 bg-orange-50 text-orange-700";
      case "solar":
        return "border-yellow-200 bg-yellow-50 text-yellow-700";
    }
  }

  function billStatusClass(value: UtilityBillStatus): string {
    switch (value) {
      case "paid":
        return "bg-emerald-50 text-emerald-700";
      case "overdue":
        return "bg-red-50 text-red-700";
      case "issued":
        return "bg-blue-50 text-blue-700";
      case "disputed":
        return "bg-amber-50 text-amber-700";
      case "cancelled":
        return "bg-neutral-100 text-neutral-700";
      default:
        return "bg-slate-100 text-slate-700";
    }
  }

  function meterStateClass(item: UtilityMeterListItem): string {
    if (!item.is_active) return "bg-neutral-100 text-neutral-700";
    return item.is_smart_meter ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700";
  }

  function anomalyClass(isAnomaly: boolean): string {
    return isAnomaly ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700";
  }

  function metersForFacility(facilityId: string, options: { activeOnly?: boolean; utilityType?: UtilityType | "" } = {}): MeterLookupItem[] {
    return metersLookup.filter((item) => {
      if (facilityId && String(item.facility ?? "") !== facilityId) return false;
      if (options.activeOnly && !item.is_active) return false;
      if (options.utilityType && item.utility_type !== options.utilityType) return false;
      return true;
    });
  }

  function selectedReadingMeter(): MeterLookupItem | null {
    const meterId = Number(readingForm.meter);
    if (!meterId) return null;
    return metersLookup.find((item) => item.id === meterId) ?? null;
  }

  function selectedBillMeter(): MeterLookupItem | null {
    const meterId = Number(billForm.meter);
    if (!meterId) return null;
    return metersLookup.find((item) => item.id === meterId) ?? null;
  }

  function filteredMeters(): UtilityMeterListItem[] {
    const searchValue = meterSearch.trim().toLowerCase();
    return meters.filter((item) => {
      if (meterFacilityFilter && String(item.facility ?? "") !== meterFacilityFilter) return false;
      if (meterUtilityFilter && item.utility_type !== meterUtilityFilter) return false;
      if (!searchValue) return true;
      return [
        item.meter_number,
        item.facility_code,
        item.property_name,
        item.location_label,
        item.provider_name,
        item.vendor_name,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    });
  }

  function filteredReadings(): UtilityReadingListItem[] {
    const searchValue = readingSearch.trim().toLowerCase();
    return readings.filter((item) => {
      if (readingFacilityFilter && String(item.facility ?? "") !== readingFacilityFilter) return false;
      if (readingUtilityFilter && item.utility_type !== readingUtilityFilter) return false;
      if (readingAnomalyFilter) {
        const wantsAnomaly = readingAnomalyFilter === "flagged";
        if (item.is_anomaly !== wantsAnomaly) return false;
      }
      if (!searchValue) return true;
      return [
        item.meter_number,
        item.facility_code,
        item.property_name,
        item.entered_by_name,
        item.anomaly_reason,
        item.notes,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    });
  }

  function filteredBills(): UtilityBillListItem[] {
    const searchValue = billSearch.trim().toLowerCase();
    return bills.filter((item) => {
      if (billFacilityFilter && String(item.facility ?? "") !== billFacilityFilter) return false;
      if (billUtilityFilter && item.utility_type !== billUtilityFilter) return false;
      if (billStatusFilter && item.status !== billStatusFilter) return false;
      if (!searchValue) return true;
      return [
        item.bill_number,
        item.provider_name,
        item.vendor_name,
        item.facility_code,
        item.property_name,
        item.finance_bill_number,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    });
  }

  function resetMeterForm() {
    meterForm = {
      facility: "",
      vendor: "",
      meter_number: "",
      utility_type: "electricity",
      unit_of_measure: "",
      location_label: "",
      provider_name: "",
      installed_at: "",
      is_smart_meter: true,
      is_active: true,
      notes: "",
    };
  }

  function resetReadingForm(prefill?: { facility?: number | null; meter?: number | null }) {
    readingForm = {
      facility: prefill?.facility ? String(prefill.facility) : "",
      meter: prefill?.meter ? String(prefill.meter) : "",
      reading_at: nextDateTimeInput(),
      reading_value: "",
      is_estimated: false,
      notes: "",
    };
  }

  function resetBillForm(prefill?: { facility?: number | null; meter?: number | null; utility_type?: UtilityType | null }) {
    billForm = {
      facility: prefill?.facility ? String(prefill.facility) : "",
      meter: prefill?.meter ? String(prefill.meter) : "",
      vendor: "",
      provider_name: "",
      utility_type: prefill?.utility_type ?? "electricity",
      bill_number: "",
      billing_period_start: todayInput(-30),
      billing_period_end: todayInput(),
      issue_date: todayInput(),
      due_date: todayInput(14),
      usage_quantity: "",
      unit_rate: "",
      subtotal: "",
      tax_amount: "",
      notes: "",
    };
  }

  async function fetchOverview() {
    overview = await api.get<UtilitiesOverview>("/facility-management/utilities/overview/");
  }

  async function fetchMeters() {
    const response = await api.get<PaginatedResponse<UtilityMeterListItem>>("/facility-management/utilities/meters/", {
      page_size: "200",
    });
    meters = response.results;
  }

  async function fetchReadings() {
    const response = await api.get<PaginatedResponse<UtilityReadingListItem>>("/facility-management/utilities/readings/", {
      page_size: "200",
    });
    readings = response.results;
  }

  async function fetchBills() {
    const response = await api.get<PaginatedResponse<UtilityBillListItem>>("/facility-management/utilities/bills/", {
      page_size: "200",
    });
    bills = response.results;
  }

  async function fetchLookups() {
    const response = await api.get<UtilitiesLookupsResponse>("/facility-management/utilities/lookups/");
    facilitiesLookup = response.facilities;
    vendorsLookup = response.vendors;
    metersLookup = response.meters;
  }

  async function syncWorkflows(options: { silent?: boolean } = {}): Promise<WorkflowSyncResult | null> {
    syncingWorkflows = true;
    try {
      const result = await api.post<WorkflowSyncResult>("/facility-management/utilities/sync/", {});
      if (!options.silent) {
        toast.success(
          "Utility workflows synced",
          [
            `${result.readings_synced} readings refreshed`,
            `${result.consumption_days_synced} daily analytics rebuilt`,
            `${result.finance_bills_synced} finance bills synced`,
          ].join(" • "),
        );
      }
      return result;
    } catch (error) {
      if (!options.silent) {
        toast.error("Workflow run failed", parseApiMessage(error, "The utilities workflow engine could not be executed."));
      }
      return null;
    } finally {
      syncingWorkflows = false;
    }
  }

  async function refreshAll() {
    if (!loading) refreshing = true;
    try {
      await Promise.all([
        fetchOverview(),
        fetchMeters(),
        fetchReadings(),
        fetchBills(),
        fetchLookups(),
      ]);
    } catch {
      overview = null;
      toast.error("Load failed", "Could not load utilities and energy management.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function handleRunWorkflows() {
    const result = await syncWorkflows();
    if (result) {
      await refreshAll();
    }
  }

  function openMeterDrawer() {
    resetMeterForm();
    showMeterDrawer = true;
    void fetchLookups();
  }

  function closeMeterDrawer() {
    showMeterDrawer = false;
    resetMeterForm();
  }

  function openReadingDrawer(prefill?: { facility?: number | null; meter?: number | null }) {
    resetReadingForm(prefill);
    showReadingDrawer = true;
    void fetchLookups();
  }

  function closeReadingDrawer() {
    showReadingDrawer = false;
    resetReadingForm();
  }

  function openBillDrawer(prefill?: { facility?: number | null; meter?: number | null; utility_type?: UtilityType | null }) {
    resetBillForm(prefill);
    showBillDrawer = true;
    void fetchLookups();
  }

  function closeBillDrawer() {
    showBillDrawer = false;
    resetBillForm();
  }

  async function handleMeterSubmit(event: Event) {
    event.preventDefault();
    if (!meterForm.facility) {
      toast.error("Missing data", "Select the facility where this meter is installed.");
      return;
    }

    meterSaving = true;
    try {
      await api.post("/facility-management/utilities/meters/", {
        facility: Number(meterForm.facility),
        vendor: meterForm.vendor ? Number(meterForm.vendor) : null,
        meter_number: meterForm.meter_number.trim(),
        utility_type: meterForm.utility_type,
        unit_of_measure: meterForm.unit_of_measure.trim(),
        location_label: meterForm.location_label.trim(),
        provider_name: meterForm.provider_name.trim(),
        installed_at: meterForm.installed_at || null,
        is_smart_meter: meterForm.is_smart_meter,
        is_active: meterForm.is_active,
        notes: meterForm.notes.trim(),
      });
      toast.success("Meter added", "The meter was saved and utility defaults were applied automatically.");
      closeMeterDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Could not save meter", parseApiMessage(error, "The utility meter could not be saved."));
    } finally {
      meterSaving = false;
    }
  }

  async function handleReadingSubmit(event: Event) {
    event.preventDefault();
    if (!readingForm.meter) {
      toast.error("Missing data", "Select the meter you want to capture.");
      return;
    }

    readingSaving = true;
    try {
      await api.post("/facility-management/utilities/readings/", {
        meter: Number(readingForm.meter),
        reading_at: new Date(readingForm.reading_at).toISOString(),
        reading_value: readingForm.reading_value,
        is_estimated: readingForm.is_estimated,
        notes: readingForm.notes.trim(),
      });
      toast.success("Reading logged", "Consumption analytics, anomaly checks, and related billing data were refreshed.");
      closeReadingDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Could not log reading", parseApiMessage(error, "The meter reading could not be saved."));
    } finally {
      readingSaving = false;
    }
  }

  async function handleBillSubmit(event: Event) {
    event.preventDefault();
    if (!billForm.facility && !billForm.meter) {
      toast.error("Missing data", "Choose a facility or a utility meter for this bill.");
      return;
    }
    if (!billForm.bill_number.trim()) {
      toast.error("Missing data", "Enter the provider bill number.");
      return;
    }

    billSaving = true;
    try {
      await api.post("/facility-management/utilities/bills/", {
        facility: billForm.facility ? Number(billForm.facility) : null,
        meter: billForm.meter ? Number(billForm.meter) : null,
        vendor: billForm.vendor ? Number(billForm.vendor) : null,
        provider_name: billForm.provider_name.trim(),
        utility_type: billForm.utility_type,
        bill_number: billForm.bill_number.trim(),
        billing_period_start: billForm.billing_period_start,
        billing_period_end: billForm.billing_period_end,
        issue_date: billForm.issue_date,
        due_date: billForm.due_date,
        usage_quantity: billForm.usage_quantity || undefined,
        unit_rate: billForm.unit_rate || undefined,
        subtotal: billForm.subtotal || undefined,
        tax_amount: billForm.tax_amount || undefined,
        notes: billForm.notes.trim(),
      });
      toast.success("Utility bill saved", "Usage, bill totals, overdue logic, and finance sync were applied automatically.");
      closeBillDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Could not save bill", parseApiMessage(error, "The utility bill could not be saved."));
    } finally {
      billSaving = false;
    }
  }

  $effect(() => {
    refreshAll();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-500">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Utilities &amp; Energy Management</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Track electricity, water, gas, and diesel usage, meter readings, provider billing, and sustainability performance.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>

    <div class="flex items-center gap-2 self-start">
      <button
        type="button"
        onclick={handleRunWorkflows}
        disabled={syncingWorkflows}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {syncingWorkflows ? "Running Workflows..." : "Run Workflows"}
      </button>
      <button
        type="button"
        onclick={refreshAll}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing utilities and energy management" : "Refresh utilities and energy management"}
        title={refreshing ? "Refreshing utilities and energy management" : "Refresh utilities and energy management"}
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

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-10 text-center text-sm text-neutral-500">
      Loading utilities and energy management...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Utilities and energy management is unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Active Meters</p>
        <p class="mt-3 text-2xl font-semibold text-amber-950">{fmtInt(overview.kpis.active_meters)}</p>
        <p class="mt-3 text-xs text-amber-800">Smart meters: {fmtInt(overview.kpis.smart_meters)}</p>
      </section>

      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Utility Cost (30d)</p>
        <p class="mt-3 text-2xl font-semibold text-amber-950">{fmtMoney(overview.kpis.utility_cost_30d)}</p>
        <p class="mt-3 text-xs text-amber-800">Overdue bills: {fmtInt(overview.kpis.overdue_bills)}</p>
      </section>

      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Readings Logged (30d)</p>
        <p class="mt-3 text-2xl font-semibold text-amber-950">{fmtInt(overview.kpis.readings_logged_30d)}</p>
        <p class="mt-3 text-xs text-amber-800">Flagged anomalies: {fmtInt(overview.kpis.anomalous_readings)}</p>
      </section>

      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Sustainability Score</p>
        <p class="mt-3 text-2xl font-semibold text-amber-950">{fmtInt(overview.kpis.sustainability_score)}</p>
        <p class="mt-3 text-xs text-amber-800">Energy change vs previous window: {fmtPercent(overview.kpis.energy_change_vs_previous_pct)}</p>
      </section>
    </div>

    <div class="grid gap-4 lg:grid-cols-12">
      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40 lg:col-span-3">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Electricity (30d)</p>
        <p class="mt-3 text-xl font-semibold text-amber-950">{fmtQty(overview.kpis.electricity_kwh_30d, "kWh")}</p>
      </section>
      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40 lg:col-span-3">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Water (30d)</p>
        <p class="mt-3 text-xl font-semibold text-amber-950">{fmtQty(overview.kpis.water_m3_30d, "m3")}</p>
      </section>
      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40 lg:col-span-3">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Carbon Emissions (30d)</p>
        <p class="mt-3 text-xl font-semibold text-amber-950">{fmtQty(overview.kpis.carbon_kg_co2e_30d, "kg CO2e")}</p>
      </section>
      <section class="rounded-2xl border border-yellow-300/80 bg-linear-to-br from-yellow-100 via-amber-50 to-orange-100 p-5 shadow-sm shadow-amber-200/40 lg:col-span-3">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Energy Intensity</p>
        <p class="mt-3 text-xl font-semibold text-amber-950">{fmtQty(overview.kpis.energy_intensity_per_1000_sqft, "per 1k sqft")}</p>
        <p class="mt-2 text-xs text-amber-800">Water intensity: {fmtQty(overview.kpis.water_intensity_per_1000_sqft, "per 1k sqft")}</p>
      </section>
    </div>

    <div class="rounded-2xl border border-neutral-200 bg-white p-2">
      <div class="flex flex-wrap gap-2">
        {#each tabs as tab}
          <button
            type="button"
            onclick={() => (activeTab = tab.key)}
            class={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-neutral-900 text-white"
                : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </button>
        {/each}
      </div>
    </div>

    {#if activeTab === "meters"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 border-b border-neutral-100 pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-base font-semibold text-neutral-900">Utilities Tracking</h2>
            <p class="text-sm text-neutral-500">Register utility meters across facilities and monitor provider coverage, smart connectivity, and anomaly exposure.</p>
          </div>
          <button
            type="button"
            onclick={openMeterDrawer}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Add Meter
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-4">
          <input bind:value={meterSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search meter, provider, or location" />
          <select bind:value={meterFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code}</option>
            {/each}
          </select>
          <select bind:value={meterUtilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All utility types</option>
            {#each utilityTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2.5 text-sm text-neutral-600">
            Showing {fmtInt(filteredMeters().length)} of {fmtInt(meters.length)} meters
          </div>
        </div>

        <div class="mt-4 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3 font-medium">Meter</th>
                <th class="px-4 py-3 font-medium">Facility</th>
                <th class="px-4 py-3 font-medium">Utility</th>
                <th class="px-4 py-3 font-medium">Provider</th>
                <th class="px-4 py-3 font-medium">State</th>
                <th class="px-4 py-3 font-medium">Last Reading</th>
                <th class="px-4 py-3 font-medium">Alerts</th>
                <th class="px-4 py-3 font-medium">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if filteredMeters().length === 0}
                <tr>
                  <td colspan="8" class="px-4 py-8 text-center text-sm text-neutral-500">No meters match the current filters.</td>
                </tr>
              {:else}
                {#each filteredMeters() as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.meter_number}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.property_name}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.facility_code || "--"}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.location_label || "No location note"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${utilityBadgeClass(item.utility_type)}`}>
                        {item.utility_type_display}
                      </span>
                      <div class="mt-2 text-xs text-neutral-500">{item.unit_of_measure || "--"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.provider_name || item.vendor_name || "--"}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.vendor_name || "No vendor sync"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${meterStateClass(item)}`}>
                        {item.is_active ? (item.is_smart_meter ? "Smart / Active" : "Legacy / Active") : "Inactive"}
                      </span>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">
                        {item.latest_reading_value ? fmtQty(item.latest_reading_value, item.unit_of_measure) : "--"}
                      </div>
                      <div class="mt-1 text-xs text-neutral-500">{fmtDateTime(item.last_reading_at)}</div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${item.open_anomalies > 0 ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
                        {item.open_anomalies > 0 ? `${fmtInt(item.open_anomalies)} flagged` : "Clean"}
                      </span>
                      <div class="mt-1 text-xs text-neutral-500">{fmtInt(item.total_readings)} total readings</div>
                    </td>
                    <td class="px-4 py-4">
                      <button
                        type="button"
                        onclick={() => openReadingDrawer({ facility: item.facility, meter: item.id })}
                        class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                      >
                        Log Reading
                      </button>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {:else if activeTab === "readings"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 border-b border-neutral-100 pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-base font-semibold text-neutral-900">Meter Readings</h2>
            <p class="text-sm text-neutral-500">Capture manual or smart-meter readings, surface anomalies, and keep consumption analytics current.</p>
          </div>
          <button
            type="button"
            onclick={() => openReadingDrawer()}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Log Reading
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-4">
          <input bind:value={readingSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search meter, facility, anomaly, notes" />
          <select bind:value={readingFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code}</option>
            {/each}
          </select>
          <select bind:value={readingUtilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All utility types</option>
            {#each utilityTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select bind:value={readingAnomalyFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All quality states</option>
            <option value="flagged">Flagged only</option>
            <option value="clean">Clean only</option>
          </select>
        </div>

        <div class="mt-4 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3 font-medium">Meter</th>
                <th class="px-4 py-3 font-medium">Facility</th>
                <th class="px-4 py-3 font-medium">Captured</th>
                <th class="px-4 py-3 font-medium">Reading</th>
                <th class="px-4 py-3 font-medium">Delta</th>
                <th class="px-4 py-3 font-medium">Quality</th>
                <th class="px-4 py-3 font-medium">Notes</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if filteredReadings().length === 0}
                <tr>
                  <td colspan="7" class="px-4 py-8 text-center text-sm text-neutral-500">No meter readings match the current filters.</td>
                </tr>
              {:else}
                {#each filteredReadings() as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.meter_number}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.utility_type_display}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.facility_code || "--"}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.property_name}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{fmtDateTime(item.reading_at)}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.entered_by_name || "System"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{fmtQty(item.reading_value, item.unit_of_measure)}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.is_estimated ? "Estimated reading" : "Actual reading"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{fmtQty(item.consumption_delta, item.unit_of_measure)}</div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${anomalyClass(item.is_anomaly)}`}>
                        {item.is_anomaly ? "Flagged" : "Clean"}
                      </span>
                      <div class="mt-1 text-xs text-neutral-500">{item.anomaly_reason || "Within expected range"}</div>
                    </td>
                    <td class="px-4 py-4 text-xs text-neutral-500">{item.notes || "--"}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {:else if activeTab === "billing"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 border-b border-neutral-100 pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-base font-semibold text-neutral-900">Utility Billing</h2>
            <p class="text-sm text-neutral-500">Capture provider bills, auto-derive usage, and sync qualifying payables into Finance.</p>
          </div>
          <button
            type="button"
            onclick={() => openBillDrawer()}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Add Utility Bill
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-4">
          <input bind:value={billSearch} class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Search bill number, provider, facility" />
          <select bind:value={billFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code}</option>
            {/each}
          </select>
          <select bind:value={billUtilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All utility types</option>
            {#each utilityTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select bind:value={billStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All bill states</option>
            {#each billStatusOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="mt-4 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3 font-medium">Bill</th>
                <th class="px-4 py-3 font-medium">Facility</th>
                <th class="px-4 py-3 font-medium">Utility</th>
                <th class="px-4 py-3 font-medium">Period</th>
                <th class="px-4 py-3 font-medium">Usage / Rate</th>
                <th class="px-4 py-3 font-medium">Amount</th>
                <th class="px-4 py-3 font-medium">Status</th>
                <th class="px-4 py-3 font-medium">Finance Sync</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if filteredBills().length === 0}
                <tr>
                  <td colspan="8" class="px-4 py-8 text-center text-sm text-neutral-500">No utility bills match the current filters.</td>
                </tr>
              {:else}
                {#each filteredBills() as item (item.id)}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.bill_number}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.provider_name || item.vendor_name || "--"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.facility_code || "--"}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.property_name}</div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${utilityBadgeClass(item.utility_type)}`}>
                        {item.utility_type_display}
                      </span>
                      <div class="mt-2 text-xs text-neutral-500">{item.meter_number || "Property-level bill"}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{fmtDate(item.billing_period_start)} - {fmtDate(item.billing_period_end)}</div>
                      <div class="mt-1 text-xs text-neutral-500">Issued {fmtDate(item.issue_date)}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{fmtQty(item.usage_quantity)}</div>
                      <div class="mt-1 text-xs text-neutral-500">Rate {fmtMoney(item.unit_rate)}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-emerald-700">{fmtMoney(item.total_amount)}</div>
                      <div class="mt-1 text-xs text-neutral-500">Balance {fmtMoney(item.balance_due)}</div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${billStatusClass(item.status)}`}>
                        {item.status_display}
                      </span>
                      <div class="mt-1 text-xs text-neutral-500">Due {fmtDate(item.due_date)}</div>
                    </td>
                    <td class="px-4 py-4">
                      <div class="font-medium text-neutral-900">{item.finance_bill_number || "--"}</div>
                      <div class="mt-1 text-xs text-neutral-500">{item.finance_bill_number ? "Synced to Finance" : "No finance record yet"}</div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {:else}
      <div class="grid gap-4 xl:grid-cols-12">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 xl:col-span-7">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-base font-semibold text-neutral-900">Consumption Trend</h2>
              <p class="text-sm text-neutral-500">Six-month view of usage and carbon impact from the daily utility ledger.</p>
            </div>
          </div>
          <div class="mt-4 overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-4 py-3 font-medium">Month</th>
                  <th class="px-4 py-3 font-medium">Electricity</th>
                  <th class="px-4 py-3 font-medium">Water</th>
                  <th class="px-4 py-3 font-medium">Gas</th>
                  <th class="px-4 py-3 font-medium">Diesel</th>
                  <th class="px-4 py-3 font-medium">Carbon</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if overview.monthly_consumption_trend.length === 0}
                  <tr>
                    <td colspan="6" class="px-4 py-8 text-center text-sm text-neutral-500">No trend data is available yet.</td>
                  </tr>
                {:else}
                  {#each overview.monthly_consumption_trend as row}
                    <tr>
                      <td class="px-4 py-4 font-medium text-neutral-900">{fmtMonth(row.month)}</td>
                      <td class="px-4 py-4 text-neutral-700">{fmtQty(row.electricity_kwh, "kWh")}</td>
                      <td class="px-4 py-4 text-neutral-700">{fmtQty(row.water_m3, "m3")}</td>
                      <td class="px-4 py-4 text-neutral-700">{fmtQty(row.gas_m3, "m3")}</td>
                      <td class="px-4 py-4 text-neutral-700">{fmtQty(row.diesel_liters, "L")}</td>
                      <td class="px-4 py-4 text-neutral-700">{fmtQty(row.carbon_kg_co2e, "kg")}</td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 xl:col-span-5">
          <h2 class="text-base font-semibold text-neutral-900">Cost Breakdown</h2>
          <p class="text-sm text-neutral-500">Provider billing mix by utility type.</p>
          <div class="mt-4 space-y-3">
            {#if overview.cost_breakdown.length === 0}
              <div class="rounded-xl border border-dashed border-neutral-200 p-4 text-sm text-neutral-500">
                Cost breakdown will appear after utility bills are recorded.
              </div>
            {:else}
              {#each overview.cost_breakdown as item}
                <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${utilityBadgeClass(item.utility_type)}`}>
                        {fmtLabel(item.utility_type)}
                      </span>
                      <p class="mt-3 text-lg font-semibold text-emerald-700">{fmtMoney(item.total_amount)}</p>
                    </div>
                    <div class="text-right text-xs text-neutral-500">
                      <p>{fmtInt(item.count)} bills</p>
                      <p class="mt-1">{fmtQty(item.usage_quantity)} usage</p>
                    </div>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </section>
      </div>

      <div class="grid gap-4 xl:grid-cols-12">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 xl:col-span-5">
          <h2 class="text-base font-semibold text-neutral-900">Sustainability Watchlist</h2>
          <p class="text-sm text-neutral-500">Top facilities by carbon footprint over the last 30 days.</p>
          <div class="mt-4 space-y-3">
            {#if overview.sustainability_watchlist.length === 0}
              <div class="rounded-xl border border-dashed border-neutral-200 p-4 text-sm text-neutral-500">
                Sustainability watch data will populate after meter readings are processed.
              </div>
            {:else}
              {#each overview.sustainability_watchlist as item}
                <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="font-medium text-neutral-900">{item.property_name}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code || "No facility code"}</p>
                    </div>
                    <div class="text-right">
                      <p class="text-sm font-semibold text-neutral-900">{fmtQty(item.carbon_kg_co2e, "kg CO2e")}</p>
                      <p class="mt-1 text-xs text-neutral-500">Energy {fmtQty(item.energy_total)}</p>
                    </div>
                  </div>
                  <p class="mt-3 text-xs text-neutral-500">Water consumption: {fmtQty(item.water_m3, "m3")}</p>
                </div>
              {/each}
            {/if}
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 xl:col-span-3">
          <h2 class="text-base font-semibold text-neutral-900">Anomaly Watchlist</h2>
          <p class="text-sm text-neutral-500">Recent exceptions from meter pattern analysis.</p>
          <div class="mt-4 space-y-3">
            {#if overview.anomaly_watchlist.length === 0}
              <div class="rounded-xl border border-dashed border-neutral-200 p-4 text-sm text-neutral-500">
                No anomalies are currently flagged.
              </div>
            {:else}
              {#each overview.anomaly_watchlist as item}
                <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="font-medium text-neutral-900">{item.meter_number}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code || "--"} • {fmtDateTime(item.reading_at)}</p>
                    </div>
                    <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${anomalyClass(item.is_anomaly)}`}>
                      Flagged
                    </span>
                  </div>
                  <p class="mt-3 text-xs text-red-700">{item.anomaly_reason}</p>
                </div>
              {/each}
            {/if}
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 xl:col-span-4">
          <h2 class="text-base font-semibold text-neutral-900">Overdue Utility Bills</h2>
          <p class="text-sm text-neutral-500">Bills needing prompt finance attention.</p>
          <div class="mt-4 space-y-3">
            {#if overview.overdue_bill_watchlist.length === 0}
              <div class="rounded-xl border border-dashed border-neutral-200 p-4 text-sm text-neutral-500">
                No overdue utility bills right now.
              </div>
            {:else}
              {#each overview.overdue_bill_watchlist as item}
                <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="font-medium text-neutral-900">{item.bill_number}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.facility_code || "--"} • {item.provider_name || item.vendor_name || "--"}</p>
                    </div>
                    <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${billStatusClass(item.status)}`}>
                      {item.status_display}
                    </span>
                  </div>
                  <div class="mt-3 flex items-center justify-between text-xs text-neutral-500">
                    <span>Due {fmtDate(item.due_date)}</span>
                    <span class="font-semibold text-emerald-700">{fmtMoney(item.balance_due)}</span>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </section>
      </div>
    {/if}
  {/if}
</div>

{#if showMeterDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeMeterDrawer}
    tabindex="-1"
    aria-label="Close utility meter drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Add Utility Meter</h2>
        <p class="mt-1 text-xs text-neutral-500">All facility management forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeMeterDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close utility meter drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="utility-meter-form" class="space-y-5" onsubmit={handleMeterSubmit}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={meterForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Utility Type</span>
            <select bind:value={meterForm.utility_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each utilityTypeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Meter Number</span>
            <input bind:value={meterForm.meter_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="ELEC-BLK-A-001" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Provider / Vendor</span>
            <select bind:value={meterForm.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select provider</option>
              {#each vendorsLookup as vendor}
                <option value={String(vendor.id)}>{vendor.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Provider Name</span>
            <input bind:value={meterForm.provider_name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Auto-filled from vendor if left blank" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Unit of Measure</span>
            <input bind:value={meterForm.unit_of_measure} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Auto-filled if left blank" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Location Label</span>
            <input bind:value={meterForm.location_label} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Main incomer room, block A ground floor" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Installed Date</span>
            <input type="date" bind:value={meterForm.installed_at} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
        </section>

        <section class="grid gap-3 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <label class="flex items-center gap-3 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={meterForm.is_smart_meter} class="rounded border-neutral-300" />
            Mark as smart / IoT-enabled meter
          </label>
          <label class="flex items-center gap-3 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={meterForm.is_active} class="rounded border-neutral-300" />
            Meter is currently active
          </label>
        </section>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={meterForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Installed during energy optimization retrofit."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillMeter} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeMeterDrawer} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
        Cancel
      </button>
      <button
        type="submit"
        form="utility-meter-form"
        disabled={meterSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {meterSaving ? "Saving..." : "Save Meter"}
      </button>
    </div>
  </aside>
{/if}

{#if showReadingDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeReadingDrawer}
    tabindex="-1"
    aria-label="Close utility reading drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Log Meter Reading</h2>
        <p class="mt-1 text-xs text-neutral-500">All facility management forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeReadingDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close utility reading drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="utility-reading-form" class="space-y-5" onsubmit={handleReadingSubmit}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select
              bind:value={readingForm.facility}
              onchange={() => {
                const currentMeter = selectedReadingMeter();
                if (currentMeter && String(currentMeter.facility ?? "") !== readingForm.facility) {
                  readingForm.meter = "";
                }
              }}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
            >
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Meter</span>
            <select
              bind:value={readingForm.meter}
              onchange={() => {
                const currentMeter = selectedReadingMeter();
                if (currentMeter) readingForm.facility = String(currentMeter.facility ?? "");
              }}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
            >
              <option value="">Select meter</option>
              {#each metersForFacility(readingForm.facility, { activeOnly: true }) as meter}
                <option value={String(meter.id)}>{meter.meter_number} • {meter.utility_type_display} • {meter.facility_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Reading Date &amp; Time</span>
            <input type="datetime-local" bind:value={readingForm.reading_at} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Reading Value</span>
            <input bind:value={readingForm.reading_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder={selectedReadingMeter()?.unit_of_measure ? `Enter value in ${selectedReadingMeter()?.unit_of_measure}` : "Enter meter value"} />
          </label>
        </section>

        {#if selectedReadingMeter()}
          <div class="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-800">
            Reading will be logged against <span class="font-semibold">{selectedReadingMeter()?.meter_number}</span> in
            {` ${selectedReadingMeter()?.facility_code || "--"} `} and processed immediately for anomaly detection and daily consumption analytics.
          </div>
        {/if}

        <section class="grid gap-3 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <label class="flex items-center gap-3 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={readingForm.is_estimated} class="rounded border-neutral-300" />
            Mark this as an estimated reading
          </label>
        </section>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={readingForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Captured during end-of-day engineering round."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillReading} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeReadingDrawer} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
        Cancel
      </button>
      <button
        type="submit"
        form="utility-reading-form"
        disabled={readingSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {readingSaving ? "Saving..." : "Save Reading"}
      </button>
    </div>
  </aside>
{/if}

{#if showBillDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeBillDrawer}
    tabindex="-1"
    aria-label="Close utility bill drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Add Utility Bill</h2>
        <p class="mt-1 text-xs text-neutral-500">All facility management forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeBillDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close utility bill drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="utility-bill-form" class="space-y-5" onsubmit={handleBillSubmit}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select
              bind:value={billForm.facility}
              onchange={() => {
                const currentMeter = selectedBillMeter();
                if (currentMeter && String(currentMeter.facility ?? "") !== billForm.facility) {
                  billForm.meter = "";
                }
              }}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
            >
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Meter (Optional)</span>
            <select
              bind:value={billForm.meter}
              onchange={() => {
                const currentMeter = selectedBillMeter();
                if (currentMeter) {
                  billForm.facility = String(currentMeter.facility ?? "");
                  billForm.utility_type = currentMeter.utility_type;
                }
              }}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
            >
              <option value="">No specific meter</option>
              {#each metersForFacility(billForm.facility, { utilityType: billForm.utility_type }) as meter}
                <option value={String(meter.id)}>{meter.meter_number} • {meter.utility_type_display} • {meter.facility_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Utility Type</span>
            <select bind:value={billForm.utility_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each utilityTypeOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Provider / Vendor</span>
            <select bind:value={billForm.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select provider</option>
              {#each vendorsLookup as vendor}
                <option value={String(vendor.id)}>{vendor.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Provider Name</span>
            <input bind:value={billForm.provider_name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Auto-filled from vendor if left blank" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Bill Number</span>
            <input bind:value={billForm.bill_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="UTIL-2026-0001" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Billing Period Start</span>
            <input type="date" bind:value={billForm.billing_period_start} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Billing Period End</span>
            <input type="date" bind:value={billForm.billing_period_end} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Issue Date</span>
            <input type="date" bind:value={billForm.issue_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Due Date</span>
            <input type="date" bind:value={billForm.due_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Usage Quantity</span>
            <input bind:value={billForm.usage_quantity} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Auto-derived if readings exist" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Unit Rate</span>
            <input bind:value={billForm.unit_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="10.00" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Subtotal</span>
            <input bind:value={billForm.subtotal} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Auto-calculated if usage and rate are available" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Tax Amount</span>
            <input bind:value={billForm.tax_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="0.00" />
          </label>
        </section>

        <div class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          When a vendor is attached, this bill will also sync into Finance as a payable record. If a meter is selected, usage and subtotal can be auto-derived from the billing period readings.
        </div>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={billForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Estimated charges were reconciled against the provider portal statement."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillBill} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={closeBillDrawer} class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
        Cancel
      </button>
      <button
        type="submit"
        form="utility-bill-form"
        disabled={billSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {billSaving ? "Saving..." : "Save Utility Bill"}
      </button>
    </div>
  </aside>
{/if}

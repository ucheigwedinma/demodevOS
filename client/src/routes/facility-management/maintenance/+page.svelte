<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    AssetComponentListItem,
    MaintenanceCategory,
    MaintenanceVendorListItem,
    PaginatedResponse,
    PredictiveAlertStatus,
    PredictiveMaintenanceAlertListItem,
    PredictiveMaintenanceRuleListItem,
    PreventiveFrequency,
    PreventiveScheduleListItem,
    PreventiveStatus,
    WorkOrderListItem,
    WorkOrderMaintenanceMode,
    WorkOrderPriority,
    WorkOrderStatus,
  } from "$lib/types";

  type MaintenanceTab = "work_orders" | "preventive" | "corrective" | "predictive";

  interface FacilityMaintenanceOverview {
    generated_at: string;
    kpis: {
      open_work_orders: number;
      in_progress_work_orders: number;
      verified_work_orders: number;
      completed_today: number;
      sla_at_risk: number;
      sla_overdue: number;
      breakdown_open: number;
      preventive_active: number;
      preventive_due_30_days: number;
      preventive_overdue: number;
      predictive_rules_active: number;
      predictive_alerts_open: number;
    };
    priority_breakdown: Array<{ priority: string; count: number }>;
    status_breakdown: Array<{ status: string; count: number }>;
    work_orders_watchlist: Array<{
      id: number;
      title: string;
      priority: WorkOrderPriority;
      status: WorkOrderStatus;
      maintenance_mode: WorkOrderMaintenanceMode;
      facility_code: string;
      location_label: string;
      asset_component_name: string;
      assigned_to: string;
      due_date: string | null;
      sla_due_at: string | null;
      sla_status: string;
    }>;
    preventive_watchlist: Array<{
      id: number;
      title: string;
      facility_code: string;
      asset_component_name: string;
      assigned_to: string;
      frequency: PreventiveFrequency;
      priority: WorkOrderPriority;
      next_due_date: string;
      generate_days_before: number;
      last_work_order_id: number | null;
      status: PreventiveStatus;
    }>;
    predictive_alerts_watchlist: Array<{
      id: number;
      title: string;
      facility_code: string;
      asset_component_name: string;
      priority: WorkOrderPriority;
      trigger_type: string;
      status: PredictiveAlertStatus;
      message: string;
      work_order_id: number | null;
      triggered_at: string;
    }>;
  }

  interface MaintenanceWorkflowSyncResult {
    preventive_work_orders_created: number;
    preventive_work_orders_skipped: number;
    predictive_alerts_created: number;
    predictive_work_orders_created: number;
    predictive_rules_skipped: number;
  }

  interface FacilityLookupItem {
    id: number;
    facility_code: string;
    property_name: string;
  }

  interface FacilitySpaceLookupItem {
    id: number;
    facility: number;
    facility_code: string;
    zone_code: string;
    zone_name: string;
    unit_number: string;
    space_label: string;
  }

  const tabs: { key: MaintenanceTab; label: string }[] = [
    { key: "work_orders", label: "Work Orders" },
    { key: "preventive", label: "Preventive Maintenance" },
    { key: "corrective", label: "Corrective Maintenance" },
    { key: "predictive", label: "Predictive Maintenance" },
  ];

  const categoryOptions: { value: MaintenanceCategory; label: string }[] = [
    { value: "general", label: "General" },
    { value: "hvac", label: "HVAC" },
    { value: "elevator", label: "Elevators" },
    { value: "generator", label: "Generators" },
    { value: "electrical", label: "Electrical" },
    { value: "mechanical", label: "Mechanical" },
    { value: "plumbing", label: "Plumbing" },
    { value: "fire_safety", label: "Fire Safety" },
    { value: "security", label: "Security" },
    { value: "water_systems", label: "Water Systems" },
    { value: "structural", label: "Structural" },
    { value: "cleaning", label: "Cleaning" },
    { value: "landscaping", label: "Landscaping" },
    { value: "painting", label: "Painting" },
  ];

  const priorityOptions: { value: WorkOrderPriority; label: string }[] = [
    { value: "critical", label: "Critical" },
    { value: "high", label: "High" },
    { value: "medium", label: "Medium" },
    { value: "low", label: "Low" },
    { value: "urgent", label: "Urgent" },
  ];

  const workOrderStatusOptions: { value: WorkOrderStatus; label: string }[] = [
    { value: "open", label: "Open" },
    { value: "assigned", label: "Assigned" },
    { value: "in_progress", label: "In Progress" },
    { value: "on_hold", label: "On Hold" },
    { value: "completed", label: "Completed" },
    { value: "verified", label: "Verified" },
    { value: "cancelled", label: "Cancelled" },
  ];

  const preventiveFrequencyOptions: { value: PreventiveFrequency; label: string }[] = [
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "biweekly", label: "Bi-Weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "semi_annual", label: "Semi-Annual" },
    { value: "annual", label: "Annual" },
  ];

  const preventiveStatusOptions: { value: PreventiveStatus; label: string }[] = [
    { value: "active", label: "Active" },
    { value: "paused", label: "Paused" },
    { value: "completed", label: "Completed" },
  ];

  const predictiveAlertStatusOptions: { value: PredictiveAlertStatus; label: string }[] = [
    { value: "open", label: "Open" },
    { value: "acknowledged", label: "Acknowledged" },
    { value: "work_order_created", label: "Work Order Created" },
    { value: "resolved", label: "Resolved" },
  ];

  const WORK_ORDER_PAGE_SIZE = 10;
  const PREVENTIVE_PAGE_SIZE = 10;
  const PREDICTIVE_RULE_PAGE_SIZE = 8;
  const PREDICTIVE_ALERT_PAGE_SIZE = 6;

  let activeTab = $state<MaintenanceTab>("work_orders");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingWorkflows = $state(false);

  let overview = $state<FacilityMaintenanceOverview | null>(null);
  let workOrders = $state<WorkOrderListItem[]>([]);
  let schedules = $state<PreventiveScheduleListItem[]>([]);
  let predictiveRules = $state<PredictiveMaintenanceRuleListItem[]>([]);
  let predictiveAlerts = $state<PredictiveMaintenanceAlertListItem[]>([]);

  let facilitiesLookup = $state<FacilityLookupItem[]>([]);
  let spacesLookup = $state<FacilitySpaceLookupItem[]>([]);
  let assetsLookup = $state<AssetComponentListItem[]>([]);
  let vendorsLookup = $state<MaintenanceVendorListItem[]>([]);

  let workOrderSearch = $state("");
  let workOrderFacilityFilter = $state("");
  let workOrderStatusFilter = $state("");
  let workOrderPriorityFilter = $state("");
  let workOrderPage = $state(1);

  let preventiveSearch = $state("");
  let preventiveFacilityFilter = $state("");
  let preventiveStatusFilter = $state("");
  let preventivePage = $state(1);

  let predictiveSearch = $state("");
  let predictiveFacilityFilter = $state("");
  let predictiveAlertStatusFilter = $state("");
  let predictiveRulePage = $state(1);
  let predictiveAlertPage = $state(1);

  let showWorkOrderDrawer = $state(false);
  let showPreventiveDrawer = $state(false);
  let showPredictiveDrawer = $state(false);

  let workOrderSaving = $state(false);
  let preventiveSaving = $state(false);
  let predictiveSaving = $state(false);

  let workOrderDrawerMode = $state<WorkOrderMaintenanceMode>("corrective");

  let workOrderForm = $state({
    facility: "",
    facility_space: "",
    asset_component: "",
    vendor: "",
    title: "",
    description: "",
    category: "general" as MaintenanceCategory,
    priority: "medium" as WorkOrderPriority,
    status: "open" as WorkOrderStatus,
    reported_by: "",
    assigned_to: "",
    due_date: "",
    sla_target_hours: "",
    maintenance_mode: "corrective" as WorkOrderMaintenanceMode,
    is_breakdown: false,
    root_cause: "",
    estimated_cost: "",
    actual_cost: "",
    verification_notes: "",
    verified_by: "",
    notes: "",
  });

  let preventiveForm = $state({
    facility: "",
    facility_space: "",
    asset_component: "",
    vendor: "",
    title: "",
    description: "",
    category: "general" as MaintenanceCategory,
    frequency: "monthly" as PreventiveFrequency,
    priority: "medium" as WorkOrderPriority,
    assigned_to: "",
    next_due_date: "",
    sla_target_hours: "",
    generate_days_before: "0",
    auto_create_work_orders: true,
    estimated_cost: "",
    status: "active" as PreventiveStatus,
    notes: "",
  });

  let predictiveForm = $state({
    facility: "",
    facility_space: "",
    asset_component: "",
    title: "",
    description: "",
    priority: "high" as WorkOrderPriority,
    assigned_to: "",
    sla_target_hours: "",
    runtime_hours_threshold: "",
    cycle_threshold: "",
    runtime_hours_reading: "",
    cycle_reading: "",
    alert_on_offline: true,
    alert_on_fault: true,
    auto_create_work_order: true,
    is_active: true,
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillWorkOrder() {
    const dueDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const titles = ["HVAC compressor vibration — Unit 3A", "Emergency lighting failure in stairwell B", "Water leak detected in basement pump room", "Elevator door misalignment — Shaft 2", "Fire alarm panel fault — Zone 4", "Generator fuel filter replacement overdue"];
    const categories: MaintenanceCategory[] = ["hvac", "electrical", "plumbing", "fire_safety", "elevator", "general"];
    const priorities: WorkOrderPriority[] = ["low", "medium", "high", "critical"];
    const modes: WorkOrderMaintenanceMode[] = ["corrective", "preventive", "predictive"];
    const idx = Math.floor(Math.random() * titles.length);

    workOrderForm.title = titles[idx];
    workOrderForm.description = `${titles[idx]}. Reported by facilities team during routine walkthrough. Requires immediate attention to prevent service disruption.`;
    workOrderForm.category = categories[idx % categories.length];
    workOrderForm.priority = priorities[Math.floor(Math.random() * priorities.length)];
    workOrderForm.status = "open";
    workOrderForm.maintenance_mode = modes[Math.floor(Math.random() * modes.length)];
    workOrderForm.is_breakdown = Math.random() > 0.7;
    workOrderForm.reported_by = "Facilities Manager";
    workOrderForm.assigned_to = "Maintenance Lead";
    workOrderForm.due_date = dueDate;
    workOrderForm.sla_target_hours = String(Math.floor(Math.random() * 48) + 4);
    workOrderForm.estimated_cost = String(Math.floor(Math.random() * 500000) + 25000);
    workOrderForm.root_cause = workOrderForm.maintenance_mode === "corrective" ? "Component wear from extended operation beyond service interval." : "";
    workOrderForm.notes = "Ensure safety protocols are followed. Coordinate with tenants for access.";
    if (facilitiesLookup.length > 0 && !workOrderForm.facility) workOrderForm.facility = String(facilitiesLookup[0].id);
    if (vendorsLookup.length > 0 && !workOrderForm.vendor) workOrderForm.vendor = String(vendorsLookup[0].id);
  }

  function devFillPreventive() {
    const nextMonth = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const titles = ["Quarterly HVAC filter replacement", "Monthly fire extinguisher inspection", "Bi-annual elevator load testing", "Weekly generator test run", "Annual electrical panel thermography", "Monthly plumbing pressure check"];
    const frequencies: PreventiveFrequency[] = ["daily", "weekly", "biweekly", "monthly", "quarterly", "annual"];
    const categories: MaintenanceCategory[] = ["hvac", "fire_safety", "elevator", "generator", "electrical", "plumbing"];
    const idx = Math.floor(Math.random() * titles.length);

    preventiveForm.title = titles[idx];
    preventiveForm.description = `Scheduled preventive maintenance: ${titles[idx].toLowerCase()}. Follow manufacturer guidelines and document findings.`;
    preventiveForm.category = categories[idx % categories.length];
    preventiveForm.frequency = frequencies[Math.floor(Math.random() * frequencies.length)];
    preventiveForm.priority = "medium";
    preventiveForm.assigned_to = "Maintenance Team";
    preventiveForm.next_due_date = nextMonth;
    preventiveForm.sla_target_hours = String(Math.floor(Math.random() * 24) + 2);
    preventiveForm.generate_days_before = "3";
    preventiveForm.auto_create_work_orders = true;
    preventiveForm.estimated_cost = String(Math.floor(Math.random() * 200000) + 15000);
    preventiveForm.status = "active";
    preventiveForm.notes = "Ensure spare parts are pre-ordered before scheduled date.";
    if (facilitiesLookup.length > 0 && !preventiveForm.facility) preventiveForm.facility = String(facilitiesLookup[0].id);
    if (vendorsLookup.length > 0 && !preventiveForm.vendor) preventiveForm.vendor = String(vendorsLookup[0].id);
  }

  function devFillPredictive() {
    const titles = ["Compressor runtime overload detection", "Pump cycle fatigue monitoring", "Generator runtime hour threshold", "Chiller performance degradation alert", "Elevator motor cycle count watch"];
    const idx = Math.floor(Math.random() * titles.length);

    predictiveForm.title = titles[idx];
    predictiveForm.description = `Predictive rule: ${titles[idx].toLowerCase()}. Triggers work order when thresholds are breached.`;
    predictiveForm.priority = "high";
    predictiveForm.assigned_to = "Senior Technician";
    predictiveForm.sla_target_hours = String(Math.floor(Math.random() * 12) + 4);
    predictiveForm.runtime_hours_threshold = String(Math.floor(Math.random() * 5000) + 1000);
    predictiveForm.cycle_threshold = String(Math.floor(Math.random() * 50000) + 10000);
    predictiveForm.runtime_hours_reading = String(Math.floor(Math.random() * 800));
    predictiveForm.cycle_reading = String(Math.floor(Math.random() * 8000));
    predictiveForm.alert_on_offline = true;
    predictiveForm.alert_on_fault = true;
    predictiveForm.auto_create_work_order = true;
    predictiveForm.is_active = true;
    predictiveForm.notes = "Monitor weekly. Escalate if readings approach 80% of threshold.";
    if (facilitiesLookup.length > 0 && !predictiveForm.facility) predictiveForm.facility = String(facilitiesLookup[0].id);
  }

  const spaceMap = $derived.by(() => {
    const entries = spacesLookup.map((item) => [item.id, item] as const);
    return new Map(entries);
  });

  const assetMap = $derived.by(() => {
    const entries = assetsLookup.map((item) => [item.id, item] as const);
    return new Map(entries);
  });

  const filteredWorkOrders = $derived.by(() => {
    const term = workOrderSearch.trim().toLowerCase();
    return workOrders.filter((item) => {
      const matchesSearch = !term || [
        item.title,
        item.asset_component_name ?? "",
        item.facility_code ?? "",
        item.facility_space_label ?? "",
        item.assigned_to,
        item.reported_by,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !workOrderFacilityFilter || String(item.facility ?? "") === workOrderFacilityFilter;
      const matchesStatus = !workOrderStatusFilter || item.status === workOrderStatusFilter;
      const matchesPriority = !workOrderPriorityFilter || item.priority === workOrderPriorityFilter;
      return matchesSearch && matchesFacility && matchesStatus && matchesPriority;
    });
  });

  const filteredCorrectiveWorkOrders = $derived.by(() =>
    filteredWorkOrders.filter((item) => item.maintenance_mode === "corrective")
  );

  const filteredSchedules = $derived.by(() => {
    const term = preventiveSearch.trim().toLowerCase();
    return schedules.filter((item) => {
      const matchesSearch = !term || [
        item.title,
        item.asset_component_name ?? "",
        item.facility_code ?? "",
        item.assigned_to,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !preventiveFacilityFilter || String(item.facility ?? "") === preventiveFacilityFilter;
      const matchesStatus = !preventiveStatusFilter || item.status === preventiveStatusFilter;
      return matchesSearch && matchesFacility && matchesStatus;
    });
  });

  const filteredPredictiveRules = $derived.by(() => {
    const term = predictiveSearch.trim().toLowerCase();
    return predictiveRules.filter((item) => {
      const matchesSearch = !term || [
        item.title,
        item.asset_component_name ?? "",
        item.facility_code ?? "",
        item.assigned_to,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !predictiveFacilityFilter || String(item.facility ?? "") === predictiveFacilityFilter;
      return matchesSearch && matchesFacility;
    });
  });

  const filteredPredictiveAlerts = $derived.by(() => {
    const term = predictiveSearch.trim().toLowerCase();
    return predictiveAlerts.filter((item) => {
      const matchesSearch = !term || [
        item.title,
        item.asset_component_name ?? "",
        item.facility_code ?? "",
        item.message,
      ].some((value) => value.toLowerCase().includes(term));
      const matchesFacility = !predictiveFacilityFilter || String(item.facility ?? "") === predictiveFacilityFilter;
      const matchesStatus = !predictiveAlertStatusFilter || item.status === predictiveAlertStatusFilter;
      return matchesSearch && matchesFacility && matchesStatus;
    });
  });

  const workOrderRows = $derived.by(() =>
    activeTab === "work_orders" ? filteredWorkOrders : filteredCorrectiveWorkOrders
  );
  const workOrderTotalPages = $derived(Math.max(1, Math.ceil(workOrderRows.length / WORK_ORDER_PAGE_SIZE)));
  const paginatedWorkOrderRows = $derived.by(() => {
    const start = (workOrderPage - 1) * WORK_ORDER_PAGE_SIZE;
    return workOrderRows.slice(start, start + WORK_ORDER_PAGE_SIZE);
  });
  const workOrderStart = $derived(workOrderRows.length === 0 ? 0 : (workOrderPage - 1) * WORK_ORDER_PAGE_SIZE + 1);
  const workOrderEnd = $derived(Math.min(workOrderPage * WORK_ORDER_PAGE_SIZE, workOrderRows.length));

  const preventiveTotalPages = $derived(Math.max(1, Math.ceil(filteredSchedules.length / PREVENTIVE_PAGE_SIZE)));
  const paginatedSchedules = $derived.by(() => {
    const start = (preventivePage - 1) * PREVENTIVE_PAGE_SIZE;
    return filteredSchedules.slice(start, start + PREVENTIVE_PAGE_SIZE);
  });
  const preventiveStart = $derived(filteredSchedules.length === 0 ? 0 : (preventivePage - 1) * PREVENTIVE_PAGE_SIZE + 1);
  const preventiveEnd = $derived(Math.min(preventivePage * PREVENTIVE_PAGE_SIZE, filteredSchedules.length));

  const predictiveRuleTotalPages = $derived(Math.max(1, Math.ceil(filteredPredictiveRules.length / PREDICTIVE_RULE_PAGE_SIZE)));
  const paginatedPredictiveRules = $derived.by(() => {
    const start = (predictiveRulePage - 1) * PREDICTIVE_RULE_PAGE_SIZE;
    return filteredPredictiveRules.slice(start, start + PREDICTIVE_RULE_PAGE_SIZE);
  });
  const predictiveRuleStart = $derived(filteredPredictiveRules.length === 0 ? 0 : (predictiveRulePage - 1) * PREDICTIVE_RULE_PAGE_SIZE + 1);
  const predictiveRuleEnd = $derived(Math.min(predictiveRulePage * PREDICTIVE_RULE_PAGE_SIZE, filteredPredictiveRules.length));

  const predictiveAlertTotalPages = $derived(Math.max(1, Math.ceil(filteredPredictiveAlerts.length / PREDICTIVE_ALERT_PAGE_SIZE)));
  const paginatedPredictiveAlerts = $derived.by(() => {
    const start = (predictiveAlertPage - 1) * PREDICTIVE_ALERT_PAGE_SIZE;
    return filteredPredictiveAlerts.slice(start, start + PREDICTIVE_ALERT_PAGE_SIZE);
  });
  const predictiveAlertStart = $derived(filteredPredictiveAlerts.length === 0 ? 0 : (predictiveAlertPage - 1) * PREDICTIVE_ALERT_PAGE_SIZE + 1);
  const predictiveAlertEnd = $derived(Math.min(predictiveAlertPage * PREDICTIVE_ALERT_PAGE_SIZE, filteredPredictiveAlerts.length));

  function pageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 7) return Array.from({ length: total }, (_, index) => index + 1);
    const pages: (number | "...")[] = [1];
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let index = start; index <= end; index += 1) pages.push(index);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  $effect(() => {
    void activeTab;
    void workOrderSearch;
    void workOrderFacilityFilter;
    void workOrderStatusFilter;
    void workOrderPriorityFilter;
    workOrderPage = 1;
  });

  $effect(() => {
    void preventiveSearch;
    void preventiveFacilityFilter;
    void preventiveStatusFilter;
    preventivePage = 1;
  });

  $effect(() => {
    void predictiveSearch;
    void predictiveFacilityFilter;
    void predictiveAlertStatusFilter;
    predictiveRulePage = 1;
    predictiveAlertPage = 1;
  });

  $effect(() => {
    if (workOrderPage > workOrderTotalPages) workOrderPage = workOrderTotalPages;
  });

  $effect(() => {
    if (preventivePage > preventiveTotalPages) preventivePage = preventiveTotalPages;
  });

  $effect(() => {
    if (predictiveRulePage > predictiveRuleTotalPages) predictiveRulePage = predictiveRuleTotalPages;
    if (predictiveAlertPage > predictiveAlertTotalPages) predictiveAlertPage = predictiveAlertTotalPages;
  });

  function fmtLabel(value: string): string {
    return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
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

  function fmtMoney(value: string | null | undefined): string {
    if (!value) return "--";
    const amount = Number(value);
    if (!Number.isFinite(amount)) return "--";
    return amount.toLocaleString("en-US", {
      style: "currency",
      currency: "NGN",
      maximumFractionDigits: 2,
    });
  }

  function fmtHours(value: number | null | undefined): string {
    if (value === null || value === undefined) return "--";
    return `${value}h`;
  }

  function badgeTone(value: string): string {
    switch (value) {
      case "critical":
      case "urgent":
      case "overdue":
      case "breached":
      case "cancelled":
      case "fault":
        return "border-red-200 bg-red-50 text-red-700";
      case "high":
      case "at_risk":
      case "in_progress":
      case "on_hold":
      case "work_order_created":
      case "acknowledged":
      case "due_soon":
      case "offline":
        return "border-amber-200 bg-amber-50 text-amber-700";
      case "verified":
      case "completed":
      case "resolved":
      case "active":
      case "met":
      case "on_track":
      case "open":
      case "assigned":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      default:
        return "border-neutral-200 bg-neutral-100 text-neutral-700";
    }
  }

  function filteredSpacesFor(facilityId: string): FacilitySpaceLookupItem[] {
    const id = Number(facilityId || 0);
    if (!id) return spacesLookup;
    return spacesLookup.filter((space) => space.facility === id);
  }

  function filteredAssetsFor(facilityId: string): AssetComponentListItem[] {
    const id = Number(facilityId || 0);
    if (!id) return assetsLookup;
    return assetsLookup.filter((asset) => asset.facility === id);
  }

  function resetWorkOrderForm(mode: WorkOrderMaintenanceMode = "corrective") {
    workOrderDrawerMode = mode;
    workOrderForm = {
      facility: "",
      facility_space: "",
      asset_component: "",
      vendor: "",
      title: "",
      description: "",
      category: "general",
      priority: mode === "corrective" ? "high" : "medium",
      status: "open",
      reported_by: "",
      assigned_to: "",
      due_date: "",
      sla_target_hours: "",
      maintenance_mode: mode,
      is_breakdown: false,
      root_cause: "",
      estimated_cost: "",
      actual_cost: "",
      verification_notes: "",
      verified_by: "",
      notes: "",
    };
  }

  function resetPreventiveForm() {
    preventiveForm = {
      facility: "",
      facility_space: "",
      asset_component: "",
      vendor: "",
      title: "",
      description: "",
      category: "general",
      frequency: "monthly",
      priority: "medium",
      assigned_to: "",
      next_due_date: "",
      sla_target_hours: "",
      generate_days_before: "0",
      auto_create_work_orders: true,
      estimated_cost: "",
      status: "active",
      notes: "",
    };
  }

  function resetPredictiveForm() {
    predictiveForm = {
      facility: "",
      facility_space: "",
      asset_component: "",
      title: "",
      description: "",
      priority: "high",
      assigned_to: "",
      sla_target_hours: "",
      runtime_hours_threshold: "",
      cycle_threshold: "",
      runtime_hours_reading: "",
      cycle_reading: "",
      alert_on_offline: true,
      alert_on_fault: true,
      auto_create_work_order: true,
      is_active: true,
      notes: "",
    };
  }

  async function fetchOverview() {
    overview = await api.get<FacilityMaintenanceOverview>("/facility-management/maintenance/overview/");
  }

  async function fetchWorkOrders() {
    const response = await api.get<PaginatedResponse<WorkOrderListItem>>("/facility-management/maintenance/work-orders/", { page_size: "200" });
    workOrders = response.results;
  }

  async function fetchSchedules() {
    const response = await api.get<PaginatedResponse<PreventiveScheduleListItem>>("/facility-management/maintenance/preventive/", { page_size: "200" });
    schedules = response.results;
  }

  async function fetchPredictiveRules() {
    const response = await api.get<PaginatedResponse<PredictiveMaintenanceRuleListItem>>("/facility-management/maintenance/predictive-rules/", { page_size: "200" });
    predictiveRules = response.results;
  }

  async function fetchPredictiveAlerts() {
    const response = await api.get<PaginatedResponse<PredictiveMaintenanceAlertListItem>>("/facility-management/maintenance/predictive-alerts/", { page_size: "200" });
    predictiveAlerts = response.results;
  }

  async function fetchLookups() {
    const [facilitiesResponse, spacesResponse, assetsResponse, vendorsResponse] = await Promise.all([
      api.get<PaginatedResponse<FacilityLookupItem>>("/facility-management/registry/facilities/", { page_size: "200" }),
      api.get<PaginatedResponse<FacilitySpaceLookupItem>>("/facility-management/registry/unit-spaces/", { page_size: "500" }),
      api.get<PaginatedResponse<AssetComponentListItem>>("/facility-management/assets/register/", { page_size: "500" }),
      api.get<PaginatedResponse<MaintenanceVendorListItem>>("/properties/maintenance/vendors/", { page_size: "200" }),
    ]);

    facilitiesLookup = facilitiesResponse.results;
    spacesLookup = spacesResponse.results;
    assetsLookup = assetsResponse.results;
    vendorsLookup = vendorsResponse.results;
  }

  async function syncWorkflows(ruleIds?: number[], options: { silent?: boolean } = {}): Promise<MaintenanceWorkflowSyncResult | null> {
    syncingWorkflows = true;
    try {
      const result = await api.post<MaintenanceWorkflowSyncResult>("/facility-management/maintenance/sync/", ruleIds?.length ? { rule_ids: ruleIds } : {});

      if (!options.silent) {
        toast.success(
          "Maintenance workflows synced",
          [
            `${result.preventive_work_orders_created} preventive work orders created`,
            `${result.predictive_alerts_created} predictive alerts raised`,
            `${result.predictive_work_orders_created} predictive work orders created`,
          ].join(" • "),
        );
      }
      return result;
    } catch (error) {
      if (!options.silent) {
        const detail =
          error instanceof ApiError && typeof error.data.detail === "string"
            ? error.data.detail
            : "Maintenance workflows could not be synchronized.";
        toast.error("Sync failed", detail);
      }
      return null;
    } finally {
      syncingWorkflows = false;
    }
  }

  async function handleRunWorkflows() {
    await syncWorkflows();
    await refreshAll();
  }

  async function refreshAll(options: { runAutomation?: boolean } = {}) {
    if (!loading) refreshing = true;
    try {
      if (options.runAutomation) {
        await syncWorkflows(undefined, { silent: true });
      }
      await Promise.all([
        fetchOverview(),
        fetchWorkOrders(),
        fetchSchedules(),
        fetchPredictiveRules(),
        fetchPredictiveAlerts(),
        fetchLookups(),
      ]);
    } catch {
      toast.error("Load failed", "Could not load maintenance management.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  function openWorkOrderDrawer(mode: WorkOrderMaintenanceMode = "corrective") {
    resetWorkOrderForm(mode);
    showWorkOrderDrawer = true;
    void fetchLookups();
  }

  function closeWorkOrderDrawer() {
    showWorkOrderDrawer = false;
    resetWorkOrderForm(workOrderDrawerMode);
  }

  function openPreventiveDrawer() {
    resetPreventiveForm();
    showPreventiveDrawer = true;
    void fetchLookups();
  }

  function closePreventiveDrawer() {
    showPreventiveDrawer = false;
    resetPreventiveForm();
  }

  function openPredictiveDrawer() {
    resetPredictiveForm();
    showPredictiveDrawer = true;
    void fetchLookups();
  }

  function closePredictiveDrawer() {
    showPredictiveDrawer = false;
    resetPredictiveForm();
  }

  async function handleWorkOrderCreate(event: Event) {
    event.preventDefault();
    if (!workOrderForm.title.trim()) {
      toast.error("Missing data", "Work order title is required.");
      return;
    }

    workOrderSaving = true;
    try {
      await api.post("/facility-management/maintenance/work-orders/", {
        facility: workOrderForm.facility ? Number(workOrderForm.facility) : null,
        facility_space: workOrderForm.facility_space ? Number(workOrderForm.facility_space) : null,
        asset_component: workOrderForm.asset_component ? Number(workOrderForm.asset_component) : null,
        vendor: workOrderForm.vendor ? Number(workOrderForm.vendor) : null,
        title: workOrderForm.title.trim(),
        description: workOrderForm.description.trim(),
        category: workOrderForm.category,
        priority: workOrderForm.priority,
        status: workOrderForm.status,
        reported_by: workOrderForm.reported_by.trim(),
        assigned_to: workOrderForm.assigned_to.trim(),
        due_date: workOrderForm.due_date || null,
        sla_target_hours: workOrderForm.sla_target_hours ? Number(workOrderForm.sla_target_hours) : null,
        maintenance_mode: workOrderForm.maintenance_mode,
        is_breakdown: workOrderForm.is_breakdown,
        root_cause: workOrderForm.root_cause.trim(),
        estimated_cost: workOrderForm.estimated_cost || null,
        actual_cost: workOrderForm.actual_cost || null,
        verification_notes: workOrderForm.verification_notes.trim(),
        verified_by: workOrderForm.verified_by.trim(),
        notes: workOrderForm.notes.trim(),
      });
      toast.success("Work order created", "Maintenance workflow and SLA targets were applied.");
      closeWorkOrderDrawer();
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the work order fields.");
      } else {
        toast.error("Create failed", "Could not create work order.");
      }
    } finally {
      workOrderSaving = false;
    }
  }

  async function handlePreventiveCreate(event: Event) {
    event.preventDefault();
    if (!preventiveForm.title.trim() || !preventiveForm.frequency) {
      toast.error("Missing data", "Preventive title and frequency are required.");
      return;
    }

    preventiveSaving = true;
    try {
      await api.post("/facility-management/maintenance/preventive/", {
        facility: preventiveForm.facility ? Number(preventiveForm.facility) : null,
        facility_space: preventiveForm.facility_space ? Number(preventiveForm.facility_space) : null,
        asset_component: preventiveForm.asset_component ? Number(preventiveForm.asset_component) : null,
        vendor: preventiveForm.vendor ? Number(preventiveForm.vendor) : null,
        title: preventiveForm.title.trim(),
        description: preventiveForm.description.trim(),
        category: preventiveForm.category,
        frequency: preventiveForm.frequency,
        priority: preventiveForm.priority,
        assigned_to: preventiveForm.assigned_to.trim(),
        next_due_date: preventiveForm.next_due_date || null,
        sla_target_hours: preventiveForm.sla_target_hours ? Number(preventiveForm.sla_target_hours) : null,
        generate_days_before: Number(preventiveForm.generate_days_before || 0),
        auto_create_work_orders: preventiveForm.auto_create_work_orders,
        estimated_cost: preventiveForm.estimated_cost || null,
        status: preventiveForm.status,
        notes: preventiveForm.notes.trim(),
      });
      toast.success("Preventive plan created", "Recurring maintenance plan saved.");
      closePreventiveDrawer();
      await refreshAll({ runAutomation: true });
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the preventive schedule fields.");
      } else {
        toast.error("Create failed", "Could not create preventive maintenance plan.");
      }
    } finally {
      preventiveSaving = false;
    }
  }

  async function handlePredictiveCreate(event: Event) {
    event.preventDefault();
    if (!predictiveForm.title.trim()) {
      toast.error("Missing data", "Predictive rule title is required.");
      return;
    }

    predictiveSaving = true;
    try {
      const response = await api.post<{ id: number }>("/facility-management/maintenance/predictive-rules/", {
        facility: predictiveForm.facility ? Number(predictiveForm.facility) : null,
        facility_space: predictiveForm.facility_space ? Number(predictiveForm.facility_space) : null,
        asset_component: predictiveForm.asset_component ? Number(predictiveForm.asset_component) : null,
        title: predictiveForm.title.trim(),
        description: predictiveForm.description.trim(),
        priority: predictiveForm.priority,
        assigned_to: predictiveForm.assigned_to.trim(),
        sla_target_hours: predictiveForm.sla_target_hours ? Number(predictiveForm.sla_target_hours) : null,
        runtime_hours_threshold: predictiveForm.runtime_hours_threshold || null,
        cycle_threshold: predictiveForm.cycle_threshold ? Number(predictiveForm.cycle_threshold) : null,
        runtime_hours_reading: predictiveForm.runtime_hours_reading || null,
        cycle_reading: predictiveForm.cycle_reading ? Number(predictiveForm.cycle_reading) : null,
        alert_on_offline: predictiveForm.alert_on_offline,
        alert_on_fault: predictiveForm.alert_on_fault,
        auto_create_work_order: predictiveForm.auto_create_work_order,
        is_active: predictiveForm.is_active,
        notes: predictiveForm.notes.trim(),
      });
      toast.success("Predictive rule created", "The rule is active and ready for evaluation.");
      closePredictiveDrawer();
      await syncWorkflows([response.id]);
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the predictive rule fields.");
      } else {
        toast.error("Create failed", "Could not create predictive rule.");
      }
    } finally {
      predictiveSaving = false;
    }
  }

  async function updateWorkOrderStatus(item: WorkOrderListItem, statusValue: WorkOrderStatus) {
    try {
      await api.patch(`/facility-management/maintenance/work-orders/${item.id}/`, {
        status: statusValue,
        verified_by: statusValue === "verified" ? "Facility Management" : item.verified_by,
      });
      toast.success("Work order updated", `Status changed to ${fmtLabel(statusValue)}.`);
      await refreshAll();
    } catch {
      toast.error("Update failed", "Could not update work order status.");
    }
  }

  async function updateAlertStatus(item: PredictiveMaintenanceAlertListItem, statusValue: PredictiveAlertStatus) {
    try {
      await api.patch(`/facility-management/maintenance/predictive-alerts/${item.id}/`, {
        status: statusValue,
      });
      toast.success("Predictive alert updated", `Alert marked as ${fmtLabel(statusValue)}.`);
      await refreshAll();
    } catch {
      toast.error("Update failed", "Could not update predictive alert.");
    }
  }

  async function evaluateRule(ruleId: number) {
    syncingWorkflows = true;
    try {
      await api.post(`/facility-management/maintenance/predictive-rules/${ruleId}/evaluate/`, {});
      toast.success("Rule evaluated", "Predictive rule evaluation completed.");
      await refreshAll();
    } catch {
      toast.error("Evaluation failed", "Could not evaluate predictive rule.");
    } finally {
      syncingWorkflows = false;
    }
  }

  let initialized = false;

  $effect(() => {
    if (initialized) return;
    initialized = true;
    void refreshAll();
  });

  $effect(() => {
    const assetId = Number(workOrderForm.asset_component || 0);
    if (!assetId) return;
    const asset = assetMap.get(assetId);
    if (!asset) return;
    if (!workOrderForm.facility && asset.facility) {
      workOrderForm.facility = String(asset.facility);
    }
    if (!workOrderForm.facility_space && asset.facility_space) {
      workOrderForm.facility_space = String(asset.facility_space);
    }
    if (!workOrderForm.category && asset.category) {
      workOrderForm.category = asset.category;
    }
  });

  $effect(() => {
    const assetId = Number(preventiveForm.asset_component || 0);
    if (!assetId) return;
    const asset = assetMap.get(assetId);
    if (!asset) return;
    if (!preventiveForm.facility && asset.facility) {
      preventiveForm.facility = String(asset.facility);
    }
    if (!preventiveForm.facility_space && asset.facility_space) {
      preventiveForm.facility_space = String(asset.facility_space);
    }
    preventiveForm.category = asset.category;
    if (!preventiveForm.title.trim()) {
      preventiveForm.title = `${asset.component_id} preventive maintenance`;
    }
  });

  $effect(() => {
    const assetId = Number(predictiveForm.asset_component || 0);
    if (!assetId) return;
    const asset = assetMap.get(assetId);
    if (!asset) return;
    if (!predictiveForm.facility && asset.facility) {
      predictiveForm.facility = String(asset.facility);
    }
    if (!predictiveForm.facility_space && asset.facility_space) {
      predictiveForm.facility_space = String(asset.facility_space);
    }
    if (!predictiveForm.title.trim()) {
      predictiveForm.title = `${asset.component_id} predictive rule`;
    }
  });

  $effect(() => {
    const spaceId = Number(workOrderForm.facility_space || 0);
    if (!spaceId) return;
    const space = spaceMap.get(spaceId);
    if (space && !workOrderForm.facility) {
      workOrderForm.facility = String(space.facility);
    }
  });

  $effect(() => {
    const spaceId = Number(preventiveForm.facility_space || 0);
    if (!spaceId) return;
    const space = spaceMap.get(spaceId);
    if (space && !preventiveForm.facility) {
      preventiveForm.facility = String(space.facility);
    }
  });

  $effect(() => {
    const spaceId = Number(predictiveForm.facility_space || 0);
    if (!spaceId) return;
    const space = spaceMap.get(spaceId);
    if (space && !predictiveForm.facility) {
      predictiveForm.facility = String(space.facility);
    }
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-500">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Maintenance Management</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Core maintenance engine for work orders, preventive schedules, corrective repairs, predictive alerts, and SLA execution across facilities.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>

    <div class="flex flex-wrap items-center gap-2 lg:ml-auto lg:justify-end">
      <button
        type="button"
        onclick={handleRunWorkflows}
        disabled={syncingWorkflows || loading}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {syncingWorkflows ? "Running Workflows..." : "Run Workflows"}
      </button>
      <button
        type="button"
        onclick={() => refreshAll({ runAutomation: false })}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing maintenance management" : "Refresh maintenance management"}
        title={refreshing ? "Refreshing maintenance management" : "Refresh maintenance management"}
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
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      Loading maintenance management...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Maintenance management overview is unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
      <section class="rounded-2xl border border-sky-200 bg-sky-50 p-4">
        <p class="text-xs uppercase tracking-wide font-semibold text-sky-700">Open Work Orders</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.open_work_orders}</p>
        <p class="mt-1 text-xs text-sky-800">In progress: {overview.kpis.in_progress_work_orders}</p>
      </section>
      <section class="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <p class="text-xs uppercase tracking-wide font-semibold text-amber-700">SLA Risk</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.sla_at_risk}</p>
        <p class="mt-1 text-xs text-amber-800">Overdue: {overview.kpis.sla_overdue}</p>
      </section>
      <section class="rounded-2xl border border-rose-200 bg-rose-50 p-4">
        <p class="text-xs uppercase tracking-wide font-semibold text-rose-700">Breakdowns</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.breakdown_open}</p>
        <p class="mt-1 text-xs text-rose-800">Reactive repairs in queue</p>
      </section>
      <section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-xs uppercase tracking-wide font-semibold text-emerald-700">Verified Today</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.verified_work_orders}</p>
        <p class="mt-1 text-xs text-emerald-800">Completed today: {overview.kpis.completed_today}</p>
      </section>
      <section class="rounded-2xl border border-violet-200 bg-violet-50 p-4">
        <p class="text-xs uppercase tracking-wide font-semibold text-violet-700">Preventive Plans</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.preventive_active}</p>
        <p class="mt-1 text-xs text-violet-800">
          Due in 30 days: {overview.kpis.preventive_due_30_days}
        </p>
      </section>
      <section class="rounded-2xl border border-orange-200 bg-orange-50 p-4">
        <p class="text-xs uppercase tracking-wide font-semibold text-orange-700">Predictive Alerts</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.predictive_alerts_open}</p>
        <p class="mt-1 text-xs text-orange-800">
          Active rules: {overview.kpis.predictive_rules_active}
        </p>
      </section>
    </div>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">SLA Watchlist</h2>
        <div class="mt-4 space-y-3">
          {#if overview.work_orders_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No watchlist items right now.</p>
          {:else}
            {#each overview.work_orders_watchlist as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{item.title}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {item.facility_code || "--"} {item.location_label ? `• ${item.location_label}` : ""}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.sla_status)}`}>
                    {fmtLabel(item.sla_status)}
                  </span>
                </div>
                <p class="mt-2 text-xs text-neutral-500">
                  Technician: {item.assigned_to || "--"} • SLA due {fmtDateTime(item.sla_due_at)}
                </p>
              </div>
            {/each}
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Preventive Due Queue</h2>
        <div class="mt-4 space-y-3">
          {#if overview.preventive_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No preventive items are due right now.</p>
          {:else}
            {#each overview.preventive_watchlist as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{item.title}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {item.facility_code || "--"} • {item.asset_component_name || "No linked asset"}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>
                    {fmtLabel(item.status)}
                  </span>
                </div>
                <p class="mt-2 text-xs text-neutral-500">
                  Due {fmtDate(item.next_due_date)} • {fmtLabel(item.frequency)} • Trigger {item.generate_days_before} day(s) early
                </p>
              </div>
            {/each}
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Predictive Alert Feed</h2>
        <div class="mt-4 space-y-3">
          {#if overview.predictive_alerts_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No active predictive alerts.</p>
          {:else}
            {#each overview.predictive_alerts_watchlist as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{item.title}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {item.facility_code || "--"} • {item.asset_component_name || "No linked asset"}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>
                    {fmtLabel(item.status)}
                  </span>
                </div>
                <p class="mt-2 text-xs text-neutral-500">{item.message}</p>
              </div>
            {/each}
          {/if}
        </div>
      </section>
    </div>

    <div class="flex flex-wrap gap-2">
      {#each tabs as tab}
        <button
          type="button"
          onclick={() => (activeTab = tab.key)}
          class={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === tab.key
              ? "bg-neutral-900 text-white"
              : "border border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300 hover:text-neutral-900"
          }`}
        >
          {tab.label}
        </button>
      {/each}
    </div>

    {#if activeTab === "work_orders" || activeTab === "corrective"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">
              {activeTab === "work_orders" ? "Work Order Register" : "Corrective Maintenance"}
            </h2>
            <p class="mt-1 text-xs text-neutral-500">
              {activeTab === "work_orders"
                ? "Create, assign, and progress work orders through SLA and verification."
                : "Reactive repairs, breakdown handling, and root-cause capture."}
            </p>
          </div>
          <button
            type="button"
            onclick={() => openWorkOrderDrawer("corrective")}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            {activeTab === "work_orders" ? "Create Work Order" : "Log Corrective Work Order"}
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-4">
          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Search
            <input
              bind:value={workOrderSearch}
              class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm normal-case tracking-normal text-neutral-900"
              placeholder="Title, asset, technician..."
            />
          </label>

          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Facility
            <select bind:value={workOrderFacilityFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
              <option value="">All facilities</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Status
            <select bind:value={workOrderStatusFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
              <option value="">All statuses</option>
              {#each workOrderStatusOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Priority
            <select bind:value={workOrderPriorityFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
              <option value="">All priorities</option>
              {#each priorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Work Order</th>
                <th class="px-3 py-2">Location</th>
                <th class="px-3 py-2">Technician</th>
                <th class="px-3 py-2">SLA</th>
                <th class="px-3 py-2">Status</th>
                <th class="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if workOrderRows.length === 0}
                <tr>
                  <td colspan="6" class="px-3 py-6 text-center text-neutral-500">
                    No work orders match the current filters.
                  </td>
                </tr>
              {:else}
                {#each paginatedWorkOrderRows as item (item.id)}
                  <tr>
                    <td class="px-3 py-3 align-top">
                      <p class="font-medium text-neutral-900">{item.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {item.asset_component_name || "No linked asset"} • {fmtLabel(item.category)}
                      </p>
                      <div class="mt-2 flex flex-wrap gap-2">
                        <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.priority)}`}>{fmtLabel(item.priority)}</span>
                        <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.maintenance_mode)}`}>{fmtLabel(item.maintenance_mode)}</span>
                        {#if item.is_breakdown}
                          <span class="inline-flex rounded-full border border-rose-200 bg-rose-50 px-2 py-1 text-xs text-rose-700">Breakdown</span>
                        {/if}
                      </div>
                      {#if activeTab === "corrective" && item.root_cause}
                        <p class="mt-2 text-xs text-neutral-500">Root cause: {item.root_cause}</p>
                      {/if}
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p class="font-medium text-neutral-800">{item.facility_code || "--"}</p>
                      <p>{item.facility_space_label || item.unit_number || "--"}</p>
                      <p>{item.property_name}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p>{item.assigned_to || "--"}</p>
                      <p class="mt-1">Reported by: {item.reported_by || "--"}</p>
                      <p class="mt-1">Opened: {fmtDate(item.reported_date)}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p><span class={`inline-flex rounded-full border px-2 py-1 ${badgeTone(item.sla_status)}`}>{fmtLabel(item.sla_status)}</span></p>
                      <p class="mt-1">Target: {fmtHours(item.sla_target_hours)}</p>
                      <p class="mt-1">Due: {fmtDate(item.due_date)}</p>
                      <p class="mt-1">Clock: {fmtDateTime(item.sla_due_at)}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p><span class={`inline-flex rounded-full border px-2 py-1 ${badgeTone(item.status)}`}>{fmtLabel(item.status)}</span></p>
                      <p class="mt-1">Completed: {fmtDate(item.completed_date)}</p>
                      <p class="mt-1">Verified: {fmtDateTime(item.verified_at)}</p>
                    </td>
                    <td class="px-3 py-3 align-top">
                      <div class="flex flex-wrap gap-2">
                        {#if item.status === "open" || item.status === "assigned"}
                          <button
                            type="button"
                            onclick={() => updateWorkOrderStatus(item, "in_progress")}
                            class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                          >
                            Start
                          </button>
                        {/if}
                        {#if item.status === "open" || item.status === "assigned" || item.status === "in_progress" || item.status === "on_hold"}
                          <button
                            type="button"
                            onclick={() => updateWorkOrderStatus(item, "completed")}
                            class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                          >
                            Complete
                          </button>
                        {/if}
                        {#if item.status === "completed"}
                          <button
                            type="button"
                            onclick={() => updateWorkOrderStatus(item, "verified")}
                            class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                          >
                            Verify
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>

        <div class="flex flex-col gap-3 border-t border-neutral-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-xs text-neutral-500">
            Showing <span class="font-medium text-neutral-700">{workOrderStart}-{workOrderEnd}</span> of <span class="font-medium text-neutral-700">{workOrderRows.length}</span>
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onclick={() => (workOrderPage = Math.max(1, workOrderPage - 1))}
              disabled={workOrderPage <= 1}
              class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            {#each pageNumbers(workOrderPage, workOrderTotalPages) as page}
              {#if page === "..."}
                <span class="px-1 text-xs text-neutral-400">...</span>
              {:else}
                <button
                  type="button"
                  onclick={() => (workOrderPage = page)}
                  class={`h-9 w-9 rounded-lg text-xs font-medium transition ${workOrderPage === page ? "bg-neutral-900 text-white" : "border border-neutral-200 text-neutral-700 hover:bg-neutral-50"}`}
                >
                  {page}
                </button>
              {/if}
            {/each}
            <button
              type="button"
              onclick={() => (workOrderPage = Math.min(workOrderTotalPages, workOrderPage + 1))}
              disabled={workOrderPage >= workOrderTotalPages}
              class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    {/if}

    {#if activeTab === "preventive"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Preventive Maintenance Plans</h2>
            <p class="mt-1 text-xs text-neutral-500">
              Scheduled maintenance plans with recurring triggers and auto-generated work orders.
            </p>
          </div>
          <button
            type="button"
            onclick={openPreventiveDrawer}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Add Maintenance Plan
          </button>
        </div>

        <div class="grid gap-3 md:grid-cols-3">
          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Search
            <input
              bind:value={preventiveSearch}
              class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm normal-case tracking-normal text-neutral-900"
              placeholder="Title, asset, technician..."
            />
          </label>

          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Facility
            <select bind:value={preventiveFacilityFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
              <option value="">All facilities</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
            Status
            <select bind:value={preventiveStatusFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
              <option value="">All statuses</option>
              {#each preventiveStatusOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Plan</th>
                <th class="px-3 py-2">Location</th>
                <th class="px-3 py-2">Schedule</th>
                <th class="px-3 py-2">Automation</th>
                <th class="px-3 py-2">Latest</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if filteredSchedules.length === 0}
                <tr>
                  <td colspan="5" class="px-3 py-6 text-center text-neutral-500">
                    No preventive plans match the current filters.
                  </td>
                </tr>
              {:else}
                {#each paginatedSchedules as item (item.id)}
                  <tr>
                    <td class="px-3 py-3 align-top">
                      <p class="font-medium text-neutral-900">{item.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {item.asset_component_name || "No linked asset"} • {fmtLabel(item.category)}
                      </p>
                      <div class="mt-2 flex flex-wrap gap-2">
                        <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.priority)}`}>{fmtLabel(item.priority)}</span>
                        <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>{fmtLabel(item.status)}</span>
                      </div>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p class="font-medium text-neutral-800">{item.facility_code || "--"}</p>
                      <p>{item.facility_space_label || "--"}</p>
                      <p>{item.property_name}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p>{fmtLabel(item.frequency)}</p>
                      <p class="mt-1">Next due: {fmtDate(item.next_due_date)}</p>
                      <p class="mt-1">Target: {fmtHours(item.sla_target_hours)}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p>{item.auto_create_work_orders ? "Auto-create enabled" : "Manual trigger"}</p>
                      <p class="mt-1">Generate {item.generate_days_before} day(s) early</p>
                      <p class="mt-1">Assigned: {item.assigned_to || "--"}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p>Last completed: {fmtDate(item.last_completed_date)}</p>
                      <p class="mt-1">Last generated: {fmtDate(item.last_generated_date)}</p>
                      <p class="mt-1">Last WO: {item.last_work_order ? `#${item.last_work_order}` : "--"}</p>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>

        <div class="flex flex-col gap-3 border-t border-neutral-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <p class="text-xs text-neutral-500">
            Showing <span class="font-medium text-neutral-700">{preventiveStart}-{preventiveEnd}</span> of <span class="font-medium text-neutral-700">{filteredSchedules.length}</span>
          </p>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onclick={() => (preventivePage = Math.max(1, preventivePage - 1))}
              disabled={preventivePage <= 1}
              class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Previous
            </button>
            {#each pageNumbers(preventivePage, preventiveTotalPages) as page}
              {#if page === "..."}
                <span class="px-1 text-xs text-neutral-400">...</span>
              {:else}
                <button
                  type="button"
                  onclick={() => (preventivePage = page)}
                  class={`h-9 w-9 rounded-lg text-xs font-medium transition ${preventivePage === page ? "bg-neutral-900 text-white" : "border border-neutral-200 text-neutral-700 hover:bg-neutral-50"}`}
                >
                  {page}
                </button>
              {/if}
            {/each}
            <button
              type="button"
              onclick={() => (preventivePage = Math.min(preventiveTotalPages, preventivePage + 1))}
              disabled={preventivePage >= preventiveTotalPages}
              class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </section>
    {/if}

    {#if activeTab === "predictive"}
      <div class="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Predictive Rules</h2>
              <p class="mt-1 text-xs text-neutral-500">
                IoT fault, offline, runtime-hour, and cycle-count triggers with automated work-order creation.
              </p>
            </div>
            <button
              type="button"
              onclick={openPredictiveDrawer}
              class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
            >
              Add Predictive Rule
            </button>
          </div>

          <div class="grid gap-3 md:grid-cols-3">
            <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Search
              <input
                bind:value={predictiveSearch}
                class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm normal-case tracking-normal text-neutral-900"
                placeholder="Rule, asset, facility..."
              />
            </label>

            <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Facility
              <select bind:value={predictiveFacilityFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
                <option value="">All facilities</option>
                {#each facilitiesLookup as facility}
                  <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
                {/each}
              </select>
            </label>

            <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Alert Status
              <select bind:value={predictiveAlertStatusFilter} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
                <option value="">All alerts</option>
                {#each predictiveAlertStatusOptions as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
            </label>
          </div>

          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-3 py-2">Rule</th>
                  <th class="px-3 py-2">Location</th>
                  <th class="px-3 py-2">Triggers</th>
                  <th class="px-3 py-2">Assignment</th>
                  <th class="px-3 py-2">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if filteredPredictiveRules.length === 0}
                  <tr>
                    <td colspan="5" class="px-3 py-6 text-center text-neutral-500">
                      No predictive rules match the current filters.
                    </td>
                  </tr>
                {:else}
                  {#each paginatedPredictiveRules as item (item.id)}
                    <tr>
                      <td class="px-3 py-3 align-top">
                        <p class="font-medium text-neutral-900">{item.title}</p>
                        <p class="mt-1 text-xs text-neutral-500">
                          {item.asset_component_name || "No linked asset"}
                        </p>
                        <div class="mt-2 flex flex-wrap gap-2">
                          <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.priority)}`}>{fmtLabel(item.priority)}</span>
                          <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.is_active ? "active" : "paused")}`}>{item.is_active ? "Active" : "Inactive"}</span>
                        </div>
                      </td>
                      <td class="px-3 py-3 align-top text-xs text-neutral-600">
                        <p class="font-medium text-neutral-800">{item.facility_code || "--"}</p>
                        <p>{item.facility_space_label || "--"}</p>
                        <p>{item.property_name}</p>
                      </td>
                      <td class="px-3 py-3 align-top text-xs text-neutral-600">
                        <p>Offline: {item.alert_on_offline ? "Yes" : "No"}</p>
                        <p class="mt-1">Fault: {item.alert_on_fault ? "Yes" : "No"}</p>
                        <p class="mt-1">Runtime: {item.runtime_hours_threshold || "--"}</p>
                        <p class="mt-1">Cycles: {item.cycle_threshold ?? "--"}</p>
                      </td>
                      <td class="px-3 py-3 align-top text-xs text-neutral-600">
                        <p>{item.assigned_to || "--"}</p>
                        <p class="mt-1">SLA: {fmtHours(item.sla_target_hours)}</p>
                        <p class="mt-1">Auto WO: {item.auto_create_work_order ? "Yes" : "No"}</p>
                      </td>
                      <td class="px-3 py-3 align-top">
                        <button
                          type="button"
                          onclick={() => evaluateRule(item.id)}
                          class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                        >
                          Evaluate
                        </button>
                      </td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>

          <div class="flex flex-col gap-3 border-t border-neutral-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-xs text-neutral-500">
              Showing <span class="font-medium text-neutral-700">{predictiveRuleStart}-{predictiveRuleEnd}</span> of <span class="font-medium text-neutral-700">{filteredPredictiveRules.length}</span>
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => (predictiveRulePage = Math.max(1, predictiveRulePage - 1))}
                disabled={predictiveRulePage <= 1}
                class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              {#each pageNumbers(predictiveRulePage, predictiveRuleTotalPages) as page}
                {#if page === "..."}
                  <span class="px-1 text-xs text-neutral-400">...</span>
                {:else}
                  <button
                    type="button"
                    onclick={() => (predictiveRulePage = page)}
                    class={`h-9 w-9 rounded-lg text-xs font-medium transition ${predictiveRulePage === page ? "bg-neutral-900 text-white" : "border border-neutral-200 text-neutral-700 hover:bg-neutral-50"}`}
                  >
                    {page}
                  </button>
                {/if}
              {/each}
              <button
                type="button"
                onclick={() => (predictiveRulePage = Math.min(predictiveRuleTotalPages, predictiveRulePage + 1))}
                disabled={predictiveRulePage >= predictiveRuleTotalPages}
                class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Predictive Alerts</h2>
            <p class="mt-1 text-xs text-neutral-500">
              Recent triggered alerts and linked maintenance responses.
            </p>
          </div>

          <div class="space-y-3">
            {#if filteredPredictiveAlerts.length === 0}
              <p class="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
                No predictive alerts match the current filters.
              </p>
            {:else}
              {#each paginatedPredictiveAlerts as item (item.id)}
                <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-neutral-900">{item.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {item.facility_code || "--"} • {item.asset_component_name || "No linked asset"}
                      </p>
                    </div>
                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.status)}`}>
                      {fmtLabel(item.status)}
                    </span>
                  </div>
                  <p class="mt-3 text-sm text-neutral-700">{item.message}</p>
                  <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-neutral-500">
                    <span class={`inline-flex rounded-full border px-2 py-1 ${badgeTone(item.priority)}`}>{fmtLabel(item.priority)}</span>
                    <span>{fmtLabel(item.trigger_type)}</span>
                    <span>Triggered {fmtDateTime(item.triggered_at)}</span>
                    <span>{item.work_order ? `WO #${item.work_order}` : "No work order yet"}</span>
                  </div>
                  <div class="mt-3 flex flex-wrap gap-2">
                    {#if item.status === "open"}
                      <button
                        type="button"
                        onclick={() => updateAlertStatus(item, "acknowledged")}
                        class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                      >
                        Acknowledge
                      </button>
                    {/if}
                    {#if item.status !== "resolved"}
                      <button
                        type="button"
                        onclick={() => updateAlertStatus(item, "resolved")}
                        class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
                      >
                        Resolve
                      </button>
                    {/if}
                  </div>
                </div>
              {/each}
            {/if}
          </div>

          <div class="flex flex-col gap-3 border-t border-neutral-100 pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-xs text-neutral-500">
              Showing <span class="font-medium text-neutral-700">{predictiveAlertStart}-{predictiveAlertEnd}</span> of <span class="font-medium text-neutral-700">{filteredPredictiveAlerts.length}</span>
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => (predictiveAlertPage = Math.max(1, predictiveAlertPage - 1))}
                disabled={predictiveAlertPage <= 1}
                class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>
              {#each pageNumbers(predictiveAlertPage, predictiveAlertTotalPages) as page}
                {#if page === "..."}
                  <span class="px-1 text-xs text-neutral-400">...</span>
                {:else}
                  <button
                    type="button"
                    onclick={() => (predictiveAlertPage = page)}
                    class={`h-9 w-9 rounded-lg text-xs font-medium transition ${predictiveAlertPage === page ? "bg-neutral-900 text-white" : "border border-neutral-200 text-neutral-700 hover:bg-neutral-50"}`}
                  >
                    {page}
                  </button>
                {/if}
              {/each}
              <button
                type="button"
                onclick={() => (predictiveAlertPage = Math.min(predictiveAlertTotalPages, predictiveAlertPage + 1))}
                disabled={predictiveAlertPage >= predictiveAlertTotalPages}
                class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 transition hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </section>
      </div>
    {/if}
  {/if}
</div>

{#if showWorkOrderDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeWorkOrderDrawer}
    tabindex="-1"
    aria-label="Close work order drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">
          {workOrderDrawerMode === "corrective" ? "Create Work Order" : "Create Maintenance Work Order"}
        </h2>
        <p class="mt-1 text-xs text-neutral-500">All maintenance forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeWorkOrderDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close work order drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="maintenance-work-order-form" class="space-y-5" onsubmit={handleWorkOrderCreate}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={workOrderForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Room / Space</span>
            <select bind:value={workOrderForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select room / space</option>
              {#each filteredSpacesFor(workOrderForm.facility) as space}
                <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Asset</span>
            <select bind:value={workOrderForm.asset_component} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select asset</option>
              {#each filteredAssetsFor(workOrderForm.facility) as asset}
                <option value={String(asset.id)}>{asset.component_id} - {asset.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Vendor</span>
            <select bind:value={workOrderForm.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select vendor</option>
              {#each vendorsLookup as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Work Order Title</span>
            <input bind:value={workOrderForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Restore chilled water circulation pump" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Description</span>
            <textarea bind:value={workOrderForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Describe the issue, repair scope, and access requirements."></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Category</span>
            <select bind:value={workOrderForm.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each categoryOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Priority</span>
            <select bind:value={workOrderForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each priorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Status</span>
            <select bind:value={workOrderForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each workOrderStatusOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Technician Assignment</span>
            <input bind:value={workOrderForm.assigned_to} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="A. Okafor" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Reported By</span>
            <input bind:value={workOrderForm.reported_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Security control room" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Due Date</span>
            <input type="date" bind:value={workOrderForm.due_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">SLA Target Hours</span>
            <input type="number" min="1" bind:value={workOrderForm.sla_target_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="8" />
          </label>

          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={workOrderForm.is_breakdown} class="rounded border-neutral-300" />
            Breakdown / emergency repair
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Estimated Cost</span>
            <input bind:value={workOrderForm.estimated_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="50000" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Root Cause</span>
            <textarea bind:value={workOrderForm.root_cause} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Document observed root cause for corrective work."></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Notes</span>
            <textarea bind:value={workOrderForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Permits, tenant coordination, or handoff notes."></textarea>
          </label>
        </section>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillWorkOrder} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeWorkOrderDrawer}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="maintenance-work-order-form"
        disabled={workOrderSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {workOrderSaving ? "Saving..." : "Save Work Order"}
      </button>
    </div>
  </aside>
{/if}

{#if showPreventiveDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closePreventiveDrawer}
    tabindex="-1"
    aria-label="Close preventive drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Create Preventive Plan</h2>
      <button
        type="button"
        onclick={closePreventiveDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close preventive drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="maintenance-preventive-form" class="space-y-5" onsubmit={handlePreventiveCreate}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={preventiveForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Room / Space</span>
            <select bind:value={preventiveForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select room / space</option>
              {#each filteredSpacesFor(preventiveForm.facility) as space}
                <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Asset</span>
            <select bind:value={preventiveForm.asset_component} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select asset</option>
              {#each filteredAssetsFor(preventiveForm.facility) as asset}
                <option value={String(asset.id)}>{asset.component_id} - {asset.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Vendor</span>
            <select bind:value={preventiveForm.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select vendor</option>
              {#each vendorsLookup as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Plan Title</span>
            <input bind:value={preventiveForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Monthly generator preventive service" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Description</span>
            <textarea bind:value={preventiveForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Include checklist scope, permit needs, and shutdown window."></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Category</span>
            <select bind:value={preventiveForm.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each categoryOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Frequency</span>
            <select bind:value={preventiveForm.frequency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each preventiveFrequencyOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Priority</span>
            <select bind:value={preventiveForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each priorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Status</span>
            <select bind:value={preventiveForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each preventiveStatusOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Technician Assignment</span>
            <input bind:value={preventiveForm.assigned_to} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Facilities Team B" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Next Due Date</span>
            <input type="date" bind:value={preventiveForm.next_due_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">SLA Target Hours</span>
            <input type="number" min="1" bind:value={preventiveForm.sla_target_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="24" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Generate Days Before Due</span>
            <input type="number" min="0" bind:value={preventiveForm.generate_days_before} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={preventiveForm.auto_create_work_orders} class="rounded border-neutral-300" />
            Auto-create work orders
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Estimated Cost</span>
            <input bind:value={preventiveForm.estimated_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="25000" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Notes</span>
            <textarea bind:value={preventiveForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Any shutdown windows, permit notes, or supplier SLAs."></textarea>
          </label>
        </section>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillPreventive} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closePreventiveDrawer}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="maintenance-preventive-form"
        disabled={preventiveSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {preventiveSaving ? "Saving..." : "Save Plan"}
      </button>
    </div>
  </aside>
{/if}

{#if showPredictiveDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closePredictiveDrawer}
    tabindex="-1"
    aria-label="Close predictive drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Create Predictive Rule</h2>
      <button
        type="button"
        onclick={closePredictiveDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close predictive drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="maintenance-predictive-form" class="space-y-5" onsubmit={handlePredictiveCreate}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={predictiveForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Room / Space</span>
            <select bind:value={predictiveForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select room / space</option>
              {#each filteredSpacesFor(predictiveForm.facility) as space}
                <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Asset</span>
            <select bind:value={predictiveForm.asset_component} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select asset</option>
              {#each filteredAssetsFor(predictiveForm.facility) as asset}
                <option value={String(asset.id)}>{asset.component_id} - {asset.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Rule Title</span>
            <input bind:value={predictiveForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Chiller runtime threshold breach" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Description</span>
            <textarea bind:value={predictiveForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Describe the trigger rationale and recommended intervention."></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Priority</span>
            <select bind:value={predictiveForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each priorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Technician Assignment</span>
            <input bind:value={predictiveForm.assigned_to} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Predictive Response Team" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">SLA Target Hours</span>
            <input type="number" min="1" bind:value={predictiveForm.sla_target_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="4" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Runtime Threshold (hours)</span>
            <input bind:value={predictiveForm.runtime_hours_threshold} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="5000" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Current Runtime Reading</span>
            <input bind:value={predictiveForm.runtime_hours_reading} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="5024" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Cycle Threshold</span>
            <input type="number" min="0" bind:value={predictiveForm.cycle_threshold} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="1200" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Current Cycle Reading</span>
            <input type="number" min="0" bind:value={predictiveForm.cycle_reading} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="1208" />
          </label>

          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={predictiveForm.alert_on_offline} class="rounded border-neutral-300" />
            Trigger on offline IoT status
          </label>

          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={predictiveForm.alert_on_fault} class="rounded border-neutral-300" />
            Trigger on fault IoT status
          </label>

          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={predictiveForm.auto_create_work_order} class="rounded border-neutral-300" />
            Auto-create work order
          </label>

          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700">
            <input type="checkbox" bind:checked={predictiveForm.is_active} class="rounded border-neutral-300" />
            Rule is active
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Notes</span>
            <textarea bind:value={predictiveForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Describe data source, expected response, and exception handling."></textarea>
          </label>
        </section>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillPredictive} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closePredictiveDrawer}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="maintenance-predictive-form"
        disabled={predictiveSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {predictiveSaving ? "Saving..." : "Save Rule"}
      </button>
    </div>
  </aside>
{/if}

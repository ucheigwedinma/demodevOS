<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    AssetComponentListItem, WorkOrderListItem, PreventiveScheduleListItem,
    InspectionListItem, Inspection, ServiceRequestListItem, MaintenanceVendorListItem,
    PropertyListItem, PaginatedResponse,
    MaintenanceCategory, WorkOrderPriority, WorkOrderStatus,
    AssetCategory, ConditionRating,
    PreventiveFrequency, PreventiveStatus,
    InspectionType, InspectionStatus, InspectionRating,
    InspectionRiskLevel, InspectionComplianceStatus,
    ServiceRequestStatus, VendorSpecialization,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // --- Tab state ---
  type Tab = "assets" | "corrective" | "preventive" | "inspections" | "requests" | "vendors";
  let activeTab = $state<Tab>("assets");

  const tabs: { key: Tab; label: string }[] = [
    { key: "assets", label: "Asset Register" },
    { key: "corrective", label: "Corrective" },
    { key: "preventive", label: "Preventive" },
    { key: "inspections", label: "Inspections" },
    { key: "requests", label: "Service Requests" },
    { key: "vendors", label: "Vendors" },
  ];

  // --- Shared state ---
  let properties = $state<PropertyListItem[]>([]);
  let assets = $state<AssetComponentListItem[]>([]);
  let vendors = $state<MaintenanceVendorListItem[]>([]);

  $effect(() => {
    api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" })
      .then((r) => { properties = r.results; }).catch(() => {});
  });

  // Lazy-load vendor + asset lookups when those tabs become relevant
  let vendorsLoaded = $state(false);
  let assetsLookupLoaded = $state(false);
  function ensureVendors() {
    if (vendorsLoaded) return;
    vendorsLoaded = true;
    api.get<PaginatedResponse<MaintenanceVendorListItem>>("/properties/maintenance/vendors/", { page_size: "200" })
      .then((r) => { vendors = r.results; }).catch(() => {});
  }
  function ensureAssets() {
    if (assetsLookupLoaded) return;
    assetsLookupLoaded = true;
    api.get<PaginatedResponse<AssetComponentListItem>>("/properties/maintenance/assets/", { page_size: "500" })
      .then((r) => { assets = r.results; }).catch(() => {});
  }

  // --- Shared helpers ---
  const PAGE_SIZE = 25;
  function formatCurrency(v: string | null): string { return v ? currency.formatCompact(v) : "\u2014"; }
  function formatDate(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  const categoryLabels: Record<string, string> = {
    plumbing: "Plumbing", electrical: "Electrical", hvac: "HVAC", structural: "Structural",
    mechanical: "Mechanical", cleaning: "Cleaning", landscaping: "Landscaping", security: "Security",
    painting: "Painting", fire_safety: "Fire & Safety", elevator: "Elevators",
    generator: "Generators", water_systems: "Water Systems", general: "General",
  };
  const priorityLabels: Record<string, string> = { low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };
  const priorityColors: Record<string, string> = {
    low: "bg-neutral-100 text-neutral-600", medium: "bg-blue-50 text-blue-700",
    high: "bg-amber-50 text-amber-700", urgent: "bg-red-50 text-red-700",
  };
  const conditionLabels: Record<string, string> = { excellent: "Excellent", good: "Good", fair: "Fair", poor: "Poor", critical: "Critical" };
  const conditionColors: Record<string, string> = {
    excellent: "bg-emerald-50 text-emerald-700", good: "bg-blue-50 text-blue-700",
    fair: "bg-amber-50 text-amber-700", poor: "bg-orange-50 text-orange-700",
    critical: "bg-red-50 text-red-700",
  };

  function statusDot(s: string): string {
    const map: Record<string, string> = {
      open: "bg-blue-500", assigned: "bg-violet-500", in_progress: "bg-amber-500",
      on_hold: "bg-neutral-400", completed: "bg-emerald-500", cancelled: "bg-red-400",
      scheduled: "bg-blue-500", active: "bg-emerald-500", paused: "bg-amber-500",
      acknowledged: "bg-violet-500", resolved: "bg-emerald-500", closed: "bg-neutral-400",
    };
    return map[s] ?? "bg-neutral-300";
  }
  function statusLabel(s: string): string {
    return s.split("_").map(w => w[0].toUpperCase() + w.slice(1)).join(" ");
  }

  // --- Shared search debounce ---
  let searchTimeout: ReturnType<typeof setTimeout>;
  function debounceSearch(setter: (v: string) => void) {
    return (e: Event) => {
      clearTimeout(searchTimeout);
      const val = (e.target as HTMLInputElement).value;
      searchTimeout = setTimeout(() => setter(val), 300);
    };
  }

  // =========================================================================
  //  1. ASSET REGISTER
  // =========================================================================
  let assetData = $state<AssetComponentListItem[]>([]);
  let assetCount = $state(0); let assetPage = $state(1); let assetLoading = $state(false);
  let assetSearch = $state(""); let assetCategory = $state(""); let assetCondition = $state(""); let assetProperty = $state("");
  let showAssetCreate = $state(false); let assetSaving = $state(false); let assetErrors = $state<Record<string, string[]>>({});
  const assetPages = $derived(Math.ceil(assetCount / PAGE_SIZE));
  let assetForm = $state({ property: 0, unit: null as number | null, component_id: "", name: "", category: "structural" as AssetCategory, description: "", location_description: "", manufacturer: "", model_number: "", serial_number: "", installation_date: "", warranty_expiry: "", expected_useful_life_years: "" as string, condition_rating: "good" as ConditionRating, is_active: true });

  async function fetchAssets() {
    assetLoading = true;
    try {
      const p: Record<string, string> = { page: String(assetPage) };
      if (assetSearch) p.search = assetSearch;
      if (assetCategory) p.category = assetCategory;
      if (assetCondition) p.condition_rating = assetCondition;
      if (assetProperty) p.property = assetProperty;
      const res = await api.get<PaginatedResponse<AssetComponentListItem>>("/properties/maintenance/assets/", p);
      assetData = res.results; assetCount = res.count;
    } catch { assetData = []; assetCount = 0; }
    assetLoading = false;
  }

  async function handleAssetCreate(e: Event) {
    e.preventDefault(); assetErrors = {}; assetSaving = true;
    try {
      await api.post("/properties/maintenance/assets/", {
        ...assetForm, property: assetForm.property || null, unit: assetForm.unit || null,
        installation_date: assetForm.installation_date || null, warranty_expiry: assetForm.warranty_expiry || null,
        expected_useful_life_years: assetForm.expected_useful_life_years ? Number(assetForm.expected_useful_life_years) : null,
      });
      toast.success("Asset created", `"${assetForm.name}" registered`);
      showAssetCreate = false; fetchAssets();
    } catch (err) {
      if (err instanceof ApiError) { assetErrors = err.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", "Could not create asset");
    }
    assetSaving = false;
  }

  // =========================================================================
  //  2. CORRECTIVE (Work Orders)
  // =========================================================================
  let woData = $state<WorkOrderListItem[]>([]);
  let woCount = $state(0); let woPage = $state(1); let woLoading = $state(false);
  let woSearch = $state(""); let woStatus = $state(""); let woPriority = $state(""); let woCategory = $state(""); let woProperty = $state("");
  let showWoCreate = $state(false); let woSaving = $state(false); let woErrors = $state<Record<string, string[]>>({});
  const woPages = $derived(Math.ceil(woCount / PAGE_SIZE));
  let woForm = $state({ property: 0, unit: null as number | null, asset_component: null as number | null, vendor: null as number | null, title: "", description: "", category: "general" as MaintenanceCategory, priority: "medium" as WorkOrderPriority, status: "open" as WorkOrderStatus, reported_by: "", assigned_to: "", due_date: "", estimated_cost: "" });

  async function fetchWorkOrders() {
    woLoading = true;
    try {
      const p: Record<string, string> = { page: String(woPage) };
      if (woSearch) p.search = woSearch;
      if (woStatus) p.status = woStatus;
      if (woPriority) p.priority = woPriority;
      if (woCategory) p.category = woCategory;
      if (woProperty) p.property = woProperty;
      const res = await api.get<PaginatedResponse<WorkOrderListItem>>("/properties/maintenance/work-orders/", p);
      woData = res.results; woCount = res.count;
    } catch { woData = []; woCount = 0; }
    woLoading = false;
  }

  async function handleWoCreate(e: Event) {
    e.preventDefault(); woErrors = {}; woSaving = true;
    try {
      await api.post("/properties/maintenance/work-orders/", {
        ...woForm, property: woForm.property || null, unit: woForm.unit || null,
        asset_component: woForm.asset_component || null, vendor: woForm.vendor || null,
        due_date: woForm.due_date || null, estimated_cost: woForm.estimated_cost || null,
      });
      toast.success("Work order created", `"${woForm.title}" logged`);
      showWoCreate = false; fetchWorkOrders();
    } catch (err) {
      if (err instanceof ApiError) { woErrors = err.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", "Could not create work order");
    }
    woSaving = false;
  }

  // =========================================================================
  //  3. PREVENTIVE MAINTENANCE
  // =========================================================================
  let pmData = $state<PreventiveScheduleListItem[]>([]);
  let pmCount = $state(0); let pmPage = $state(1); let pmLoading = $state(false);
  let pmSearch = $state(""); let pmStatus = $state(""); let pmFrequency = $state(""); let pmProperty = $state("");
  let showPmCreate = $state(false); let pmSaving = $state(false); let pmErrors = $state<Record<string, string[]>>({});
  const pmPages = $derived(Math.ceil(pmCount / PAGE_SIZE));
  let pmForm = $state({ property: 0, asset_component: null as number | null, vendor: null as number | null, title: "", description: "", category: "general" as MaintenanceCategory, frequency: "monthly" as PreventiveFrequency, assigned_to: "", next_due_date: "", estimated_cost: "", status: "active" as PreventiveStatus });

  const frequencyLabels: Record<string, string> = { daily: "Daily", weekly: "Weekly", biweekly: "Bi-Weekly", monthly: "Monthly", quarterly: "Quarterly", semi_annual: "Semi-Annual", annual: "Annual" };
  const pmStatusLabels: Record<string, string> = { active: "Active", paused: "Paused", completed: "Completed" };

  async function fetchPreventive() {
    pmLoading = true;
    try {
      const p: Record<string, string> = { page: String(pmPage) };
      if (pmSearch) p.search = pmSearch;
      if (pmStatus) p.status = pmStatus;
      if (pmFrequency) p.frequency = pmFrequency;
      if (pmProperty) p.property = pmProperty;
      const res = await api.get<PaginatedResponse<PreventiveScheduleListItem>>("/properties/maintenance/preventive/", p);
      pmData = res.results; pmCount = res.count;
    } catch { pmData = []; pmCount = 0; }
    pmLoading = false;
  }

  async function handlePmCreate(e: Event) {
    e.preventDefault(); pmErrors = {}; pmSaving = true;
    try {
      await api.post("/properties/maintenance/preventive/", {
        ...pmForm, property: pmForm.property || null,
        asset_component: pmForm.asset_component || null, vendor: pmForm.vendor || null,
        next_due_date: pmForm.next_due_date || null, estimated_cost: pmForm.estimated_cost || null,
      });
      toast.success("Schedule created", `"${pmForm.title}" added`);
      showPmCreate = false; fetchPreventive();
    } catch (err) {
      if (err instanceof ApiError) { pmErrors = err.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", "Could not create schedule");
    }
    pmSaving = false;
  }

  // =========================================================================
  //  4. INSPECTIONS
  // =========================================================================
  let inspData = $state<InspectionListItem[]>([]);
  let inspCount = $state(0); let inspPage = $state(1); let inspLoading = $state(false);
  let inspSearch = $state(""); let inspStatus = $state(""); let inspType = $state(""); let inspProperty = $state("");
  let showInspCreate = $state(false); let inspSaving = $state(false); let inspErrors = $state<Record<string, string[]>>({});
  const inspPages = $derived(Math.ceil(inspCount / PAGE_SIZE));
  let inspForm = $state({ property: 0, unit: null as number | null, asset_component: null as number | null, title: "", inspection_type: "routine" as InspectionType, status: "scheduled" as InspectionStatus, scheduled_date: "", inspector: "", risk_level: "" as InspectionRiskLevel | "", corrective_action_required: false, compliance_status: "" as InspectionComplianceStatus | "", expiry_date: "", findings: "" });
  let inspEditingId = $state<number | null>(null);
  let inspExpandedId = $state<number | null>(null);
  let inspDetail = $state<Inspection | null>(null);
  let inspDetailLoading = $state(false);
  let showInspView = $state(false);
  let inspViewItem = $state<Inspection | null>(null);
  let showInspDelete = $state(false);
  let inspDeleteId = $state<number | null>(null);
  let inspDeleteTitle = $state("");
  let inspDeleting = $state(false);

  const inspTypeLabels: Record<string, string> = { routine: "Routine", safety: "Safety", compliance: "Compliance", pre_handover: "Pre-Handover", post_incident: "Post-Incident", condition_survey: "Condition Survey", fire_safety: "Fire Safety", electrical: "Electrical", structural_integrity: "Structural Integrity", elevator_certification: "Elevator Certification", environmental_audit: "Environmental Audit", health_safety: "Health & Safety" };
  const inspStatusLabels: Record<string, string> = { scheduled: "Scheduled", in_progress: "In Progress", completed: "Completed", cancelled: "Cancelled" };
  const ratingLabels: Record<string, string> = { pass: "Pass", fail: "Fail", conditional: "Conditional" };
  const ratingColors: Record<string, string> = { pass: "bg-emerald-50 text-emerald-700", fail: "bg-red-50 text-red-700", conditional: "bg-amber-50 text-amber-700" };
  const riskLevelLabels: Record<string, string> = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };
  const riskLevelColors: Record<string, string> = { low: "bg-emerald-50 text-emerald-700", medium: "bg-amber-50 text-amber-700", high: "bg-orange-50 text-orange-700", critical: "bg-red-50 text-red-700" };
  const complianceStatusLabels: Record<string, string> = { compliant: "Compliant", non_compliant: "Non-Compliant", partially_compliant: "Partially Compliant", pending_review: "Pending Review" };
  const complianceStatusColors: Record<string, string> = { compliant: "bg-emerald-50 text-emerald-700", non_compliant: "bg-red-50 text-red-700", partially_compliant: "bg-amber-50 text-amber-700", pending_review: "bg-blue-50 text-blue-700" };

  async function fetchInspections() {
    inspLoading = true;
    try {
      const p: Record<string, string> = { page: String(inspPage) };
      if (inspSearch) p.search = inspSearch;
      if (inspStatus) p.status = inspStatus;
      if (inspType) p.inspection_type = inspType;
      if (inspProperty) p.property = inspProperty;
      const res = await api.get<PaginatedResponse<InspectionListItem>>("/properties/maintenance/inspections/", p);
      inspData = res.results; inspCount = res.count;
    } catch { inspData = []; inspCount = 0; }
    inspLoading = false;
  }

  async function handleInspSave(e: Event) {
    e.preventDefault(); inspErrors = {}; inspSaving = true;
    const payload = {
      ...inspForm, property: inspForm.property || null,
      unit: inspForm.unit || null, asset_component: inspForm.asset_component || null,
      scheduled_date: inspForm.scheduled_date || null,
      expiry_date: inspForm.expiry_date || null,
      risk_level: inspForm.risk_level || "",
      compliance_status: inspForm.compliance_status || "",
      findings: inspForm.findings || "",
    };
    try {
      if (inspEditingId) {
        await api.patch(`/properties/maintenance/inspections/${inspEditingId}/`, payload);
        toast.success("Inspection updated", `"${inspForm.title}" saved`);
      } else {
        await api.post("/properties/maintenance/inspections/", payload);
        toast.success("Inspection created", `"${inspForm.title}" scheduled`);
      }
      showInspCreate = false; inspEditingId = null; fetchInspections();
    } catch (err) {
      if (err instanceof ApiError) { inspErrors = err.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", inspEditingId ? "Could not update inspection" : "Could not create inspection");
    }
    inspSaving = false;
  }

  async function fetchInspDetail(id: number) {
    inspDetailLoading = true;
    try {
      inspDetail = await api.get<Inspection>(`/properties/maintenance/inspections/${id}/`);
    } catch { inspDetail = null; }
    inspDetailLoading = false;
  }

  function openInspEdit(item: InspectionListItem) {
    inspEditingId = item.id;
    inspForm = {
      property: item.property, unit: item.unit, asset_component: item.asset_component,
      title: item.title, inspection_type: item.inspection_type, status: item.status,
      scheduled_date: item.scheduled_date, inspector: item.inspector,
      risk_level: item.risk_level, corrective_action_required: item.corrective_action_required,
      compliance_status: item.compliance_status, expiry_date: item.expiry_date ?? "",
      findings: "",
    };
    // Fetch detail to get findings field
    api.get<Inspection>(`/properties/maintenance/inspections/${item.id}/`).then((d) => {
      inspForm.findings = d.findings;
    }).catch(() => {});
    inspErrors = {};
    showInspCreate = true;
  }

  async function openInspView(item: InspectionListItem) {
    showInspView = true; inspViewItem = null;
    try {
      inspViewItem = await api.get<Inspection>(`/properties/maintenance/inspections/${item.id}/`);
    } catch { toast.error("Error", "Could not load inspection details"); showInspView = false; }
  }

  async function handleInspDelete() {
    if (!inspDeleteId) return;
    inspDeleting = true;
    try {
      await api.delete(`/properties/maintenance/inspections/${inspDeleteId}/`);
      toast.success("Inspection deleted", `"${inspDeleteTitle}" removed`);
      showInspDelete = false; inspDeleteId = null; fetchInspections();
    } catch { toast.error("Error", "Could not delete inspection"); }
    inspDeleting = false;
  }

  // =========================================================================
  //  5. SERVICE REQUESTS
  // =========================================================================
  let srData = $state<ServiceRequestListItem[]>([]);
  let srCount = $state(0); let srPage = $state(1); let srLoading = $state(false);
  let srSearch = $state(""); let srStatus = $state(""); let srPriority = $state(""); let srProperty = $state("");
  let showSrCreate = $state(false); let srSaving = $state(false); let srErrors = $state<Record<string, string[]>>({});
  const srPages = $derived(Math.ceil(srCount / PAGE_SIZE));
  let srForm = $state({ property: 0, unit: null as number | null, title: "", description: "", category: "general" as MaintenanceCategory, priority: "medium" as WorkOrderPriority, requested_by: "", assigned_to: "" });

  const srStatusLabels: Record<string, string> = { open: "Open", acknowledged: "Acknowledged", in_progress: "In Progress", resolved: "Resolved", closed: "Closed" };

  async function fetchServiceRequests() {
    srLoading = true;
    try {
      const p: Record<string, string> = { page: String(srPage) };
      if (srSearch) p.search = srSearch;
      if (srStatus) p.status = srStatus;
      if (srPriority) p.priority = srPriority;
      if (srProperty) p.property = srProperty;
      const res = await api.get<PaginatedResponse<ServiceRequestListItem>>("/properties/maintenance/service-requests/", p);
      srData = res.results; srCount = res.count;
    } catch { srData = []; srCount = 0; }
    srLoading = false;
  }

  async function handleSrCreate(e: Event) {
    e.preventDefault(); srErrors = {}; srSaving = true;
    try {
      await api.post("/properties/maintenance/service-requests/", {
        ...srForm, property: srForm.property || null, unit: srForm.unit || null,
      });
      toast.success("Request created", `"${srForm.title}" submitted`);
      showSrCreate = false; fetchServiceRequests();
    } catch (err) {
      if (err instanceof ApiError) { srErrors = err.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", "Could not create service request");
    }
    srSaving = false;
  }

  // =========================================================================
  //  6. VENDORS
  // =========================================================================
  let vendorData = $state<MaintenanceVendorListItem[]>([]);
  let vendorCount = $state(0); let vendorPage = $state(1); let vendorLoading = $state(false);
  let vendorSearch = $state(""); let vendorSpec = $state(""); let vendorActive = $state("");
  let showVendorCreate = $state(false); let vendorSaving = $state(false); let vendorErrors = $state<Record<string, string[]>>({});
  const vendorPages = $derived(Math.ceil(vendorCount / PAGE_SIZE));
  let vendorForm = $state({ name: "", contact_person: "", email: "", phone: "", address: "", specialization: "general" as VendorSpecialization, license_number: "", license_expiry: "", insurance_expiry: "", rating: "", hourly_rate: "", is_active: true, notes: "" });

  async function fetchVendors() {
    vendorLoading = true;
    try {
      const p: Record<string, string> = { page: String(vendorPage) };
      if (vendorSearch) p.search = vendorSearch;
      if (vendorSpec) p.specialization = vendorSpec;
      if (vendorActive) p.is_active = vendorActive;
      const res = await api.get<PaginatedResponse<MaintenanceVendorListItem>>("/properties/maintenance/vendors/", p);
      vendorData = res.results; vendorCount = res.count;
    } catch { vendorData = []; vendorCount = 0; }
    vendorLoading = false;
  }

  async function handleVendorCreate(e: Event) {
    e.preventDefault(); vendorErrors = {}; vendorSaving = true;
    try {
      await api.post("/properties/maintenance/vendors/", {
        ...vendorForm,
        license_expiry: vendorForm.license_expiry || null,
        insurance_expiry: vendorForm.insurance_expiry || null,
        rating: vendorForm.rating || null,
        hourly_rate: vendorForm.hourly_rate || null,
      });
      toast.success("Vendor created", `"${vendorForm.name}" added`);
      showVendorCreate = false; fetchVendors(); vendorsLoaded = false;
    } catch (err) {
      if (err instanceof ApiError) { vendorErrors = err.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", "Could not create vendor");
    }
    vendorSaving = false;
  }

  // --- Fetch on tab change ---
  $effect(() => {
    if (activeTab === "assets") { void assetSearch; void assetCategory; void assetCondition; void assetProperty; void assetPage; fetchAssets(); }
  });
  $effect(() => {
    if (activeTab === "corrective") { void woSearch; void woStatus; void woPriority; void woCategory; void woProperty; void woPage; fetchWorkOrders(); ensureVendors(); ensureAssets(); }
  });
  $effect(() => {
    if (activeTab === "preventive") { void pmSearch; void pmStatus; void pmFrequency; void pmProperty; void pmPage; fetchPreventive(); ensureVendors(); ensureAssets(); }
  });
  $effect(() => {
    if (activeTab === "inspections") { void inspSearch; void inspStatus; void inspType; void inspProperty; void inspPage; fetchInspections(); ensureAssets(); }
  });
  $effect(() => {
    if (activeTab === "requests") { void srSearch; void srStatus; void srPriority; void srProperty; void srPage; fetchServiceRequests(); }
  });
  $effect(() => {
    if (activeTab === "vendors") { void vendorSearch; void vendorSpec; void vendorActive; void vendorPage; fetchVendors(); }
  });

  function fieldErr(errs: Record<string, string[]>, f: string) { return errs[f]?.[0] ?? ""; }

  // Shared select classes
  const selectCls = "px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent";
  const inputCls = "w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent";
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Facilities & Maintenance</h1>
    <p class="text-sm text-neutral-400 mt-1">Asset register, work orders, schedules, inspections, service requests & vendors</p>
  </div>

  <!-- Tab Navigation -->
  <div class="border-b border-neutral-200">
    <nav class="flex gap-0 -mb-px">
      {#each tabs as t}
        <button
          onclick={() => { activeTab = t.key; }}
          class="px-5 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                 {activeTab === t.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600 hover:border-neutral-300'}"
        >
          {t.label}
        </button>
      {/each}
    </nav>
  </div>

  <!-- ================================================================== -->
  <!--  TAB 1: ASSET REGISTER                                             -->
  <!-- ================================================================== -->
  {#if activeTab === "assets"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">{assetCount} asset{assetCount !== 1 ? 's' : ''} registered</p>
      <button onclick={() => { assetForm = { property: 0, unit: null, component_id: "", name: "", category: "structural", description: "", location_description: "", manufacturer: "", model_number: "", serial_number: "", installation_date: "", warranty_expiry: "", expected_useful_life_years: "", condition_rating: "good", is_active: true }; assetErrors = {}; showAssetCreate = true; }} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Asset</button>
    </div>

    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search assets..." oninput={debounceSearch((v) => { assetSearch = v; assetPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={assetCategory} onchange={() => (assetPage = 1)} class={selectCls}>
        <option value="">All Categories</option>
        {#each ["structural","electrical","mechanical","plumbing","hvac","fire_safety","elevator","generator","water_systems","security"] as c}<option value={c}>{categoryLabels[c]}</option>{/each}
      </select>
      <select bind:value={assetCondition} onchange={() => (assetPage = 1)} class={selectCls}>
        <option value="">All Conditions</option>
        {#each Object.entries(conditionLabels) as [v, l]}<option value={v}>{l}</option>{/each}
      </select>
      <select bind:value={assetProperty} onchange={() => (assetPage = 1)} class={selectCls}>
        <option value="">All Properties</option>
        {#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if assetLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading assets...</p></div>
      {:else if assetData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No assets found</p><p class="mt-1 text-sm text-neutral-400">Register your first asset component to get started.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Component ID</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Category</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Condition</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Manufacturer</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Warranty</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Installed</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each assetData as a}
              {@const warrantyExpired = a.warranty_expiry && new Date(a.warranty_expiry) < new Date()}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 font-mono text-xs text-neutral-600">{a.component_id}</td>
                <td class="px-5 py-4"><span class="font-medium text-neutral-900">{a.name}</span>{#if a.unit_number}<span class="text-xs text-neutral-400 ml-1.5">Unit {a.unit_number}</span>{/if}</td>
                <td class="px-5 py-4 text-neutral-500 max-w-[140px] truncate">{a.property_name}</td>
                <td class="px-5 py-4 text-neutral-500">{categoryLabels[a.category] ?? a.category}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {conditionColors[a.condition_rating] ?? 'bg-neutral-100 text-neutral-600'}">{conditionLabels[a.condition_rating] ?? a.condition_rating}</span></td>
                <td class="px-5 py-4 text-neutral-500">{a.manufacturer || "\u2014"}</td>
                <td class="px-5 py-4 text-sm tabular-nums {warrantyExpired ? 'text-red-600 font-medium' : 'text-neutral-500'}">{formatDate(a.warranty_expiry)}</td>
                <td class="px-5 py-4 text-neutral-500 tabular-nums">{formatDate(a.installation_date)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    {#if assetPages > 1}
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{(assetPage - 1) * PAGE_SIZE + 1}–{Math.min(assetPage * PAGE_SIZE, assetCount)}</span> of <span class="font-medium text-neutral-600">{assetCount}</span></p>
        <div class="flex items-center gap-1">
          <button onclick={() => assetPage--} disabled={assetPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg></button>
          <button onclick={() => assetPage++} disabled={assetPage >= assetPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ================================================================== -->
  <!--  TAB 2: CORRECTIVE MAINTENANCE (Work Orders)                       -->
  <!-- ================================================================== -->
  {#if activeTab === "corrective"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">{woCount} work order{woCount !== 1 ? 's' : ''}</p>
      <button onclick={() => { woForm = { property: 0, unit: null, asset_component: null, vendor: null, title: "", description: "", category: "general", priority: "medium", status: "open", reported_by: "", assigned_to: "", due_date: "", estimated_cost: "" }; woErrors = {}; showWoCreate = true; }} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Work Order</button>
    </div>

    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search work orders..." oninput={debounceSearch((v) => { woSearch = v; woPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={woStatus} onchange={() => (woPage = 1)} class={selectCls}><option value="">All Statuses</option><option value="open">Open</option><option value="assigned">Assigned</option><option value="in_progress">In Progress</option><option value="on_hold">On Hold</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select>
      <select bind:value={woPriority} onchange={() => (woPage = 1)} class={selectCls}><option value="">All Priorities</option>{#each Object.entries(priorityLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={woCategory} onchange={() => (woPage = 1)} class={selectCls}><option value="">All Categories</option>{#each Object.entries(categoryLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={woProperty} onchange={() => (woPage = 1)} class={selectCls}><option value="">All Properties</option>{#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}</select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if woLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading work orders...</p></div>
      {:else if woData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No work orders found</p><p class="mt-1 text-sm text-neutral-400">Create your first reactive maintenance work order.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Category</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Priority</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Assigned To</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Due Date</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Est. Cost</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each woData as wo}
              {@const overdue = wo.due_date && wo.status !== "completed" && wo.status !== "cancelled" && new Date(wo.due_date) < new Date()}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4"><span class="font-medium text-neutral-900">{wo.title}</span>{#if wo.unit_number}<span class="text-xs text-neutral-400 ml-1.5">Unit {wo.unit_number}</span>{/if}</td>
                <td class="px-5 py-4 text-neutral-500 max-w-[140px] truncate">{wo.property_name}</td>
                <td class="px-5 py-4 text-neutral-500">{categoryLabels[wo.category] ?? wo.category}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {priorityColors[wo.priority] ?? 'bg-neutral-100 text-neutral-600'}">{priorityLabels[wo.priority] ?? wo.priority}</span></td>
                <td class="px-5 py-4"><span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-700"><span class="w-1.5 h-1.5 rounded-full {statusDot(wo.status)}"></span>{statusLabel(wo.status)}</span></td>
                <td class="px-5 py-4 text-neutral-500">{wo.assigned_to || "\u2014"}</td>
                <td class="px-5 py-4 text-sm tabular-nums {overdue ? 'text-red-600 font-medium' : 'text-neutral-500'}">{formatDate(wo.due_date)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(wo.estimated_cost)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    {#if woPages > 1}
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{(woPage - 1) * PAGE_SIZE + 1}–{Math.min(woPage * PAGE_SIZE, woCount)}</span> of <span class="font-medium text-neutral-600">{woCount}</span></p>
        <div class="flex items-center gap-1">
          <button onclick={() => woPage--} disabled={woPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg></button>
          <button onclick={() => woPage++} disabled={woPage >= woPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ================================================================== -->
  <!--  TAB 3: PREVENTIVE MAINTENANCE                                     -->
  <!-- ================================================================== -->
  {#if activeTab === "preventive"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">{pmCount} schedule{pmCount !== 1 ? 's' : ''}</p>
      <button onclick={() => { pmForm = { property: 0, asset_component: null, vendor: null, title: "", description: "", category: "general", frequency: "monthly", assigned_to: "", next_due_date: "", estimated_cost: "", status: "active" }; pmErrors = {}; showPmCreate = true; }} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Schedule</button>
    </div>

    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search schedules..." oninput={debounceSearch((v) => { pmSearch = v; pmPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={pmStatus} onchange={() => (pmPage = 1)} class={selectCls}><option value="">All Statuses</option>{#each Object.entries(pmStatusLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={pmFrequency} onchange={() => (pmPage = 1)} class={selectCls}><option value="">All Frequencies</option>{#each Object.entries(frequencyLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={pmProperty} onchange={() => (pmPage = 1)} class={selectCls}><option value="">All Properties</option>{#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}</select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if pmLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading schedules...</p></div>
      {:else if pmData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No preventive schedules found</p><p class="mt-1 text-sm text-neutral-400">Create a planned maintenance schedule to get started.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Category</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Frequency</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Assigned To</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Next Due</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Est. Cost</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each pmData as pm}
              {@const overdue = pm.status === "active" && pm.next_due_date && new Date(pm.next_due_date) < new Date()}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4"><span class="font-medium text-neutral-900">{pm.title}</span>{#if pm.asset_component_name}<span class="text-xs text-neutral-400 ml-1.5">{pm.asset_component_name}</span>{/if}</td>
                <td class="px-5 py-4 text-neutral-500 max-w-[140px] truncate">{pm.property_name}</td>
                <td class="px-5 py-4 text-neutral-500">{categoryLabels[pm.category] ?? pm.category}</td>
                <td class="px-5 py-4 text-neutral-500">{frequencyLabels[pm.frequency] ?? pm.frequency}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-700"><span class="w-1.5 h-1.5 rounded-full {statusDot(pm.status)}"></span>{pmStatusLabels[pm.status] ?? pm.status}</span></td>
                <td class="px-5 py-4 text-neutral-500">{pm.assigned_to || "\u2014"}</td>
                <td class="px-5 py-4 text-sm tabular-nums {overdue ? 'text-red-600 font-medium' : 'text-neutral-500'}">{formatDate(pm.next_due_date)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(pm.estimated_cost)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    {#if pmPages > 1}
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{(pmPage - 1) * PAGE_SIZE + 1}–{Math.min(pmPage * PAGE_SIZE, pmCount)}</span> of <span class="font-medium text-neutral-600">{pmCount}</span></p>
        <div class="flex items-center gap-1">
          <button onclick={() => pmPage--} disabled={pmPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg></button>
          <button onclick={() => pmPage++} disabled={pmPage >= pmPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ================================================================== -->
  <!--  TAB 4: INSPECTIONS                                                -->
  <!-- ================================================================== -->
  {#if activeTab === "inspections"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">{inspCount} inspection{inspCount !== 1 ? 's' : ''}</p>
      <button onclick={() => { inspEditingId = null; inspForm = { property: 0, unit: null, asset_component: null, title: "", inspection_type: "routine", status: "scheduled", scheduled_date: "", inspector: "", risk_level: "", corrective_action_required: false, compliance_status: "", expiry_date: "", findings: "" }; inspErrors = {}; showInspCreate = true; }} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Inspection</button>
    </div>

    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search inspections..." oninput={debounceSearch((v) => { inspSearch = v; inspPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={inspStatus} onchange={() => (inspPage = 1)} class={selectCls}><option value="">All Statuses</option>{#each Object.entries(inspStatusLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={inspType} onchange={() => (inspPage = 1)} class={selectCls}><option value="">All Types</option>{#each Object.entries(inspTypeLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={inspProperty} onchange={() => (inspPage = 1)} class={selectCls}><option value="">All Properties</option>{#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}</select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if inspLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading inspections...</p></div>
      {:else if inspData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No inspections found</p><p class="mt-1 text-sm text-neutral-400">Schedule your first inspection to begin.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="w-8 px-2"></th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Inspector</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Scheduled</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Risk</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Compliance</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each inspData as ins}
              <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => { if (inspExpandedId === ins.id) { inspExpandedId = null; inspDetail = null; } else { inspExpandedId = ins.id; fetchInspDetail(ins.id); } }}>
                <td class="px-2 py-4 text-neutral-400"><svg class="w-4 h-4 transition-transform {inspExpandedId === ins.id ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></td>
                <td class="px-5 py-4"><span class="font-medium text-neutral-900">{ins.title}</span>{#if ins.asset_component_name}<span class="text-xs text-neutral-400 ml-1.5">{ins.asset_component_name}</span>{/if}</td>
                <td class="px-5 py-4 text-neutral-500 max-w-[140px] truncate">{ins.property_name}</td>
                <td class="px-5 py-4 text-neutral-500">{inspTypeLabels[ins.inspection_type] ?? ins.inspection_type}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-700"><span class="w-1.5 h-1.5 rounded-full {statusDot(ins.status)}"></span>{inspStatusLabels[ins.status] ?? ins.status}</span></td>
                <td class="px-5 py-4 text-neutral-500">{ins.inspector || "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-500 tabular-nums">{formatDate(ins.scheduled_date)}</td>
                <td class="px-5 py-4">{#if ins.risk_level}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {riskLevelColors[ins.risk_level] ?? 'bg-neutral-100 text-neutral-600'}">{riskLevelLabels[ins.risk_level] ?? ins.risk_level}</span>{:else}<span class="text-neutral-300">&mdash;</span>{/if}</td>
                <td class="px-5 py-4">{#if ins.compliance_status}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {complianceStatusColors[ins.compliance_status] ?? 'bg-neutral-100 text-neutral-600'}">{complianceStatusLabels[ins.compliance_status] ?? ins.compliance_status}</span>{:else}<span class="text-neutral-300">&mdash;</span>{/if}</td>
                <td class="px-5 py-4">
                  <div class="flex items-center gap-1">
                    <button onclick={(e: MouseEvent) => { e.stopPropagation(); openInspView(ins); }} class="p-1.5 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors" title="View"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg></button>
                    <button onclick={(e: MouseEvent) => { e.stopPropagation(); openInspEdit(ins); }} class="p-1.5 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors" title="Edit"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" /></svg></button>
                    <button onclick={(e: MouseEvent) => { e.stopPropagation(); inspDeleteId = ins.id; inspDeleteTitle = ins.title; showInspDelete = true; }} class="p-1.5 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Delete"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg></button>
                  </div>
                </td>
              </tr>
              {#if inspExpandedId === ins.id}
                <tr>
                  <td colspan="10" class="bg-neutral-50 px-8 py-5">
                    {#if inspDetailLoading}
                      <div class="flex items-center gap-2 text-sm text-neutral-400"><div class="w-4 h-4 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div> Loading details...</div>
                    {:else if inspDetail}
                      <div class="grid grid-cols-4 gap-4 text-sm">
                        <div><span class="text-neutral-400 text-xs">Rating</span><p class="font-medium text-neutral-900 mt-0.5">{#if inspDetail.rating}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {ratingColors[inspDetail.rating] ?? 'bg-neutral-100 text-neutral-600'}">{ratingLabels[inspDetail.rating] ?? inspDetail.rating}</span>{:else}&mdash;{/if}</p></div>
                        <div><span class="text-neutral-400 text-xs">Risk Level</span><p class="font-medium text-neutral-900 mt-0.5">{#if inspDetail.risk_level}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {riskLevelColors[inspDetail.risk_level] ?? 'bg-neutral-100 text-neutral-600'}">{riskLevelLabels[inspDetail.risk_level] ?? inspDetail.risk_level}</span>{:else}&mdash;{/if}</p></div>
                        <div><span class="text-neutral-400 text-xs">Compliance Status</span><p class="font-medium text-neutral-900 mt-0.5">{#if inspDetail.compliance_status}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {complianceStatusColors[inspDetail.compliance_status] ?? 'bg-neutral-100 text-neutral-600'}">{complianceStatusLabels[inspDetail.compliance_status] ?? inspDetail.compliance_status}</span>{:else}&mdash;{/if}</p></div>
                        <div><span class="text-neutral-400 text-xs">Expiry Date</span><p class="font-medium text-neutral-900 mt-0.5">{formatDate(inspDetail.expiry_date ?? null)}</p></div>
                        <div><span class="text-neutral-400 text-xs">Corrective Action</span><p class="font-medium text-neutral-900 mt-0.5">{inspDetail.corrective_action_required ? "Required" : "Not Required"}</p></div>
                        <div><span class="text-neutral-400 text-xs">Follow-up</span><p class="font-medium text-neutral-900 mt-0.5">{inspDetail.follow_up_required ? "Required" : "Not Required"}</p></div>
                        <div><span class="text-neutral-400 text-xs">Completed</span><p class="font-medium text-neutral-900 mt-0.5">{formatDate(inspDetail.completed_date)}</p></div>
                        <div><span class="text-neutral-400 text-xs">Unit</span><p class="font-medium text-neutral-900 mt-0.5">{inspDetail.unit_number ?? "\u2014"}</p></div>
                        {#if inspDetail.findings}<div class="col-span-4"><span class="text-neutral-400 text-xs">Findings</span><p class="font-medium text-neutral-900 mt-0.5 whitespace-pre-wrap">{inspDetail.findings}</p></div>{/if}
                        {#if inspDetail.follow_up_notes}<div class="col-span-4"><span class="text-neutral-400 text-xs">Follow-up Notes</span><p class="font-medium text-neutral-900 mt-0.5 whitespace-pre-wrap">{inspDetail.follow_up_notes}</p></div>{/if}
                        {#if inspDetail.notes}<div class="col-span-4"><span class="text-neutral-400 text-xs">Notes</span><p class="font-medium text-neutral-900 mt-0.5 whitespace-pre-wrap">{inspDetail.notes}</p></div>{/if}
                      </div>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    {#if inspPages > 1}
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{(inspPage - 1) * PAGE_SIZE + 1}–{Math.min(inspPage * PAGE_SIZE, inspCount)}</span> of <span class="font-medium text-neutral-600">{inspCount}</span></p>
        <div class="flex items-center gap-1">
          <button onclick={() => inspPage--} disabled={inspPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg></button>
          <button onclick={() => inspPage++} disabled={inspPage >= inspPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ================================================================== -->
  <!--  TAB 5: SERVICE REQUESTS                                           -->
  <!-- ================================================================== -->
  {#if activeTab === "requests"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">{srCount} service request{srCount !== 1 ? 's' : ''}</p>
      <button onclick={() => { srForm = { property: 0, unit: null, title: "", description: "", category: "general", priority: "medium", requested_by: "", assigned_to: "" }; srErrors = {}; showSrCreate = true; }} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Request</button>
    </div>

    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search requests..." oninput={debounceSearch((v) => { srSearch = v; srPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={srStatus} onchange={() => (srPage = 1)} class={selectCls}><option value="">All Statuses</option>{#each Object.entries(srStatusLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={srPriority} onchange={() => (srPage = 1)} class={selectCls}><option value="">All Priorities</option>{#each Object.entries(priorityLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={srProperty} onchange={() => (srPage = 1)} class={selectCls}><option value="">All Properties</option>{#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}</select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if srLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading requests...</p></div>
      {:else if srData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No service requests found</p><p class="mt-1 text-sm text-neutral-400">Submit your first service request.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Category</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Priority</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Requested By</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Assigned To</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each srData as sr}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4"><span class="font-medium text-neutral-900">{sr.title}</span>{#if sr.unit_number}<span class="text-xs text-neutral-400 ml-1.5">Unit {sr.unit_number}</span>{/if}{#if sr.work_order}<span class="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-50 text-violet-600">WO linked</span>{/if}</td>
                <td class="px-5 py-4 text-neutral-500 max-w-[140px] truncate">{sr.property_name}</td>
                <td class="px-5 py-4 text-neutral-500">{categoryLabels[sr.category] ?? sr.category}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {priorityColors[sr.priority] ?? 'bg-neutral-100 text-neutral-600'}">{priorityLabels[sr.priority] ?? sr.priority}</span></td>
                <td class="px-5 py-4"><span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-700"><span class="w-1.5 h-1.5 rounded-full {statusDot(sr.status)}"></span>{srStatusLabels[sr.status] ?? sr.status}</span></td>
                <td class="px-5 py-4 text-neutral-500">{sr.requested_by || "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-500">{sr.assigned_to || "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-500 tabular-nums">{formatDate(sr.requested_date)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    {#if srPages > 1}
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{(srPage - 1) * PAGE_SIZE + 1}–{Math.min(srPage * PAGE_SIZE, srCount)}</span> of <span class="font-medium text-neutral-600">{srCount}</span></p>
        <div class="flex items-center gap-1">
          <button onclick={() => srPage--} disabled={srPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg></button>
          <button onclick={() => srPage++} disabled={srPage >= srPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></button>
        </div>
      </div>
    {/if}
  {/if}

  <!-- ================================================================== -->
  <!--  TAB 6: VENDORS                                                    -->
  <!-- ================================================================== -->
  {#if activeTab === "vendors"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">{vendorCount} vendor{vendorCount !== 1 ? 's' : ''}</p>
      <button onclick={() => { vendorForm = { name: "", contact_person: "", email: "", phone: "", address: "", specialization: "general", license_number: "", license_expiry: "", insurance_expiry: "", rating: "", hourly_rate: "", is_active: true, notes: "" }; vendorErrors = {}; showVendorCreate = true; }} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Vendor</button>
    </div>

    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[200px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search vendors..." oninput={debounceSearch((v) => { vendorSearch = v; vendorPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={vendorSpec} onchange={() => (vendorPage = 1)} class={selectCls}><option value="">All Specializations</option>{#each Object.entries(categoryLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select>
      <select bind:value={vendorActive} onchange={() => (vendorPage = 1)} class={selectCls}><option value="">All</option><option value="true">Active</option><option value="false">Inactive</option></select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if vendorLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading vendors...</p></div>
      {:else if vendorData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No vendors found</p><p class="mt-1 text-sm text-neutral-400">Add your first maintenance vendor to begin.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Specialization</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Contact</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">License</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Insurance</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Rating</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Rate/hr</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Work Orders</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each vendorData as v}
              {@const licenseExpired = v.license_expiry && new Date(v.license_expiry) < new Date()}
              {@const insuranceExpired = v.insurance_expiry && new Date(v.insurance_expiry) < new Date()}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4"><span class="font-medium text-neutral-900">{v.name}</span>{#if !v.is_active}<span class="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-neutral-100 text-neutral-500">Inactive</span>{/if}</td>
                <td class="px-5 py-4 text-neutral-500">{categoryLabels[v.specialization] ?? v.specialization}</td>
                <td class="px-5 py-4"><div class="text-neutral-900 text-xs">{v.contact_person || "\u2014"}</div><div class="text-neutral-400 text-xs">{v.email || ""}</div></td>
                <td class="px-5 py-4 text-sm tabular-nums {licenseExpired ? 'text-red-600 font-medium' : 'text-neutral-500'}">{v.license_number ? `${v.license_number}` : "\u2014"}{#if v.license_expiry}<br/><span class="text-xs">{formatDate(v.license_expiry)}</span>{/if}</td>
                <td class="px-5 py-4 text-sm tabular-nums {insuranceExpired ? 'text-red-600 font-medium' : 'text-neutral-500'}">{formatDate(v.insurance_expiry)}</td>
                <td class="px-5 py-4">{#if v.rating}<span class="text-neutral-900 font-medium">{Number(v.rating).toFixed(1)}</span><span class="text-neutral-400 text-xs">/5</span>{:else}<span class="text-neutral-300">&mdash;</span>{/if}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{v.hourly_rate ? formatCurrency(v.hourly_rate) : "\u2014"}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{v.work_order_count}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>

    {#if vendorPages > 1}
      <div class="flex items-center justify-between">
        <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{(vendorPage - 1) * PAGE_SIZE + 1}–{Math.min(vendorPage * PAGE_SIZE, vendorCount)}</span> of <span class="font-medium text-neutral-600">{vendorCount}</span></p>
        <div class="flex items-center gap-1">
          <button onclick={() => vendorPage--} disabled={vendorPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg></button>
          <button onclick={() => vendorPage++} disabled={vendorPage >= vendorPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg></button>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- ====================================================================== -->
<!--  CREATE MODALS                                                         -->
<!-- ====================================================================== -->

<!-- Asset Create -->
{#if showAssetCreate}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showAssetCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">New Asset Component</h2>
        <button onclick={() => (showAssetCreate = false)} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <form onsubmit={handleAssetCreate} class="overflow-y-auto p-6 space-y-5">
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Component ID</label><input bind:value={assetForm.component_id} placeholder="e.g. AST-0001" class={inputCls} />{#if fieldErr(assetErrors,"component_id")}<p class="mt-1 text-xs text-red-500">{fieldErr(assetErrors,"component_id")}</p>{/if}</div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Name</label><input bind:value={assetForm.name} placeholder="e.g. Main Elevator" class={inputCls} />{#if fieldErr(assetErrors,"name")}<p class="mt-1 text-xs text-red-500">{fieldErr(assetErrors,"name")}</p>{/if}</div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Property</label><select bind:value={assetForm.property} class={inputCls}><option value={0} disabled>Select property</option>{#each properties as p}<option value={p.id}>{p.name}</option>{/each}</select>{#if fieldErr(assetErrors,"property")}<p class="mt-1 text-xs text-red-500">{fieldErr(assetErrors,"property")}</p>{/if}</div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Category</label><select bind:value={assetForm.category} class={inputCls}>{#each ["structural","electrical","mechanical","plumbing","hvac","fire_safety","elevator","generator","water_systems","security"] as c}<option value={c}>{categoryLabels[c]}</option>{/each}</select></div>
        </div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Condition</label><select bind:value={assetForm.condition_rating} class={inputCls}>{#each Object.entries(conditionLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
        <div class="grid grid-cols-3 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Manufacturer</label><input bind:value={assetForm.manufacturer} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Model #</label><input bind:value={assetForm.model_number} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Serial #</label><input bind:value={assetForm.serial_number} class={inputCls} /></div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Installed</label><DateInput bind:value={assetForm.installation_date} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Warranty Expiry</label><DateInput bind:value={assetForm.warranty_expiry} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Useful Life (yrs)</label><input bind:value={assetForm.expected_useful_life_years} placeholder="e.g. 15" class={inputCls} /></div>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={assetSaving} class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{assetSaving ? "Saving..." : "Create Asset"}</button>
          <button type="button" onclick={() => (showAssetCreate = false)} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Work Order Create -->
{#if showWoCreate}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showWoCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">New Work Order</h2>
        <button onclick={() => (showWoCreate = false)} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <form onsubmit={handleWoCreate} class="overflow-y-auto p-6 space-y-5">
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Property</label><select bind:value={woForm.property} class={inputCls}><option value={0} disabled>Select property</option>{#each properties as p}<option value={p.id}>{p.name}</option>{/each}</select>{#if fieldErr(woErrors,"property")}<p class="mt-1 text-xs text-red-500">{fieldErr(woErrors,"property")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Title</label><input bind:value={woForm.title} placeholder="e.g. Leaking pipe in Unit 3B" class={inputCls} />{#if fieldErr(woErrors,"title")}<p class="mt-1 text-xs text-red-500">{fieldErr(woErrors,"title")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Description</label><textarea bind:value={woForm.description} rows={3} class="{inputCls} resize-none" placeholder="Describe the issue..."></textarea></div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Category</label><select bind:value={woForm.category} class={inputCls}>{#each Object.entries(categoryLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Priority</label><select bind:value={woForm.priority} class={inputCls}>{#each Object.entries(priorityLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Vendor</label><select bind:value={woForm.vendor} class={inputCls}><option value={null}>None</option>{#each vendors as v}<option value={v.id}>{v.name}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Asset</label><select bind:value={woForm.asset_component} class={inputCls}><option value={null}>None</option>{#each assets.filter(a => !woForm.property || a.property === woForm.property) as a}<option value={a.id}>{a.component_id} — {a.name}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Reported By</label><input bind:value={woForm.reported_by} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Assigned To</label><input bind:value={woForm.assigned_to} class={inputCls} /></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Due Date</label><DateInput bind:value={woForm.due_date} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Estimated Cost ({currency.config.symbol})</label><input bind:value={woForm.estimated_cost} placeholder="0.00" class="{inputCls} tabular-nums" /></div>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={woSaving} class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{woSaving ? "Saving..." : "Create Work Order"}</button>
          <button type="button" onclick={() => (showWoCreate = false)} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Preventive Schedule Create -->
{#if showPmCreate}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showPmCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">New Preventive Schedule</h2>
        <button onclick={() => (showPmCreate = false)} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <form onsubmit={handlePmCreate} class="overflow-y-auto p-6 space-y-5">
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Property</label><select bind:value={pmForm.property} class={inputCls}><option value={0} disabled>Select property</option>{#each properties as p}<option value={p.id}>{p.name}</option>{/each}</select>{#if fieldErr(pmErrors,"property")}<p class="mt-1 text-xs text-red-500">{fieldErr(pmErrors,"property")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Title</label><input bind:value={pmForm.title} placeholder="e.g. Quarterly HVAC filter replacement" class={inputCls} />{#if fieldErr(pmErrors,"title")}<p class="mt-1 text-xs text-red-500">{fieldErr(pmErrors,"title")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Description</label><textarea bind:value={pmForm.description} rows={3} class="{inputCls} resize-none" placeholder="Describe the maintenance task..."></textarea></div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Category</label><select bind:value={pmForm.category} class={inputCls}>{#each Object.entries(categoryLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Frequency</label><select bind:value={pmForm.frequency} class={inputCls}>{#each Object.entries(frequencyLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Asset</label><select bind:value={pmForm.asset_component} class={inputCls}><option value={null}>None</option>{#each assets.filter(a => !pmForm.property || a.property === pmForm.property) as a}<option value={a.id}>{a.component_id} — {a.name}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Vendor</label><select bind:value={pmForm.vendor} class={inputCls}><option value={null}>None</option>{#each vendors as v}<option value={v.id}>{v.name}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Assigned To</label><input bind:value={pmForm.assigned_to} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Next Due Date</label><DateInput bind:value={pmForm.next_due_date} />{#if fieldErr(pmErrors,"next_due_date")}<p class="mt-1 text-xs text-red-500">{fieldErr(pmErrors,"next_due_date")}</p>{/if}</div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Est. Cost ({currency.config.symbol})</label><input bind:value={pmForm.estimated_cost} placeholder="0.00" class="{inputCls} tabular-nums" /></div>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={pmSaving} class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{pmSaving ? "Saving..." : "Create Schedule"}</button>
          <button type="button" onclick={() => (showPmCreate = false)} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Inspection Create/Edit -->
{#if showInspCreate}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => { showInspCreate = false; inspEditingId = null; }} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">{inspEditingId ? "Edit Inspection" : "New Inspection"}</h2>
        <button onclick={() => { showInspCreate = false; inspEditingId = null; }} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <form onsubmit={handleInspSave} class="overflow-y-auto p-6 space-y-5">
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Property</label><select bind:value={inspForm.property} class={inputCls}><option value={0} disabled>Select property</option>{#each properties as p}<option value={p.id}>{p.name}</option>{/each}</select>{#if fieldErr(inspErrors,"property")}<p class="mt-1 text-xs text-red-500">{fieldErr(inspErrors,"property")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Title</label><input bind:value={inspForm.title} placeholder="e.g. Annual fire safety inspection" class={inputCls} />{#if fieldErr(inspErrors,"title")}<p class="mt-1 text-xs text-red-500">{fieldErr(inspErrors,"title")}</p>{/if}</div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Inspection Type</label><select bind:value={inspForm.inspection_type} class={inputCls}>{#each Object.entries(inspTypeLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Scheduled Date</label><DateInput bind:value={inspForm.scheduled_date} />{#if fieldErr(inspErrors,"scheduled_date")}<p class="mt-1 text-xs text-red-500">{fieldErr(inspErrors,"scheduled_date")}</p>{/if}</div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Inspector</label><input bind:value={inspForm.inspector} placeholder="Inspector name" class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Asset (optional)</label><select bind:value={inspForm.asset_component} class={inputCls}><option value={null}>None</option>{#each assets.filter(a => !inspForm.property || a.property === inspForm.property) as a}<option value={a.id}>{a.component_id} — {a.name}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Risk Level</label><select bind:value={inspForm.risk_level} class={inputCls}><option value="">None</option>{#each Object.entries(riskLevelLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Compliance Status</label><select bind:value={inspForm.compliance_status} class={inputCls}><option value="">None</option>{#each Object.entries(complianceStatusLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Expiry Date</label><DateInput bind:value={inspForm.expiry_date} /></div>
          <div class="flex items-end pb-1"><label class="flex items-center gap-2 text-sm text-neutral-700 cursor-pointer"><input type="checkbox" bind:checked={inspForm.corrective_action_required} class="rounded border-neutral-300" /> Corrective Action Required</label></div>
        </div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Findings</label><textarea bind:value={inspForm.findings} rows={3} class="{inputCls} resize-none" placeholder="Inspection findings..."></textarea></div>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={inspSaving} class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{inspSaving ? "Saving..." : inspEditingId ? "Save Changes" : "Schedule Inspection"}</button>
          <button type="button" onclick={() => { showInspCreate = false; inspEditingId = null; }} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Inspection View Detail -->
{#if showInspView}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showInspView = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">Inspection Details</h2>
        <button onclick={() => (showInspView = false)} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="overflow-y-auto p-6">
        {#if inspViewItem}
          <div class="space-y-4 text-sm">
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Title</span><p class="font-medium text-neutral-900 mt-0.5">{inspViewItem.title}</p></div>
              <div><span class="text-neutral-400 text-xs">Property</span><p class="font-medium text-neutral-900 mt-0.5">{inspViewItem.property_name}</p></div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Type</span><p class="font-medium text-neutral-900 mt-0.5">{inspTypeLabels[inspViewItem.inspection_type] ?? inspViewItem.inspection_type}</p></div>
              <div><span class="text-neutral-400 text-xs">Status</span><p class="font-medium text-neutral-900 mt-0.5">{inspStatusLabels[inspViewItem.status] ?? inspViewItem.status}</p></div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Inspector</span><p class="font-medium text-neutral-900 mt-0.5">{inspViewItem.inspector || "\u2014"}</p></div>
              <div><span class="text-neutral-400 text-xs">Scheduled Date</span><p class="font-medium text-neutral-900 mt-0.5">{formatDate(inspViewItem.scheduled_date)}</p></div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Rating</span><p class="font-medium text-neutral-900 mt-0.5">{#if inspViewItem.rating}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {ratingColors[inspViewItem.rating] ?? ''}">{ratingLabels[inspViewItem.rating] ?? inspViewItem.rating}</span>{:else}&mdash;{/if}</p></div>
              <div><span class="text-neutral-400 text-xs">Completed</span><p class="font-medium text-neutral-900 mt-0.5">{formatDate(inspViewItem.completed_date)}</p></div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Risk Level</span><p class="font-medium text-neutral-900 mt-0.5">{#if inspViewItem.risk_level}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {riskLevelColors[inspViewItem.risk_level] ?? ''}">{riskLevelLabels[inspViewItem.risk_level] ?? inspViewItem.risk_level}</span>{:else}&mdash;{/if}</p></div>
              <div><span class="text-neutral-400 text-xs">Compliance Status</span><p class="font-medium text-neutral-900 mt-0.5">{#if inspViewItem.compliance_status}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {complianceStatusColors[inspViewItem.compliance_status] ?? ''}">{complianceStatusLabels[inspViewItem.compliance_status] ?? inspViewItem.compliance_status}</span>{:else}&mdash;{/if}</p></div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Expiry Date</span><p class="font-medium text-neutral-900 mt-0.5">{formatDate(inspViewItem.expiry_date ?? null)}</p></div>
              <div><span class="text-neutral-400 text-xs">Corrective Action</span><p class="font-medium text-neutral-900 mt-0.5">{inspViewItem.corrective_action_required ? "Required" : "Not Required"}</p></div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div><span class="text-neutral-400 text-xs">Follow-up Required</span><p class="font-medium text-neutral-900 mt-0.5">{inspViewItem.follow_up_required ? "Yes" : "No"}</p></div>
              <div><span class="text-neutral-400 text-xs">Unit</span><p class="font-medium text-neutral-900 mt-0.5">{inspViewItem.unit_number ?? "\u2014"}</p></div>
            </div>
            {#if inspViewItem.findings}<div><span class="text-neutral-400 text-xs">Findings</span><p class="font-medium text-neutral-900 mt-0.5 whitespace-pre-wrap">{inspViewItem.findings}</p></div>{/if}
            {#if inspViewItem.follow_up_notes}<div><span class="text-neutral-400 text-xs">Follow-up Notes</span><p class="font-medium text-neutral-900 mt-0.5 whitespace-pre-wrap">{inspViewItem.follow_up_notes}</p></div>{/if}
            {#if inspViewItem.notes}<div><span class="text-neutral-400 text-xs">Notes</span><p class="font-medium text-neutral-900 mt-0.5 whitespace-pre-wrap">{inspViewItem.notes}</p></div>{/if}
          </div>
        {:else}
          <div class="flex items-center justify-center py-8"><div class="w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Inspection Delete Confirm -->
{#if showInspDelete}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showInspDelete = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden">
      <div class="h-1 bg-red-600"></div>
      <div class="p-6 space-y-4">
        <h2 class="text-base font-bold text-neutral-900">Delete Inspection</h2>
        <p class="text-sm text-neutral-600">Are you sure you want to delete <span class="font-medium">"{inspDeleteTitle}"</span>? This action cannot be undone.</p>
        <div class="flex gap-3 pt-2">
          <button onclick={handleInspDelete} disabled={inspDeleting} class="px-6 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors">{inspDeleting ? "Deleting..." : "Delete"}</button>
          <button onclick={() => (showInspDelete = false)} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Service Request Create -->
{#if showSrCreate}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showSrCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">New Service Request</h2>
        <button onclick={() => (showSrCreate = false)} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <form onsubmit={handleSrCreate} class="overflow-y-auto p-6 space-y-5">
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Property</label><select bind:value={srForm.property} class={inputCls}><option value={0} disabled>Select property</option>{#each properties as p}<option value={p.id}>{p.name}</option>{/each}</select>{#if fieldErr(srErrors,"property")}<p class="mt-1 text-xs text-red-500">{fieldErr(srErrors,"property")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Title</label><input bind:value={srForm.title} placeholder="e.g. AC not cooling in Unit 5A" class={inputCls} />{#if fieldErr(srErrors,"title")}<p class="mt-1 text-xs text-red-500">{fieldErr(srErrors,"title")}</p>{/if}</div>
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Description</label><textarea bind:value={srForm.description} rows={3} class="{inputCls} resize-none" placeholder="Describe the service needed..."></textarea></div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Category</label><select bind:value={srForm.category} class={inputCls}>{#each Object.entries(categoryLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Priority</label><select bind:value={srForm.priority} class={inputCls}>{#each Object.entries(priorityLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Requested By</label><input bind:value={srForm.requested_by} placeholder="Tenant name" class={inputCls} />{#if fieldErr(srErrors,"requested_by")}<p class="mt-1 text-xs text-red-500">{fieldErr(srErrors,"requested_by")}</p>{/if}</div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Assigned To</label><input bind:value={srForm.assigned_to} class={inputCls} /></div>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={srSaving} class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{srSaving ? "Saving..." : "Submit Request"}</button>
          <button type="button" onclick={() => (showSrCreate = false)} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Vendor Create -->
{#if showVendorCreate}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showVendorCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] flex flex-col">
      <div class="h-1 bg-neutral-900"></div>
      <div class="px-6 pt-5 pb-4 border-b border-neutral-200 flex items-center justify-between shrink-0">
        <h2 class="text-base font-bold text-neutral-900">New Maintenance Vendor</h2>
        <button onclick={() => (showVendorCreate = false)} class="text-neutral-400 hover:text-neutral-600"><svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <form onsubmit={handleVendorCreate} class="overflow-y-auto p-6 space-y-5">
        <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Company Name</label><input bind:value={vendorForm.name} placeholder="e.g. ABC Plumbing Services" class={inputCls} />{#if fieldErr(vendorErrors,"name")}<p class="mt-1 text-xs text-red-500">{fieldErr(vendorErrors,"name")}</p>{/if}</div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Contact Person</label><input bind:value={vendorForm.contact_person} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Specialization</label><select bind:value={vendorForm.specialization} class={inputCls}>{#each Object.entries(categoryLabels) as [v, l]}<option value={v}>{l}</option>{/each}</select></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Email</label><input type="email" bind:value={vendorForm.email} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Phone</label><input bind:value={vendorForm.phone} class={inputCls} /></div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">License #</label><input bind:value={vendorForm.license_number} class={inputCls} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">License Expiry</label><DateInput bind:value={vendorForm.license_expiry} /></div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Insurance Expiry</label><DateInput bind:value={vendorForm.insurance_expiry} /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Rating (0-5)</label><input bind:value={vendorForm.rating} placeholder="e.g. 4.5" class="{inputCls} tabular-nums" /></div>
          <div><label class="block text-xs font-medium text-neutral-500 mb-1.5">Hourly Rate ({currency.config.symbol})</label><input bind:value={vendorForm.hourly_rate} placeholder="0.00" class="{inputCls} tabular-nums" /></div>
        </div>
        <div class="flex gap-3 pt-2">
          <button type="submit" disabled={vendorSaving} class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{vendorSaving ? "Saving..." : "Create Vendor"}</button>
          <button type="button" onclick={() => (showVendorCreate = false)} class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
        </div>
      </form>
    </div>
  </div>
{/if}

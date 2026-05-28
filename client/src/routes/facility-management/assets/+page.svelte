<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    AssetCategory,
    AssetComponentListItem,
    AssetDepreciationMethod,
    AssetIoTStatus,
    AssetLifecycleStage,
    ConditionRating,
    MaintenanceVendorListItem,
    PaginatedResponse,
  } from "$lib/types";

  type AssetTab =
    | "register"
    | "categorization"
    | "lifecycle"
    | "warranty_amc"
    | "depreciation"
    | "iot";

  interface BreakdownItem {
    key: string;
    count: number;
  }

  interface WatchListItem {
    id: number;
    component_id: string;
    name: string;
    property_name: string;
    facility_code: string;
    location_label: string;
    vendor_name: string;
    amc_vendor_name: string;
    maintenance_next_due_date: string | null;
    warranty_expiry: string | null;
    amc_end_date: string | null;
    lifecycle_stage: AssetLifecycleStage;
    condition_rating: ConditionRating;
    iot_status: AssetIoTStatus;
    iot_last_seen_at: string | null;
    monthly_depreciation: string | null;
    current_book_value: string | null;
    warranty_status: "active" | "expiring" | "expired" | "not_covered";
    amc_status: "active" | "expiring" | "expired" | "not_covered";
    maintenance_status: "not_scheduled" | "scheduled" | "due_soon" | "overdue" | "retired";
  }

  interface FacilityAssetOverview {
    generated_at: string;
    kpis: {
      total_assets: number;
      active_assets: number;
      critical_assets: number;
      maintenance_due_30_days: number;
      warranty_expiring_90_days: number;
      amc_expiring_90_days: number;
      depreciating_assets: number;
      iot_connected_assets: number;
    };
    category_breakdown: BreakdownItem[];
    lifecycle_breakdown: BreakdownItem[];
    warranty_breakdown: BreakdownItem[];
    amc_breakdown: BreakdownItem[];
    depreciation: {
      tracked_assets: number;
      total_acquisition_cost: string;
      total_book_value: string;
      total_monthly_depreciation: string;
      synced_this_month: number;
    };
    iot: {
      enabled: number;
      connected: number;
      offline: number;
      fault: number;
      not_connected: number;
    };
    maintenance_watchlist: WatchListItem[];
    warranty_watchlist: WatchListItem[];
    amc_watchlist: WatchListItem[];
    depreciation_watchlist: WatchListItem[];
    iot_watchlist: WatchListItem[];
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

  const PAGE_SIZE = 25;

  const tabs: { key: AssetTab; label: string }[] = [
    { key: "register", label: "Asset Register" },
    { key: "categorization", label: "Asset Categorization" },
    { key: "lifecycle", label: "Asset Lifecycle" },
    { key: "warranty_amc", label: "Warranty & AMC" },
    { key: "depreciation", label: "Asset Depreciation" },
    { key: "iot", label: "IoT Assets" },
  ];

  const categoryOptions: { value: AssetCategory; label: string }[] = [
    { value: "structural", label: "Structural" },
    { value: "electrical", label: "Electrical" },
    { value: "mechanical", label: "Mechanical" },
    { value: "plumbing", label: "Plumbing" },
    { value: "hvac", label: "HVAC" },
    { value: "fire_safety", label: "Fire & Safety" },
    { value: "elevator", label: "Elevators" },
    { value: "generator", label: "Generators" },
    { value: "water_systems", label: "Water Systems" },
    { value: "security", label: "Security Systems" },
  ];

  const lifecycleOptions: { value: AssetLifecycleStage; label: string }[] = [
    { value: "install", label: "Install" },
    { value: "operate", label: "Operate" },
    { value: "maintain", label: "Maintain" },
    { value: "retire", label: "Retire" },
  ];

  const conditionOptions: { value: ConditionRating; label: string }[] = [
    { value: "excellent", label: "Excellent" },
    { value: "good", label: "Good" },
    { value: "fair", label: "Fair" },
    { value: "poor", label: "Poor" },
    { value: "critical", label: "Critical" },
  ];

  const maintenanceFrequencyOptions = [
    { value: "", label: "Not scheduled" },
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "biweekly", label: "Bi-Weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "semi_annual", label: "Semi-Annual" },
    { value: "annual", label: "Annual" },
  ];

  let activeTab = $state<AssetTab>("register");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingDepreciation = $state(false);

  let overview = $state<FacilityAssetOverview | null>(null);

  let assets = $state<AssetComponentListItem[]>([]);
  let assetsCount = $state(0);
  let assetsPage = $state(1);
  let assetsLoading = $state(false);

  let facilitiesLookup = $state<FacilityLookupItem[]>([]);
  let spacesLookup = $state<FacilitySpaceLookupItem[]>([]);
  let vendorsLookup = $state<MaintenanceVendorListItem[]>([]);

  let assetSearch = $state("");
  let assetCategory = $state("");
  let assetLifecycle = $state("");
  let assetCondition = $state("");
  let assetFacility = $state("");

  let showAssetDrawer = $state(false);
  let assetSaving = $state(false);
  let expandedAssetRowId = $state<number | null>(null);

  let assetForm = $state({
    facility: "",
    facility_space: "",
    vendor: "",
    name: "",
    component_id: "",
    category: "hvac" as AssetCategory,
    lifecycle_stage: "operate" as AssetLifecycleStage,
    condition_rating: "good" as ConditionRating,
    manufacturer: "",
    model_number: "",
    serial_number: "",
    description: "",
    location_description: "",
    installation_date: "",
    commissioned_date: "",
    warranty_expiry: "",
    maintenance_frequency: "",
    maintenance_next_due_date: "",
    auto_schedule_maintenance: true,
    expected_useful_life_years: "",
    acquisition_cost: "",
    salvage_value: "",
    depreciation_enabled: false,
    depreciation_method: "straight_line" as AssetDepreciationMethod,
    depreciation_start_date: "",
    amc_vendor: "",
    amc_start_date: "",
    amc_end_date: "",
    amc_amount: "",
    amc_reference: "",
    amc_notes: "",
    is_iot_enabled: false,
    iot_device_id: "",
    iot_status: "not_connected" as AssetIoTStatus,
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillAsset() {
    const today = new Date().toISOString().slice(0, 10);
    const nextYear = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const nextMonth = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const categories: AssetCategory[] = ["hvac", "electrical", "mechanical", "plumbing", "fire_safety", "elevator", "generator", "water_systems", "security", "structural"];
    const conditions: ConditionRating[] = ["excellent", "good", "fair", "poor", "critical"];
    const names = ["Split AC Unit 2HP", "Fire Alarm Panel", "CCTV Camera Dome", "Generator 100KVA", "Water Pump Booster", "Access Control Reader", "UPS 3KVA", "Elevator Motor Unit"];
    const manufacturers = ["Daikin", "Honeywell", "Hikvision", "Caterpillar", "Grundfos", "ZKTeco", "APC", "Otis"];
    const idx = Math.floor(Math.random() * names.length);

    assetForm.name = names[idx];
    assetForm.component_id = `CMP-${String(Math.floor(Math.random() * 9000) + 1000)}`;
    assetForm.category = categories[Math.floor(Math.random() * categories.length)];
    assetForm.lifecycle_stage = "operate";
    assetForm.condition_rating = conditions[Math.floor(Math.random() * conditions.length)];
    assetForm.manufacturer = manufacturers[idx];
    assetForm.model_number = `MDL-${Math.floor(Math.random() * 9000) + 1000}`;
    assetForm.serial_number = `SN${Date.now().toString(36).toUpperCase()}`;
    assetForm.description = `${names[idx]} — installed for facility operations.`;
    assetForm.location_description = "Ground floor, main utility room";
    assetForm.installation_date = today;
    assetForm.commissioned_date = today;
    assetForm.warranty_expiry = nextYear;
    assetForm.maintenance_frequency = "quarterly";
    assetForm.maintenance_next_due_date = nextMonth;
    assetForm.auto_schedule_maintenance = true;
    assetForm.expected_useful_life_years = String(Math.floor(Math.random() * 10) + 5);
    assetForm.acquisition_cost = String(Math.floor(Math.random() * 5000000) + 200000);
    assetForm.salvage_value = String(Math.floor(Math.random() * 50000) + 10000);
    assetForm.depreciation_enabled = true;
    assetForm.depreciation_method = "straight_line";
    assetForm.depreciation_start_date = today;
    assetForm.amc_start_date = today;
    assetForm.amc_end_date = nextYear;
    assetForm.amc_amount = String(Math.floor(Math.random() * 500000) + 50000);
    assetForm.amc_reference = `AMC-${Math.floor(Math.random() * 9000) + 1000}`;
    assetForm.amc_notes = "Annual maintenance contract with quarterly servicing.";
    assetForm.notes = "Auto-filled for development testing.";
    if (facilitiesLookup.length > 0 && !assetForm.facility) {
      assetForm.facility = String(facilitiesLookup[0].id);
    }
    if (vendorsLookup.length > 0 && !assetForm.vendor) {
      assetForm.vendor = String(vendorsLookup[0].id);
    }
    if (vendorsLookup.length > 0 && !assetForm.amc_vendor) {
      assetForm.amc_vendor = String(vendorsLookup[0].id);
    }
  }

  const totalPages = $derived(Math.max(1, Math.ceil(assetsCount / PAGE_SIZE)));

  const filteredSpaces = $derived.by(() => {
    const facilityId = Number(assetForm.facility || 0);
    if (!facilityId) return spacesLookup;
    return spacesLookup.filter((space) => space.facility === facilityId);
  });

  const selectedFacilitySpace = $derived.by(() => {
    const spaceId = Number(assetForm.facility_space || 0);
    if (!spaceId) return null;
    return spacesLookup.find((space) => space.id === spaceId) ?? null;
  });

  function resetAssetForm() {
    assetForm = {
      facility: "",
      facility_space: "",
      vendor: "",
      name: "",
      component_id: "",
      category: "hvac",
      lifecycle_stage: "operate",
      condition_rating: "good",
      manufacturer: "",
      model_number: "",
      serial_number: "",
      description: "",
      location_description: "",
      installation_date: "",
      commissioned_date: "",
      warranty_expiry: "",
      maintenance_frequency: "",
      maintenance_next_due_date: "",
      auto_schedule_maintenance: true,
      expected_useful_life_years: "",
      acquisition_cost: "",
      salvage_value: "",
      depreciation_enabled: false,
      depreciation_method: "straight_line",
      depreciation_start_date: "",
      amc_vendor: "",
      amc_start_date: "",
      amc_end_date: "",
      amc_amount: "",
      amc_reference: "",
      amc_notes: "",
      is_iot_enabled: false,
      iot_device_id: "",
      iot_status: "not_connected",
      notes: "",
    };
  }

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
    return currency.format(amount);
  }

  function toggleAssetRow(assetId: number) {
    expandedAssetRowId = expandedAssetRowId === assetId ? null : assetId;
  }

  function badgeTone(status: string): string {
    switch (status) {
      case "critical":
      case "expired":
      case "overdue":
      case "fault":
      case "retire":
        return "bg-red-50 text-red-700 border-red-200";
      case "poor":
      case "expiring":
      case "due_soon":
      case "offline":
      case "maintain":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "connected":
      case "active":
      case "operate":
      case "scheduled":
      case "excellent":
      case "good":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      default:
        return "bg-neutral-100 text-neutral-700 border-neutral-200";
    }
  }

  async function fetchOverview() {
    overview = await api.get<FacilityAssetOverview>("/facility-management/assets/overview/");
  }

  async function fetchAssets() {
    assetsLoading = true;
    try {
      const params: Record<string, string> = {
        page: String(assetsPage),
        page_size: String(PAGE_SIZE),
      };
      if (assetSearch.trim()) params.search = assetSearch.trim();
      if (assetCategory) params.category = assetCategory;
      if (assetLifecycle) params.lifecycle_stage = assetLifecycle;
      if (assetCondition) params.condition_rating = assetCondition;
      if (assetFacility) params.facility = assetFacility;
      const response = await api.get<PaginatedResponse<AssetComponentListItem>>("/facility-management/assets/register/", params);
      assets = response.results;
      assetsCount = response.count;
    } catch {
      assets = [];
      assetsCount = 0;
      toast.error("Load failed", "Could not load asset register.");
    } finally {
      assetsLoading = false;
    }
  }

  async function fetchLookups() {
    const [facilitiesResponse, spacesResponse, vendorsResponse] = await Promise.all([
      api.get<PaginatedResponse<FacilityLookupItem>>("/facility-management/registry/facilities/", { page_size: "200" }),
      api.get<PaginatedResponse<FacilitySpaceLookupItem>>("/facility-management/registry/unit-spaces/", { page_size: "500" }),
      api.get<PaginatedResponse<MaintenanceVendorListItem>>("/properties/maintenance/vendors/", { page_size: "200" }),
    ]);

    facilitiesLookup = facilitiesResponse.results;
    spacesLookup = spacesResponse.results;
    vendorsLookup = vendorsResponse.results;
  }

  async function refreshAll() {
    if (!loading) refreshing = true;
    try {
      await Promise.all([fetchOverview(), fetchAssets(), fetchLookups()]);
    } catch {
      toast.error("Load failed", "Could not load asset management.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  function openAssetDrawer() {
    resetAssetForm();
    showAssetDrawer = true;
    void fetchLookups();
  }

  function closeAssetDrawer() {
    showAssetDrawer = false;
    resetAssetForm();
  }

  async function handleAssetCreate(event: Event) {
    event.preventDefault();
    if (!assetForm.name.trim() || !assetForm.component_id.trim() || !assetForm.facility) {
      toast.error("Missing data", "Facility, asset name, and component ID are required.");
      return;
    }

    assetSaving = true;
    try {
      await api.post("/facility-management/assets/register/", {
        facility: Number(assetForm.facility),
        facility_space: assetForm.facility_space ? Number(assetForm.facility_space) : null,
        vendor: assetForm.vendor ? Number(assetForm.vendor) : null,
        name: assetForm.name.trim(),
        component_id: assetForm.component_id.trim(),
        category: assetForm.category,
        lifecycle_stage: assetForm.lifecycle_stage,
        condition_rating: assetForm.condition_rating,
        manufacturer: assetForm.manufacturer.trim(),
        model_number: assetForm.model_number.trim(),
        serial_number: assetForm.serial_number.trim(),
        description: assetForm.description.trim(),
        location_description: assetForm.location_description.trim(),
        installation_date: assetForm.installation_date || null,
        commissioned_date: assetForm.commissioned_date || null,
        warranty_expiry: assetForm.warranty_expiry || null,
        maintenance_frequency: assetForm.maintenance_frequency || "",
        maintenance_next_due_date: assetForm.maintenance_next_due_date || null,
        auto_schedule_maintenance: assetForm.auto_schedule_maintenance,
        expected_useful_life_years: assetForm.expected_useful_life_years ? Number(assetForm.expected_useful_life_years) : null,
        acquisition_cost: assetForm.acquisition_cost || null,
        salvage_value: assetForm.salvage_value || null,
        depreciation_enabled: assetForm.depreciation_enabled,
        depreciation_method: assetForm.depreciation_method,
        depreciation_start_date: assetForm.depreciation_start_date || null,
        amc_vendor: assetForm.amc_vendor ? Number(assetForm.amc_vendor) : null,
        amc_start_date: assetForm.amc_start_date || null,
        amc_end_date: assetForm.amc_end_date || null,
        amc_amount: assetForm.amc_amount || null,
        amc_reference: assetForm.amc_reference.trim(),
        amc_notes: assetForm.amc_notes.trim(),
        is_iot_enabled: assetForm.is_iot_enabled,
        iot_device_id: assetForm.iot_device_id.trim(),
        iot_status: assetForm.is_iot_enabled ? assetForm.iot_status : "not_connected",
        notes: assetForm.notes.trim(),
      });
      toast.success("Asset created", "Asset has been registered and workflows were synchronized.");
      closeAssetDrawer();
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the asset fields.");
      } else {
        toast.error("Create failed", "Could not create asset.");
      }
    } finally {
      assetSaving = false;
    }
  }

  async function handleSyncDepreciation(assetId: number) {
    try {
      await api.post(`/facility-management/assets/register/${assetId}/sync-depreciation/`, {});
      toast.success("Depreciation synced", "Draft accounting journal updated for this asset.");
      await Promise.all([fetchOverview(), fetchAssets()]);
    } catch {
      toast.error("Sync failed", "Asset depreciation could not be synchronized.");
    }
  }

  async function handleBulkDepreciationSync() {
    syncingDepreciation = true;
    try {
      const response = await api.post<{ synced: number; skipped: number }>("/facility-management/assets/register/sync-depreciation/", {});
      toast.success("Depreciation sync complete", `${response.synced} assets synchronized, ${response.skipped} skipped.`);
      await Promise.all([fetchOverview(), fetchAssets()]);
    } catch {
      toast.error("Sync failed", "Bulk depreciation sync could not be completed.");
    } finally {
      syncingDepreciation = false;
    }
  }

  function resetFilters() {
    assetSearch = "";
    assetCategory = "";
    assetLifecycle = "";
    assetCondition = "";
    assetFacility = "";
    assetsPage = 1;
  }

  let initialized = false;

  $effect(() => {
    if (initialized) return;
    initialized = true;
    void refreshAll();
  });

  $effect(() => {
    assetsPage;
    assetSearch;
    assetCategory;
    assetLifecycle;
    assetCondition;
    assetFacility;
    if (!initialized) return;
    void fetchAssets();
  });

  $effect(() => {
    const facilityId = Number(assetForm.facility || 0);
    const selectedSpaceId = Number(assetForm.facility_space || 0);
    if (!selectedSpaceId) return;

    const selectedSpace = spacesLookup.find((space) => space.id === selectedSpaceId) ?? null;
    if (!selectedSpace) {
      assetForm.facility_space = "";
      return;
    }

    if (facilityId && selectedSpace.facility !== facilityId) {
      assetForm.facility_space = "";
      return;
    }

    if (!assetForm.location_description.trim()) {
      assetForm.location_description = selectedSpace.space_label || selectedSpace.unit_number || "";
    }
  });

  $effect(() => {
    assets;
    if (expandedAssetRowId !== null && !assets.some((asset) => asset.id === expandedAssetRowId)) {
      expandedAssetRowId = null;
    }
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-500">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-800 tracking-wide">Asset Management</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Central register for assets, lifecycle posture, warranty and AMC coverage, depreciation sync, and IoT readiness across facilities.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>

    <div class="flex flex-wrap items-center gap-2 lg:ml-auto lg:justify-end">
      <button
        type="button"
        onclick={handleBulkDepreciationSync}
        disabled={syncingDepreciation || loading}
        class="rounded-lg border border-neutral-300 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {syncingDepreciation ? "Syncing..." : "Sync Depreciation"}
      </button>
      <button
        type="button"
        onclick={refreshAll}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing asset management" : "Refresh asset management"}
        title={refreshing ? "Refreshing asset management" : "Refresh asset management"}
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
      Loading asset management...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Asset management overview is unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <section class="rounded-2xl border border-sky-200 bg-sky-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-sky-700">Tracked Assets</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.total_assets}</p>
        <p class="mt-1 text-xs text-sky-800">Active: {overview.kpis.active_assets}</p>
      </section>
      <section class="rounded-2xl border border-amber-200 bg-amber-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-amber-700">Maintenance Due</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.maintenance_due_30_days}</p>
        <p class="mt-1 text-xs text-amber-800">Within 30 days</p>
      </section>
      <section class="rounded-2xl border border-rose-200 bg-rose-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-rose-700">Coverage Risk</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">
          {overview.kpis.warranty_expiring_90_days + overview.kpis.amc_expiring_90_days}
        </p>
        <p class="mt-1 text-xs text-rose-800">
          Warranty: {overview.kpis.warranty_expiring_90_days} | AMC: {overview.kpis.amc_expiring_90_days}
        </p>
      </section>
      <section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <p class="text-xs uppercase font-semibold tracking-wide text-emerald-700">Connected IoT</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.kpis.iot_connected_assets}</p>
        <p class="mt-1 text-xs text-emerald-800">Depreciating assets: {overview.kpis.depreciating_assets}</p>
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

    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
          Search
          <input
            bind:value={assetSearch}
            class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm normal-case tracking-normal text-neutral-900"
            placeholder="Asset code, name, serial..."
          />
        </label>

        <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
          Facility
          <select bind:value={assetFacility} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
          Category
          <select bind:value={assetCategory} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
            <option value="">All categories</option>
            {#each categoryOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
          Lifecycle
          <select bind:value={assetLifecycle} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
            <option value="">All stages</option>
            {#each lifecycleOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs font-medium uppercase tracking-wide text-neutral-500">
          Condition
          <select bind:value={assetCondition} class="mt-1 w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm normal-case tracking-normal text-neutral-900">
            <option value="">All conditions</option>
            {#each conditionOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
      </div>

      <div class="mt-3 flex justify-end">
        <button
          type="button"
          onclick={resetFilters}
          class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900"
        >
          Reset Filters
        </button>
      </div>
    </section>

    {#if activeTab === "register"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Asset Register</h2>
            <p class="mt-1 text-xs text-neutral-500">Physical assets mapped to facilities, rooms, schedules, coverage, and accounting sync.</p>
          </div>
          <div class="flex items-center gap-3 sm:justify-end">
            <p class="text-xs text-neutral-500">{assetsCount} assets</p>
            <button
              type="button"
              onclick={openAssetDrawer}
              class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
            >
              Add Asset
            </button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="w-12 px-3 py-2"></th>
                <th class="px-3 py-2">Asset</th>
                <th class="px-3 py-2">Location</th>
                <th class="px-3 py-2">Condition</th>
                <th class="px-3 py-2">Maintenance</th>
                <th class="px-3 py-2">Depreciation</th>
                <th class="px-3 py-2">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if assetsLoading}
                <tr><td colspan="7" class="px-3 py-6 text-center text-neutral-500">Loading assets...</td></tr>
              {:else if assets.length === 0}
                <tr><td colspan="7" class="px-3 py-6 text-center text-neutral-500">No assets match the current filters.</td></tr>
              {:else}
                {#each assets as asset (asset.id)}
                  <tr class={expandedAssetRowId === asset.id ? "bg-neutral-50/60" : ""}>
                    <td class="px-3 py-3 align-top">
                      <button
                        type="button"
                        onclick={() => toggleAssetRow(asset.id)}
                        aria-expanded={expandedAssetRowId === asset.id}
                        aria-label={expandedAssetRowId === asset.id ? `Collapse details for ${asset.name}` : `Expand details for ${asset.name}`}
                        title={expandedAssetRowId === asset.id ? "Collapse details" : "Expand details"}
                        class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-neutral-200 bg-white text-neutral-500 transition-colors hover:border-neutral-300 hover:text-neutral-900"
                      >
                        <svg
                          class={`h-4 w-4 transition-transform ${expandedAssetRowId === asset.id ? "rotate-90" : ""}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          stroke-width="2"
                          aria-hidden="true"
                        >
                          <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                        </svg>
                      </button>
                    </td>
                    <td class="px-3 py-3 align-top">
                      <p class="font-medium text-neutral-900">{asset.name}</p>
                      <p class="text-xs text-neutral-500">{asset.component_id} {asset.serial_number ? `• ${asset.serial_number}` : ""}</p>
                      <p class="text-xs text-neutral-500">{asset.manufacturer || "--"} {asset.model_number ? `• ${asset.model_number}` : ""}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p class="font-medium text-neutral-800">{asset.facility_code || "--"}</p>
                      <p>{asset.facility_space_label || asset.location_description || asset.unit_number || "--"}</p>
                      <p>{asset.property_name}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <span class={`inline-flex rounded-full border px-2 py-1 ${badgeTone(asset.condition_rating)}`}>{fmtLabel(asset.condition_rating)}</span>
                      <p class="mt-2 text-neutral-500">Inspection: {fmtDate(asset.last_inspection_date)}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p><span class={`inline-flex rounded-full border px-2 py-1 ${badgeTone(asset.maintenance_status)}`}>{fmtLabel(asset.maintenance_status)}</span></p>
                      <p class="mt-1">{asset.maintenance_frequency ? fmtLabel(asset.maintenance_frequency) : "Not scheduled"}</p>
                      <p class="mt-1">Next: {fmtDate(asset.maintenance_next_due_date)}</p>
                    </td>
                    <td class="px-3 py-3 align-top text-xs text-neutral-600">
                      <p>{asset.depreciation_enabled ? "Enabled" : "Disabled"}</p>
                      <p class="mt-1">Book: {fmtMoney(asset.current_book_value)}</p>
                      <p class="mt-1">Monthly: {fmtMoney(asset.monthly_depreciation)}</p>
                    </td>
                    <td class="px-3 py-3 align-top">
                      <button
                        type="button"
                        onclick={() => handleSyncDepreciation(asset.id)}
                        disabled={!asset.depreciation_enabled}
                        class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Sync Journal
                      </button>
                    </td>
                  </tr>
                  {#if expandedAssetRowId === asset.id}
                    <tr class="bg-neutral-50/60">
                      <td colspan="7" class="px-3 pb-4 pt-0">
                        <div class="rounded-2xl border border-neutral-200 bg-white p-4">
                          <div class="grid gap-4 xl:grid-cols-4">
                            <section class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                              <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Asset Profile</h3>
                              <dl class="mt-3 space-y-2 text-sm">
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Category</dt>
                                  <dd class="text-right text-neutral-900">{fmtLabel(asset.category)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Lifecycle Stage</dt>
                                  <dd class="text-right">
                                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(asset.lifecycle_stage)}`}>{fmtLabel(asset.lifecycle_stage)}</span>
                                  </dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Condition</dt>
                                  <dd class="text-right">
                                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(asset.condition_rating)}`}>{fmtLabel(asset.condition_rating)}</span>
                                  </dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Manufacturer</dt>
                                  <dd class="text-right text-neutral-900">{asset.manufacturer || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Model</dt>
                                  <dd class="text-right text-neutral-900">{asset.model_number || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Serial</dt>
                                  <dd class="text-right text-neutral-900">{asset.serial_number || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Installed</dt>
                                  <dd class="text-right text-neutral-900">{fmtDate(asset.installation_date)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Commissioned</dt>
                                  <dd class="text-right text-neutral-900">{fmtDate(asset.commissioned_date)}</dd>
                                </div>
                              </dl>
                            </section>

                            <section class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                              <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Coverage & Maintenance</h3>
                              <dl class="mt-3 space-y-2 text-sm">
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Warranty Status</dt>
                                  <dd class="text-right">
                                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(asset.warranty_status)}`}>{fmtLabel(asset.warranty_status)}</span>
                                  </dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Warranty Expiry</dt>
                                  <dd class="text-right text-neutral-900">{fmtDate(asset.warranty_expiry)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">AMC Status</dt>
                                  <dd class="text-right">
                                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(asset.amc_status)}`}>{fmtLabel(asset.amc_status)}</span>
                                  </dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">AMC Vendor</dt>
                                  <dd class="text-right text-neutral-900">{asset.amc_vendor_name || asset.vendor_name || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">AMC Window</dt>
                                  <dd class="text-right text-neutral-900">{fmtDate(asset.amc_start_date)} to {fmtDate(asset.amc_end_date)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">AMC Reference</dt>
                                  <dd class="text-right text-neutral-900">{asset.amc_reference || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Maintenance Program</dt>
                                  <dd class="text-right text-neutral-900">
                                    {asset.maintenance_frequency ? `${fmtLabel(asset.maintenance_frequency)} • ${fmtDate(asset.maintenance_next_due_date)}` : "Not scheduled"}
                                  </dd>
                                </div>
                              </dl>
                            </section>

                            <section class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                              <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Depreciation</h3>
                              <dl class="mt-3 space-y-2 text-sm">
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Enabled</dt>
                                  <dd class="text-right text-neutral-900">{asset.depreciation_enabled ? "Yes" : "No"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Acquisition Cost</dt>
                                  <dd class="text-right text-neutral-900">{fmtMoney(asset.acquisition_cost)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Salvage Value</dt>
                                  <dd class="text-right text-neutral-900">{fmtMoney(asset.salvage_value)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Book Value</dt>
                                  <dd class="text-right text-neutral-900">{fmtMoney(asset.current_book_value)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Monthly Charge</dt>
                                  <dd class="text-right text-neutral-900">{fmtMoney(asset.monthly_depreciation)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Last Sync</dt>
                                  <dd class="text-right text-neutral-900">{fmtDateTime(asset.last_depreciation_sync_at)}</dd>
                                </div>
                              </dl>
                            </section>

                            <section class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                              <h3 class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Operations & IoT</h3>
                              <dl class="mt-3 space-y-2 text-sm">
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Room / Space</dt>
                                  <dd class="text-right text-neutral-900">{asset.facility_space_label || asset.location_description || asset.unit_number || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Vendor</dt>
                                  <dd class="text-right text-neutral-900">{asset.vendor_name || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">IoT Status</dt>
                                  <dd class="text-right">
                                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(asset.iot_status)}`}>{fmtLabel(asset.iot_status)}</span>
                                  </dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">IoT Device</dt>
                                  <dd class="text-right text-neutral-900">{asset.iot_device_id || "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Last Seen</dt>
                                  <dd class="text-right text-neutral-900">{fmtDateTime(asset.iot_last_seen_at)}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Useful Life</dt>
                                  <dd class="text-right text-neutral-900">{asset.expected_useful_life_years ? `${asset.expected_useful_life_years} years` : "--"}</dd>
                                </div>
                                <div class="flex items-start justify-between gap-3">
                                  <dt class="text-neutral-500">Last Inspection</dt>
                                  <dd class="text-right text-neutral-900">{fmtDate(asset.last_inspection_date)}</dd>
                                </div>
                              </dl>
                            </section>
                          </div>
                        </div>
                      </td>
                    </tr>
                  {/if}
                {/each}
              {/if}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-end gap-2">
          <button type="button" onclick={() => (assetsPage = Math.max(1, assetsPage - 1))} disabled={assetsPage <= 1} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-500">Page {assetsPage} of {totalPages}</span>
          <button type="button" onclick={() => (assetsPage = Math.min(totalPages, assetsPage + 1))} disabled={assetsPage >= totalPages} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Next</button>
        </div>
      </section>
    {/if}

    {#if activeTab === "categorization"}
      <div class="grid gap-4 lg:grid-cols-2">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Category Mix</h2>
          {#if overview.category_breakdown.length === 0}
            <p class="text-sm text-neutral-500">No asset categories available yet.</p>
          {:else}
            <div class="space-y-2">
              {#each overview.category_breakdown as item}
                <div class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <span class="text-sm text-neutral-700">{fmtLabel(item.key)}</span>
                  <span class="text-sm font-semibold text-neutral-900">{item.count}</span>
                </div>
              {/each}
            </div>
          {/if}
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Current Filtered Assets</h2>
          {#if assets.length === 0}
            <p class="text-sm text-neutral-500">No assets in the current filtered list.</p>
          {:else}
            <div class="space-y-2">
              {#each assets.slice(0, 10) as asset}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <p class="text-sm font-medium text-neutral-900">{asset.name}</p>
                  <p class="mt-1 text-xs text-neutral-500">{asset.component_id} • {fmtLabel(asset.category)} • {asset.facility_code || asset.property_name}</p>
                </div>
              {/each}
            </div>
          {/if}
        </section>
      </div>
    {/if}

    {#if activeTab === "lifecycle"}
      <div class="grid gap-4 lg:grid-cols-2">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Lifecycle Stages</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            {#each overview.lifecycle_breakdown as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <p class="text-xs uppercase tracking-wide text-neutral-500">{fmtLabel(item.key)}</p>
                <p class="mt-2 text-2xl font-semibold text-neutral-900">{item.count}</p>
              </div>
            {/each}
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Lifecycle Register Snapshot</h2>
          <div class="mt-4 space-y-2">
            {#if assets.length === 0}
              <p class="text-sm text-neutral-500">No assets in the current filtered list.</p>
            {:else}
              {#each assets.slice(0, 12) as asset}
                <div class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{asset.name}</p>
                    <p class="text-xs text-neutral-500">{asset.facility_code || asset.property_name} • Installed {fmtDate(asset.installation_date)}</p>
                  </div>
                  <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(asset.lifecycle_stage)}`}>{fmtLabel(asset.lifecycle_stage)}</span>
                </div>
              {/each}
            {/if}
          </div>
        </section>
      </div>
    {/if}

    {#if activeTab === "warranty_amc"}
      <div class="grid gap-4 xl:grid-cols-2">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Warranty Watchlist</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            {#each overview.warranty_breakdown as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <p class="text-xs uppercase tracking-wide text-neutral-500">{fmtLabel(item.key)}</p>
                <p class="mt-2 text-2xl font-semibold text-neutral-900">{item.count}</p>
              </div>
            {/each}
          </div>
          <div class="space-y-2">
            {#if overview.warranty_watchlist.length === 0}
              <p class="text-sm text-neutral-500">No expiring or expired warranties.</p>
            {:else}
              {#each overview.warranty_watchlist as item}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-neutral-900">{item.name}</p>
                      <p class="text-xs text-neutral-500">{item.component_id} • {item.facility_code || item.property_name} • {item.location_label || "--"}</p>
                    </div>
                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.warranty_status)}`}>{fmtLabel(item.warranty_status)}</span>
                  </div>
                  <p class="mt-2 text-xs text-neutral-600">Expiry: {fmtDate(item.warranty_expiry)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">AMC Coverage</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            {#each overview.amc_breakdown as item}
              <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                <p class="text-xs uppercase tracking-wide text-neutral-500">{fmtLabel(item.key)}</p>
                <p class="mt-2 text-2xl font-semibold text-neutral-900">{item.count}</p>
              </div>
            {/each}
          </div>
          <div class="space-y-2">
            {#if overview.amc_watchlist.length === 0}
              <p class="text-sm text-neutral-500">No expiring or expired AMC coverage.</p>
            {:else}
              {#each overview.amc_watchlist as item}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-neutral-900">{item.name}</p>
                      <p class="text-xs text-neutral-500">{item.component_id} • AMC Vendor: {item.amc_vendor_name || item.vendor_name || "--"}</p>
                    </div>
                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.amc_status)}`}>{fmtLabel(item.amc_status)}</span>
                  </div>
                  <p class="mt-2 text-xs text-neutral-600">AMC End: {fmtDate(item.amc_end_date)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </section>
      </div>
    {/if}

    {#if activeTab === "depreciation"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-xs uppercase tracking-wide text-neutral-500">Tracked Assets</p>
            <p class="mt-2 text-xl font-semibold text-neutral-900">{overview.depreciation.tracked_assets}</p>
          </div>
          <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-xs uppercase tracking-wide text-neutral-500">Acquisition Value</p>
            <p class="mt-2 text-xl font-semibold text-emerald-700">{fmtMoney(overview.depreciation.total_acquisition_cost)}</p>
          </div>
          <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-xs uppercase tracking-wide text-neutral-500">Current Book Value</p>
            <p class="mt-2 text-xl font-semibold text-emerald-700">{fmtMoney(overview.depreciation.total_book_value)}</p>
          </div>
          <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-xs uppercase tracking-wide text-neutral-500">Synced This Month</p>
            <p class="mt-2 text-xl font-semibold text-neutral-900">{overview.depreciation.synced_this_month}</p>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Asset</th>
                <th class="px-3 py-2">Location</th>
                <th class="px-3 py-2">Acquisition</th>
                <th class="px-3 py-2">Book Value</th>
                <th class="px-3 py-2">Monthly</th>
                <th class="px-3 py-2">Sync</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if overview.depreciation_watchlist.length === 0}
                <tr><td colspan="6" class="px-3 py-6 text-center text-neutral-500">No depreciating assets configured yet.</td></tr>
              {:else}
                {#each overview.depreciation_watchlist as item}
                  <tr>
                    <td class="px-3 py-3">
                      <p class="font-medium text-neutral-900">{item.name}</p>
                      <p class="text-xs text-neutral-500">{item.component_id}</p>
                    </td>
                    <td class="px-3 py-3 text-xs text-neutral-600">
                      <p>{item.facility_code || item.property_name}</p>
                      <p>{item.location_label || "--"}</p>
                    </td>
                    <td class="px-3 py-3">{fmtMoney(assets.find((asset) => asset.id === item.id)?.acquisition_cost || null)}</td>
                    <td class="px-3 py-3">{fmtMoney(item.current_book_value)}</td>
                    <td class="px-3 py-3">{fmtMoney(item.monthly_depreciation)}</td>
                    <td class="px-3 py-3">
                      <button type="button" onclick={() => handleSyncDepreciation(item.id)} class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">
                        Sync Journal
                      </button>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    {#if activeTab === "iot"}
      <div class="grid gap-4 lg:grid-cols-2">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">IoT Connectivity Posture</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">Enabled</p>
              <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.iot.enabled}</p>
            </div>
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">Connected</p>
              <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.iot.connected}</p>
            </div>
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">Offline</p>
              <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.iot.offline}</p>
            </div>
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs uppercase tracking-wide text-neutral-500">Fault</p>
              <p class="mt-2 text-2xl font-semibold text-neutral-900">{overview.iot.fault}</p>
            </div>
          </div>
          <p class="text-xs text-neutral-500">IoT-connected assets are optional. Assets without a device stay in the register without blocking maintenance or accounting workflows.</p>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">IoT Asset Watchlist</h2>
          <div class="mt-4 space-y-2">
            {#if overview.iot_watchlist.length === 0}
              <p class="text-sm text-neutral-500">No IoT-connected assets configured.</p>
            {:else}
              {#each overview.iot_watchlist as item}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-medium text-neutral-900">{item.name}</p>
                      <p class="text-xs text-neutral-500">{item.component_id} • {item.facility_code || item.property_name}</p>
                    </div>
                    <span class={`inline-flex rounded-full border px-2 py-1 text-xs ${badgeTone(item.iot_status)}`}>{fmtLabel(item.iot_status)}</span>
                  </div>
                  <p class="mt-2 text-xs text-neutral-600">Last seen: {fmtDateTime(item.iot_last_seen_at)}</p>
                </div>
              {/each}
            {/if}
          </div>
        </section>
      </div>
    {/if}
  {/if}
</div>

{#if showAssetDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeAssetDrawer}
    tabindex="-1"
    aria-label="Close asset drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Register Asset</h2>
      <button
        type="button"
        onclick={closeAssetDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close asset drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-asset-form" class="space-y-5" onsubmit={handleAssetCreate}>
        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={assetForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select facility</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Room / Space</span>
            <select bind:value={assetForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select room / space</option>
              {#each filteredSpaces as space}
                <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Asset Name</span>
            <input bind:value={assetForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Main rooftop chiller" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Component ID</span>
            <input bind:value={assetForm.component_id} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="AST-CH-001" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Category</span>
            <select bind:value={assetForm.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each categoryOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Lifecycle Stage</span>
            <select bind:value={assetForm.lifecycle_stage} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each lifecycleOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Condition</span>
            <select bind:value={assetForm.condition_rating} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each conditionOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Vendor / Supplier</span>
            <select bind:value={assetForm.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select vendor</option>
              {#each vendorsLookup as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Manufacturer</span>
            <input bind:value={assetForm.manufacturer} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Carrier" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Model Number</span>
            <input bind:value={assetForm.model_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="30XA-1202" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Serial Number</span>
            <input bind:value={assetForm.serial_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="SN-0098123" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Installation Date</span>
            <input type="date" bind:value={assetForm.installation_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Commissioned Date</span>
            <input type="date" bind:value={assetForm.commissioned_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Warranty Expiry</span>
            <input type="date" bind:value={assetForm.warranty_expiry} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Location Notes</span>
            <input bind:value={assetForm.location_description} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Roof deck east corner" />
          </label>
        </section>

        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Maintenance Frequency</span>
            <select bind:value={assetForm.maintenance_frequency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each maintenanceFrequencyOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Next Maintenance Date</span>
            <input type="date" bind:value={assetForm.maintenance_next_due_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={assetForm.auto_schedule_maintenance} class="rounded border-neutral-300" />
            Auto-create preventive maintenance workflow
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Useful Life (Years)</span>
            <input type="number" min="0" bind:value={assetForm.expected_useful_life_years} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
        </section>

        <section class="grid gap-4 md:grid-cols-2">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={assetForm.depreciation_enabled} class="rounded border-neutral-300" />
            Enable accounting depreciation sync
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Depreciation Method</span>
            <select bind:value={assetForm.depreciation_method} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="straight_line">Straight Line</option>
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Acquisition Cost</span>
            <input type="number" step="0.01" bind:value={assetForm.acquisition_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="0.00" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Salvage Value</span>
            <input type="number" step="0.01" bind:value={assetForm.salvage_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="0.00" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Depreciation Start Date</span>
            <input type="date" bind:value={assetForm.depreciation_start_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
        </section>

        <section class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">AMC Vendor</span>
            <select bind:value={assetForm.amc_vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Select AMC vendor</option>
              {#each vendorsLookup as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">AMC Reference</span>
            <input bind:value={assetForm.amc_reference} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="AMC-2026-014" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">AMC Start Date</span>
            <input type="date" bind:value={assetForm.amc_start_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">AMC End Date</span>
            <input type="date" bind:value={assetForm.amc_end_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">AMC Amount</span>
            <input type="number" step="0.01" bind:value={assetForm.amc_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="0.00" />
          </label>
        </section>

        <section class="space-y-4">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={assetForm.is_iot_enabled} class="rounded border-neutral-300" />
            Mark asset as IoT-connected
          </label>

          <div class="grid gap-4 md:grid-cols-2">
            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block">IoT Device ID</span>
              <input bind:value={assetForm.iot_device_id} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="sensor-east-roof-01" />
            </label>

            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block">IoT Status</span>
              <select bind:value={assetForm.iot_status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
                <option value="not_connected">Not Connected</option>
                <option value="connected">Connected</option>
                <option value="offline">Offline</option>
                <option value="fault">Fault</option>
              </select>
            </label>
          </div>
        </section>

        <section class="space-y-4">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Description</span>
            <textarea rows="3" bind:value={assetForm.description} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Short operational summary"></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">AMC Notes</span>
            <textarea rows="3" bind:value={assetForm.amc_notes} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Coverage clauses, response SLAs, exclusions"></textarea>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">General Notes</span>
            <textarea rows="3" bind:value={assetForm.notes} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Any extra asset notes"></textarea>
          </label>
        </section>

        {#if selectedFacilitySpace}
          <div class="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-800">
            Selected space: {selectedFacilitySpace.space_label || selectedFacilitySpace.unit_number} in zone {selectedFacilitySpace.zone_code} ({selectedFacilitySpace.zone_name})
          </div>
        {/if}
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillAsset} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeAssetDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-asset-form"
        disabled={assetSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {assetSaving ? "Saving..." : "Save Asset"}
      </button>
    </div>
  </aside>
{/if}

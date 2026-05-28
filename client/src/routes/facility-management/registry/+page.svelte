<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse, PropertyListItem, Unit } from "$lib/types";

  type RegistryTab =
    | "facilities"
    | "floors_zones"
    | "spaces"
    | "classification"
    | "ownership_lease";

  interface BreakdownItem {
    key: string;
    count: number;
  }

  interface FacilityRegistryOverview {
    generated_at: string;
    kpis: {
      facilities: number;
      floors: number;
      zones: number;
      unit_spaces: number;
      leased_facilities: number;
      lease_expiring_90_days: number;
    };
    classification_breakdown: BreakdownItem[];
    ownership_breakdown: BreakdownItem[];
    facility_type_breakdown: BreakdownItem[];
  }

  interface FacilityRegistryItem {
    id: number;
    property: number;
    property_name: string;
    property_type: string;
    property_classification: string;
    property_address: string;
    facility_code: string;
    facility_classification: string;
    ownership_type: string;
    lease_start_date: string | null;
    lease_end_date: string | null;
    lease_party_name: string;
    lease_amount: string | null;
    floors_count: number;
    zones_count: number;
    unit_spaces_count: number;
    created_at: string;
    updated_at: string;
  }

  interface FacilityFloorItem {
    id: number;
    facility: number;
    facility_code: string;
    facility_name: string;
    name: string;
    floor_code: string;
    floor_number: number;
    gross_area_sqft: string | null;
    usage_type: string;
    is_active: boolean;
    zone_count: number;
    created_at: string;
    updated_at: string;
  }

  interface FacilityZoneItem {
    id: number;
    facility: number;
    facility_code: string;
    facility_name: string;
    floor: number;
    floor_name: string;
    floor_number: number;
    name: string;
    zone_code: string;
    zone_type: string;
    gross_area_sqft: string | null;
    is_active: boolean;
    unit_spaces_count: number;
    created_at: string;
    updated_at: string;
  }

  interface FacilityUnitSpaceItem {
    id: number;
    facility: number;
    facility_code: string;
    facility_name: string;
    zone: number;
    zone_name: string;
    zone_code: string;
    floor_name: string;
    floor_number: number;
    unit: number;
    unit_number: string;
    unit_status: string;
    property_name: string;
    space_label: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  const PAGE_SIZE = 25;

  const tabs: { key: RegistryTab; label: string }[] = [
    { key: "facilities", label: "Facilities" },
    { key: "floors_zones", label: "Floors & Zones" },
    { key: "spaces", label: "Rooms / Units / Spaces" },
    { key: "classification", label: "Facility Classification" },
    { key: "ownership_lease", label: "Facility Ownership & Lease" },
  ];

  let activeTab = $state<RegistryTab>("facilities");
  let loading = $state(true);
  let refreshing = $state(false);

  let overview = $state<FacilityRegistryOverview | null>(null);

  let facilities = $state<FacilityRegistryItem[]>([]);
  let facilitiesCount = $state(0);
  let facilitiesPage = $state(1);
  let facilitiesLoading = $state(false);

  let floors = $state<FacilityFloorItem[]>([]);
  let floorsCount = $state(0);
  let floorsPage = $state(1);
  let floorsLoading = $state(false);

  let zones = $state<FacilityZoneItem[]>([]);
  let zonesCount = $state(0);
  let zonesPage = $state(1);
  let zonesLoading = $state(false);

  let unitSpaces = $state<FacilityUnitSpaceItem[]>([]);
  let unitSpacesCount = $state(0);
  let unitSpacesPage = $state(1);
  let unitSpacesLoading = $state(false);

  let propertiesLookup = $state<PropertyListItem[]>([]);
  let facilitiesLookup = $state<FacilityRegistryItem[]>([]);
  let floorsLookup = $state<FacilityFloorItem[]>([]);
  let zonesLookup = $state<FacilityZoneItem[]>([]);
  let unitsLookup = $state<Unit[]>([]);

  let showFacilityForm = $state(false);
  let showFloorForm = $state(false);
  let showZoneForm = $state(false);
  let showSpaceForm = $state(false);

  let facilitySaving = $state(false);
  let floorSaving = $state(false);
  let zoneSaving = $state(false);
  let spaceSaving = $state(false);

  let facilityForm = $state({
    property: "",
    facility_code: "",
    facility_classification: "residential",
    ownership_type: "owned",
    lease_start_date: "",
    lease_end_date: "",
    lease_party_name: "",
    lease_amount: "",
    lease_terms: "",
    notes: "",
  });

  let floorForm = $state({
    facility: "",
    name: "",
    floor_code: "",
    floor_number: "0",
    gross_area_sqft: "",
    usage_type: "",
    is_active: true,
  });

  let zoneForm = $state({
    facility: "",
    floor: "",
    name: "",
    zone_code: "",
    zone_type: "other",
    gross_area_sqft: "",
    is_active: true,
  });

  let spaceForm = $state({
    facility: "",
    zone: "",
    unit: "",
    space_label: "",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillFacility() {
    const code = `FAC-${String(Math.floor(Math.random() * 900) + 100)}`;
    const today = new Date().toISOString().slice(0, 10);
    const endDate = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    facilityForm.facility_code = code;
    facilityForm.facility_classification = ["residential", "commercial", "industrial", "mixed_use"][Math.floor(Math.random() * 4)];
    facilityForm.ownership_type = ["owned", "leased", "managed", "mixed"][Math.floor(Math.random() * 4)];
    facilityForm.lease_start_date = today;
    facilityForm.lease_end_date = endDate;
    facilityForm.lease_party_name = "Crescent Property Holdings Ltd";
    facilityForm.lease_amount = String(Math.floor(Math.random() * 5000000) + 500000);
    facilityForm.lease_terms = "12-month renewable lease with 90-day notice period. Annual rent review clause applies.";
    facilityForm.notes = "Primary facility for Lagos Phase 2 operations.";
    if (propertiesLookup.length > 0 && !facilityForm.property) {
      facilityForm.property = String(propertiesLookup[0].id);
    }
  }

  function devFillFloor() {
    const num = Math.floor(Math.random() * 20) + 1;
    floorForm.name = `Floor ${num}`;
    floorForm.floor_code = `FL-${String(num).padStart(2, "0")}`;
    floorForm.floor_number = String(num);
    floorForm.gross_area_sqft = String(Math.floor(Math.random() * 10000) + 2000);
    floorForm.usage_type = ["office", "retail", "residential", "parking", "utility"][Math.floor(Math.random() * 5)];
    floorForm.is_active = true;
    if (facilitiesLookup.length > 0 && !floorForm.facility) {
      floorForm.facility = String(facilitiesLookup[0].id);
    }
  }

  function devFillZone() {
    const types = ["office", "common_area", "utility", "storage", "retail", "other"];
    const type = types[Math.floor(Math.random() * types.length)];
    const num = Math.floor(Math.random() * 50) + 1;
    zoneForm.name = `${type.charAt(0).toUpperCase() + type.slice(1).replace("_", " ")} Zone ${num}`;
    zoneForm.zone_code = `ZN-${String(num).padStart(3, "0")}`;
    zoneForm.zone_type = type;
    zoneForm.gross_area_sqft = String(Math.floor(Math.random() * 3000) + 500);
    zoneForm.is_active = true;
    if (facilitiesLookup.length > 0 && !zoneForm.facility) {
      zoneForm.facility = String(facilitiesLookup[0].id);
    }
  }

  function devFillSpace() {
    const labels = ["Conference Room A", "Server Room 1", "Break Room", "Storage Unit B3", "Reception Lobby", "Open Plan Office 2"];
    spaceForm.space_label = labels[Math.floor(Math.random() * labels.length)];
    spaceForm.notes = "Auto-generated test space for development.";
    if (facilitiesLookup.length > 0 && !spaceForm.facility) {
      spaceForm.facility = String(facilitiesLookup[0].id);
    }
  }

  const facilitiesTotalPages = $derived(Math.max(1, Math.ceil(facilitiesCount / PAGE_SIZE)));
  const floorsTotalPages = $derived(Math.max(1, Math.ceil(floorsCount / PAGE_SIZE)));
  const zonesTotalPages = $derived(Math.max(1, Math.ceil(zonesCount / PAGE_SIZE)));
  const unitSpacesTotalPages = $derived(Math.max(1, Math.ceil(unitSpacesCount / PAGE_SIZE)));

  const zoneFormFloorOptions = $derived.by(() => {
    const facilityId = Number(zoneForm.facility || 0);
    if (!facilityId) return floorsLookup;
    return floorsLookup.filter((row) => row.facility === facilityId);
  });

  const spaceFormZoneOptions = $derived.by(() => {
    const facilityId = Number(spaceForm.facility || 0);
    if (!facilityId) return zonesLookup;
    return zonesLookup.filter((row) => row.facility === facilityId);
  });

  const selectedSpaceFacility = $derived.by(() => {
    const facilityId = Number(spaceForm.facility || 0);
    if (!facilityId) return null;
    return facilitiesLookup.find((row) => row.id === facilityId) ?? null;
  });

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtLabel(value: string | null | undefined): string {
    if (!value) return "--";
    return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
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
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(amount);
  }

  async function fetchOverview() {
    try {
      overview = await api.get<FacilityRegistryOverview>("/facility-management/registry/overview/");
    } catch {
      overview = null;
    }
  }

  async function fetchFacilities() {
    facilitiesLoading = true;
    try {
      const response = await api.get<PaginatedResponse<FacilityRegistryItem>>(
        "/facility-management/registry/facilities/",
        { page: String(facilitiesPage) },
      );
      facilities = response.results;
      facilitiesCount = response.count;
    } catch {
      facilities = [];
      facilitiesCount = 0;
      toast.error("Load failed", "Could not load facility records.");
    } finally {
      facilitiesLoading = false;
    }
  }

  async function fetchFloors() {
    floorsLoading = true;
    try {
      const response = await api.get<PaginatedResponse<FacilityFloorItem>>(
        "/facility-management/registry/floors/",
        { page: String(floorsPage) },
      );
      floors = response.results;
      floorsCount = response.count;
    } catch {
      floors = [];
      floorsCount = 0;
      toast.error("Load failed", "Could not load floor records.");
    } finally {
      floorsLoading = false;
    }
  }

  async function fetchZones() {
    zonesLoading = true;
    try {
      const response = await api.get<PaginatedResponse<FacilityZoneItem>>(
        "/facility-management/registry/zones/",
        { page: String(zonesPage) },
      );
      zones = response.results;
      zonesCount = response.count;
    } catch {
      zones = [];
      zonesCount = 0;
      toast.error("Load failed", "Could not load zone records.");
    } finally {
      zonesLoading = false;
    }
  }

  async function fetchUnitSpaces() {
    unitSpacesLoading = true;
    try {
      const response = await api.get<PaginatedResponse<FacilityUnitSpaceItem>>(
        "/facility-management/registry/unit-spaces/",
        { page: String(unitSpacesPage) },
      );
      unitSpaces = response.results;
      unitSpacesCount = response.count;
    } catch {
      unitSpaces = [];
      unitSpacesCount = 0;
      toast.error("Load failed", "Could not load unit-space mappings.");
    } finally {
      unitSpacesLoading = false;
    }
  }

  async function fetchPropertiesLookup() {
    try {
      const response = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      propertiesLookup = response.results;
    } catch {
      propertiesLookup = [];
    }
  }

  async function fetchFacilitiesLookup() {
    try {
      const response = await api.get<PaginatedResponse<FacilityRegistryItem>>(
        "/facility-management/registry/facilities/",
        { page_size: "200" },
      );
      facilitiesLookup = response.results;
    } catch {
      facilitiesLookup = [];
    }
  }

  async function fetchFloorsLookup(facilityId?: number) {
    try {
      const params: Record<string, string> = { page_size: "400" };
      if (facilityId) params.facility = String(facilityId);
      const response = await api.get<PaginatedResponse<FacilityFloorItem>>(
        "/facility-management/registry/floors/",
        params,
      );
      floorsLookup = response.results;
    } catch {
      floorsLookup = [];
    }
  }

  async function fetchZonesLookup(facilityId?: number) {
    try {
      const params: Record<string, string> = { page_size: "500" };
      if (facilityId) params.facility = String(facilityId);
      const response = await api.get<PaginatedResponse<FacilityZoneItem>>(
        "/facility-management/registry/zones/",
        params,
      );
      zonesLookup = response.results;
    } catch {
      zonesLookup = [];
    }
  }

  async function fetchUnitsLookupForFacility(facilityId?: number) {
    if (!facilityId) {
      unitsLookup = [];
      return;
    }
    try {
      const response = await api.get<PaginatedResponse<Unit>>("/facility-management/registry/units/", {
        page_size: "300",
        facility: String(facilityId),
      });
      unitsLookup = response.results;
    } catch {
      unitsLookup = [];
    }
  }

  async function fetchAllLookups() {
    await Promise.all([
      fetchPropertiesLookup(),
      fetchFacilitiesLookup(),
      fetchFloorsLookup(),
      fetchZonesLookup(),
    ]);
  }

  async function initialize() {
    loading = true;
    await Promise.all([fetchOverview(), fetchFacilities(), fetchFloors(), fetchZones(), fetchUnitSpaces(), fetchAllLookups()]);
    loading = false;
  }

  async function refreshAll() {
    refreshing = true;
    await initialize();
    refreshing = false;
  }

  function resetFacilityForm() {
    facilityForm = {
      property: "",
      facility_code: "",
      facility_classification: "residential",
      ownership_type: "owned",
      lease_start_date: "",
      lease_end_date: "",
      lease_party_name: "",
      lease_amount: "",
      lease_terms: "",
      notes: "",
    };
  }

  function resetFloorForm() {
    floorForm = {
      facility: "",
      name: "",
      floor_code: "",
      floor_number: "0",
      gross_area_sqft: "",
      usage_type: "",
      is_active: true,
    };
  }

  function resetZoneForm() {
    zoneForm = {
      facility: "",
      floor: "",
      name: "",
      zone_code: "",
      zone_type: "other",
      gross_area_sqft: "",
      is_active: true,
    };
  }

  function resetSpaceForm() {
    spaceForm = {
      facility: "",
      zone: "",
      unit: "",
      space_label: "",
      notes: "",
    };
    unitsLookup = [];
  }

  function closeAllFormDrawers() {
    showFacilityForm = false;
    showFloorForm = false;
    showZoneForm = false;
    showSpaceForm = false;
  }

  function openFacilityDrawer() {
    closeAllFormDrawers();
    showFacilityForm = true;
    void fetchPropertiesLookup();
  }

  function closeFacilityDrawer() {
    showFacilityForm = false;
    resetFacilityForm();
  }

  function openFloorDrawer() {
    closeAllFormDrawers();
    showFloorForm = true;
    void fetchFacilitiesLookup();
  }

  function closeFloorDrawer() {
    showFloorForm = false;
    resetFloorForm();
  }

  function openZoneDrawer() {
    closeAllFormDrawers();
    showZoneForm = true;
    void fetchFacilitiesLookup();
    void fetchFloorsLookup();
  }

  function closeZoneDrawer() {
    showZoneForm = false;
    resetZoneForm();
  }

  function openSpaceDrawer() {
    closeAllFormDrawers();
    showSpaceForm = true;
    void fetchFacilitiesLookup();
  }

  function closeSpaceDrawer() {
    showSpaceForm = false;
    resetSpaceForm();
  }

  async function handleFacilityCreate(event: Event) {
    event.preventDefault();
    if (!facilityForm.property || !facilityForm.facility_code.trim()) {
      toast.error("Missing data", "Facility property and code are required.");
      return;
    }
    facilitySaving = true;
    try {
      await api.post("/facility-management/registry/facilities/", {
        property: Number(facilityForm.property),
        facility_code: facilityForm.facility_code.trim(),
        facility_classification: facilityForm.facility_classification,
        ownership_type: facilityForm.ownership_type,
        lease_start_date: facilityForm.lease_start_date || null,
        lease_end_date: facilityForm.lease_end_date || null,
        lease_party_name: facilityForm.lease_party_name.trim(),
        lease_amount: facilityForm.lease_amount || null,
        lease_terms: facilityForm.lease_terms.trim(),
        notes: facilityForm.notes.trim(),
      });
      toast.success("Facility created", "Registry record has been created.");
      closeFacilityDrawer();
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the form fields.");
      } else {
        toast.error("Create failed", "Could not create facility.");
      }
    } finally {
      facilitySaving = false;
    }
  }

  async function handleFloorCreate(event: Event) {
    event.preventDefault();
    if (!floorForm.facility || !floorForm.name.trim()) {
      toast.error("Missing data", "Facility and floor name are required.");
      return;
    }
    floorSaving = true;
    try {
      await api.post("/facility-management/registry/floors/", {
        facility: Number(floorForm.facility),
        name: floorForm.name.trim(),
        floor_code: floorForm.floor_code.trim(),
        floor_number: Number(floorForm.floor_number || 0),
        gross_area_sqft: floorForm.gross_area_sqft || null,
        usage_type: floorForm.usage_type.trim(),
        is_active: floorForm.is_active,
      });
      toast.success("Floor created", "Floor record has been created.");
      closeFloorDrawer();
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the form fields.");
      } else {
        toast.error("Create failed", "Could not create floor.");
      }
    } finally {
      floorSaving = false;
    }
  }

  async function handleZoneCreate(event: Event) {
    event.preventDefault();
    if (!zoneForm.facility || !zoneForm.floor || !zoneForm.name.trim() || !zoneForm.zone_code.trim()) {
      toast.error("Missing data", "Facility, floor, zone name, and zone code are required.");
      return;
    }
    zoneSaving = true;
    try {
      await api.post("/facility-management/registry/zones/", {
        facility: Number(zoneForm.facility),
        floor: Number(zoneForm.floor),
        name: zoneForm.name.trim(),
        zone_code: zoneForm.zone_code.trim(),
        zone_type: zoneForm.zone_type,
        gross_area_sqft: zoneForm.gross_area_sqft || null,
        is_active: zoneForm.is_active,
      });
      toast.success("Zone created", "Zone record has been created.");
      closeZoneDrawer();
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the form fields.");
      } else {
        toast.error("Create failed", "Could not create zone.");
      }
    } finally {
      zoneSaving = false;
    }
  }

  async function handleSpaceCreate(event: Event) {
    event.preventDefault();
    if (!spaceForm.facility || !spaceForm.zone || !spaceForm.unit) {
      toast.error("Missing data", "Facility, zone, and unit are required.");
      return;
    }
    spaceSaving = true;
    try {
      await api.post("/facility-management/registry/unit-spaces/", {
        facility: Number(spaceForm.facility),
        zone: Number(spaceForm.zone),
        unit: Number(spaceForm.unit),
        space_label: spaceForm.space_label.trim(),
        notes: spaceForm.notes.trim(),
      });
      toast.success("Unit mapped", "Unit/space mapping has been created.");
      closeSpaceDrawer();
      await refreshAll();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Validation error", Object.values(error.fieldErrors).flat().join(" ") || "Check the form fields.");
      } else {
        toast.error("Create failed", "Could not create unit-space mapping.");
      }
    } finally {
      spaceSaving = false;
    }
  }

  function goToFacilitiesPage(page: number) {
    if (page < 1 || page > facilitiesTotalPages || page === facilitiesPage) return;
    facilitiesPage = page;
    fetchFacilities();
  }

  function goToFloorsPage(page: number) {
    if (page < 1 || page > floorsTotalPages || page === floorsPage) return;
    floorsPage = page;
    fetchFloors();
  }

  function goToZonesPage(page: number) {
    if (page < 1 || page > zonesTotalPages || page === zonesPage) return;
    zonesPage = page;
    fetchZones();
  }

  function goToUnitSpacesPage(page: number) {
    if (page < 1 || page > unitSpacesTotalPages || page === unitSpacesPage) return;
    unitSpacesPage = page;
    fetchUnitSpaces();
  }

  $effect(() => {
    initialize();
  });

  let previousZoneFacility = "";
  $effect(() => {
    const facilityId = zoneForm.facility;
    if (!showZoneForm) {
      previousZoneFacility = "";
      return;
    }
    if (facilityId === previousZoneFacility) return;
    previousZoneFacility = facilityId;
    zoneForm.floor = "";
    void fetchFloorsLookup(Number(facilityId || 0) || undefined);
  });

  let previousSpaceFacility = "";
  $effect(() => {
    const facilityId = spaceForm.facility;
    if (!showSpaceForm) {
      previousSpaceFacility = "";
      return;
    }
    if (facilityId === previousSpaceFacility) return;
    previousSpaceFacility = facilityId;
    spaceForm.zone = "";
    spaceForm.unit = "";
    void Promise.all([
      fetchZonesLookup(Number(facilityId || 0) || undefined),
      fetchUnitsLookupForFacility(Number(facilityId || 0) || undefined),
    ]);
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-500">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-800 tracking-wide">Facility Registry</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Core system of record for facilities, floor/zone hierarchy, units/spaces, classification, and lease ownership posture.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>
    <button
      onclick={refreshAll}
      disabled={refreshing || loading}
      class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50"
      aria-label={refreshing ? "Refreshing facility registry" : "Refresh facility registry"}
      title={refreshing ? "Refreshing facility registry" : "Refresh facility registry"}
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

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
    <section class="rounded-2xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-4">
      <p class="text-xs uppercase tracking-wide text-emerald-700">Facilities</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.facilities)}</p>
    </section>
    <section class="rounded-2xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-4">
      <p class="text-xs uppercase tracking-wide text-emerald-700">Floors</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.floors)}</p>
    </section>
    <section class="rounded-2xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-4">
      <p class="text-xs uppercase tracking-wide text-emerald-700">Zones</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.zones)}</p>
    </section>
    <section class="rounded-2xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-4">
      <p class="text-xs uppercase tracking-wide text-emerald-700">Unit Spaces</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.unit_spaces)}</p>
    </section>
    <section class="rounded-2xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-4">
      <p class="text-xs uppercase tracking-wide text-emerald-700">Leased Facilities</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.leased_facilities)}</p>
    </section>
    <section class="rounded-2xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-4">
      <p class="text-xs uppercase tracking-wide text-emerald-700">Lease Expiring (90d)</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.lease_expiring_90_days)}</p>
    </section>
  </div>

  <div class="flex flex-wrap gap-2">
    {#each tabs as tab}
      <button
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

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      Loading facility registry...
    </div>
  {:else}
    {#if activeTab === "facilities"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Facilities</h2>
          <button
            onclick={openFacilityDrawer}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Add Facility
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Code</th>
                <th class="px-3 py-2">Facility</th>
                <th class="px-3 py-2">Type</th>
                <th class="px-3 py-2">Classification</th>
                <th class="px-3 py-2">Ownership</th>
                <th class="px-3 py-2">Lease End</th>
                <th class="px-3 py-2">Hierarchy</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if facilitiesLoading}
                <tr><td colspan="7" class="px-3 py-6 text-center text-neutral-500">Loading facilities...</td></tr>
              {:else if facilities.length === 0}
                <tr><td colspan="7" class="px-3 py-6 text-center text-neutral-500">No facility records yet.</td></tr>
              {:else}
                {#each facilities as row (row.id)}
                  <tr>
                    <td class="px-3 py-3 font-medium text-neutral-900">{row.facility_code}</td>
                    <td class="px-3 py-3">
                      <p class="font-medium text-neutral-900">{row.property_name}</p>
                      <p class="text-xs text-neutral-500">{row.property_address}</p>
                    </td>
                    <td class="px-3 py-3">{fmtLabel(row.property_type)}</td>
                    <td class="px-3 py-3">{fmtLabel(row.facility_classification)}</td>
                    <td class="px-3 py-3">{fmtLabel(row.ownership_type)}</td>
                    <td class="px-3 py-3">{fmtDate(row.lease_end_date)}</td>
                    <td class="px-3 py-3 text-xs text-neutral-600">
                      Floors: {row.floors_count} | Zones: {row.zones_count} | Units: {row.unit_spaces_count}
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-end gap-2">
          <button onclick={() => goToFacilitiesPage(facilitiesPage - 1)} disabled={facilitiesPage <= 1} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-500">Page {facilitiesPage} of {facilitiesTotalPages}</span>
          <button onclick={() => goToFacilitiesPage(facilitiesPage + 1)} disabled={facilitiesPage >= facilitiesTotalPages} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Next</button>
        </div>
      </section>
    {/if}

    {#if activeTab === "floors_zones"}
      <div class="grid gap-4 xl:grid-cols-2">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Floors</h2>
            <button
              onclick={openFloorDrawer}
              class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
            >
              Add Floor
            </button>
          </div>

          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-3 py-2">Facility</th>
                  <th class="px-3 py-2">Floor</th>
                  <th class="px-3 py-2">Code</th>
                  <th class="px-3 py-2">Zones</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if floorsLoading}
                  <tr><td colspan="4" class="px-3 py-6 text-center text-neutral-500">Loading floors...</td></tr>
                {:else if floors.length === 0}
                  <tr><td colspan="4" class="px-3 py-6 text-center text-neutral-500">No floor records.</td></tr>
                {:else}
                  {#each floors as row (row.id)}
                    <tr>
                      <td class="px-3 py-3 text-neutral-800">{row.facility_code}</td>
                      <td class="px-3 py-3">
                        <p class="font-medium text-neutral-900">{row.name}</p>
                        <p class="text-xs text-neutral-500">No. {row.floor_number}</p>
                      </td>
                      <td class="px-3 py-3">{row.floor_code || "--"}</td>
                      <td class="px-3 py-3">{row.zone_count}</td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
          <div class="flex items-center justify-end gap-2">
            <button onclick={() => goToFloorsPage(floorsPage - 1)} disabled={floorsPage <= 1} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Previous</button>
            <span class="text-xs text-neutral-500">Page {floorsPage} of {floorsTotalPages}</span>
            <button onclick={() => goToFloorsPage(floorsPage + 1)} disabled={floorsPage >= floorsTotalPages} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Next</button>
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Zones</h2>
            <button
              onclick={openZoneDrawer}
              class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
            >
              Add Zone
            </button>
          </div>

          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-3 py-2">Facility</th>
                  <th class="px-3 py-2">Zone</th>
                  <th class="px-3 py-2">Floor</th>
                  <th class="px-3 py-2">Units</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if zonesLoading}
                  <tr><td colspan="4" class="px-3 py-6 text-center text-neutral-500">Loading zones...</td></tr>
                {:else if zones.length === 0}
                  <tr><td colspan="4" class="px-3 py-6 text-center text-neutral-500">No zone records.</td></tr>
                {:else}
                  {#each zones as row (row.id)}
                    <tr>
                      <td class="px-3 py-3 text-neutral-800">{row.facility_code}</td>
                      <td class="px-3 py-3">
                        <p class="font-medium text-neutral-900">{row.name}</p>
                        <p class="text-xs text-neutral-500">{row.zone_code}</p>
                      </td>
                      <td class="px-3 py-3 text-neutral-700">Floor {row.floor_number}</td>
                      <td class="px-3 py-3">{row.unit_spaces_count}</td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
          <div class="flex items-center justify-end gap-2">
            <button onclick={() => goToZonesPage(zonesPage - 1)} disabled={zonesPage <= 1} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Previous</button>
            <span class="text-xs text-neutral-500">Page {zonesPage} of {zonesTotalPages}</span>
            <button onclick={() => goToZonesPage(zonesPage + 1)} disabled={zonesPage >= zonesTotalPages} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Next</button>
          </div>
        </section>
      </div>
    {/if}

    {#if activeTab === "spaces"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Rooms / Units / Spaces</h2>
          <button
            onclick={openSpaceDrawer}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Map Unit To Zone
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Facility</th>
                <th class="px-3 py-2">Floor / Zone</th>
                <th class="px-3 py-2">Unit</th>
                <th class="px-3 py-2">Status</th>
                <th class="px-3 py-2">Space Label</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if unitSpacesLoading}
                <tr><td colspan="5" class="px-3 py-6 text-center text-neutral-500">Loading unit-space mappings...</td></tr>
              {:else if unitSpaces.length === 0}
                <tr><td colspan="5" class="px-3 py-6 text-center text-neutral-500">No mapped spaces.</td></tr>
              {:else}
                {#each unitSpaces as row (row.id)}
                  <tr>
                    <td class="px-3 py-3">
                      <p class="font-medium text-neutral-900">{row.facility_code}</p>
                      <p class="text-xs text-neutral-500">{row.facility_name}</p>
                    </td>
                    <td class="px-3 py-3">
                      <p class="text-neutral-800">Floor {row.floor_number} - {row.floor_name}</p>
                      <p class="text-xs text-neutral-500">{row.zone_code} ({row.zone_name})</p>
                    </td>
                    <td class="px-3 py-3 font-medium text-neutral-900">{row.unit_number}</td>
                    <td class="px-3 py-3">{fmtLabel(row.unit_status)}</td>
                    <td class="px-3 py-3">{row.space_label || "--"}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
        <div class="flex items-center justify-end gap-2">
          <button onclick={() => goToUnitSpacesPage(unitSpacesPage - 1)} disabled={unitSpacesPage <= 1} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-500">Page {unitSpacesPage} of {unitSpacesTotalPages}</span>
          <button onclick={() => goToUnitSpacesPage(unitSpacesPage + 1)} disabled={unitSpacesPage >= unitSpacesTotalPages} class="rounded border border-neutral-300 px-3 py-1.5 text-xs text-neutral-700 disabled:opacity-40">Next</button>
        </div>
      </section>
    {/if}

    {#if activeTab === "classification"}
      <div class="grid gap-4 lg:grid-cols-2">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Facility Classification Mix</h2>
          <div class="space-y-2">
            {#if !overview || overview.classification_breakdown.length === 0}
              <p class="text-sm text-neutral-500">No classification data yet.</p>
            {:else}
              {#each overview.classification_breakdown as item}
                <div class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <span class="text-sm text-neutral-700">{fmtLabel(item.key)}</span>
                  <span class="text-sm font-semibold text-neutral-900">{item.count}</span>
                </div>
              {/each}
            {/if}
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Facility Type Mix</h2>
          <div class="space-y-2">
            {#if !overview || overview.facility_type_breakdown.length === 0}
              <p class="text-sm text-neutral-500">No facility type data yet.</p>
            {:else}
              {#each overview.facility_type_breakdown as item}
                <div class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <span class="text-sm text-neutral-700">{fmtLabel(item.key)}</span>
                  <span class="text-sm font-semibold text-neutral-900">{item.count}</span>
                </div>
              {/each}
            {/if}
          </div>
        </section>
      </div>
    {/if}

    {#if activeTab === "ownership_lease"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 space-y-4">
        <div class="grid gap-3 sm:grid-cols-2">
          <div class="rounded-xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-3">
            <p class="text-xs uppercase tracking-wide text-emerald-700">Leased Facilities</p>
            <p class="mt-1 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.leased_facilities)}</p>
          </div>
          <div class="rounded-xl border border-emerald-200/80 bg-linear-to-br from-emerald-50 via-green-50 to-lime-50 p-3">
            <p class="text-xs uppercase tracking-wide text-emerald-700">Lease Expiring In 90 Days</p>
            <p class="mt-1 text-2xl font-semibold text-neutral-900">{toNumber(overview?.kpis.lease_expiring_90_days)}</p>
          </div>
        </div>

        <div class="space-y-2">
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Ownership Type Breakdown</h2>
          {#if !overview || overview.ownership_breakdown.length === 0}
            <p class="text-sm text-neutral-500">No ownership data yet.</p>
          {:else}
            <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
              {#each overview.ownership_breakdown as item}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <p class="text-xs uppercase tracking-wide text-neutral-500">{fmtLabel(item.key)}</p>
                  <p class="text-lg font-semibold text-neutral-900">{item.count}</p>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-3 py-2">Facility</th>
                <th class="px-3 py-2">Ownership</th>
                <th class="px-3 py-2">Lease Party</th>
                <th class="px-3 py-2">Lease Start</th>
                <th class="px-3 py-2">Lease End</th>
                <th class="px-3 py-2">Lease Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if facilities.length === 0}
                <tr><td colspan="6" class="px-3 py-6 text-center text-neutral-500">No facility records available.</td></tr>
              {:else}
                {#each facilities as row (row.id)}
                  <tr>
                    <td class="px-3 py-3">
                      <p class="font-medium text-neutral-900">{row.facility_code}</p>
                      <p class="text-xs text-neutral-500">{row.property_name}</p>
                    </td>
                    <td class="px-3 py-3">{fmtLabel(row.ownership_type)}</td>
                    <td class="px-3 py-3">{row.lease_party_name || "--"}</td>
                    <td class="px-3 py-3">{fmtDate(row.lease_start_date)}</td>
                    <td class="px-3 py-3">{fmtDate(row.lease_end_date)}</td>
                    <td class="px-3 py-3">{fmtMoney(row.lease_amount)}</td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}
  {/if}
</div>

{#if showFacilityForm}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeFacilityDrawer}
    tabindex="-1"
    aria-label="Close facility drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Add Facility</h2>
      <button
        type="button"
        onclick={closeFacilityDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close facility drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-drawer-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleFacilityCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Property</span>
          <select bind:value={facilityForm.property} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select property</option>
            {#each propertiesLookup as property}
              <option value={String(property.id)}>{property.name} {property.address ? `- ${property.address}` : ""}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility Code</span>
          <input bind:value={facilityForm.facility_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="FAC-001" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Classification</span>
          <select bind:value={facilityForm.facility_classification} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="residential">Residential</option>
            <option value="commercial">Commercial</option>
            <option value="industrial">Industrial</option>
            <option value="mixed_use">Mixed Use</option>
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Ownership Type</span>
          <select bind:value={facilityForm.ownership_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="owned">Owned</option>
            <option value="leased">Leased</option>
            <option value="managed">Managed</option>
            <option value="mixed">Mixed</option>
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Lease Start Date</span>
          <input type="date" bind:value={facilityForm.lease_start_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Lease End Date</span>
          <input type="date" bind:value={facilityForm.lease_end_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Lease Party Name</span>
          <input bind:value={facilityForm.lease_party_name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Landlord / lessor" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Lease Amount</span>
          <input type="number" step="0.01" bind:value={facilityForm.lease_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="0.00" />
        </label>

        <label class="md:col-span-2 text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Lease Terms</span>
          <textarea rows="3" bind:value={facilityForm.lease_terms} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Enter lease clauses, review windows, or renewal notes"></textarea>
        </label>
        <label class="md:col-span-2 text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea rows="3" bind:value={facilityForm.notes} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Any operational or registry notes"></textarea>
        </label>

        {#if propertiesLookup.length === 0}
          <p class="md:col-span-2 text-sm text-amber-700">
            No properties are available yet. Create or sync a property first before registering a facility.
          </p>
        {/if}
      </form>
    </div>
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillFacility} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeFacilityDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-drawer-form"
        disabled={facilitySaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {facilitySaving ? "Saving..." : "Save Facility"}
      </button>
    </div>
  </aside>
{/if}

{#if showFloorForm}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeFloorDrawer}
    tabindex="-1"
    aria-label="Close floor drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Add Floor</h2>
      <button
        type="button"
        onclick={closeFloorDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close floor drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="floor-drawer-form" class="space-y-4" onsubmit={handleFloorCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={floorForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Floor Name</span>
          <input bind:value={floorForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Ground Floor" />
        </label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Floor Number</span>
            <input type="number" bind:value={floorForm.floor_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Floor Code</span>
            <input bind:value={floorForm.floor_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="GF" />
          </label>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Area (sqft)</span>
            <input type="number" step="0.01" bind:value={floorForm.gross_area_sqft} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Usage Type</span>
            <input bind:value={floorForm.usage_type} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Commercial" />
          </label>
        </div>
        <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
          <input type="checkbox" bind:checked={floorForm.is_active} class="rounded border-neutral-300" />
          Floor is active
        </label>
      </form>
    </div>
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillFloor} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeFloorDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="floor-drawer-form"
        disabled={floorSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {floorSaving ? "Saving..." : "Save Floor"}
      </button>
    </div>
  </aside>
{/if}

{#if showZoneForm}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeZoneDrawer}
    tabindex="-1"
    aria-label="Close zone drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Add Zone</h2>
      <button
        type="button"
        onclick={closeZoneDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close zone drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="zone-drawer-form" class="space-y-4" onsubmit={handleZoneCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={zoneForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Floor</span>
          <select bind:value={zoneForm.floor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select floor</option>
            {#each zoneFormFloorOptions as floor}
              <option value={String(floor.id)}>Floor {floor.floor_number} - {floor.name}</option>
            {/each}
          </select>
        </label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Zone Name</span>
            <input bind:value={zoneForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="North Wing" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Zone Code</span>
            <input bind:value={zoneForm.zone_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="NW-01" />
          </label>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Zone Type</span>
            <select bind:value={zoneForm.zone_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="residential">Residential</option>
              <option value="commercial">Commercial</option>
              <option value="industrial">Industrial</option>
              <option value="common">Common Area</option>
              <option value="amenity">Amenity</option>
              <option value="service">Service</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Area (sqft)</span>
            <input type="number" step="0.01" bind:value={zoneForm.gross_area_sqft} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>
        </div>
        <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
          <input type="checkbox" bind:checked={zoneForm.is_active} class="rounded border-neutral-300" />
          Zone is active
        </label>
      </form>
    </div>
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillZone} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeZoneDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="zone-drawer-form"
        disabled={zoneSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {zoneSaving ? "Saving..." : "Save Zone"}
      </button>
    </div>
  </aside>
{/if}

{#if showSpaceForm}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeSpaceDrawer}
    tabindex="-1"
    aria-label="Close space drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-lg font-semibold text-neutral-900">Map Unit To Zone</h2>
      <button
        type="button"
        onclick={closeSpaceDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close space drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="space-drawer-form" class="space-y-4" onsubmit={handleSpaceCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={spaceForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Zone</span>
          <select bind:value={spaceForm.zone} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select zone</option>
            {#each spaceFormZoneOptions as zone}
              <option value={String(zone.id)}>Floor {zone.floor_number} - {zone.zone_code} ({zone.name})</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Unit</span>
          <select bind:value={spaceForm.unit} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select unit</option>
            {#each unitsLookup as unit}
              <option value={String(unit.id)}>{unit.unit_number} ({fmtLabel(unit.status)})</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Space Label</span>
          <input bind:value={spaceForm.space_label} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Showroom A1" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea rows="2" bind:value={spaceForm.notes} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"></textarea>
        </label>
        {#if selectedSpaceFacility}
          <p class="text-sm text-neutral-500">
            Selected facility property: {selectedSpaceFacility.property_name}
          </p>
        {/if}
      </form>
    </div>
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillSpace} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeSpaceDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="space-drawer-form"
        disabled={spaceSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {spaceSaving ? "Saving..." : "Save Mapping"}
      </button>
    </div>
  </aside>
{/if}

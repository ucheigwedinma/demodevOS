<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EquipmentDetailDrawer from "./EquipmentDetailDrawer.svelte";
  import type {
    EquipmentListItem,
    EquipmentFleetKpis,
    EquipmentStatus,
    EquipmentType as EqType,
    EquipmentOwnership,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // ── State ──────────────────────────────────────────────────────────────
  let loading = $state(true);
  let rows = $state<EquipmentListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let kpis = $state<EquipmentFleetKpis | null>(null);

  // Filters
  let searchInput = $state("");
  let searchQuery = $state("");
  let statusFilter = $state("");
  let typeFilter = $state("");
  let ownershipFilter = $state("");

  // Pagination
  let currentPage = $state(1);
  let pageSize = $state(15);
  let totalCount = $state(0);
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  // Drawer
  let selectedEquipmentId = $state<number | null>(null);
  let drawerOpen = $state(false);

  // Create drawer
  let showCreateDrawer = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      name: "",
      equipment_type: "other" as EqType,
      status: "idle" as EquipmentStatus,
      make: "",
      model_name: "",
      year_of_manufacture: "",
      serial_number: "",
      engine_number: "",
      fuel_type: "diesel",
      fuel_consumption_rate: "",
      capacity: "",
      weight_kg: "",
      current_project: "",
      current_location: "",
      current_operator: "",
      operator_license_verified: false,
      hour_meter_reading: "0",
      odometer_reading: "0",
      last_service_date: "",
      next_service_due: "",
      service_interval_hours: "",
      ownership: "owned" as EquipmentOwnership,
      purchase_price: "",
      current_book_value: "",
      internal_daily_rate: "",
      internal_hourly_rate: "",
      mobilization_cost: "",
      insurance_policy_number: "",
      insurance_expiry: "",
      notes: "",
    };
  }

  type EqForm = ReturnType<typeof defaultForm>;
  const EQUIPMENT_SAMPLES: EqForm[] = [
    {
      name: "Hyster Forklift (3 Ton)",
      equipment_type: "material_handling",
      status: "operational",
      make: "Hyster",
      model_name: "H3.0FT",
      year_of_manufacture: "2022",
      serial_number: "H3FT-22-004871",
      engine_number: "YM-4TNV98",
      fuel_type: "diesel",
      fuel_consumption_rate: "4.5",
      capacity: "3 Ton",
      weight_kg: "4620",
      current_project: "",
      current_location: "Abuja Phase 2",
      current_operator: "Chukwuemeka Obi",
      operator_license_verified: true,
      hour_meter_reading: "3842",
      odometer_reading: "0",
      last_service_date: "2026-01-15",
      next_service_due: "2026-04-15",
      service_interval_hours: "500",
      ownership: "owned",
      purchase_price: "12500000",
      current_book_value: "9800000",
      internal_daily_rate: "25000",
      internal_hourly_rate: "3500",
      mobilization_cost: "150000",
      insurance_policy_number: "INS-EQ-2026-0041",
      insurance_expiry: "2027-01-31",
      notes: "Solid pneumatic tyres fitted. Scheduled for transmission fluid change at next service.",
    },
    {
      name: "JCB Backhoe Loader 3CX",
      equipment_type: "earthmoving",
      status: "in_repair",
      make: "JCB",
      model_name: "3CX",
      year_of_manufacture: "2020",
      serial_number: "JCB3CX-20-916445",
      engine_number: "JCB-DI-55kW",
      fuel_type: "diesel",
      fuel_consumption_rate: "8.2",
      capacity: "1 m³ bucket",
      weight_kg: "8070",
      current_project: "",
      current_location: "Lekki Site — Workshop Bay",
      current_operator: "",
      operator_license_verified: false,
      hour_meter_reading: "6210",
      odometer_reading: "14500",
      last_service_date: "2026-02-20",
      next_service_due: "2026-05-20",
      service_interval_hours: "500",
      ownership: "owned",
      purchase_price: "32000000",
      current_book_value: "21500000",
      internal_daily_rate: "45000",
      internal_hourly_rate: "6000",
      mobilization_cost: "350000",
      insurance_policy_number: "INS-EQ-2026-0012",
      insurance_expiry: "2026-12-31",
      notes: "Hydraulic hose replacement in progress. Expected return to service in 3 days.",
    },
    {
      name: "Liebherr Mobile Crane LTM 1100",
      equipment_type: "lifting",
      status: "idle",
      make: "Liebherr",
      model_name: "LTM 1100-4.2",
      year_of_manufacture: "2019",
      serial_number: "LTM-1100-19-007823",
      engine_number: "LBH-D936-A6",
      fuel_type: "diesel",
      fuel_consumption_rate: "28.5",
      capacity: "100 Ton",
      weight_kg: "60000",
      current_project: "",
      current_location: "Central Warehouse",
      current_operator: "",
      operator_license_verified: false,
      hour_meter_reading: "4180",
      odometer_reading: "32400",
      last_service_date: "2025-12-10",
      next_service_due: "2026-03-10",
      service_interval_hours: "250",
      ownership: "leased",
      purchase_price: "",
      current_book_value: "",
      internal_daily_rate: "180000",
      internal_hourly_rate: "25000",
      mobilization_cost: "850000",
      insurance_policy_number: "INS-EQ-2025-0089",
      insurance_expiry: "2026-06-30",
      notes: "Leased from Liebherr Nigeria. Next deployment pending Lekki Tower project confirmation.",
    },
    {
      name: "CAT D6 Bulldozer",
      equipment_type: "earthmoving",
      status: "operational",
      make: "Caterpillar",
      model_name: "D6T XL",
      year_of_manufacture: "2021",
      serial_number: "CAT-D6T-21-RKG03487",
      engine_number: "C9.3B-ACERT",
      fuel_type: "diesel",
      fuel_consumption_rate: "22.0",
      capacity: "185 HP",
      weight_kg: "22000",
      current_project: "",
      current_location: "Ikeja Residential Phase 3",
      current_operator: "Adamu Bello",
      operator_license_verified: true,
      hour_meter_reading: "5460",
      odometer_reading: "0",
      last_service_date: "2026-02-28",
      next_service_due: "2026-05-28",
      service_interval_hours: "500",
      ownership: "owned",
      purchase_price: "95000000",
      current_book_value: "72000000",
      internal_daily_rate: "120000",
      internal_hourly_rate: "16000",
      mobilization_cost: "500000",
      insurance_policy_number: "INS-EQ-2026-0033",
      insurance_expiry: "2027-02-28",
      notes: "Fitted with GPS tracking module. Blade edge wear at 60% — schedule replacement at next service.",
    },
  ];

  let devIdx = 0;
  function devFillEquipment() {
    const sample = EQUIPMENT_SAMPLES[devIdx % EQUIPMENT_SAMPLES.length];
    devIdx++;
    form = {
      ...sample,
      current_project: form.current_project || (projects.length > 0 ? String(projects[0].id) : ""),
    };
  }

  // ── Data fetching ─────────────────────────────────────────────────────

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  async function fetchEquipment() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.equipment_type = typeFilter;
      if (ownershipFilter) params.ownership = ownershipFilter;

      const [res, kpiRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<EquipmentListItem>>("/projects/equipment/", params),
        api.get<EquipmentFleetKpis>("/projects/equipment/fleet-kpis/"),
        projects.length === 0
          ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" })
          : Promise.resolve(null),
      ]);

      rows = res.results;
      totalCount = res.count;
      kpis = kpiRes;
      if (projRes) projects = projRes.results;
    } catch {
      rows = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => {
    void searchQuery;
    void statusFilter;
    void typeFilter;
    void ownershipFilter;
    void currentPage;
    fetchEquipment();
  });

  function onSearchInput(event: Event) {
    searchInput = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim().toLowerCase();
      currentPage = 1;
    }, 250);
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    statusFilter = "";
    typeFilter = "";
    ownershipFilter = "";
    currentPage = 1;
  }

  function fmtCurrency(value: string | number | null | undefined): string {
    if (!value) return "--";
    return currency.formatCompact(value);
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "--";
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function openDetail(id: number) {
    selectedEquipmentId = id;
    drawerOpen = true;
  }

  function resetCreateForm() {
    form = defaultForm();
  }

  async function saveEquipment(event: Event) {
    event.preventDefault();
    if (!form.name.trim()) {
      toast.error("Validation error", "Equipment name is required.");
      return;
    }

    saving = true;
    try {
      const payload: Record<string, unknown> = {
        ...form,
        year_of_manufacture: form.year_of_manufacture ? Number(form.year_of_manufacture) : null,
        fuel_consumption_rate: form.fuel_consumption_rate || null,
        weight_kg: form.weight_kg || null,
        current_project: form.current_project ? Number(form.current_project) : null,
        hour_meter_reading: form.hour_meter_reading || "0",
        odometer_reading: form.odometer_reading || "0",
        service_interval_hours: form.service_interval_hours ? Number(form.service_interval_hours) : null,
        purchase_price: form.purchase_price || null,
        current_book_value: form.current_book_value || null,
        internal_daily_rate: form.internal_daily_rate || null,
        internal_hourly_rate: form.internal_hourly_rate || null,
        mobilization_cost: form.mobilization_cost || null,
        last_service_date: form.last_service_date || null,
        next_service_due: form.next_service_due || null,
        insurance_expiry: form.insurance_expiry || null,
      };
      await api.post("/projects/equipment/", payload);
      toast.success("Equipment registered", `"${form.name}" has been added to the fleet.`);
      showCreateDrawer = false;
      resetCreateForm();
      await fetchEquipment();
    } catch (error) {
      if (error instanceof ApiError) {
        const firstField = Object.values(error.fieldErrors)[0]?.[0];
        toast.error("Save failed", firstField ?? "Could not register equipment.");
      } else {
        toast.error("Save failed", "Could not register equipment.");
      }
    } finally {
      saving = false;
    }
  }

  const startRow = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endRow = $derived(Math.min(currentPage * pageSize, totalCount));
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Equipment & Machinery</h1>
      <p class="mt-1 text-sm text-neutral-500">Central registry for high-value physical assets — track, maintain, and recover costs.</p>
    </div>
    <div class="flex items-center gap-2">
      <button
        onclick={() => { resetCreateForm(); showCreateDrawer = true; }}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
      >
        + Register Equipment
      </button>
      <button
        onclick={fetchEquipment}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>
  </div>

  <!-- KPI Cards -->
  {#if kpis}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-600">Fleet Value</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{fmtCurrency(kpis.total_book_value)}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Deployment Rate</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{kpis.deployment_rate}%</p>
      </div>
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Maintenance Due</p>
        <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{kpis.maintenance_due}</p>
      </div>
      <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Utilization Index</p>
        <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{kpis.utilization_index}%</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Fleet</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{kpis.total_fleet}</p>
      </div>
      <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">In Repair</p>
        <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{kpis.in_repair}</p>
      </div>
    </div>
  {/if}

  <!-- Filter Bar + Table -->
  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4 sm:p-5">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <input
          type="text"
          value={searchInput}
          oninput={onSearchInput}
          placeholder="Search asset ID, name, location..."
          class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />

        <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="operational">Operational</option>
          <option value="in_repair">In Repair</option>
          <option value="idle">Idle</option>
          <option value="in_transit">In Transit</option>
          <option value="decommissioned">Decommissioned</option>
        </select>

        <select bind:value={typeFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Types</option>
          <option value="earthmoving">Earthmoving</option>
          <option value="lifting">Lifting</option>
          <option value="material_handling">Material Handling</option>
          <option value="concrete">Concrete</option>
          <option value="piling">Piling</option>
          <option value="compaction">Compaction</option>
          <option value="transport">Transport</option>
          <option value="scaffolding">Scaffolding</option>
          <option value="power_generation">Power Generation</option>
          <option value="other">Other</option>
        </select>

        <select bind:value={ownershipFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Ownership</option>
          <option value="owned">Owned</option>
          <option value="leased">Leased</option>
          <option value="rented">Rented</option>
        </select>
      </div>

      <div class="mt-3 flex justify-end">
        <button onclick={resetFilters} class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100">
          Reset filters
        </button>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if rows.length === 0}
      <div class="px-6 py-14 text-center">
        <p class="text-sm text-neutral-500">No equipment matches the current filters.</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[980px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Asset ID</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Equipment</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Location</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Book Value</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Last Service</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as row}
              <tr
                class="hover:bg-neutral-50 cursor-pointer"
                onclick={() => openDetail(row.id)}
              >
                <td class="px-4 py-3">
                  <p class="text-sm font-semibold text-neutral-900">{row.asset_id}</p>
                </td>
                <td class="px-4 py-3">
                  <p class="text-sm font-medium text-neutral-900">{row.name}</p>
                  <p class="mt-0.5 text-xs text-neutral-500">{row.make} {row.model_name}</p>
                </td>
                <td class="px-4 py-3">
                  <span class="text-xs font-medium text-neutral-600">{row.equipment_type_display}</span>
                </td>
                <td class="px-4 py-3">
                  <p class="text-sm text-neutral-700 max-w-[200px] truncate">{row.current_location || "--"}</p>
                  {#if row.current_project_name}
                    <p class="mt-0.5 text-xs text-neutral-400">{row.current_project_name}</p>
                  {/if}
                </td>
                <td class="px-4 py-3">
                  <StatusBadge status={row.status} />
                  {#if row.maintenance_due}
                    <span class="ml-1 inline-block px-1.5 py-0.5 text-[9px] font-semibold bg-orange-100 text-orange-700 rounded">SERVICE DUE</span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-right text-sm font-semibold tabular-nums text-neutral-900">
                  {fmtCurrency(row.current_book_value)}
                </td>
                <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(row.last_service_date)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-4 py-3">
        <p class="text-xs text-neutral-500">
          Showing <span class="font-semibold text-neutral-700">{startRow}</span>–<span class="font-semibold text-neutral-700">{endRow}</span> of
          <span class="font-semibold text-neutral-700">{totalCount}</span>
        </p>
        <div class="flex items-center gap-2">
          <button
            onclick={() => (currentPage = Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>
          <span class="text-xs font-medium text-neutral-600">Page {currentPage} of {totalPages}</span>
          <button
            onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  </section>
</div>

<!-- Detail Drawer -->
<EquipmentDetailDrawer
  open={drawerOpen}
  equipmentId={selectedEquipmentId}
  onclose={() => (drawerOpen = false)}
/>

<!-- Create Drawer -->
{#if showCreateDrawer}
  <div
    class="fixed inset-0 bg-black/30 z-998 transition-opacity"
    onclick={() => { showCreateDrawer = false; resetCreateForm(); }}
    role="presentation"
  ></div>

  <div
    class="fixed inset-y-0 right-0 z-999 w-full max-w-[560px] bg-white shadow-2xl
           flex flex-col overflow-hidden animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="Register Equipment"
  >
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 bg-neutral-50/60">
      <div>
        <h2 class="text-base font-semibold text-neutral-900">Register Equipment</h2>
        <p class="text-xs text-neutral-500 mt-0.5">Add a new asset to the fleet registry</p>
      </div>
      <button
        onclick={() => { showCreateDrawer = false; resetCreateForm(); }}
        class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto">
      <form onsubmit={saveEquipment} class="p-6 space-y-4">
        <!-- Identity -->
        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Equipment Name *</span>
          <input bind:value={form.name} placeholder="e.g. CAT D6 Bulldozer" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span>
            <select bind:value={form.equipment_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="earthmoving">Earthmoving</option>
              <option value="lifting">Lifting</option>
              <option value="material_handling">Material Handling</option>
              <option value="concrete">Concrete</option>
              <option value="piling">Piling</option>
              <option value="compaction">Compaction</option>
              <option value="transport">Transport</option>
              <option value="scaffolding">Scaffolding</option>
              <option value="power_generation">Power Generation</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span>
            <select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="operational">Operational</option>
              <option value="in_repair">In Repair</option>
              <option value="idle">Idle</option>
              <option value="in_transit">In Transit</option>
              <option value="decommissioned">Decommissioned</option>
            </select>
          </label>
        </div>

        <div class="grid grid-cols-3 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Make</span>
            <input bind:value={form.make} placeholder="e.g. Caterpillar" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Model</span>
            <input bind:value={form.model_name} placeholder="e.g. D6T XL" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Year</span>
            <input type="number" bind:value={form.year_of_manufacture} placeholder="2024" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Serial Number</span>
            <input bind:value={form.serial_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Engine Number</span>
            <input bind:value={form.engine_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <!-- Performance -->
        <div class="grid grid-cols-3 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Fuel Type</span>
            <select bind:value={form.fuel_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="diesel">Diesel</option>
              <option value="petrol">Petrol</option>
              <option value="electric">Electric</option>
              <option value="hybrid">Hybrid</option>
              <option value="na">N/A</option>
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Fuel Rate (L/hr)</span>
            <input type="number" step="0.1" bind:value={form.fuel_consumption_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Capacity</span>
            <input bind:value={form.capacity} placeholder="e.g. 15 Ton" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <!-- Location -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Current Location</span>
            <input bind:value={form.current_location} placeholder="Site or warehouse" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Project</span>
            <select bind:value={form.current_project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">None</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
          </label>
        </div>

        <!-- Financial -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Ownership</span>
            <select bind:value={form.ownership} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="owned">Owned</option>
              <option value="leased">Leased</option>
              <option value="rented">Rented</option>
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Purchase Price</span>
            <input type="number" step="0.01" bind:value={form.purchase_price} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Book Value</span>
            <input type="number" step="0.01" bind:value={form.current_book_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Daily Rate (Internal)</span>
            <input type="number" step="0.01" bind:value={form.internal_daily_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
        </div>

        <!-- Maintenance -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Last Service Date</span>
            <DateInput bind:value={form.last_service_date} />
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Next Service Due</span>
            <DateInput bind:value={form.next_service_due} />
          </label>
        </div>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
          <textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </label>

        <!-- Actions -->
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" onclick={() => { showCreateDrawer = false; resetCreateForm(); }} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
            Cancel
          </button>
          {#if isDev}
            <button type="button" onclick={devFillEquipment} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">
              Dev Fill
            </button>
          {/if}
          <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
            {saving ? "Saving..." : "Register Equipment"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }
  .animate-slide-in {
    animation: slideIn 0.2s ease-out;
  }
</style>

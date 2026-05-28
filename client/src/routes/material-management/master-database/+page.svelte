<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    MaterialMasterListItem,
    MaterialMasterItem,
    MasterDataEntry,
    PaginatedResponse,
    VendorListItem,
    CostCenter,
  } from "$lib/types";

  type AccountOption = { id: number; code: string; name: string };

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  const MATERIAL_SAMPLES = [
    {
      sku: "MAT-CEM-001",
      name: "Ordinary Portland Cement (OPC 42.5N)",
      description: "General-purpose cement conforming to BS EN 197-1. Suitable for structural concrete, mortar, and plastering works. 50kg bags, palletised.",
      category: "structural",
      subcategory: "Cement & Binders",
      unit_of_measure: "Bags",
      default_unit_cost: "12.50",
      preferred_vendor: "",
      lead_time_days: "3",
      target_stock_level: "2000",
      reorder_level: "500",
      storage_requirements: "Dry covered store, off-ground on pallets. Max stack height 10 bags. Avoid moisture and direct sunlight. Use within 3 months of manufacture date.",
      quality_specification: "BS EN 197-1:2011, ASTM C150 Type I. 28-day compressive strength >= 42.5 MPa. Initial setting time >= 60 min.",
      material_grade: "42.5N",
      alternative_materials: "Sulphate Resistant Cement (SRC), PPC Pozzolanic Cement",
      hs_code: "2523.29.00",
      compliance_requirements: "Supplier must provide mill test certificate per batch. Independent testing every 500 bags.",
      expense_account: "",
      cost_center: "",
      is_active: true,
    },
    {
      sku: "MAT-STL-010",
      name: "Deformed Steel Reinforcement Bar (Y16)",
      description: "Hot-rolled high-yield deformed reinforcing bar, 16mm diameter, 12m standard lengths. Grade B500B per BS 4449:2005+A3:2016.",
      category: "structural",
      subcategory: "Steel & Reinforcement",
      unit_of_measure: "Tons",
      default_unit_cost: "950.00",
      preferred_vendor: "",
      lead_time_days: "7",
      target_stock_level: "50",
      reorder_level: "15",
      storage_requirements: "Open yard acceptable if raised on dunnage. Separate by diameter and heat number. Cover with tarpaulin during prolonged storage. Avoid contact with soil.",
      quality_specification: "BS 4449:2005+A3:2016 Grade B500B. Yield strength >= 500 MPa. Elongation >= 14%. Bend/rebend test required.",
      material_grade: "B500B",
      alternative_materials: "Y12, Y20 (alternative diameters), Stainless Steel Rebar (for marine exposure)",
      hs_code: "7214.20.00",
      compliance_requirements: "Mill certificate required per heat. Chemical analysis and mechanical testing per CARES approved scheme. Traceability markings mandatory.",
      expense_account: "",
      cost_center: "",
      is_active: true,
    },
    {
      sku: "MAT-ELC-025",
      name: "PVC Electrical Conduit (25mm)",
      description: "Heavy-gauge rigid PVC conduit pipe, 25mm outer diameter, 3m lengths. Self-extinguishing, UV-stabilised for concealed and surface wiring installations.",
      category: "mep",
      subcategory: "Electrical Containment",
      unit_of_measure: "Meters",
      default_unit_cost: "8.50",
      preferred_vendor: "",
      lead_time_days: "5",
      target_stock_level: "3000",
      reorder_level: "800",
      storage_requirements: "Indoor storage preferred. Keep flat to prevent warping. Avoid prolonged UV exposure if stored outdoors. Temperature range: 5\u00B0C to 60\u00B0C.",
      quality_specification: "BS EN 61386-1, IEC 61386. Impact resistance: medium (3 Joules at -5\u00B0C). IP rating: IP40 minimum.",
      material_grade: "Heavy Gauge",
      alternative_materials: "GI Conduit (for fire-rated areas), Flexible Corrugated Conduit (for tight bends)",
      hs_code: "3917.23.00",
      compliance_requirements: "BASEC or equivalent third-party certification. Fire classification per EN 13501-1. Halogen-free certification for healthcare/education projects.",
      expense_account: "",
      cost_center: "",
      is_active: true,
    },
  ];

  let materialDevIdx = 0;

  function devFillMaterial() {
    const sample = MATERIAL_SAMPLES[materialDevIdx % MATERIAL_SAMPLES.length];
    materialDevIdx++;
    form = { ...sample };
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let materials = $state<MaterialMasterListItem[]>([]);
  let vendors = $state<VendorListItem[]>([]);
  let accounts = $state<AccountOption[]>([]);
  let costCenters = $state<CostCenter[]>([]);
  let categories = $state<MasterDataEntry[]>([]);

  let loading = $state(true);
  let saving = $state(false);

  // Filters
  let search = $state("");
  let filterCategory = $state("");
  let filterActive = $state("");

  // Pagination
  let currentPage = $state(1);
  let pageSize = $state(25);
  let totalCount = $state(0);
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endItem = $derived(Math.min(currentPage * pageSize, totalCount));

  // Detail drawer
  type DrawerMode = "closed" | "create" | "view" | "edit";
  let drawerMode = $state<DrawerMode>("closed");
  let selectedMaterial = $state<MaterialMasterItem | null>(null);
  let drawerErrors = $state<Record<string, string>>({});

  const emptyForm = () => ({
    sku: "",
    name: "",
    description: "",
    category: "",
    subcategory: "",
    unit_of_measure: "ea",
    default_unit_cost: "0.00",
    preferred_vendor: "",
    lead_time_days: "",
    target_stock_level: "0",
    reorder_level: "0",
    storage_requirements: "",
    quality_specification: "",
    material_grade: "",
    alternative_materials: "",
    hs_code: "",
    compliance_requirements: "",
    expense_account: "",
    cost_center: "",
    is_active: true,
  });
  let form = $state(emptyForm());

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
      ordering: "name",
    };
    if (search.trim()) params.search = search.trim();
    if (filterCategory) params.category = filterCategory;
    if (filterActive) params.is_active = filterActive;
    return params;
  }

  async function fetchMaterials() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<MaterialMasterListItem>>("/materials/", buildParams());
      materials = res.results;
      totalCount = res.count;
    } catch {
      materials = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load material master data.");
    } finally {
      loading = false;
    }
  }

  async function fetchOptions() {
    try {
      const [vendorRes, accountRes, costCenterRes, categoryRes] = await Promise.all([
        api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200", ordering: "name" }),
        api.get<PaginatedResponse<AccountOption>>("/finance/accounts/", { page_size: "200", ordering: "code" }),
        api.get<PaginatedResponse<CostCenter>>("/settings/cost-centers/", { page_size: "200", ordering: "name" }),
        api.get<PaginatedResponse<MasterDataEntry>>("/settings/master-data/", { category: "material_category", page_size: "200", is_active: "true" }),
      ]);
      vendors = vendorRes.results;
      accounts = accountRes.results;
      costCenters = costCenterRes.results;
      categories = categoryRes.results;
    } catch {
      /* options are non-critical */
    }
  }

  $effect(() => {
    fetchOptions();
  });

  $effect(() => {
    fetchMaterials();
  });

  // ---------------------------------------------------------------------------
  // Drawer helpers
  // ---------------------------------------------------------------------------

  function openCreate() {
    form = emptyForm();
    drawerErrors = {};
    drawerMode = "create";
  }

  async function openDetail(id: number) {
    drawerMode = "view";
    drawerErrors = {};
    try {
      selectedMaterial = await api.get<MaterialMasterItem>(`/materials/${id}/`);
    } catch {
      toast.error("Error", "Could not load material details.");
      drawerMode = "closed";
    }
  }

  function startEdit() {
    if (!selectedMaterial) return;
    const m = selectedMaterial;
    form = {
      sku: m.sku,
      name: m.name,
      description: m.description,
      category: m.category,
      subcategory: m.subcategory,
      unit_of_measure: m.unit_of_measure,
      default_unit_cost: m.default_unit_cost,
      preferred_vendor: m.preferred_vendor ? String(m.preferred_vendor) : "",
      lead_time_days: m.lead_time_days != null ? String(m.lead_time_days) : "",
      target_stock_level: m.target_stock_level,
      reorder_level: m.reorder_level,
      storage_requirements: m.storage_requirements,
      quality_specification: m.quality_specification,
      material_grade: m.material_grade,
      alternative_materials: m.alternative_materials,
      hs_code: m.hs_code,
      compliance_requirements: m.compliance_requirements,
      expense_account: m.expense_account ? String(m.expense_account) : "",
      cost_center: m.cost_center ? String(m.cost_center) : "",
      is_active: m.is_active,
    };
    drawerErrors = {};
    drawerMode = "edit";
  }

  function closeDrawer() {
    drawerMode = "closed";
    selectedMaterial = null;
    drawerErrors = {};
  }

  // ---------------------------------------------------------------------------
  // Create / Update
  // ---------------------------------------------------------------------------

  function buildPayload() {
    return {
      sku: form.sku.trim(),
      name: form.name.trim(),
      description: form.description.trim(),
      category: form.category || "other",
      subcategory: form.subcategory.trim(),
      unit_of_measure: form.unit_of_measure.trim() || "ea",
      default_unit_cost: form.default_unit_cost || "0.00",
      preferred_vendor: form.preferred_vendor ? Number(form.preferred_vendor) : null,
      lead_time_days: form.lead_time_days ? Number(form.lead_time_days) : null,
      target_stock_level: form.target_stock_level || "0",
      reorder_level: form.reorder_level || "0",
      storage_requirements: form.storage_requirements.trim(),
      quality_specification: form.quality_specification.trim(),
      material_grade: form.material_grade.trim(),
      alternative_materials: form.alternative_materials.trim(),
      hs_code: form.hs_code.trim(),
      compliance_requirements: form.compliance_requirements.trim(),
      expense_account: form.expense_account ? Number(form.expense_account) : null,
      cost_center: form.cost_center ? Number(form.cost_center) : null,
      is_active: form.is_active,
    };
  }

  async function handleSave() {
    if (!form.sku.trim() || !form.name.trim()) {
      toast.error("Validation", "Material ID (SKU) and Name are required.");
      return;
    }
    saving = true;
    drawerErrors = {};
    try {
      if (drawerMode === "create") {
        await api.post("/materials/", buildPayload());
        toast.success("Created", `"${form.name}" added to the material master.`);
      } else if (drawerMode === "edit" && selectedMaterial) {
        await api.put(`/materials/${selectedMaterial.id}/`, buildPayload());
        toast.success("Updated", `"${form.name}" has been updated.`);
      }
      closeDrawer();
      currentPage = 1;
      await fetchMaterials();
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        drawerErrors = Object.fromEntries(
          Object.entries(err.fieldErrors).map(([field, messages]) => [
            field,
            messages.join(" "),
          ]),
        ) as Record<string, string>;
      } else {
        toast.error("Save failed", "Could not save material record.");
      }
    } finally {
      saving = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Formatting
  // ---------------------------------------------------------------------------

  function fmtCurrency(value: string): string {
    return currency.format(Number(value || 0));
  }

  function categoryLabel(code: string): string {
    const entry = categories.find((c) => c.code === code);
    return entry?.label || code.replaceAll("_", " ");
  }
</script>

<!-- Backdrop overlay -->
{#if drawerMode !== "closed"}
  <button
    class="fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px]"
    onclick={closeDrawer}
    aria-label="Close drawer"
  ></button>
{/if}

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Material Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Material Master Database</h1>
      <p class="text-sm text-neutral-400 mt-1">Central catalog of all construction materials across the organization.</p>
    </div>
    <button
      class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
      onclick={openCreate}
    >
      Add Material
    </button>
  </div>

  <!-- Filters -->
  <section class="bg-white rounded-xl border border-neutral-200 p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
      <input
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        placeholder="Search by name, SKU, grade, HS code..."
        bind:value={search}
        oninput={() => { currentPage = 1; fetchMaterials(); }}
      />
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        bind:value={filterCategory}
        onchange={() => { currentPage = 1; fetchMaterials(); }}
      >
        <option value="">All Categories</option>
        {#each categories as cat}
          <option value={cat.code}>{cat.label}</option>
        {/each}
      </select>
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        bind:value={filterActive}
        onchange={() => { currentPage = 1; fetchMaterials(); }}
      >
        <option value="">All Statuses</option>
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        bind:value={pageSize}
        onchange={() => { currentPage = 1; fetchMaterials(); }}
      >
        <option value={10}>10 rows</option>
        <option value={25}>25 rows</option>
        <option value={50}>50 rows</option>
      </select>
    </div>

    <!-- Table -->
    <div class="mt-4 overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 text-left text-[11px] uppercase tracking-wider text-neutral-400">
            <th class="px-3 py-2">Material</th>
            <th class="px-3 py-2">Category</th>
            <th class="px-3 py-2">Grade</th>
            <th class="px-3 py-2">UoM</th>
            <th class="px-3 py-2 text-right">Std Cost</th>
            <th class="px-3 py-2 text-right">Lead Time</th>
            <th class="px-3 py-2">Vendor</th>
            <th class="px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-50">
          {#if loading}
            <tr><td colspan="8" class="px-3 py-10 text-center text-sm text-neutral-400">Loading materials...</td></tr>
          {:else if materials.length === 0}
            <tr><td colspan="8" class="px-3 py-10 text-center text-sm text-neutral-400">No materials found</td></tr>
          {:else}
            {#each materials as mat}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openDetail(mat.id)}
              >
                <td class="px-3 py-3">
                  <p class="text-sm font-medium text-neutral-900">{mat.name}</p>
                  <p class="text-xs text-neutral-400">{mat.sku}</p>
                </td>
                <td class="px-3 py-3">
                  <span class="text-xs font-medium text-neutral-600">{categoryLabel(mat.category)}</span>
                  {#if mat.subcategory}
                    <p class="text-[11px] text-neutral-400">{mat.subcategory}</p>
                  {/if}
                </td>
                <td class="px-3 py-3 text-sm text-neutral-600">{mat.material_grade || "—"}</td>
                <td class="px-3 py-3 text-sm text-neutral-600">{mat.unit_of_measure}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-700 tabular-nums">{fmtCurrency(mat.default_unit_cost)}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-600 tabular-nums">
                  {mat.lead_time_days != null ? `${mat.lead_time_days}d` : "—"}
                </td>
                <td class="px-3 py-3 text-xs text-neutral-500">
                  {mat.preferred_vendor_name || "—"}
                </td>
                <td class="px-3 py-3">
                  <span class={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${mat.is_active ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-500"}`}>
                    {mat.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="mt-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <p class="text-xs text-neutral-400">Showing {startItem}–{endItem} of {totalCount}</p>
      <div class="flex items-center gap-2">
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40"
          onclick={() => { if (currentPage > 1) { currentPage -= 1; fetchMaterials(); } }}
          disabled={currentPage <= 1}
        >Prev</button>
        <span class="text-sm text-neutral-500">Page {currentPage} of {totalPages}</span>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40"
          onclick={() => { if (currentPage < totalPages) { currentPage += 1; fetchMaterials(); } }}
          disabled={currentPage >= totalPages}
        >Next</button>
      </div>
    </div>
  </section>
</div>

<!-- ========================================================================= -->
<!-- Right-side Drawer                                                          -->
<!-- ========================================================================= -->
{#if drawerMode !== "closed"}
  <div
    class="fixed top-0 right-0 z-50 h-full w-full max-w-xl bg-white border-l border-neutral-200 shadow-2xl flex flex-col"
    style="animation: slideInRight 0.25s ease-out"
  >
    <!-- Drawer header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
      <h2 class="text-lg font-bold text-neutral-900">
        {#if drawerMode === "create"}New Material{:else if drawerMode === "edit"}Edit Material{:else}{selectedMaterial?.name ?? "Material"}{/if}
      </h2>
      <button onclick={closeDrawer} class="text-neutral-400 hover:text-neutral-900 transition-colors text-xl leading-none">&times;</button>
    </div>

    <!-- Drawer body -->
    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      {#if drawerMode === "view" && selectedMaterial}
        <!-- READ-ONLY VIEW -->
        {@const m = selectedMaterial}
        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Material ID</p>
              <p class="text-sm font-medium text-neutral-900 mt-0.5">{m.sku}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Status</p>
              <span class={`inline-flex items-center mt-0.5 px-2 py-0.5 rounded-full text-[11px] font-medium ${m.is_active ? "bg-emerald-50 text-emerald-700" : "bg-neutral-100 text-neutral-500"}`}>
                {m.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <div class="col-span-2">
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Material Name</p>
              <p class="text-sm text-neutral-900 mt-0.5">{m.name}</p>
            </div>
            {#if m.description}
              <div class="col-span-2">
                <p class="text-[11px] uppercase tracking-wider text-neutral-400">Description</p>
                <p class="text-sm text-neutral-600 mt-0.5">{m.description}</p>
              </div>
            {/if}
          </div>

          <hr class="border-neutral-100" />
          <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Classification</h3>
          <div class="grid grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Category</p>
              <p class="text-sm text-neutral-900 mt-0.5">{categoryLabel(m.category)}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Subcategory</p>
              <p class="text-sm text-neutral-600 mt-0.5">{m.subcategory || "—"}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Material Grade</p>
              <p class="text-sm text-neutral-600 mt-0.5">{m.material_grade || "—"}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">HS Code</p>
              <p class="text-sm text-neutral-600 mt-0.5 font-mono">{m.hs_code || "—"}</p>
            </div>
          </div>

          <hr class="border-neutral-100" />
          <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Costing & Supply</h3>
          <div class="grid grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Unit of Measure</p>
              <p class="text-sm text-neutral-900 mt-0.5">{m.unit_of_measure}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Standard Cost</p>
              <p class="text-sm font-medium text-neutral-900 mt-0.5 tabular-nums">{fmtCurrency(m.default_unit_cost)}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Preferred Vendor</p>
              <p class="text-sm text-neutral-600 mt-0.5">{m.preferred_vendor_name || "—"}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Lead Time</p>
              <p class="text-sm text-neutral-600 mt-0.5">{m.lead_time_days != null ? `${m.lead_time_days} days` : "—"}</p>
            </div>
          </div>

          <hr class="border-neutral-100" />
          <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Stock Parameters</h3>
          <div class="grid grid-cols-2 gap-x-6 gap-y-3">
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Reorder Level</p>
              <p class="text-sm text-neutral-600 mt-0.5 tabular-nums">{Number(m.reorder_level).toLocaleString()}</p>
            </div>
            <div>
              <p class="text-[11px] uppercase tracking-wider text-neutral-400">Safety Stock Level</p>
              <p class="text-sm text-neutral-600 mt-0.5 tabular-nums">{Number(m.target_stock_level).toLocaleString()}</p>
            </div>
          </div>

          {#if m.storage_requirements || m.quality_specification || m.compliance_requirements || m.alternative_materials}
            <hr class="border-neutral-100" />
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Specifications & Compliance</h3>
            <div class="space-y-3">
              {#if m.quality_specification}
                <div>
                  <p class="text-[11px] uppercase tracking-wider text-neutral-400">Quality Specification</p>
                  <p class="text-sm text-neutral-600 mt-0.5">{m.quality_specification}</p>
                </div>
              {/if}
              {#if m.storage_requirements}
                <div>
                  <p class="text-[11px] uppercase tracking-wider text-neutral-400">Storage Requirements</p>
                  <p class="text-sm text-neutral-600 mt-0.5">{m.storage_requirements}</p>
                </div>
              {/if}
              {#if m.compliance_requirements}
                <div>
                  <p class="text-[11px] uppercase tracking-wider text-neutral-400">Compliance Requirements</p>
                  <p class="text-sm text-neutral-600 mt-0.5">{m.compliance_requirements}</p>
                </div>
              {/if}
              {#if m.alternative_materials}
                <div>
                  <p class="text-[11px] uppercase tracking-wider text-neutral-400">Alternative Materials</p>
                  <p class="text-sm text-neutral-600 mt-0.5">{m.alternative_materials}</p>
                </div>
              {/if}
            </div>
          {/if}

          {#if m.expense_account_code || m.cost_center_name}
            <hr class="border-neutral-100" />
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Finance Mapping</h3>
            <div class="grid grid-cols-2 gap-x-6 gap-y-3">
              <div>
                <p class="text-[11px] uppercase tracking-wider text-neutral-400">Expense Account</p>
                <p class="text-sm text-neutral-600 mt-0.5">{m.expense_account_code ? `${m.expense_account_code} — ${m.expense_account_name}` : "—"}</p>
              </div>
              <div>
                <p class="text-[11px] uppercase tracking-wider text-neutral-400">Cost Center</p>
                <p class="text-sm text-neutral-600 mt-0.5">{m.cost_center_name || "—"}</p>
              </div>
            </div>
          {/if}
        </div>

      {:else if drawerMode === "create" || drawerMode === "edit"}
        <!-- CREATE / EDIT FORM -->
        <div class="space-y-5">
          <div>
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Identification</h3>
            <div class="grid grid-cols-2 gap-3">
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Material ID (SKU) *</span>
                <input
                  class="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
                         {drawerErrors.sku ? 'border-red-300' : 'border-neutral-200'}"
                  bind:value={form.sku}
                />
                {#if drawerErrors.sku}<p class="text-xs text-red-600 mt-1">{drawerErrors.sku}</p>{/if}
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Material Name *</span>
                <input
                  class="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
                         {drawerErrors.name ? 'border-red-300' : 'border-neutral-200'}"
                  bind:value={form.name}
                />
                {#if drawerErrors.name}<p class="text-xs text-red-600 mt-1">{drawerErrors.name}</p>{/if}
              </label>
            </div>
            <label class="block mt-3">
              <span class="text-xs font-medium text-neutral-500">Description</span>
              <textarea
                rows={2}
                class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                bind:value={form.description}
              ></textarea>
            </label>
          </div>

          <hr class="border-neutral-100" />
          <div>
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Classification</h3>
            <div class="grid grid-cols-2 gap-3">
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Category</span>
                <select
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.category}
                >
                  <option value="">Select category</option>
                  {#each categories as cat}
                    <option value={cat.code}>{cat.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Subcategory</span>
                <input
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  placeholder="e.g. Portland Type I"
                  bind:value={form.subcategory}
                />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Material Grade</span>
                <input
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  placeholder="e.g. Grade 60, BS 4449"
                  bind:value={form.material_grade}
                />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">HS Code</span>
                <input
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm font-mono
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  placeholder="e.g. 7214.20.00"
                  bind:value={form.hs_code}
                />
              </label>
            </div>
          </div>

          <hr class="border-neutral-100" />
          <div>
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Costing & Supply</h3>
            <div class="grid grid-cols-2 gap-3">
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Unit of Measure</span>
                <input
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  placeholder="bags, tons, kg, pieces, meters"
                  bind:value={form.unit_of_measure}
                />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Standard Cost</span>
                <input
                  type="number" min="0" step="0.01"
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.default_unit_cost}
                />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Preferred Vendor</span>
                <select
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.preferred_vendor}
                >
                  <option value="">None</option>
                  {#each vendors as v}
                    <option value={v.id}>{v.name}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Lead Time (days)</span>
                <input
                  type="number" min="0"
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.lead_time_days}
                />
              </label>
            </div>
          </div>

          <hr class="border-neutral-100" />
          <div>
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Stock Parameters</h3>
            <div class="grid grid-cols-2 gap-3">
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Reorder Level</span>
                <input
                  type="number" min="0" step="0.001"
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.reorder_level}
                />
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Safety Stock Level</span>
                <input
                  type="number" min="0" step="0.001"
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.target_stock_level}
                />
              </label>
            </div>
          </div>

          <hr class="border-neutral-100" />
          <div>
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Specifications & Compliance</h3>
            <label class="block">
              <span class="text-xs font-medium text-neutral-500">Quality Specification</span>
              <textarea
                rows={2}
                class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="e.g. ASTM C150, EN 197-1"
                bind:value={form.quality_specification}
              ></textarea>
            </label>
            <label class="block mt-3">
              <span class="text-xs font-medium text-neutral-500">Storage Requirements</span>
              <textarea
                rows={2}
                class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="e.g. Dry store, avoid moisture, stack max 10 bags"
                bind:value={form.storage_requirements}
              ></textarea>
            </label>
            <label class="block mt-3">
              <span class="text-xs font-medium text-neutral-500">Compliance Requirements</span>
              <textarea
                rows={2}
                class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="Regulatory or compliance notes"
                bind:value={form.compliance_requirements}
              ></textarea>
            </label>
            <label class="block mt-3">
              <span class="text-xs font-medium text-neutral-500">Alternative Materials</span>
              <input
                class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="Comma-separated substitutes"
                bind:value={form.alternative_materials}
              />
            </label>
          </div>

          <hr class="border-neutral-100" />
          <div>
            <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Finance Mapping</h3>
            <div class="grid grid-cols-2 gap-3">
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Expense Account</span>
                <select
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.expense_account}
                >
                  <option value="">None</option>
                  {#each accounts as acct}
                    <option value={acct.id}>{acct.code} — {acct.name}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="text-xs font-medium text-neutral-500">Cost Center</span>
                <select
                  class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  bind:value={form.cost_center}
                >
                  <option value="">None</option>
                  {#each costCenters as cc}
                    <option value={cc.id}>{cc.name}</option>
                  {/each}
                </select>
              </label>
            </div>
          </div>

          <label class="inline-flex items-center gap-2 text-sm text-neutral-600 mt-2">
            <input type="checkbox" class="rounded border-neutral-300" bind:checked={form.is_active} /> Active
          </label>
        </div>
      {/if}
    </div>

    <!-- Drawer footer -->
    <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
      {#if drawerMode === "view"}
        <button
          onclick={closeDrawer}
          class="px-4 py-2 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >Close</button>
        <button
          onclick={startEdit}
          class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
        >Edit</button>
      {:else}
        {#if isDev}
          <button
            onclick={devFillMaterial}
            class="px-3 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors mr-auto"
          >Dev Fill</button>
        {/if}
        <button
          onclick={closeDrawer}
          class="px-4 py-2 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >Cancel</button>
        <button
          onclick={handleSave}
          disabled={saving}
          class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-60 transition-colors"
        >
          {saving ? "Saving..." : drawerMode === "create" ? "Create Material" : "Save Changes"}
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
</style>

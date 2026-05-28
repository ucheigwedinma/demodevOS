<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { SPVEntity, SPVEntityType, SPVStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  const SPV_SAMPLES = [
    {
      name: "Horizon Tower Development Holdings Ltd",
      entity_type: "company" as SPVEntityType,
      status: "active" as SPVStatus,
      registration_number: "RC-2024-78341",
      registration_date: "2024-03-15",
      registered_address: "Level 14, Gate District Tower 2, DIFC, Dubai, UAE\nPO Box 506745",
      tax_id: "TRN-100458923",
      jurisdiction: "DIFC, Dubai, UAE",
      authorized_capital: "50000000",
      paid_up_capital: "12500000",
      purpose: "Ring-fenced holding vehicle for the Horizon Tower mixed-use development project. Isolates project-level debt, contractor liabilities, and off-plan sales receivables from the parent group balance sheet.",
      parent_entity: "",
      notes: "Board: 3 directors (2 nominee, 1 independent). Annual audit by Deloitte. Regulated by DFSA. Shareholder agreement executed 12 Mar 2024. First capital call completed.",
      is_active: true,
    },
    {
      name: "Meridian Residences Project Finance SPV",
      entity_type: "llc" as SPVEntityType,
      status: "under_formation" as SPVStatus,
      registration_number: "LLC-2025-00214",
      registration_date: "2025-11-28",
      registered_address: "Office 1204, Convergence Tower, Al Reem Island, Abu Dhabi, UAE",
      tax_id: "",
      jurisdiction: "ADGM, Abu Dhabi, UAE",
      authorized_capital: "35000000",
      paid_up_capital: "0",
      purpose: "Project finance vehicle for the 280-unit Meridian Residences development. Will hold construction financing facility, land lease, and all project contracts. Structured for limited-recourse senior debt from syndicated bank facility.",
      parent_entity: "",
      notes: "Awaiting ADGM registration certificate. Legal counsel: Allen & Overy. Target financial close: Q1 2026. Syndication led by Emirates NBD with FAB and Mashreq participating.",
      is_active: true,
    },
    {
      name: "Crescent Real Estate Investment Trust",
      entity_type: "trust" as SPVEntityType,
      status: "active" as SPVStatus,
      registration_number: "TR-2023-45102",
      registration_date: "2023-06-01",
      registered_address: "Suite 802, Boulevard Plaza Tower 1, Downtown Dubai, UAE\nPO Box 334521",
      tax_id: "TRN-100672844",
      jurisdiction: "DIFC, Dubai, UAE",
      authorized_capital: "200000000",
      paid_up_capital: "87500000",
      purpose: "Closed-ended real estate investment trust holding income-generating commercial and residential assets. Target portfolio: 8-12 stabilised properties across UAE. Distribution policy: 90% of net rental income paid quarterly to unitholders.",
      parent_entity: "",
      notes: "Trustee: National Bonds Corporation. Fund administrator: Apex Group. NAV calculated quarterly. Current portfolio: 4 assets (2 commercial towers, 1 residential community, 1 retail podium). Occupancy: 94% weighted average.",
      is_active: true,
    },
  ];

  let spvDevIdx = 0;

  function devFillSPV() {
    const sample = SPV_SAMPLES[spvDevIdx % SPV_SAMPLES.length];
    spvDevIdx++;
    form = { ...sample };
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let entities = $state<SPVEntity[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let saving = $state(false);
  let deleting = $state(false);

  // Filters
  let searchQuery = $state("");
  let filterEntityType = $state("");
  let filterStatus = $state("");
  let currentPage = $state(1);
  const pageSize = 20;

  // Modal
  let showModal = $state(false);
  let editingEntity = $state<SPVEntity | null>(null);
  let parentOptions = $state<SPVEntity[]>([]);
  let fieldErrors = $state<Record<string, string[]>>({});

  // Delete confirmation
  let showDeleteConfirm = $state(false);
  let entityToDelete = $state<SPVEntity | null>(null);

  // Form
  let form = $state({
    name: "",
    entity_type: "company" as SPVEntityType,
    status: "active" as SPVStatus,
    registration_number: "",
    registration_date: "",
    registered_address: "",
    tax_id: "",
    jurisdiction: "",
    authorized_capital: "",
    paid_up_capital: "",
    purpose: "",
    parent_entity: "" as string,
    notes: "",
    is_active: true,
  });

  // ---------------------------------------------------------------------------
  // Labels & badge maps
  // ---------------------------------------------------------------------------
  const entityTypeLabels: Record<SPVEntityType, string> = {
    company: "Company",
    llp: "LLP",
    trust: "Trust",
    fund: "Fund",
    llc: "LLC",
    other: "Other",
  };

  // ---------------------------------------------------------------------------
  // Derived
  // ---------------------------------------------------------------------------
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingEntity !== null);
  let modalTitle = $derived(isEditing ? "Edit SPV Entity" : "Create SPV Entity");

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function formatCapital(value: string | null): string {
    if (!value) return "\u2014";
    return currency.format(value);
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.join(", ") ?? "";
  }

  function resetForm() {
    form = {
      name: "",
      entity_type: "company",
      status: "active",
      registration_number: "",
      registration_date: "",
      registered_address: "",
      tax_id: "",
      jurisdiction: "",
      authorized_capital: "",
      paid_up_capital: "",
      purpose: "",
      parent_entity: "",
      notes: "",
      is_active: true,
    };
    fieldErrors = {};
  }

  function populateForm(entity: SPVEntity) {
    form = {
      name: entity.name,
      entity_type: entity.entity_type,
      status: entity.status,
      registration_number: entity.registration_number,
      registration_date: entity.registration_date ?? "",
      registered_address: entity.registered_address,
      tax_id: entity.tax_id,
      jurisdiction: entity.jurisdiction,
      authorized_capital: entity.authorized_capital ?? "",
      paid_up_capital: entity.paid_up_capital ?? "",
      purpose: entity.purpose,
      parent_entity: entity.parent_entity ? String(entity.parent_entity) : "",
      notes: entity.notes,
      is_active: entity.is_active,
    };
  }

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  async function fetchEntities() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (filterEntityType) params.entity_type = filterEntityType;
      if (filterStatus) params.status = filterStatus;

      const res = await api.get<PaginatedResponse<SPVEntity>>("/finance/spv-entities/", params);
      entities = res.results;
      totalCount = res.count;
    } catch {
      toast.error("Error", "Could not load SPV entities.");
      entities = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchParentOptions() {
    try {
      const res = await api.get<PaginatedResponse<SPVEntity>>("/finance/spv-entities/", {
        page_size: "200",
        status: "active",
      });
      parentOptions = res.results;
    } catch {
      parentOptions = [];
    }
  }

  // Auto-fetch when filters or page change
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;

  $effect(() => {
    // Track reactive dependencies
    void searchQuery;
    void filterEntityType;
    void filterStatus;
    void currentPage;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      fetchEntities();
    }, searchQuery ? 300 : 0);
  });

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  function openCreateModal() {
    resetForm();
    editingEntity = null;
    showModal = true;
    fetchParentOptions();
  }

  function openEditModal(entity: SPVEntity) {
    editingEntity = entity;
    populateForm(entity);
    fieldErrors = {};
    showModal = true;
    fetchParentOptions();
  }

  function closeModal() {
    showModal = false;
    editingEntity = null;
    resetForm();
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};

    const payload: Record<string, unknown> = {
      name: form.name,
      entity_type: form.entity_type,
      status: form.status,
      registration_number: form.registration_number,
      registration_date: form.registration_date || null,
      registered_address: form.registered_address,
      tax_id: form.tax_id,
      jurisdiction: form.jurisdiction,
      authorized_capital: form.authorized_capital || null,
      paid_up_capital: form.paid_up_capital || null,
      purpose: form.purpose,
      parent_entity: form.parent_entity ? Number(form.parent_entity) : null,
      notes: form.notes,
      is_active: form.is_active,
    };

    try {
      if (isEditing && editingEntity) {
        await api.patch<SPVEntity>(`/finance/spv-entities/${editingEntity.id}/`, payload);
        toast.success("SPV Updated", "The SPV entity has been updated successfully.");
      } else {
        await api.post<SPVEntity>("/finance/spv-entities/", payload);
        toast.success("SPV Created", "The SPV entity has been created successfully.");
      }
      closeModal();
      await fetchEntities();
    } catch (err) {
      if (err instanceof ApiError) {
        fieldErrors = err.fieldErrors;
        toast.error("Validation Error", "Please fix the highlighted fields below.");
      } else {
        toast.error("Error", "Could not save the SPV entity.");
      }
    } finally {
      saving = false;
    }
  }

  function confirmDelete(entity: SPVEntity) {
    entityToDelete = entity;
    showDeleteConfirm = true;
  }

  function cancelDelete() {
    showDeleteConfirm = false;
    entityToDelete = null;
  }

  async function handleDelete() {
    if (!entityToDelete) return;
    const deletedEntity = entityToDelete;
    deleting = true;
    try {
      await api.delete(`/finance/spv-entities/${deletedEntity.id}/`);
      toast.success("SPV Deleted", `"${deletedEntity.name}" has been removed.`);
      showDeleteConfirm = false;
      entityToDelete = null;

      // If we were viewing this entity in the modal, close it
      if (editingEntity?.id === deletedEntity.id) {
        closeModal();
      }

      await fetchEntities();
    } catch {
      toast.error("Error", "Could not delete the SPV entity.");
    } finally {
      deleting = false;
    }
  }

  function goToPage(page: number) {
    if (page >= 1 && page <= totalPages) {
      currentPage = page;
    }
  }

  function handleFilterReset() {
    searchQuery = "";
    filterEntityType = "";
    filterStatus = "";
    currentPage = 1;
  }
</script>

<!-- ======================================================================= -->
<!-- MARKUP                                                                    -->
<!-- ======================================================================= -->

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-800">SPV Entities</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage special purpose vehicles and legal entities</p>
    </div>
    <button
      onclick={openCreateModal}
      class="inline-flex items-center gap-2 px-5 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Create SPV
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-4">
    <div class="flex flex-col sm:flex-row items-start sm:items-center gap-3">
      <!-- Search -->
      <div class="relative flex-1 w-full sm:w-auto">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Search by name..."
          class="w-full pl-9 pr-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
      </div>

      <!-- Entity Type Filter -->
      <select
        bind:value={filterEntityType}
        class="px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">All Types</option>
        <option value="company">Company</option>
        <option value="llp">LLP</option>
        <option value="trust">Trust</option>
        <option value="fund">Fund</option>
        <option value="llc">LLC</option>
        <option value="other">Other</option>
      </select>

      <!-- Status Filter -->
      <select
        bind:value={filterStatus}
        class="px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">All Statuses</option>
        <option value="active">Active</option>
        <option value="dormant">Dormant</option>
        <option value="dissolved">Dissolved</option>
        <option value="under_formation">Under Formation</option>
      </select>

      <!-- Reset -->
      {#if searchQuery || filterEntityType || filterStatus}
        <button
          onclick={handleFilterReset}
          class="px-3 py-2 text-sm text-neutral-500 hover:text-neutral-800 transition-colors"
        >
          Reset
        </button>
      {/if}
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-24">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if entities.length === 0}
      <div class="text-center py-24">
        <svg class="mx-auto w-10 h-10 text-neutral-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
        </svg>
        <p class="text-sm text-neutral-400">No SPV entities found</p>
        {#if searchQuery || filterEntityType || filterStatus}
          <button
            onclick={handleFilterReset}
            class="mt-3 text-sm font-medium text-neutral-800 hover:underline"
          >
            Clear filters
          </button>
        {:else}
          <button
            onclick={openCreateModal}
            class="mt-3 text-sm font-medium text-neutral-800 hover:underline"
          >
            Create your first SPV entity
          </button>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/50">
              <th class="px-5 py-3.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Name</th>
              <th class="px-5 py-3.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Entity Type</th>
              <th class="px-5 py-3.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Jurisdiction</th>
              <th class="px-5 py-3.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Registration #</th>
              <th class="px-5 py-3.5 text-center text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Subsidiaries</th>
              <th class="px-5 py-3.5 text-center text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Projects</th>
              <th class="px-5 py-3.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each entities as entity (entity.id)}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openEditModal(entity)}
              >
                <td class="px-5 py-4">
                  <div class="font-medium text-neutral-800">{entity.name}</div>
                  {#if entity.parent_entity_name}
                    <div class="text-[11px] text-neutral-400 mt-0.5">Parent: {entity.parent_entity_name}</div>
                  {/if}
                </td>
                <td class="px-5 py-4 text-neutral-600">
                  {entityTypeLabels[entity.entity_type] ?? entity.entity_type}
                </td>
                <td class="px-5 py-4">
                  <StatusBadge status={entity.status} />
                </td>
                <td class="px-5 py-4 text-neutral-600">{entity.jurisdiction || "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-600 tabular-nums">{entity.registration_number || "\u2014"}</td>
                <td class="px-5 py-4 text-center text-neutral-600 tabular-nums">{entity.subsidiary_count}</td>
                <td class="px-5 py-4 text-center text-neutral-600 tabular-nums">{entity.project_count}</td>
                <td class="px-5 py-4 text-neutral-400 text-xs">{formatDate(entity.created_at?.split("T")[0] ?? null)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {#if totalPages > 1}
        <div class="flex items-center justify-between px-5 py-3 border-t border-neutral-200">
          <p class="text-xs text-neutral-400">
            Showing {(currentPage - 1) * pageSize + 1}&ndash;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
          </p>
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              class="px-2.5 py-1.5 text-xs font-medium text-neutral-600 rounded-md hover:bg-neutral-100
                     disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            {#each Array.from({ length: totalPages }, (_, i) => i + 1) as pg}
              {#if pg === 1 || pg === totalPages || (pg >= currentPage - 1 && pg <= currentPage + 1)}
                <button
                  onclick={() => goToPage(pg)}
                  class="w-8 h-8 text-xs font-medium rounded-md transition-colors
                         {pg === currentPage ? 'bg-neutral-800 text-white' : 'text-neutral-600 hover:bg-neutral-100'}"
                >
                  {pg}
                </button>
              {:else if pg === currentPage - 2 || pg === currentPage + 2}
                <span class="w-8 h-8 flex items-center justify-center text-xs text-neutral-300">...</span>
              {/if}
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              class="px-2.5 py-1.5 text-xs font-medium text-neutral-600 rounded-md hover:bg-neutral-100
                     disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>

<!-- ======================================================================= -->
<!-- CREATE / EDIT MODAL                                                       -->
<!-- ======================================================================= -->
{#if showModal}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity"
    onclick={closeModal}
    onkeydown={(e) => e.key === "Escape" && closeModal()}
    role="button"
    tabindex="-1"
  ></div>

  <!-- Slide-over panel -->
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col">
    <!-- Panel header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 shrink-0">
      <h2 class="text-lg font-semibold text-neutral-800">{modalTitle}</h2>
      <div class="flex items-center gap-2">
        {#if isEditing && editingEntity}
          <button
            onclick={() => confirmDelete(editingEntity!)}
            class="px-3 py-1.5 text-xs font-medium text-neutral-500 border border-neutral-200 rounded-lg
                   hover:text-neutral-700 hover:border-neutral-300 transition-colors"
          >
            Delete
          </button>
        {/if}
        <button
          onclick={closeModal}
          aria-label="Close"
          class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Panel body (scrollable) -->
    <div class="flex-1 overflow-y-auto px-6 py-6">
      <div class="space-y-5">
        <!-- Name -->
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-neutral-400">*</span></span>
          <input
            type="text"
            bind:value={form.name}
            placeholder="e.g. Horizon SPV Ltd"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
          {#if fieldError("name")}<p class="mt-1 text-xs text-red-600">{fieldError("name")}</p>{/if}
        </label>

        <!-- Entity Type + Status -->
        <div class="grid grid-cols-2 gap-4">
          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Entity Type</span>
            <select
              bind:value={form.entity_type}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            >
              {#each Object.entries(entityTypeLabels) as [val, label]}
                <option value={val}>{label}</option>
              {/each}
            </select>
            {#if fieldError("entity_type")}<p class="mt-1 text-xs text-red-600">{fieldError("entity_type")}</p>{/if}
          </label>

          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
            <select
              bind:value={form.status}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            >
              <option value="active">Active</option>
              <option value="dormant">Dormant</option>
              <option value="dissolved">Dissolved</option>
              <option value="under_formation">Under Formation</option>
            </select>
            {#if fieldError("status")}<p class="mt-1 text-xs text-red-600">{fieldError("status")}</p>{/if}
          </label>
        </div>

        <!-- Registration Number + Date -->
        <div class="grid grid-cols-2 gap-4">
          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Registration Number</span>
            <input
              type="text"
              bind:value={form.registration_number}
              placeholder="e.g. RC-123456"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
            {#if fieldError("registration_number")}<p class="mt-1 text-xs text-red-600">{fieldError("registration_number")}</p>{/if}
          </label>

          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Registration Date</span>
            <DateInput bind:value={form.registration_date} />
            {#if fieldError("registration_date")}<p class="mt-1 text-xs text-red-600">{fieldError("registration_date")}</p>{/if}
          </label>
        </div>

        <!-- Tax ID + Jurisdiction -->
        <div class="grid grid-cols-2 gap-4">
          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tax ID</span>
            <input
              type="text"
              bind:value={form.tax_id}
              placeholder="e.g. 12-3456789"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
            {#if fieldError("tax_id")}<p class="mt-1 text-xs text-red-600">{fieldError("tax_id")}</p>{/if}
          </label>

          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Jurisdiction</span>
            <input
              type="text"
              bind:value={form.jurisdiction}
              placeholder="e.g. Delaware, USA"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
            {#if fieldError("jurisdiction")}<p class="mt-1 text-xs text-red-600">{fieldError("jurisdiction")}</p>{/if}
          </label>
        </div>

        <!-- Authorized Capital + Paid-up Capital -->
        <div class="grid grid-cols-2 gap-4">
          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Authorized Capital</span>
            <input
              type="text"
              bind:value={form.authorized_capital}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
            {#if fieldError("authorized_capital")}<p class="mt-1 text-xs text-red-600">{fieldError("authorized_capital")}</p>{/if}
          </label>

          <label class="block">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Paid-up Capital</span>
            <input
              type="text"
              bind:value={form.paid_up_capital}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
            {#if fieldError("paid_up_capital")}<p class="mt-1 text-xs text-red-600">{fieldError("paid_up_capital")}</p>{/if}
          </label>
        </div>

        <!-- Registered Address -->
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Registered Address</span>
          <textarea
            bind:value={form.registered_address}
            rows={3}
            placeholder="Full registered address..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          ></textarea>
          {#if fieldError("registered_address")}<p class="mt-1 text-xs text-red-600">{fieldError("registered_address")}</p>{/if}
        </label>

        <!-- Purpose -->
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Purpose</span>
          <textarea
            bind:value={form.purpose}
            rows={3}
            placeholder="Describe the purpose of this SPV..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          ></textarea>
          {#if fieldError("purpose")}<p class="mt-1 text-xs text-red-600">{fieldError("purpose")}</p>{/if}
        </label>

        <!-- Parent Entity -->
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Parent Entity <span class="text-neutral-400 font-normal">(optional)</span></span>
          <select
            bind:value={form.parent_entity}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          >
            <option value="">None</option>
            {#each parentOptions.filter(e => e.id !== editingEntity?.id) as parent}
              <option value={String(parent.id)}>{parent.name}</option>
            {/each}
          </select>
          {#if fieldError("parent_entity")}<p class="mt-1 text-xs text-red-600">{fieldError("parent_entity")}</p>{/if}
        </label>

        <!-- Notes -->
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={form.notes}
            rows={3}
            placeholder="Internal notes..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          ></textarea>
        </label>

        <!-- Active toggle -->
        <label class="flex items-center gap-3 cursor-pointer select-none">
          <button
            type="button"
            role="switch"
            aria-checked={form.is_active}
            aria-label="Toggle active status"
            onclick={() => (form.is_active = !form.is_active)}
            class="relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out
                   focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:ring-offset-2
                   {form.is_active ? 'bg-neutral-800' : 'bg-neutral-200'}"
          >
            <span
              class="pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ease-in-out
                     {form.is_active ? 'translate-x-4' : 'translate-x-0'}"
            ></span>
          </button>
          <span class="text-sm text-neutral-700">Active</span>
        </label>

        <!-- Read-only info when editing -->
        {#if isEditing && editingEntity}
          <div class="border-t border-neutral-200 pt-5 mt-2">
            <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">Statistics</h4>
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-neutral-50 rounded-lg p-3">
                <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Subsidiaries</p>
                <p class="text-lg font-bold text-neutral-800 mt-0.5">{editingEntity.subsidiary_count}</p>
              </div>
              <div class="bg-neutral-50 rounded-lg p-3">
                <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Projects</p>
                <p class="text-lg font-bold text-neutral-800 mt-0.5">{editingEntity.project_count}</p>
              </div>
              {#if editingEntity.authorized_capital}
                <div class="bg-neutral-50 rounded-lg p-3">
                  <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Authorized Capital</p>
                  <p class="text-lg font-bold text-neutral-800 mt-0.5 tabular-nums">{formatCapital(editingEntity.authorized_capital)}</p>
                </div>
              {/if}
              {#if editingEntity.paid_up_capital}
                <div class="bg-neutral-50 rounded-lg p-3">
                  <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Paid-up Capital</p>
                  <p class="text-lg font-bold text-neutral-800 mt-0.5 tabular-nums">{formatCapital(editingEntity.paid_up_capital)}</p>
                </div>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Panel footer -->
    <div class="flex items-center justify-between px-6 py-4 border-t border-neutral-200 shrink-0 bg-neutral-50/50">
      <div class="flex items-center gap-2">
        <button
          onclick={closeModal}
          class="px-4 py-2.5 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg
                 hover:bg-neutral-100 transition-colors"
        >
          Cancel
        </button>
        {#if isDev}
          <button
            onclick={devFillSPV}
            class="px-3 py-2.5 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors"
          >
            Dev Fill
          </button>
        {/if}
      </div>
      <button
        onclick={handleSave}
        disabled={saving}
        class="inline-flex items-center px-6 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg
               hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {#if saving}
          <div class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"></div>
        {/if}
        {isEditing ? "Save Changes" : "Create SPV"}
      </button>
    </div>
  </div>
{/if}

<!-- ======================================================================= -->
<!-- DELETE CONFIRMATION DIALOG                                                -->
<!-- ======================================================================= -->
{#if showDeleteConfirm && entityToDelete}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-60 bg-black/50 backdrop-blur-sm"
    onclick={cancelDelete}
    onkeydown={(e) => e.key === "Escape" && cancelDelete()}
    role="button"
    tabindex="-1"
  ></div>

  <!-- Dialog -->
  <div class="fixed inset-0 z-70 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl border border-neutral-200 shadow-2xl w-full max-w-md p-6">
      <div class="flex items-start gap-4">
        <div class="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center shrink-0">
          <svg class="w-5 h-5 text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-base font-semibold text-neutral-800">Delete SPV Entity</h3>
          <p class="mt-2 text-sm text-neutral-500">
            Are you sure you want to delete <span class="font-medium text-neutral-700">{entityToDelete.name}</span>? This action cannot be undone.
          </p>
          {#if entityToDelete.subsidiary_count > 0 || entityToDelete.project_count > 0}
            <div class="mt-3 p-3 bg-neutral-50 rounded-lg border border-neutral-200 text-xs text-neutral-600">
              This entity has {entityToDelete.subsidiary_count} subsidiary(ies) and {entityToDelete.project_count} project(s) linked.
            </div>
          {/if}
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-6">
        <button
          onclick={cancelDelete}
          class="px-4 py-2.5 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg
                 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={handleDelete}
          disabled={deleting}
          class="inline-flex items-center px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg
                 hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {#if deleting}
            <div class="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white mr-2"></div>
          {/if}
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

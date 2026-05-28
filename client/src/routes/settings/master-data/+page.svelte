<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { VARIANT_PALETTE, type BadgeVariant } from "$lib/stores/statusRegistry.svelte";
  import type { PaginatedResponse, MasterDataEntry, MasterDataCategory } from "$lib/types";

  const VARIANT_OPTIONS: BadgeVariant[] = [
    "neutral", "muted", "info", "success", "warning", "danger", "orange", "violet", "rose",
  ];

  // ---------------------------------------------------------------------------
  // Category config — mirrors the seed groups
  // ---------------------------------------------------------------------------

  interface CategoryDef {
    value: MasterDataCategory;
    label: string;
  }

  interface CategoryGroup {
    title: string;
    categories: CategoryDef[];
  }

  const categoryGroups: CategoryGroup[] = [
    {
      title: "People & Organizations",
      categories: [
        { value: "vendor_type", label: "Vendor Type" },
        { value: "client_type", label: "Client / Buyer Type" },
        { value: "consultant_specialization", label: "Consultant Specialization" },
        { value: "contractor_classification", label: "Contractor Classification" },
        { value: "investor_type", label: "Investor Type" },
      ],
    },
    {
      title: "Property & Assets",
      categories: [
        { value: "property_type", label: "Property Type" },
        { value: "property_classification", label: "Property Classification" },
        { value: "unit_typology", label: "Unit Typology" },
        { value: "asset_category", label: "Asset Category" },
        { value: "ownership_structure", label: "Ownership Structure" },
      ],
    },
    {
      title: "Operations",
      categories: [
        { value: "maintenance_category", label: "Maintenance Category" },
        { value: "inspection_type", label: "Inspection Type" },
      ],
    },
    {
      title: "Finance",
      categories: [
        { value: "cost_code", label: "Cost Code" },
        { value: "material_category", label: "Material Category" },
        { value: "payment_method", label: "Payment Method" },
        { value: "currency", label: "Currency" },
      ],
    },
    {
      title: "Risk & Compliance",
      categories: [
        { value: "risk_category", label: "Risk Category" },
        { value: "issue_category", label: "Issue Category" },
        { value: "compliance_category", label: "Compliance Category" },
      ],
    },
    {
      title: "Projects",
      categories: [
        { value: "project_type", label: "Project Type" },
        { value: "land_status", label: "Land Status" },
      ],
    },
    {
      title: "Documents",
      categories: [
        { value: "document_type", label: "Document Type" },
      ],
    },
    {
      title: "System",
      categories: [
        { value: "status_badge", label: "Status Badges" },
      ],
    },
  ];

  const allCategories = categoryGroups.flatMap((g) => g.categories);

  function categoryLabel(cat: MasterDataCategory): string {
    return allCategories.find((c) => c.value === cat)?.label ?? cat;
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let selectedCategory = $state<MasterDataCategory>("vendor_type");
  let entries = $state<MasterDataEntry[]>([]);
  let loading = $state(false);
  let totalCount = $state(0);

  let searchQuery = $state("");
  let showInactive = $state(false);
  let searchTimeout: ReturnType<typeof setTimeout>;

  // Modal
  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let form = $state({
    code: "",
    label: "",
    description: "",
    sort_order: 0,
    variant: "neutral" as BadgeVariant,
  });

  // Delete
  let showDeleteConfirm = $state<number | null>(null);
  let deleting = $state<number | null>(null);

  // Toggle active
  let toggling = $state<number | null>(null);

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async function loadEntries() {
    loading = true;
    try {
      const params: Record<string, string> = {
        category: selectedCategory,
        ordering: "sort_order,label",
      };
      if (searchQuery) params.search = searchQuery;
      if (!showInactive) params.is_active = "true";

      const res = await api.get<PaginatedResponse<MasterDataEntry>>(
        "/settings/master-data/",
        params,
      );
      entries = res.results;
      totalCount = res.count;
    } catch {
      toast.error("Load failed", "Could not load master data entries.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void selectedCategory;
    void searchQuery;
    void showInactive;
    loadEntries();
  });

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
    }, 300);
  }

  function openAdd() {
    editingId = null;
    form = { code: "", label: "", description: "", sort_order: (entries.length + 1) * 10, variant: "neutral" };
    showModal = true;
  }

  function openEdit(entry: MasterDataEntry) {
    editingId = entry.id;
    form = {
      code: entry.code,
      label: entry.label,
      description: entry.description,
      sort_order: entry.sort_order,
      variant: ((entry.metadata as Record<string, unknown>)?.variant as BadgeVariant) ?? "neutral",
    };
    showModal = true;
  }

  async function handleSave() {
    if (!form.code.trim()) {
      toast.error("Validation", "Code is required.");
      return;
    }
    if (!form.label.trim()) {
      toast.error("Validation", "Label is required.");
      return;
    }
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        code: form.code,
        label: form.label,
        description: form.description,
        sort_order: form.sort_order,
      };
      if (selectedCategory === "status_badge") {
        payload.metadata = { variant: form.variant };
      }
      if (editingId) {
        await api.patch(`/settings/master-data/${editingId}/`, payload);
        toast.success("Updated", "Entry updated successfully.");
      } else {
        await api.post("/settings/master-data/", {
          ...payload,
          category: selectedCategory,
        });
        toast.success("Created", "Entry created successfully.");
      }
      showModal = false;
      await loadEntries();
    } catch (err) {
      if (err instanceof ApiError) {
        const msgs = Object.values(err.fieldErrors).flat().join(" ");
        toast.error("Save failed", msgs || "Please check the form for errors.");
      } else {
        toast.error("Save failed", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  async function handleToggleActive(entry: MasterDataEntry) {
    toggling = entry.id;
    try {
      await api.patch(`/settings/master-data/${entry.id}/`, {
        is_active: !entry.is_active,
      });
      toast.success(entry.is_active ? "Deactivated" : "Activated", `"${entry.label}" ${entry.is_active ? "deactivated" : "activated"}.`);
      await loadEntries();
    } catch {
      toast.error("Update failed", "Could not toggle entry status.");
    } finally {
      toggling = null;
    }
  }

  async function handleDelete(id: number) {
    deleting = id;
    try {
      await api.delete(`/settings/master-data/${id}/`);
      toast.success("Deleted", "Entry removed.");
      showDeleteConfirm = null;
      await loadEntries();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error("Cannot delete", "System entries cannot be deleted.");
      } else {
        toast.error("Delete failed", "Could not delete entry.");
      }
    } finally {
      deleting = null;
    }
  }
</script>

<!-- Page header -->
<div class="mb-8">
  <h2 class="text-xl font-semibold text-neutral-800">Master Data</h2>
  <p class="mt-1 text-sm text-neutral-500">
    Manage reference data and lookup values used across the platform.
  </p>
</div>

<div class="flex gap-6">
  <!-- ===== Category sidebar ===== -->
  <div class="w-56 shrink-0">
    {#each categoryGroups as group}
      <div class="mb-6">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-2 px-2">
          {group.title}
        </p>
        <nav class="space-y-0.5">
          {#each group.categories as cat}
            <button
              onclick={() => { selectedCategory = cat.value; searchQuery = ""; }}
              class="w-full text-left px-2 py-1.5 rounded-md text-[13px] font-medium transition-colors
                     {selectedCategory === cat.value
                       ? 'bg-neutral-800 text-white'
                       : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-800'}"
            >
              {cat.label}
            </button>
          {/each}
        </nav>
      </div>
    {/each}
  </div>

  <!-- ===== Content area ===== -->
  <div class="flex-1 min-w-0">
    <!-- Toolbar -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-3">
        <h3 class="text-base font-semibold text-neutral-800">
          {categoryLabel(selectedCategory)}
        </h3>
        <span class="text-xs text-neutral-400 bg-neutral-100 rounded-full px-2 py-0.5">
          {totalCount}
        </span>
      </div>
      <button
        onclick={openAdd}
        class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-neutral-800 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add Entry
      </button>
    </div>

    <!-- Search + filters -->
    <div class="flex items-center gap-3 mb-4">
      <div class="relative flex-1 max-w-sm">
        <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          type="text"
          placeholder="Search code, label, description..."
          value={searchQuery}
          oninput={onSearchInput}
          class="w-full rounded-lg border border-neutral-200 bg-white py-1.5 pl-8 pr-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
        />
      </div>
      <label class="inline-flex items-center gap-2 text-sm text-neutral-600 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={showInactive}
          onchange={() => (showInactive = !showInactive)}
          class="rounded border-neutral-300 text-neutral-800 focus:ring-neutral-400"
        />
        Show inactive
      </label>
    </div>

    <!-- Table -->
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      {#if loading && entries.length === 0}
        <div class="flex items-center justify-center py-16 text-sm text-neutral-400">
          Loading...
        </div>
      {:else if entries.length === 0}
        <div class="flex flex-col items-center justify-center py-16 text-sm text-neutral-400">
          <p>No entries found.</p>
          <button onclick={openAdd} class="mt-2 text-neutral-800 hover:underline font-medium">
            Add the first entry
          </button>
        </div>
      {:else}
        <table class="w-full text-left text-sm">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-50/60">
              <th class="px-4 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Code</th>
              <th class="px-4 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Label</th>
              {#if selectedCategory === "status_badge"}
                <th class="px-4 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide">Preview</th>
              {:else}
                <th class="px-4 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide hidden lg:table-cell">Description</th>
              {/if}
              <th class="px-4 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide w-20 text-center">Status</th>
              <th class="px-4 py-2.5 font-semibold text-neutral-500 text-xs uppercase tracking-wide w-28 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each entries as entry (entry.id)}
              <tr class="border-b border-neutral-50 hover:bg-neutral-50/50 transition-colors {!entry.is_active ? 'opacity-50' : ''}">
                <td class="px-4 py-2.5 font-mono text-xs text-neutral-700">{entry.code}</td>
                <td class="px-4 py-2.5 font-medium text-neutral-800">{entry.label}</td>
                {#if selectedCategory === "status_badge"}
                  <td class="px-4 py-2.5">
                    <StatusBadge status={entry.code} label={entry.label} />
                  </td>
                {:else}
                  <td class="px-4 py-2.5 text-neutral-500 hidden lg:table-cell max-w-xs truncate">{entry.description}</td>
                {/if}
                <td class="px-4 py-2.5 text-center">
                  {#if entry.is_active}
                    <span class="inline-block rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">Active</span>
                  {:else}
                    <span class="inline-block rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-500">Inactive</span>
                  {/if}
                </td>
                <td class="px-4 py-2.5 text-right">
                  <div class="inline-flex items-center gap-1">
                    <!-- Edit -->
                    <button
                      onclick={() => openEdit(entry)}
                      title="Edit"
                      class="rounded p-1 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                      </svg>
                    </button>
                    <!-- Toggle active -->
                    <button
                      onclick={() => handleToggleActive(entry)}
                      disabled={toggling === entry.id}
                      title={entry.is_active ? "Deactivate" : "Activate"}
                      class="rounded p-1 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors disabled:opacity-40"
                    >
                      {#if entry.is_active}
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M3.98 8.223A10.477 10.477 0 0 0 1.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.451 10.451 0 0 1 12 4.5c4.756 0 8.773 3.162 10.065 7.498a10.522 10.522 0 0 1-4.293 5.774M6.228 6.228 3 3m3.228 3.228 3.65 3.65m7.894 7.894L21 21m-3.228-3.228-3.65-3.65m0 0a3 3 0 1 0-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      {:else}
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" />
                          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                        </svg>
                      {/if}
                    </button>
                    <!-- Delete (non-system only) -->
                    {#if !entry.is_system}
                      <button
                        onclick={() => (showDeleteConfirm = entry.id)}
                        title="Delete"
                        class="rounded p-1 text-neutral-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </button>
                    {:else}
                      <span class="rounded p-1 text-neutral-200 cursor-not-allowed" title="System entry — cannot delete">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
                        </svg>
                      </span>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
</div>

<!-- ===== Create / Edit Modal ===== -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm"
      onclick={() => (showModal = false)}
      aria-label="Close"
    ></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-semibold text-neutral-800 mb-4">
        {editingId ? "Edit Entry" : "New Entry"}
      </h3>

      <div class="space-y-4">
        <!-- Code -->
        <div>
          <label for="mdm-code" class="block text-sm font-medium text-neutral-700 mb-1">Code</label>
          <input
            id="mdm-code"
            type="text"
            bind:value={form.code}
            disabled={editingId !== null}
            placeholder="e.g. general_supplier"
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400 disabled:bg-neutral-50 disabled:text-neutral-500"
          />
          {#if editingId}
            <p class="mt-1 text-xs text-neutral-400">Code cannot be changed after creation.</p>
          {/if}
        </div>

        <!-- Label -->
        <div>
          <label for="mdm-label" class="block text-sm font-medium text-neutral-700 mb-1">Label</label>
          <input
            id="mdm-label"
            type="text"
            bind:value={form.label}
            placeholder="e.g. General Supplier"
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
          />
        </div>

        <!-- Description -->
        <div>
          <label for="mdm-desc" class="block text-sm font-medium text-neutral-700 mb-1">Description</label>
          <textarea
            id="mdm-desc"
            bind:value={form.description}
            rows={3}
            placeholder="Brief description of this entry..."
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400 resize-none"
          ></textarea>
        </div>

        <!-- Variant (status_badge only) -->
        {#if selectedCategory === "status_badge"}
          <div>
            <label for="mdm-variant" class="block text-sm font-medium text-neutral-700 mb-1">Variant</label>
            <select
              id="mdm-variant"
              bind:value={form.variant}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
            >
              {#each VARIANT_OPTIONS as v}
                <option value={v}>{v.charAt(0).toUpperCase() + v.slice(1)}</option>
              {/each}
            </select>
            <div class="mt-2 flex items-center gap-2">
              <span class="text-xs text-neutral-500">Preview:</span>
              <span class="inline-flex items-center border rounded-md font-medium px-2 py-0.5 text-[11px] {VARIANT_PALETTE[form.variant]}">
                {form.label || "Sample"}
              </span>
            </div>
          </div>
        {/if}

        <!-- Sort Order -->
        <div>
          <label for="mdm-sort" class="block text-sm font-medium text-neutral-700 mb-1">Sort Order</label>
          <input
            id="mdm-sort"
            type="number"
            bind:value={form.sort_order}
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
          />
        </div>
      </div>

      <!-- Actions -->
      <div class="mt-6 flex justify-end gap-2">
        <button
          onclick={() => (showModal = false)}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={handleSave}
          disabled={saving}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 transition-colors disabled:opacity-50"
        >
          {saving ? "Saving..." : editingId ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ===== Delete Confirmation ===== -->
{#if showDeleteConfirm !== null}
  {@const target = entries.find((e) => e.id === showDeleteConfirm)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm"
      onclick={() => (showDeleteConfirm = null)}
      aria-label="Close"
    ></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6 text-center">
      <div class="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-red-50">
        <svg class="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
      </div>
      <h3 class="text-base font-semibold text-neutral-800 mb-1">Delete Entry</h3>
      <p class="text-sm text-neutral-500 mb-5">
        Are you sure you want to delete <strong class="text-neutral-700">{target?.label}</strong>? This action cannot be undone.
      </p>
      <div class="flex justify-center gap-2">
        <button
          onclick={() => (showDeleteConfirm = null)}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={() => showDeleteConfirm !== null && handleDelete(showDeleteConfirm)}
          disabled={deleting !== null}
          class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50"
        >
          {deleting !== null ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import type { BOMListItem, BOMDetail, BOMItemEntry, PaginatedResponse } from "$lib/types";

  type ProjectOption = { id: number; name: string };

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------

  let boms = $state<BOMListItem[]>([]);
  let projects = $state<ProjectOption[]>([]);

  let loading = $state(true);
  let saving = $state(false);

  // Search & pagination
  let search = $state("");
  let currentPage = $state(1);
  let pageSize = $state(25);
  let totalCount = $state(0);
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endItem = $derived(Math.min(currentPage * pageSize, totalCount));

  // Expandable rows
  let expandedId = $state<number | null>(null);
  let expandedDetail = $state<BOMDetail | null>(null);
  let expandLoading = $state(false);

  // Modal
  let modalOpen = $state(false);
  let modalMode = $state<"create" | "edit">("create");
  let editingId = $state<number | null>(null);
  let formErrors = $state<Record<string, string[]>>({});

  // Form
  const emptyItem = (): BOMItemEntry => ({
    material_name: "",
    category: "",
    quantity: 0,
    unit_of_measure: "",
    unit_cost: 0,
    notes: "",
    sort_order: 0,
  });

  const emptyForm = () => ({
    name: "",
    description: "",
    project: "" as string,
    unit_type: "",
    quantity_of_units: 1,
    status: "draft",
    items: [emptyItem()] as BOMItemEntry[],
  });

  let form = $state(emptyForm());

  // ---------------------------------------------------------------------------
  // Dev Fill
  // ---------------------------------------------------------------------------

  const isDev = typeof window !== "undefined" && window.location.hostname === "localhost";

  const BOM_SAMPLES = [
    {
      name: "Residential Unit — Shell & Core",
      unit_type: "Residential Unit",
      quantity_of_units: 1,
      status: "draft",
      description: "Standard bill of materials for a single residential unit shell and core construction.",
      items: [
        { material_name: "Cement", category: "Structural", quantity: 450, unit_of_measure: "Bags", unit_cost: 12, notes: "OPC 42.5 Grade", sort_order: 0 },
        { material_name: "Sand", category: "Structural", quantity: 30, unit_of_measure: "Tons", unit_cost: 45, notes: "Washed plastering sand", sort_order: 1 },
        { material_name: "Rebar", category: "Structural", quantity: 4, unit_of_measure: "Tons", unit_cost: 950, notes: "Y12 & Y16 deformed bars", sort_order: 2 },
        { material_name: "Blocks", category: "Masonry", quantity: 5000, unit_of_measure: "Pieces", unit_cost: 1.50, notes: "200mm hollow concrete blocks", sort_order: 3 },
        { material_name: "Electrical Conduit", category: "MEP", quantity: 300, unit_of_measure: "Meters", unit_cost: 8.50, notes: "25mm PVC conduit", sort_order: 4 },
      ],
    },
    {
      name: "Villa Type A — Complete Build",
      unit_type: "Villa",
      quantity_of_units: 1,
      status: "draft",
      description: "Complete material list for Villa Type A including structure, finishes, and MEP rough-in.",
      items: [
        { material_name: "Concrete", category: "Structural", quantity: 180, unit_of_measure: "m\u00B3", unit_cost: 120, notes: "C30/37 ready-mix", sort_order: 0 },
        { material_name: "Steel Reinforcement", category: "Structural", quantity: 8, unit_of_measure: "Tons", unit_cost: 1100, notes: "Mixed bar sizes", sort_order: 1 },
        { material_name: "Bricks", category: "Masonry", quantity: 12000, unit_of_measure: "Pieces", unit_cost: 0.85, notes: "Standard clay facing bricks", sort_order: 2 },
        { material_name: "Timber Formwork", category: "Temporary Works", quantity: 200, unit_of_measure: "m\u00B2", unit_cost: 35, notes: "Marine plywood 18mm", sort_order: 3 },
        { material_name: "Plumbing Pipes", category: "MEP", quantity: 450, unit_of_measure: "Meters", unit_cost: 15, notes: "PPR hot & cold water pipes", sort_order: 4 },
      ],
    },
    {
      name: "Commercial Floor Fit-Out",
      unit_type: "Floor",
      quantity_of_units: 1,
      status: "draft",
      description: "Fit-out materials for a single commercial floor, covering ceilings, partitions, flooring, and fire safety.",
      items: [
        { material_name: "Ceiling Tiles", category: "Finishes", quantity: 500, unit_of_measure: "m\u00B2", unit_cost: 18, notes: "600x600 mineral fibre", sort_order: 0 },
        { material_name: "Partition Drywall", category: "Finishes", quantity: 320, unit_of_measure: "m\u00B2", unit_cost: 25, notes: "12.5mm gypsum board double-sided", sort_order: 1 },
        { material_name: "Floor Tiles", category: "Finishes", quantity: 400, unit_of_measure: "m\u00B2", unit_cost: 42, notes: "600x600 porcelain", sort_order: 2 },
        { material_name: "Cable Tray", category: "MEP", quantity: 150, unit_of_measure: "Meters", unit_cost: 28, notes: "Perforated galvanized 300mm", sort_order: 3 },
        { material_name: "Fire Sprinkler Heads", category: "Fire Safety", quantity: 80, unit_of_measure: "Pieces", unit_cost: 65, notes: "Concealed pendant type", sort_order: 4 },
      ],
    },
  ];

  let bomDevIdx = 0;

  function devFillBOM() {
    const sample = BOM_SAMPLES[bomDevIdx % BOM_SAMPLES.length];
    bomDevIdx++;
    form.name = sample.name;
    form.description = sample.description;
    form.unit_type = sample.unit_type;
    form.quantity_of_units = sample.quantity_of_units;
    form.status = sample.status;
    form.project = "";
    form.items = sample.items.map((it) => ({ ...it }));
  }

  // ---------------------------------------------------------------------------
  // Data loading
  // ---------------------------------------------------------------------------

  async function fetchBOMs() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search.trim()) params.search = search.trim();
      const res = await api.get<PaginatedResponse<BOMListItem>>("/bom/", params);
      boms = res.results;
      totalCount = res.count;
    } catch {
      boms = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load bills of materials.");
    } finally {
      loading = false;
    }
  }

  async function fetchProjects() {
    try {
      const res = await api.get<PaginatedResponse<ProjectOption>>("/projects/", { page_size: "200", ordering: "name" });
      projects = res.results;
    } catch {
      /* non-critical */
    }
  }

  $effect(() => {
    fetchProjects();
  });

  $effect(() => {
    fetchBOMs();
  });

  // ---------------------------------------------------------------------------
  // Expand row
  // ---------------------------------------------------------------------------

  async function toggleExpand(id: number) {
    if (expandedId === id) {
      expandedId = null;
      expandedDetail = null;
      return;
    }
    expandedId = id;
    expandedDetail = null;
    expandLoading = true;
    try {
      expandedDetail = await api.get<BOMDetail>(`/bom/${id}/`);
    } catch {
      toast.error("Error", "Could not load BOM details.");
      expandedId = null;
    } finally {
      expandLoading = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Modal helpers
  // ---------------------------------------------------------------------------

  function openCreate() {
    form = emptyForm();
    formErrors = {};
    editingId = null;
    modalMode = "create";
    modalOpen = true;
  }

  async function openEdit(id: number) {
    formErrors = {};
    modalMode = "edit";
    editingId = id;
    try {
      const detail = await api.get<BOMDetail>(`/bom/${id}/`);
      form = {
        name: detail.name,
        description: detail.description,
        project: detail.project ? String(detail.project) : "",
        unit_type: detail.unit_type,
        quantity_of_units: detail.quantity_of_units,
        status: detail.status,
        items: detail.items.map((it) => ({
          material_name: it.material_name,
          category: it.category,
          quantity: it.quantity,
          unit_of_measure: it.unit_of_measure,
          unit_cost: it.unit_cost,
          notes: it.notes,
          sort_order: it.sort_order,
        })),
      };
      if (form.items.length === 0) form.items = [emptyItem()];
      modalOpen = true;
    } catch {
      toast.error("Error", "Could not load BOM for editing.");
    }
  }

  function closeModal() {
    modalOpen = false;
    editingId = null;
    formErrors = {};
  }

  function addItem() {
    form.items = [...form.items, emptyItem()];
  }

  function removeItem(idx: number) {
    form.items = form.items.filter((_, i) => i !== idx);
    if (form.items.length === 0) form.items = [emptyItem()];
  }

  // ---------------------------------------------------------------------------
  // Save
  // ---------------------------------------------------------------------------

  function buildPayload() {
    return {
      name: form.name.trim(),
      description: form.description.trim(),
      project: form.project ? Number(form.project) : null,
      unit_type: form.unit_type.trim(),
      quantity_of_units: form.quantity_of_units,
      status: form.status,
      items: form.items
        .filter((it) => it.material_name.trim())
        .map((it, idx) => ({
          material_name: it.material_name.trim(),
          category: it.category.trim(),
          quantity: String(it.quantity),
          unit_of_measure: it.unit_of_measure.trim(),
          unit_cost: String(it.unit_cost),
          notes: it.notes.trim(),
          sort_order: idx,
        })),
    };
  }

  async function handleSave() {
    if (!form.name.trim()) {
      toast.error("Validation", "BOM name is required.");
      return;
    }
    saving = true;
    formErrors = {};
    try {
      if (modalMode === "create") {
        await api.post("/bom/", buildPayload());
        toast.success("Created", `BOM "${form.name}" created.`);
      } else if (editingId) {
        await api.put(`/bom/${editingId}/`, buildPayload());
        toast.success("Updated", `BOM "${form.name}" updated.`);
      }
      closeModal();
      await fetchBOMs();
      // Refresh expanded row if it was the one edited
      if (expandedId && expandedId === editingId) {
        expandedDetail = await api.get<BOMDetail>(`/bom/${expandedId}/`);
      }
    } catch (err) {
      if (err instanceof ApiError && err.fieldErrors) {
        formErrors = err.fieldErrors;
      } else {
        toast.error("Save failed", "Could not save the bill of materials.");
      }
    } finally {
      saving = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Delete
  // ---------------------------------------------------------------------------

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete BOM "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/bom/${id}/`);
      toast.success("Deleted", `BOM "${name}" removed.`);
      if (expandedId === id) {
        expandedId = null;
        expandedDetail = null;
      }
      await fetchBOMs();
    } catch {
      toast.error("Error", "Could not delete BOM.");
    }
  }

  // ---------------------------------------------------------------------------
  // Formatting
  // ---------------------------------------------------------------------------

  function fmtCurrency(value: string | number): string {
    return currency.format(Number(value || 0));
  }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  }

  const statusClasses: Record<string, string> = {
    draft: "bg-amber-50 text-amber-700",
    approved: "bg-emerald-50 text-emerald-700",
    archived: "bg-neutral-100 text-neutral-500",
  };

  function itemLineTotal(it: BOMItemEntry): number {
    return (Number(it.quantity) || 0) * (Number(it.unit_cost) || 0);
  }

  const formTotal = $derived(
    form.items.reduce((sum, it) => sum + itemLineTotal(it), 0),
  );
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Material Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Bills of Materials</h1>
      <p class="text-sm text-neutral-400 mt-1">Define material requirements for construction projects and building components.</p>
    </div>
    <button
      class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 transition-colors"
      onclick={openCreate}
    >
      New BOM
    </button>
  </div>

  <!-- Search & Filters -->
  <section class="bg-white rounded-xl border border-neutral-200 p-4">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <input
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        placeholder="Search by BOM #, name, project, unit type..."
        bind:value={search}
        oninput={() => { currentPage = 1; fetchBOMs(); }}
      />
      <select
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        bind:value={pageSize}
        onchange={() => { currentPage = 1; fetchBOMs(); }}
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
            <th class="px-3 py-2 w-8"></th>
            <th class="px-3 py-2">BOM #</th>
            <th class="px-3 py-2">Name</th>
            <th class="px-3 py-2">Project</th>
            <th class="px-3 py-2">Unit Type</th>
            <th class="px-3 py-2 text-right">Units</th>
            <th class="px-3 py-2">Status</th>
            <th class="px-3 py-2 text-right">Est. Cost</th>
            <th class="px-3 py-2 text-right">Items</th>
            <th class="px-3 py-2">Created</th>
            <th class="px-3 py-2 w-20"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-50">
          {#if loading}
            <tr><td colspan="11" class="px-3 py-10 text-center text-sm text-neutral-400">Loading bills of materials...</td></tr>
          {:else if boms.length === 0}
            <tr><td colspan="11" class="px-3 py-10 text-center text-sm text-neutral-400">No bills of materials found</td></tr>
          {:else}
            {#each boms as bom}
              <!-- Main row -->
              <tr
                class="hover:bg-neutral-50 transition-colors group"
              >
                <td class="px-3 py-3">
                  <button
                    class="text-neutral-400 hover:text-neutral-700 transition-colors"
                    onclick={() => toggleExpand(bom.id)}
                    aria-label={expandedId === bom.id ? "Collapse" : "Expand"}
                  >
                    <svg class="w-4 h-4 transition-transform {expandedId === bom.id ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m9 5 7 7-7 7" />
                    </svg>
                  </button>
                </td>
                <td class="px-3 py-3">
                  <button class="text-sm font-mono text-neutral-900 hover:underline" onclick={() => toggleExpand(bom.id)}>{bom.bom_number}</button>
                </td>
                <td class="px-3 py-3 text-sm font-medium text-neutral-900">{bom.name}</td>
                <td class="px-3 py-3 text-sm text-neutral-600">{bom.project_name || "—"}</td>
                <td class="px-3 py-3 text-sm text-neutral-600">{bom.unit_type || "—"}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-600 tabular-nums">{bom.quantity_of_units}</td>
                <td class="px-3 py-3">
                  <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium capitalize {statusClasses[bom.status] || 'bg-neutral-100 text-neutral-500'}">
                    {bom.status}
                  </span>
                </td>
                <td class="px-3 py-3 text-sm text-right font-medium text-neutral-900 tabular-nums">{fmtCurrency(bom.total_estimated_cost)}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-600 tabular-nums">{bom.item_count}</td>
                <td class="px-3 py-3 text-xs text-neutral-400">{fmtDate(bom.created_at)}</td>
                <td class="px-3 py-3">
                  <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      class="p-1 rounded text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 transition-colors"
                      onclick={() => openEdit(bom.id)}
                      aria-label="Edit"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
                      </svg>
                    </button>
                    <button
                      class="p-1 rounded text-neutral-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      onclick={() => handleDelete(bom.id, bom.name)}
                      aria-label="Delete"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Expanded detail row -->
              {#if expandedId === bom.id}
                <tr>
                  <td colspan="11" class="px-0 py-0">
                    <div class="bg-neutral-50/80 border-t border-b border-neutral-100 px-10 py-4">
                      {#if expandLoading}
                        <p class="text-sm text-neutral-400 py-4 text-center">Loading items...</p>
                      {:else if expandedDetail}
                        {#if expandedDetail.description}
                          <p class="text-sm text-neutral-500 mb-3">{expandedDetail.description}</p>
                        {/if}
                        <table class="w-full text-sm">
                          <thead>
                            <tr class="text-[11px] uppercase tracking-wider text-neutral-400 border-b border-neutral-200">
                              <th class="px-3 py-2 text-left">Material</th>
                              <th class="px-3 py-2 text-left">Category</th>
                              <th class="px-3 py-2 text-right">Qty</th>
                              <th class="px-3 py-2 text-left">Unit</th>
                              <th class="px-3 py-2 text-right">Unit Cost</th>
                              <th class="px-3 py-2 text-right">Line Total</th>
                              <th class="px-3 py-2 text-left">Notes</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-neutral-100">
                            {#each expandedDetail.items as item}
                              <tr>
                                <td class="px-3 py-2 font-medium text-neutral-900">{item.material_name}</td>
                                <td class="px-3 py-2 text-neutral-500">{item.category || "—"}</td>
                                <td class="px-3 py-2 text-right tabular-nums text-neutral-700">{Number(item.quantity).toLocaleString()}</td>
                                <td class="px-3 py-2 text-neutral-500">{item.unit_of_measure}</td>
                                <td class="px-3 py-2 text-right tabular-nums text-neutral-700">{fmtCurrency(item.unit_cost)}</td>
                                <td class="px-3 py-2 text-right tabular-nums font-medium text-neutral-900">{fmtCurrency(item.line_total)}</td>
                                <td class="px-3 py-2 text-neutral-400 text-xs">{item.notes || "—"}</td>
                              </tr>
                            {/each}
                          </tbody>
                          <tfoot>
                            <tr class="border-t border-neutral-200">
                              <td colspan="5" class="px-3 py-2 text-right text-xs font-semibold uppercase text-neutral-500">Total</td>
                              <td class="px-3 py-2 text-right tabular-nums font-bold text-neutral-900">{fmtCurrency(expandedDetail.total_estimated_cost)}</td>
                              <td></td>
                            </tr>
                          </tfoot>
                        </table>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/if}
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
          onclick={() => { if (currentPage > 1) { currentPage -= 1; fetchBOMs(); } }}
          disabled={currentPage <= 1}
        >Prev</button>
        <span class="text-sm text-neutral-500">Page {currentPage} of {totalPages}</span>
        <button
          class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40"
          onclick={() => { if (currentPage < totalPages) { currentPage += 1; fetchBOMs(); } }}
          disabled={currentPage >= totalPages}
        >Next</button>
      </div>
    </div>
  </section>
</div>

<!-- ========================================================================= -->
<!-- Create / Edit Modal                                                        -->
<!-- ========================================================================= -->
<Modal
  open={modalOpen}
  onclose={closeModal}
  title={modalMode === "create" ? "New Bill of Materials" : "Edit Bill of Materials"}
  maxWidth="max-w-4xl"
>
  <div class="space-y-5">
    <!-- BOM Header Fields -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <label class="block">
        <span class="text-xs font-medium text-neutral-500">BOM Name *</span>
        <input
          class="mt-1 w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
                 {formErrors.name ? 'border-red-300' : 'border-neutral-200'}"
          placeholder="e.g. Residential Unit — Shell & Core"
          bind:value={form.name}
        />
        {#if formErrors.name}<p class="text-xs text-red-600 mt-1">{formErrors.name.join(", ")}</p>{/if}
      </label>
      <label class="block">
        <span class="text-xs font-medium text-neutral-500">Project</span>
        <select
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          bind:value={form.project}
        >
          <option value="">None (Template)</option>
          {#each projects as p}
            <option value={p.id}>{p.name}</option>
          {/each}
        </select>
      </label>
      <label class="block">
        <span class="text-xs font-medium text-neutral-500">Unit Type</span>
        <input
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="e.g. Residential Unit, Villa, Floor"
          bind:value={form.unit_type}
        />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="block">
          <span class="text-xs font-medium text-neutral-500">Quantity of Units</span>
          <input
            type="number" min="1"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            bind:value={form.quantity_of_units}
          />
        </label>
        <label class="block">
          <span class="text-xs font-medium text-neutral-500">Status</span>
          <select
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            bind:value={form.status}
          >
            <option value="draft">Draft</option>
            <option value="approved">Approved</option>
            <option value="archived">Archived</option>
          </select>
        </label>
      </div>
    </div>
    <label class="block">
      <span class="text-xs font-medium text-neutral-500">Description</span>
      <textarea
        rows={2}
        class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        placeholder="Purpose or scope of this BOM..."
        bind:value={form.description}
      ></textarea>
    </label>

    <!-- Items Section -->
    <hr class="border-neutral-100" />
    <div class="flex items-center justify-between">
      <h3 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Material Items</h3>
      <span class="text-xs text-neutral-400 tabular-nums">Total: {fmtCurrency(formTotal)}</span>
    </div>

    <div class="overflow-x-auto -mx-1">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-[11px] uppercase tracking-wider text-neutral-400 border-b border-neutral-200">
            <th class="px-2 py-2 text-left">Material *</th>
            <th class="px-2 py-2 text-left">Category</th>
            <th class="px-2 py-2 text-right w-24">Qty *</th>
            <th class="px-2 py-2 text-left w-28">Unit *</th>
            <th class="px-2 py-2 text-right w-28">Unit Cost *</th>
            <th class="px-2 py-2 text-right w-28">Line Total</th>
            <th class="px-2 py-2 text-left">Notes</th>
            <th class="px-2 py-2 w-10"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-50">
          {#each form.items as item, idx}
            <tr>
              <td class="px-2 py-1.5">
                <input
                  class="w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  placeholder="Material name"
                  bind:value={item.material_name}
                />
              </td>
              <td class="px-2 py-1.5">
                <input
                  class="w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  placeholder="Category"
                  bind:value={item.category}
                />
              </td>
              <td class="px-2 py-1.5">
                <input
                  type="number" min="0" step="0.01"
                  class="w-full rounded border border-neutral-200 px-2 py-1.5 text-sm text-right tabular-nums focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  bind:value={item.quantity}
                />
              </td>
              <td class="px-2 py-1.5">
                <input
                  class="w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  placeholder="Unit"
                  bind:value={item.unit_of_measure}
                />
              </td>
              <td class="px-2 py-1.5">
                <input
                  type="number" min="0" step="0.01"
                  class="w-full rounded border border-neutral-200 px-2 py-1.5 text-sm text-right tabular-nums focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  bind:value={item.unit_cost}
                />
              </td>
              <td class="px-2 py-1.5 text-right tabular-nums text-sm font-medium text-neutral-700">
                {fmtCurrency(itemLineTotal(item))}
              </td>
              <td class="px-2 py-1.5">
                <input
                  class="w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-900"
                  placeholder="Notes"
                  bind:value={item.notes}
                />
              </td>
              <td class="px-2 py-1.5 text-center">
                <button
                  class="p-1 rounded text-neutral-300 hover:text-red-500 hover:bg-red-50 transition-colors"
                  onclick={() => removeItem(idx)}
                  aria-label="Remove item"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <button
      class="text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors flex items-center gap-1"
      onclick={addItem}
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Item
    </button>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 pt-3 border-t border-neutral-100">
      {#if isDev}
        <button
          class="mr-auto px-3 py-2 rounded-lg bg-orange-500 text-white text-sm font-medium hover:bg-orange-600 transition-colors"
          onclick={devFillBOM}
        >Dev Fill</button>
      {/if}
      <button
        onclick={closeModal}
        class="px-4 py-2 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
      >Cancel</button>
      <button
        onclick={handleSave}
        disabled={saving}
        class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-60 transition-colors"
      >
        {saving ? "Saving..." : modalMode === "create" ? "Create BOM" : "Save Changes"}
      </button>
    </div>
  </div>
</Modal>

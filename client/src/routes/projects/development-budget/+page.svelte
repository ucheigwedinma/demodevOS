<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    DevBudgetListItem,
    DevBudgetDetail,
    DevBudgetCategoryItem,
    DevBudgetStatus,
    BudgetCostType,
    BudgetCategoryStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let budgets = $state<DevBudgetListItem[]>([]);
  let loading = $state(true);
  let projectFilter = $state("");

  let detailOpen = $state(false);
  let detail = $state<DevBudgetDetail | null>(null);
  let detailLoading = $state(false);
  let costTypeFilter = $state<"" | "hard" | "soft">("");

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());
  let categoryRows = $state<{ name: string; cost_type: BudgetCostType; allocated_amount: string; status: BudgetCategoryStatus }[]>([]);

  // Add category drawer
  let addCatOpen = $state(false);
  let addCatSaving = $state(false);
  let addCatForm = $state({ name: "", cost_type: "hard" as BudgetCostType, allocated_amount: "", status: "draft" as BudgetCategoryStatus, notes: "" });
  let addCatBudgetId = $state<number | null>(null);

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      version: "1.0",
      equity_amount: "",
      debt_amount: "",
      total_land_area_sqm: "",
      contingency_pct: "5",
      prepared_by: "",
      notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      equity_amount: "1000000000",
      debt_amount: "1500000000",
      total_land_area_sqm: "28000",
      contingency_pct: "5",
      prepared_by: "QS Funke Adeyemi",
    };
    categoryRows = [
      { name: "Land Acquisition", cost_type: "hard", allocated_amount: "450000000", status: "locked" },
      { name: "Construction Cost", cost_type: "hard", allocated_amount: "1200000000", status: "draft" },
      { name: "Infrastructure", cost_type: "hard", allocated_amount: "150000000", status: "estimated" },
      { name: "Professional Fees", cost_type: "soft", allocated_amount: "120000000", status: "contracted" },
      { name: "Marketing & Sales", cost_type: "soft", allocated_amount: "85000000", status: "planned" },
      { name: "Finance Costs", cost_type: "soft", allocated_amount: "180000000", status: "estimated" },
      { name: "Legal & Regulatory", cost_type: "soft", allocated_amount: "45000000", status: "planned" },
      { name: "Contingency", cost_type: "soft", allocated_amount: "125000000", status: "draft" },
    ];
  }

  async function fetchBudgets() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<DevBudgetListItem>>("/projects/dev-budgets/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      budgets = res.results;
      if (projRes) projects = projRes.results;
    } catch { budgets = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; fetchBudgets(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    costTypeFilter = "";
    try { detail = await api.get<DevBudgetDetail>(`/projects/dev-budgets/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveBudget(e: Event) {
    e.preventDefault();
    if (!form.project) { toast.error("Required", "Select a project."); return; }
    saving = true;
    try {
      const created = await api.post<DevBudgetListItem>("/projects/dev-budgets/", {
        ...form,
        project: Number(form.project),
        equity_amount: form.equity_amount || "0",
        debt_amount: form.debt_amount || "0",
        total_land_area_sqm: form.total_land_area_sqm || null,
      });
      for (let i = 0; i < categoryRows.length; i++) {
        const row = categoryRows[i];
        if (!row.name.trim()) continue;
        await api.post(`/projects/dev-budgets/${created.id}/categories/`, {
          ...row,
          allocated_amount: row.allocated_amount || "0",
          sort_order: i,
        });
      }
      toast.success("Budget created", `v${form.version} saved with ${categoryRows.filter(r => r.name.trim()).length} categories.`);
      createOpen = false;
      form = defaultForm();
      categoryRows = [];
      await fetchBudgets();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  async function saveAddCategory(e: Event) {
    e.preventDefault();
    if (!addCatBudgetId || !addCatForm.name.trim()) return;
    addCatSaving = true;
    try {
      await api.post(`/projects/dev-budgets/${addCatBudgetId}/categories/`, {
        ...addCatForm,
        allocated_amount: addCatForm.allocated_amount || "0",
      });
      toast.success("Category added", "");
      addCatOpen = false;
      if (detail) detail = await api.get<DevBudgetDetail>(`/projects/dev-budgets/${detail.id}/`);
    } catch { toast.error("Failed", "Could not add category."); }
    addCatSaving = false;
  }

  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }

  function catStatusColor(s: string): string {
    if (s === "locked") return "bg-emerald-100 text-emerald-800";
    if (s === "contracted") return "bg-blue-100 text-blue-800";
    if (s === "planned") return "bg-indigo-100 text-indigo-800";
    if (s === "estimated") return "bg-amber-100 text-amber-800";
    return "bg-neutral-100 text-neutral-600";
  }

  const filteredCategories = $derived(
    detail ? (costTypeFilter ? detail.categories.filter(c => c.cost_type === costTypeFilter) : detail.categories) : []
  );
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Development Budget</h1>
      <p class="mt-1 text-sm text-neutral-500">Strategic budget baseline — cost categories, funding mix, and contingency tracking.</p>
    </div>
    <button onclick={() => { form = defaultForm(); categoryRows = []; createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Budget</button>
  </div>

  <div class="flex items-center gap-3">
    <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if budgets.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No development budgets found.</p></div>
  {:else}
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each budgets as b}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openDetail(b.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-neutral-900">{b.project_name}</p>
              <p class="text-[10px] text-neutral-500 mt-0.5">v{b.version}</p>
            </div>
            <StatusBadge status={b.status} />
          </div>
          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <p class="text-[9px] text-neutral-400">TDC</p>
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtC(b.total_development_cost)}</p>
            </div>
            <div>
              <p class="text-[9px] text-neutral-400">Cost/sqm</p>
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{b.cost_per_sqm ? fmtC(b.cost_per_sqm) : "--"}</p>
            </div>
          </div>
          <div class="flex items-center justify-between text-xs text-neutral-500">
            <span>{b.category_count} categories</span>
            {#if b.is_baseline}<span class="text-emerald-600 font-semibold">Baseline</span>{/if}
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Development Budget" subtitle={detail ? `${detail.project_name} — v${detail.version}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    {@const eq = Number(detail.equity_amount) || 0}
    {@const db = Number(detail.debt_amount) || 0}
    {@const total = eq + db}
    <div class="p-6 space-y-5">
      <!-- HUD -->
      <div class="flex items-center justify-between">
        <StatusBadge status={detail.status} />
        {#if detail.is_baseline}<span class="text-xs font-semibold text-emerald-600">Baseline Locked</span>{/if}
      </div>

      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">TDC</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.total_development_cost)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-400">Cost/sqm</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{detail.cost_per_sqm ? fmtC(detail.cost_per_sqm) : "--"}</p>
        </div>
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-amber-700">Contingency</p>
          <p class="mt-1 text-lg font-bold text-amber-900 tabular-nums">{detail.contingency_pct}%</p>
        </div>
        <div class="rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase tracking-wider text-indigo-700">Funding</p>
          <p class="mt-1 text-sm font-bold text-indigo-900 tabular-nums">{total > 0 ? Math.round(eq / total * 100) : 0}% Eq / {total > 0 ? Math.round(db / total * 100) : 0}% Debt</p>
        </div>
      </div>

      <!-- Hard/Soft toggle -->
      <div class="flex items-center gap-2">
        <button onclick={() => (costTypeFilter = "")} class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors {costTypeFilter === '' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}">All</button>
        <button onclick={() => (costTypeFilter = "hard")} class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors {costTypeFilter === 'hard' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}">Hard Costs</button>
        <button onclick={() => (costTypeFilter = "soft")} class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors {costTypeFilter === 'soft' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}">Soft Costs</button>
        <div class="flex-1"></div>
        <button onclick={() => { addCatBudgetId = detail!.id; addCatForm = { name: "", cost_type: "hard", allocated_amount: "", status: "draft", notes: "" }; addCatOpen = true; }} class="rounded-md bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200">+ Add Category</button>
      </div>

      <!-- Categories table -->
      {#if filteredCategories.length > 0}
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-neutral-50">
              <tr>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Category</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Allocated</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">% TDC</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actual</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each filteredCategories as cat}
                <tr class="{Number(cat.variance) < 0 ? 'bg-red-50/40' : ''}">
                  <td class="px-3 py-2.5">
                    <p class="text-sm font-medium text-neutral-900">{cat.name}</p>
                    <p class="text-[10px] text-neutral-400">{cat.cost_type_display}</p>
                  </td>
                  <td class="px-3 py-2.5 text-right text-sm font-bold tabular-nums text-neutral-900">{fmtC(cat.allocated_amount)}</td>
                  <td class="px-3 py-2.5 text-center text-xs tabular-nums text-neutral-600">{cat.pct_of_tdc}%</td>
                  <td class="px-3 py-2.5 text-right text-sm tabular-nums {Number(cat.actual_amount) > Number(cat.allocated_amount) ? 'text-red-600 font-semibold' : Number(cat.actual_amount) > 0 ? 'text-emerald-600' : 'text-neutral-400'}">{fmtC(cat.actual_amount)}</td>
                  <td class="px-3 py-2.5 text-center"><span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {catStatusColor(cat.status)}">{cat.status_display}</span></td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <p class="text-sm text-neutral-400 text-center py-6">No categories defined.</p>
      {/if}

      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Prepared By</p><p class="text-sm text-neutral-900">{detail.prepared_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Approved By</p><p class="text-sm text-neutral-900">{detail.approved_by || "--"}</p></div>
      </div>

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Development Budget" subtitle="Define the strategic cost baseline" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveBudget} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Version</span><input bind:value={form.version} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Equity Amount</span><input type="number" step="0.01" bind:value={form.equity_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Debt Amount</span><input type="number" step="0.01" bind:value={form.debt_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Total Land Area (sqm)</span><input type="number" step="0.01" bind:value={form.total_land_area_sqm} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contingency %</span><input type="number" step="0.1" bind:value={form.contingency_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Prepared By</span><input bind:value={form.prepared_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>

    <!-- Categories -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-neutral-600">Budget Categories</span>
        <button type="button" onclick={() => { categoryRows = [...categoryRows, { name: "", cost_type: "hard", allocated_amount: "", status: "draft" }]; }} class="rounded-md bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200">+ Add</button>
      </div>
      {#each categoryRows as row, idx}
        <div class="rounded-lg border border-neutral-200 p-3 mb-2 space-y-2 relative">
          <button type="button" onclick={() => { categoryRows = categoryRows.filter((_, i) => i !== idx); }} class="absolute top-2 right-2 text-neutral-400 hover:text-red-500 text-xs">X</button>
          <input bind:value={row.name} placeholder="Category name" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
          <div class="grid grid-cols-3 gap-2">
            <select bind:value={row.cost_type} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs"><option value="hard">Hard</option><option value="soft">Soft</option></select>
            <input type="number" step="0.01" bind:value={row.allocated_amount} placeholder="Amount" class="rounded-md border border-neutral-200 px-2 py-1.5 text-xs" />
            <select bind:value={row.status} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs"><option value="draft">Draft</option><option value="estimated">Estimated</option><option value="planned">Planned</option><option value="contracted">Contracted</option><option value="locked">Locked</option></select>
          </div>
        </div>
      {/each}
    </div>

    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Budget"}</button>
    </div>
  </form>
</DrawerShell>

<!-- ═══════════ ADD CATEGORY DRAWER ═══════════ -->
<DrawerShell open={addCatOpen} title="Add Category" subtitle="" width="max-w-md" onclose={() => (addCatOpen = false)}>
  <form onsubmit={saveAddCategory} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Name *</span><input bind:value={addCatForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Type</span><select bind:value={addCatForm.cost_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="hard">Hard</option><option value="soft">Soft</option></select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span><select bind:value={addCatForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="draft">Draft</option><option value="estimated">Estimated</option><option value="planned">Planned</option><option value="contracted">Contracted</option><option value="locked">Locked</option></select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Allocated Amount</span><input type="number" step="0.01" bind:value={addCatForm.allocated_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (addCatOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button type="submit" disabled={addCatSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{addCatSaving ? "Saving..." : "Add"}</button>
    </div>
  </form>
</DrawerShell>

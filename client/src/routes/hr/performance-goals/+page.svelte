<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { PerformanceGoalListItem, PerformanceGoalType, PerformanceGoalStatus, PerformanceGoalPriority, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<PerformanceGoalListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterType = $state("");
  let filterStatus = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({ employee: "", title: "", description: "", goal_type: "kpi" as PerformanceGoalType, status: "draft" as PerformanceGoalStatus, priority: "medium" as PerformanceGoalPriority, target_value: "", current_value: "", unit: "", weight: "0", start_date: "", due_date: "", progress: "0", parent_goal: "", notes: "" });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const typeLabels: Record<PerformanceGoalType, string> = { okr: "OKR", kpi: "KPI", project: "Project Goal", development: "Development" };
  const statusLabels: Record<PerformanceGoalStatus, string> = { draft: "Draft", active: "Active", completed: "Completed", cancelled: "Cancelled" };
  const priorityLabels: Record<PerformanceGoalPriority, string> = { low: "Low", medium: "Medium", high: "High", critical: "Critical" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterType) params.goal_type = filterType;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<PerformanceGoalListItem>>("/hr/performance-goals/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() { form = { employee: "", title: "", description: "", goal_type: "kpi", status: "draft", priority: "medium", target_value: "", current_value: "", unit: "", weight: "0", start_date: "", due_date: "", progress: "0", parent_goal: "", notes: "" }; fieldErrors = {}; editingId = null; }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: PerformanceGoalListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/performance-goals/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.title = d.title;
      form.description = d.description ?? "";
      form.goal_type = d.goal_type;
      form.status = d.status;
      form.priority = d.priority;
      form.target_value = d.target_value;
      form.current_value = d.current_value;
      form.unit = d.unit;
      form.weight = String(d.weight);
      form.start_date = d.start_date ?? "";
      form.due_date = d.due_date ?? "";
      form.progress = String(d.progress);
      form.parent_goal = String(d.parent_goal ?? "");
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { title: form.title, description: form.description, goal_type: form.goal_type, status: form.status, priority: form.priority, target_value: form.target_value, current_value: form.current_value, unit: form.unit, weight: Number(form.weight) || 0, progress: Number(form.progress) || 0, notes: form.notes };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.start_date) payload.start_date = form.start_date;
      if (form.due_date) payload.due_date = form.due_date;
      if (form.parent_goal) payload.parent_goal = Number(form.parent_goal);
      if (isEditing) { await api.patch(`/hr/performance-goals/${editingId}/`, payload); toast.success("Goal updated"); }
      else { await api.post("/hr/performance-goals/", payload); toast.success("Goal created"); }
      showSlideOver = false; resetForm(); fetchItems();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        const message = err.fieldErrors.non_field_errors?.[0] ?? Object.values(err.fieldErrors)[0]?.[0] ?? "Please fix the highlighted fields and try again.";
        toast.error("Validation error", message);
      }
      else toast.error("Failed to save");
    } finally { saving = false; }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(v: string) { searchQuery = v; clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300); }
  function goToPage(p: number) { if (p >= 1 && p <= totalPages) { currentPage = p; fetchItems(); } }
  function fieldError(f: string): string { return fieldErrors[f]?.[0] ?? ""; }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Performance Goals</h1>
      <p class="mt-1 text-sm text-neutral-500">Track OKRs, KPIs, and development goals</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Goal
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search goals..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterType} onchange={(e) => { filterType = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      {#each Object.entries(typeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterType || filterStatus ? "No goals match your filters" : "No performance goals yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Goal</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Priority</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Progress</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Due</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5">
                <p class="font-medium text-neutral-900">{item.title}</p>
                {#if item.target_value}<p class="text-xs text-neutral-400 mt-0.5">Target: {item.target_value}{item.unit ? ` ${item.unit}` : ""}</p>{/if}
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{typeLabels[item.goal_type] ?? item.goal_type}</td>
              <td class="px-5 py-3.5 text-neutral-600">{priorityLabels[item.priority]}</td>
              <td class="px-5 py-3.5">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden"><div class="h-full bg-neutral-900 rounded-full" style="width:{item.progress}%"></div></div>
                  <span class="text-xs text-neutral-500 w-8 text-right">{item.progress}%</span>
                </div>
              </td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.due_date ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-center">
                <StatusBadge status={item.status} />
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} goal{totalCount !== 1 ? "s" : ""}</span>
        <div class="flex items-center gap-1">
          <button onclick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&laquo;</button>
          {#each Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1) as p}
            <button onclick={() => goToPage(p)} class="px-2.5 py-1 rounded text-sm {p === currentPage ? 'bg-neutral-900 text-white' : 'hover:bg-neutral-100'}">{p}</button>
          {/each}
          <button onclick={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&raquo;</button>
        </div>
      </div>
    {/if}
  {/if}
</div>

{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Goal" : "New Goal"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="pg-title" class="block text-sm font-medium text-neutral-700 mb-1">Title <span class="text-red-500">*</span></label>
          <input id="pg-title" type="text" bind:value={form.title} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('title') ? 'border-red-400' : ''}" />
          {#if fieldError("title")}<p class="text-xs text-red-500 mt-1">{fieldError("title")}</p>{/if}
        </div>
        {#if !isEditing}
          <div>
            <label for="pg-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="pg-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div>
          <label for="pg-desc" class="block text-sm font-medium text-neutral-700 mb-1">Description</label>
          <textarea id="pg-desc" bind:value={form.description} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="pg-type" class="block text-sm font-medium text-neutral-700 mb-1">Type</label>
            <select id="pg-type" bind:value={form.goal_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(typeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="pg-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="pg-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="pg-priority" class="block text-sm font-medium text-neutral-700 mb-1">Priority</label>
            <select id="pg-priority" bind:value={form.priority} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(priorityLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="pg-target" class="block text-sm font-medium text-neutral-700 mb-1">Target Value</label>
            <input id="pg-target" type="text" bind:value={form.target_value} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="pg-current" class="block text-sm font-medium text-neutral-700 mb-1">Current Value</label>
            <input id="pg-current" type="text" bind:value={form.current_value} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="pg-unit" class="block text-sm font-medium text-neutral-700 mb-1">Unit</label>
            <input id="pg-unit" type="text" bind:value={form.unit} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. %" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pg-start" class="block text-sm font-medium text-neutral-700 mb-1">Start Date</label>
            <DateInput id="pg-start" bind:value={form.start_date} />
          </div>
          <div>
            <label for="pg-due" class="block text-sm font-medium text-neutral-700 mb-1">Due Date</label>
            <DateInput id="pg-due" bind:value={form.due_date} />
          </div>
        </div>
        <div>
          <label for="pg-progress" class="block text-sm font-medium text-neutral-700 mb-1">Progress (%)</label>
          <input id="pg-progress" type="number" min="0" max="100" bind:value={form.progress} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="pg-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="pg-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : isEditing ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .animate-slide-in-right { animation: slideInRight 0.25s ease-out both; }
</style>

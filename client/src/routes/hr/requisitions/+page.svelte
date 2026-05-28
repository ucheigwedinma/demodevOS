<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { JobRequisitionListItem, RequisitionStatus, RequisitionPriority, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<JobRequisitionListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");
  let filterPriority = $state("");

  // Slide-over
  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    title: "",
    position: "" as string,
    department: "" as string,
    requisition_type: "",
    justification: "",
    headcount_requested: 1,
    priority: "medium" as RequisitionPriority,
    salary_range_min: "",
    salary_range_max: "",
    target_start_date: "",
    notes: "",
  });
  let positionOptions = $state<{ id: number; title: string }[]>([]);
  let departmentOptions = $state<{ id: number; name: string }[]>([]);

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<RequisitionStatus, string> = { draft: "Draft", pending_approval: "Pending Approval", approved: "Approved", rejected: "Rejected", cancelled: "Cancelled", filled: "Filled" };
  const priorityLabels: Record<RequisitionPriority, string> = { low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };
  const priorityDot: Record<RequisitionPriority, string> = { low: "bg-neutral-200", medium: "bg-neutral-400", high: "bg-neutral-600", urgent: "bg-neutral-900" };

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      if (filterPriority) params.priority = filterPriority;
      const res = await api.get<PaginatedResponse<JobRequisitionListItem>>("/hr/requisitions/", params);
      items = res.results;
      totalCount = res.count;
    } catch {
      items = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    form = { title: "", position: "", department: "", requisition_type: "", justification: "", headcount_requested: 1, priority: "medium", salary_range_min: "", salary_range_max: "", target_start_date: "", notes: "" };
    fieldErrors = {};
    editingId = null;
  }

  async function loadOptions() {
    try {
      const [posRes, deptRes] = await Promise.all([
        api.get<{ results: { id: number; title: string }[] }>("/hr/positions/", { page_size: "200" }),
        api.get<{ results: { id: number; name: string }[] }>("/settings/departments/", { page_size: "200" }),
      ]);
      positionOptions = posRes.results;
      departmentOptions = deptRes.results;
    } catch { /* ignore */ }
  }

  async function openCreate() {
    resetForm();
    await loadOptions();
    showSlideOver = true;
  }

  async function openEdit(item: JobRequisitionListItem) {
    resetForm();
    editingId = item.id;
    form.title = item.title;
    form.position = item.position ? String(item.position) : "";
    form.department = item.department ? String(item.department) : "";
    form.requisition_type = item.requisition_type;
    form.headcount_requested = item.headcount_requested;
    form.priority = item.priority;
    form.salary_range_min = item.salary_range_min ?? "";
    form.salary_range_max = item.salary_range_max ?? "";
    form.target_start_date = item.target_start_date ?? "";
    await loadOptions();
    try {
      const detail = await api.get<{ justification: string; notes: string }>(`/hr/requisitions/${item.id}/`);
      form.justification = detail.justification;
      form.notes = detail.notes;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        requisition_type: form.requisition_type,
        justification: form.justification,
        headcount_requested: form.headcount_requested,
        priority: form.priority,
        currency: currency.config.code,
        notes: form.notes,
      };
      if (form.position) payload.position = Number(form.position);
      if (form.department) payload.department = Number(form.department);
      if (form.salary_range_min) payload.salary_range_min = form.salary_range_min;
      if (form.salary_range_max) payload.salary_range_max = form.salary_range_max;
      if (form.target_start_date) payload.target_start_date = form.target_start_date;

      if (isEditing) {
        await api.patch(`/hr/requisitions/${editingId}/`, payload);
        toast.success("Requisition updated");
      } else {
        await api.post("/hr/requisitions/", payload);
        toast.success("Requisition created");
      }
      showSlideOver = false;
      resetForm();
      fetchItems();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
        const message = err.fieldErrors.non_field_errors?.[0] ?? Object.values(err.fieldErrors)[0]?.[0] ?? "Please fix the highlighted fields and try again.";
        toast.error("Validation error", message);
      }
      else toast.error("Failed to save requisition");
    } finally {
      saving = false;
    }
  }

  async function submitForApproval(id: number) {
    try {
      await api.post(`/hr/requisitions/${id}/submit_for_approval/`, {});
      toast.success("Requisition submitted for approval");
      fetchItems();
    } catch {
      toast.error("Failed to submit for approval");
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchItems();
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Job Requisitions</h1>
      <p class="mt-1 text-sm text-neutral-500">Headcount requests and approval tracking</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      New Requisition
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search requisitions..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterPriority} onchange={(e) => { filterPriority = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Priority</option>
      {#each Object.entries(priorityLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus || filterPriority ? "No requisitions match your filters" : "No requisitions yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/50">
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Title</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Headcount</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Priority</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Requested By</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Target Date</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each items as item}
              <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
                <td class="px-5 py-3.5 font-medium text-neutral-900">{item.title}</td>
                <td class="px-5 py-3.5 text-neutral-600">{item.department_name ?? "\u2014"}</td>
                <td class="px-5 py-3.5 text-center text-neutral-600">{item.headcount_requested}</td>
                <td class="px-5 py-3.5 text-center">
                  <span class="inline-flex items-center gap-1.5 text-xs"><span class="w-2 h-2 rounded-full {priorityDot[item.priority]}"></span>{priorityLabels[item.priority]}</span>
                </td>
                <td class="px-5 py-3.5 text-neutral-600">{item.requested_by_name}</td>
                <td class="px-5 py-3.5 text-neutral-600 text-xs">{formatDate(item.target_start_date)}</td>
                <td class="px-5 py-3.5 text-center">
                  <StatusBadge status={item.status} />
                </td>
                <td class="px-5 py-3.5 text-center">
                  {#if item.status === "draft"}
                    <button onclick={(e) => { e.stopPropagation(); submitForApproval(item.id); }} class="text-xs font-medium text-neutral-600 hover:text-neutral-900 underline">Submit</button>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} requisition{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Requisition" : "New Requisition"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="req-title" class="block text-sm font-medium text-neutral-700 mb-1">Title <span class="text-red-500">*</span></label>
          <input id="req-title" type="text" bind:value={form.title} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('title') ? 'border-red-400' : ''}" />
          {#if fieldError("title")}<p class="text-xs text-red-500 mt-1">{fieldError("title")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="req-pos" class="block text-sm font-medium text-neutral-700 mb-1">Position</label>
            <select id="req-pos" bind:value={form.position} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">None</option>
              {#each positionOptions as pos}<option value={String(pos.id)}>{pos.title}</option>{/each}
            </select>
          </div>
          <div>
            <label for="req-dept" class="block text-sm font-medium text-neutral-700 mb-1">Department</label>
            <select id="req-dept" bind:value={form.department} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">None</option>
              {#each departmentOptions as dept}<option value={String(dept.id)}>{dept.name}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="req-hc" class="block text-sm font-medium text-neutral-700 mb-1">Headcount</label>
            <input id="req-hc" type="number" min="1" bind:value={form.headcount_requested} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="req-pri" class="block text-sm font-medium text-neutral-700 mb-1">Priority</label>
            <select id="req-pri" bind:value={form.priority} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(priorityLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="req-sal-min" class="block text-sm font-medium text-neutral-700 mb-1">Salary Min</label>
            <input id="req-sal-min" type="text" bind:value={form.salary_range_min} placeholder="0.00" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="req-sal-max" class="block text-sm font-medium text-neutral-700 mb-1">Salary Max</label>
            <input id="req-sal-max" type="text" bind:value={form.salary_range_max} placeholder="0.00" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="req-target" class="block text-sm font-medium text-neutral-700 mb-1">Target Start Date</label>
          <DateInput id="req-target" bind:value={form.target_start_date} />
        </div>
        <div>
          <label for="req-just" class="block text-sm font-medium text-neutral-700 mb-1">Justification</label>
          <textarea id="req-just" bind:value={form.justification} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="req-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="req-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {saving ? "Saving..." : isEditing ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>

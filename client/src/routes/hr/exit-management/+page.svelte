<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { ExitManagementListItem, ExitType, ClearanceStatus, SettlementStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<ExitManagementListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterExitType = $state("");
  let filterClearance = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    exit_type: "resignation" as ExitType,
    notice_date: "",
    last_working_day: "",
    reason: "",
    clearance_status: "pending" as ClearanceStatus,
    final_settlement_status: "pending" as SettlementStatus,
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const exitTypeLabels: Record<ExitType, string> = { resignation: "Resignation", termination: "Termination", retirement: "Retirement", end_of_contract: "End of Contract", redundancy: "Redundancy", other: "Other" };
  const clearanceLabels: Record<ClearanceStatus, string> = { pending: "Pending", in_progress: "In Progress", completed: "Completed" };
  const settlementLabels: Record<SettlementStatus, string> = { pending: "Pending", processing: "Processing", paid: "Paid" };
  const clearanceBadge: Record<ClearanceStatus, string> = { pending: "bg-neutral-100 text-neutral-600", in_progress: "bg-neutral-900 text-white", completed: "bg-neutral-200 text-neutral-500" };
  const settlementBadge: Record<SettlementStatus, string> = { pending: "bg-neutral-100 text-neutral-600", processing: "bg-neutral-900 text-white", paid: "bg-neutral-200 text-neutral-500" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterExitType) params.exit_type = filterExitType;
      if (filterClearance) params.clearance_status = filterClearance;
      const res = await api.get<PaginatedResponse<ExitManagementListItem>>("/hr/exit-management/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", exit_type: "resignation", notice_date: "", last_working_day: "", reason: "", clearance_status: "pending", final_settlement_status: "pending", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: ExitManagementListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/exit-management/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.exit_type = d.exit_type;
      form.notice_date = d.notice_date ?? "";
      form.last_working_day = d.last_working_day ?? "";
      form.reason = d.reason ?? "";
      form.clearance_status = d.clearance_status;
      form.final_settlement_status = d.final_settlement_status;
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { exit_type: form.exit_type, clearance_status: form.clearance_status, final_settlement_status: form.final_settlement_status };
      if (form.employee && !isEditing) payload.employee = Number(form.employee);
      if (form.notice_date) payload.notice_date = form.notice_date;
      if (form.last_working_day) payload.last_working_day = form.last_working_day;
      if (form.reason) payload.reason = form.reason;
      if (form.notes) payload.notes = form.notes;
      if (isEditing) { await api.patch(`/hr/exit-management/${editingId}/`, payload); toast.success("Record updated"); }
      else { await api.post("/hr/exit-management/", payload); toast.success("Record created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Exit Management</h1>
      <p class="mt-1 text-sm text-neutral-500">Manage employee separations, clearance, and settlements</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Exit Record
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search exit records..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterExitType} onchange={(e) => { filterExitType = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      {#each Object.entries(exitTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterClearance} onchange={(e) => { filterClearance = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Clearance</option>
      {#each Object.entries(clearanceLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterExitType || filterClearance ? "No records match your filters" : "No exit records yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Exit Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Notice Date</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Last Working Day</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Clearance</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Settlement</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Processed By</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{exitTypeLabels[item.exit_type]}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.notice_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.last_working_day}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {clearanceBadge[item.clearance_status]}">{clearanceLabels[item.clearance_status]}</span>
              </td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {settlementBadge[item.final_settlement_status]}">{settlementLabels[item.final_settlement_status]}</span>
              </td>
              <td class="px-5 py-3.5 text-neutral-500">{item.processed_by_name ?? "\u2014"}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} record{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Exit Record" : "New Exit Record"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="em-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="em-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div>
          <label for="em-type" class="block text-sm font-medium text-neutral-700 mb-1">Exit Type <span class="text-red-500">*</span></label>
          <select id="em-type" bind:value={form.exit_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(exitTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="em-nd" class="block text-sm font-medium text-neutral-700 mb-1">Notice Date <span class="text-red-500">*</span></label>
            <DateInput id="em-nd" bind:value={form.notice_date} />
            {#if fieldError("notice_date")}<p class="text-xs text-red-500 mt-1">{fieldError("notice_date")}</p>{/if}
          </div>
          <div>
            <label for="em-lwd" class="block text-sm font-medium text-neutral-700 mb-1">Last Working Day <span class="text-red-500">*</span></label>
            <DateInput id="em-lwd" bind:value={form.last_working_day} />
            {#if fieldError("last_working_day")}<p class="text-xs text-red-500 mt-1">{fieldError("last_working_day")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="em-cl" class="block text-sm font-medium text-neutral-700 mb-1">Clearance Status</label>
            <select id="em-cl" bind:value={form.clearance_status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(clearanceLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="em-st" class="block text-sm font-medium text-neutral-700 mb-1">Settlement Status</label>
            <select id="em-st" bind:value={form.final_settlement_status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(settlementLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div>
          <label for="em-reason" class="block text-sm font-medium text-neutral-700 mb-1">Reason</label>
          <textarea id="em-reason" bind:value={form.reason} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="em-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="em-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

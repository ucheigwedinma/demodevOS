<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { PromotionListItem, PromotionStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<PromotionListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    from_position: "",
    to_position: "",
    from_grade: "",
    to_grade: "",
    effective_date: "",
    salary_adjustment: "",
    new_salary: "",
    reason: "",
    status: "pending" as PromotionStatus,
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<PromotionStatus, string> = { pending: "Pending", approved: "Approved", effective: "Effective", cancelled: "Cancelled" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<PromotionListItem>>("/hr/promotions/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", from_position: "", to_position: "", from_grade: "", to_grade: "", effective_date: "", salary_adjustment: "", new_salary: "", reason: "", status: "pending" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: PromotionListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/promotions/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.from_position = d.from_position ?? "";
      form.to_position = d.to_position ?? "";
      form.from_grade = d.from_grade ?? "";
      form.to_grade = d.to_grade ?? "";
      form.effective_date = d.effective_date ?? "";
      form.salary_adjustment = d.salary_adjustment ?? "";
      form.new_salary = d.new_salary ?? "";
      form.reason = d.reason ?? "";
      form.status = d.status;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { to_position: form.to_position, status: form.status };
      if (form.employee && !isEditing) payload.employee = Number(form.employee);
      if (form.from_position) payload.from_position = form.from_position;
      if (form.from_grade) payload.from_grade = form.from_grade;
      if (form.to_grade) payload.to_grade = form.to_grade;
      if (form.effective_date) payload.effective_date = form.effective_date;
      if (form.salary_adjustment) payload.salary_adjustment = form.salary_adjustment;
      if (form.new_salary) payload.new_salary = form.new_salary;
      if (form.reason) payload.reason = form.reason;
      if (isEditing) { await api.patch(`/hr/promotions/${editingId}/`, payload); toast.success("Promotion updated"); }
      else { await api.post("/hr/promotions/", payload); toast.success("Promotion created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Promotions</h1>
      <p class="mt-1 text-sm text-neutral-500">Track employee promotions and career advancement</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Promotion
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search promotions..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No promotions match your filters" : "No promotions yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">From</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">To</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Effective Date</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Adjustment</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Approved By</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-500">{item.from_position || "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-900 font-medium">{item.to_position}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.effective_date}</td>
              <td class="px-5 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{currency.config.code} {item.salary_adjustment}</td>
              <td class="px-5 py-3.5 text-neutral-500">{item.approved_by_name ?? "\u2014"}</td>
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
        <span>{totalCount} promotion{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Promotion" : "New Promotion"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="pr-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="pr-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pr-from" class="block text-sm font-medium text-neutral-700 mb-1">From Position</label>
            <input id="pr-from" type="text" bind:value={form.from_position} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="pr-to" class="block text-sm font-medium text-neutral-700 mb-1">To Position <span class="text-red-500">*</span></label>
            <input id="pr-to" type="text" bind:value={form.to_position} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('to_position') ? 'border-red-400' : ''}" />
            {#if fieldError("to_position")}<p class="text-xs text-red-500 mt-1">{fieldError("to_position")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pr-fg" class="block text-sm font-medium text-neutral-700 mb-1">From Grade</label>
            <input id="pr-fg" type="text" bind:value={form.from_grade} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="pr-tg" class="block text-sm font-medium text-neutral-700 mb-1">To Grade</label>
            <input id="pr-tg" type="text" bind:value={form.to_grade} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pr-date" class="block text-sm font-medium text-neutral-700 mb-1">Effective Date <span class="text-red-500">*</span></label>
            <DateInput id="pr-date" bind:value={form.effective_date} />
            {#if fieldError("effective_date")}<p class="text-xs text-red-500 mt-1">{fieldError("effective_date")}</p>{/if}
          </div>
          <div>
            <label for="pr-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="pr-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pr-adj" class="block text-sm font-medium text-neutral-700 mb-1">Salary Adjustment</label>
            <input id="pr-adj" type="number" step="0.01" bind:value={form.salary_adjustment} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="pr-new" class="block text-sm font-medium text-neutral-700 mb-1">New Salary</label>
            <input id="pr-new" type="number" step="0.01" bind:value={form.new_salary} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div>
          <label for="pr-reason" class="block text-sm font-medium text-neutral-700 mb-1">Reason</label>
          <textarea id="pr-reason" bind:value={form.reason} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

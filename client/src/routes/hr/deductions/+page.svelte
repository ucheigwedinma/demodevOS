<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { DeductionListItem, DeductionType, AllowanceFrequency, PaginatedResponse } from "$lib/types";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<DeductionListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterType = $state("");
  let filterActive = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let deletingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    deduction_type: "other" as DeductionType,
    name: "",
    amount: "",
    frequency: "monthly" as AllowanceFrequency,
    start_date: "",
    end_date: "",
    is_active: true,
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const typeLabels: Record<DeductionType, string> = { tax: "Tax", insurance: "Insurance", pension: "Pension", loan: "Loan Repayment", union: "Union Dues", other: "Other" };
  const freqLabels: Record<AllowanceFrequency, string> = { monthly: "Monthly", quarterly: "Quarterly", annually: "Annually", one_time: "One-Time" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterType) params.deduction_type = filterType;
      if (filterActive) params.is_active = filterActive;
      const res = await api.get<PaginatedResponse<DeductionListItem>>("/hr/deductions/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", deduction_type: "other", name: "", amount: "", frequency: "monthly", start_date: "", end_date: "", is_active: true };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: DeductionListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/deductions/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.deduction_type = d.deduction_type;
      form.name = d.name ?? "";
      form.amount = d.amount ?? "";
      form.frequency = d.frequency;
      form.start_date = d.start_date ?? "";
      form.end_date = d.end_date ?? "";
      form.is_active = d.is_active ?? true;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { deduction_type: form.deduction_type, name: form.name, frequency: form.frequency, is_active: form.is_active };
      if (form.employee && !isEditing) payload.employee = Number(form.employee);
      if (form.amount) payload.amount = form.amount;
      payload.currency = currency.config.code;
      if (form.start_date) payload.start_date = form.start_date;
      if (form.end_date) payload.end_date = form.end_date;
      if (isEditing) { await api.patch(`/hr/deductions/${editingId}/`, payload); toast.success("Deduction updated"); }
      else { await api.post("/hr/deductions/", payload); toast.success("Deduction created"); }
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

  async function handleDelete(item: DeductionListItem) {
    if (!confirm(`Delete deduction "${item.name}" for ${item.employee_name}?`)) return;
    deletingId = item.id;
    try {
      await api.delete(`/hr/deductions/${item.id}/`);
      toast.success("Deduction deleted");
      if (items.length === 1 && currentPage > 1) currentPage -= 1;
      await fetchItems();
    } catch {
      toast.error("Delete failed", "Could not delete deduction.");
    } finally {
      deletingId = null;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(v: string) { searchQuery = v; clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300); }
  function goToPage(p: number) { if (p >= 1 && p <= totalPages) { currentPage = p; fetchItems(); } }
  function fieldError(f: string): string { return fieldErrors[f]?.[0] ?? ""; }

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const DEV_SAMPLES = [
    { employee: "1", deduction_type: "pension" as DeductionType, name: "Pension Fund Contribution", amount: "750", frequency: "monthly" as AllowanceFrequency, start_date: "2026-01-01", end_date: "", is_active: true },
    { employee: "1", deduction_type: "insurance" as DeductionType, name: "Medical Insurance Premium", amount: "1200", frequency: "monthly" as AllowanceFrequency, start_date: "2026-01-01", end_date: "", is_active: true },
    { employee: "1", deduction_type: "loan" as DeductionType, name: "Staff Housing Loan", amount: "3500", frequency: "monthly" as AllowanceFrequency, start_date: "2025-06-01", end_date: "2027-05-31", is_active: true },
  ];
  let devFillIdx = 0;
  function devFill() {
    const s = DEV_SAMPLES[devFillIdx % DEV_SAMPLES.length]; devFillIdx++;
    form = { ...s };
  }

  $effect(() => { fetchItems(); });
</script>

<div class="space-y-4 overflow-x-clip">
  <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
        <a href="/hr" class="hover:text-indigo-700">HR</a>
        <span class="text-neutral-300"> › </span>
        <span class="text-indigo-600">Earnings & Deductions</span>
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Earnings & Deductions</h1>
      <p class="mt-1 max-w-2xl text-sm text-neutral-500">Manage payroll earnings and deductions.</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Deduction
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search deductions..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterType} onchange={(e) => { filterType = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      {#each Object.entries(typeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterActive} onchange={(e) => { filterActive = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterType || filterActive ? "No deductions match your filters" : "No deductions yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Name</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Amount</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Frequency</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{typeLabels[item.deduction_type]}</td>
              <td class="px-5 py-3.5 text-neutral-700">{item.name}</td>
              <td class="px-5 py-3.5 text-neutral-900 text-right tabular-nums">{currency.config.code} {item.amount}</td>
              <td class="px-5 py-3.5 text-neutral-600">{freqLabels[item.frequency]}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {item.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-500'}">{item.is_active ? "Active" : "Inactive"}</span>
              </td>
              <td class="px-5 py-3.5">
                <div class="flex items-center justify-end gap-3">
                  <button onclick={() => openEdit(item)} class="text-xs font-medium text-neutral-500 hover:text-neutral-900 transition-colors">Edit</button>
                  <button
                    onclick={() => handleDelete(item)}
                    disabled={deletingId === item.id}
                    class="text-xs font-medium text-neutral-500 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {deletingId === item.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} deduction{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Deduction" : "New Deduction"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="dd-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="dd-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="dd-type" class="block text-sm font-medium text-neutral-700 mb-1">Type</label>
            <select id="dd-type" bind:value={form.deduction_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(typeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="dd-freq" class="block text-sm font-medium text-neutral-700 mb-1">Frequency</label>
            <select id="dd-freq" bind:value={form.frequency} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(freqLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div>
          <label for="dd-name" class="block text-sm font-medium text-neutral-700 mb-1">Name <span class="text-red-500">*</span></label>
          <input id="dd-name" type="text" bind:value={form.name} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('name') ? 'border-red-400' : ''}" />
          {#if fieldError("name")}<p class="text-xs text-red-500 mt-1">{fieldError("name")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="dd-amt" class="block text-sm font-medium text-neutral-700 mb-1">Amount <span class="text-red-500">*</span></label>
            <input id="dd-amt" type="number" step="0.01" bind:value={form.amount} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums {fieldError('amount') ? 'border-red-400' : ''}" />
            {#if fieldError("amount")}<p class="text-xs text-red-500 mt-1">{fieldError("amount")}</p>{/if}
          </div>
          <div>
            <label for="dd-curr" class="block text-sm font-medium text-neutral-700 mb-1">Currency</label>
            <p id="dd-curr" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-neutral-50 text-neutral-700">{currency.config.code}</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="dd-start" class="block text-sm font-medium text-neutral-700 mb-1">Start Date</label>
            <DateInput id="dd-start" bind:value={form.start_date} />
          </div>
          <div>
            <label for="dd-end" class="block text-sm font-medium text-neutral-700 mb-1">End Date</label>
            <DateInput id="dd-end" bind:value={form.end_date} />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <input id="dd-active" type="checkbox" bind:checked={form.is_active} class="rounded border-neutral-300" />
          <label for="dd-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button type="button" onclick={devFill} class="px-4 py-2 text-sm font-semibold text-white bg-orange-500 rounded-lg hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : isEditing ? "Update" : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .animate-slide-in-right { animation: slideInRight 0.25s ease-out both; }
</style>

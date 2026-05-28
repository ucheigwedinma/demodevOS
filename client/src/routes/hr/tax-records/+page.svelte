<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { TaxRecordListItem, TaxType, FilingStatus, PaginatedResponse } from "$lib/types";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";

  let items = $state<TaxRecordListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterTaxType = $state("");
  let filterFilingStatus = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let deletingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    fiscal_year: "",
    tax_type: "income_tax" as TaxType,
    taxable_income: "",
    tax_amount: "",
    tax_paid: "",
    filing_status: "pending" as FilingStatus,
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const taxTypeLabels: Record<TaxType, string> = { income_tax: "Income Tax", social_security: "Social Security", municipal: "Municipal Tax", other: "Other" };
  const filingStatusLabels: Record<FilingStatus, string> = { pending: "Pending", filed: "Filed", assessed: "Assessed", paid: "Paid" };
  const filingStatusBadge: Record<FilingStatus, string> = { pending: "bg-neutral-100 text-neutral-600", filed: "bg-neutral-900 text-white", assessed: "bg-neutral-200 text-neutral-500", paid: "bg-neutral-300 text-neutral-600" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterTaxType) params.tax_type = filterTaxType;
      if (filterFilingStatus) params.filing_status = filterFilingStatus;
      const res = await api.get<PaginatedResponse<TaxRecordListItem>>("/hr/tax-records/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", fiscal_year: "", tax_type: "income_tax", taxable_income: "", tax_amount: "", tax_paid: "", filing_status: "pending" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: TaxRecordListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/tax-records/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.fiscal_year = d.fiscal_year ?? "";
      form.tax_type = d.tax_type;
      form.taxable_income = d.taxable_income ?? "";
      form.tax_amount = d.tax_amount ?? "";
      form.tax_paid = d.tax_paid ?? "";
      form.filing_status = d.filing_status;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { tax_type: form.tax_type, filing_status: form.filing_status };
      if (form.employee && !isEditing) payload.employee = Number(form.employee);
      if (form.fiscal_year) payload.fiscal_year = form.fiscal_year;
      if (form.taxable_income) payload.taxable_income = form.taxable_income;
      if (form.tax_amount) payload.tax_amount = form.tax_amount;
      if (form.tax_paid) payload.tax_paid = form.tax_paid;
      if (isEditing) { await api.patch(`/hr/tax-records/${editingId}/`, payload); toast.success("Tax record updated"); }
      else { await api.post("/hr/tax-records/", payload); toast.success("Tax record created"); }
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

  async function handleDelete(item: TaxRecordListItem) {
    if (!confirm(`Delete tax record for ${item.employee_name} (${item.fiscal_year})?`)) return;
    deletingId = item.id;
    try {
      await api.delete(`/hr/tax-records/${item.id}/`);
      toast.success("Tax record deleted");
      if (items.length === 1 && currentPage > 1) currentPage -= 1;
      await fetchItems();
    } catch {
      toast.error("Delete failed", "Could not delete tax record.");
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
    { employee: "1", fiscal_year: "2025", tax_type: "income_tax" as TaxType, taxable_income: "360000", tax_amount: "18000", tax_paid: "18000", filing_status: "paid" as FilingStatus },
    { employee: "1", fiscal_year: "2026", tax_type: "social_security" as TaxType, taxable_income: "264000", tax_amount: "13200", tax_paid: "6600", filing_status: "filed" as FilingStatus },
    { employee: "1", fiscal_year: "2025", tax_type: "municipal" as TaxType, taxable_income: "180000", tax_amount: "3600", tax_paid: "0", filing_status: "pending" as FilingStatus },
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
        <span class="text-indigo-600">Tax Records</span>
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Tax Records</h1>
      <p class="mt-1 max-w-2xl text-sm text-neutral-500">Track employee tax filings and payments.</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Record
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search tax records..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterTaxType} onchange={(e) => { filterTaxType = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      {#each Object.entries(taxTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterFilingStatus} onchange={(e) => { filterFilingStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(filingStatusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterTaxType || filterFilingStatus ? "No tax records match your filters" : "No tax records yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Fiscal Year</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Tax Type</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Tax Amount</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Tax Paid</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Balance</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 tabular-nums">{item.fiscal_year}</td>
              <td class="px-5 py-3.5 text-neutral-600">{taxTypeLabels[item.tax_type]}</td>
              <td class="px-5 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{currency.config.code} {item.tax_amount}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right tabular-nums">{currency.config.code} {item.tax_paid}</td>
              <td class="px-5 py-3.5 text-right tabular-nums {Number(item.balance) > 0 ? 'text-neutral-900 font-semibold' : 'text-neutral-500'}">{currency.config.code} {item.balance}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {filingStatusBadge[item.filing_status]}">{filingStatusLabels[item.filing_status]}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Tax Record" : "New Tax Record"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="tx-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="tx-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tx-year" class="block text-sm font-medium text-neutral-700 mb-1">Fiscal Year <span class="text-red-500">*</span></label>
            <input id="tx-year" type="text" bind:value={form.fiscal_year} placeholder="2026" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('fiscal_year') ? 'border-red-400' : ''}" />
            {#if fieldError("fiscal_year")}<p class="text-xs text-red-500 mt-1">{fieldError("fiscal_year")}</p>{/if}
          </div>
          <div>
            <label for="tx-type" class="block text-sm font-medium text-neutral-700 mb-1">Tax Type</label>
            <select id="tx-type" bind:value={form.tax_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(taxTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tx-income" class="block text-sm font-medium text-neutral-700 mb-1">Taxable Income</label>
            <input id="tx-income" type="number" step="0.01" bind:value={form.taxable_income} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums {fieldError('taxable_income') ? 'border-red-400' : ''}" />
            {#if fieldError("taxable_income")}<p class="text-xs text-red-500 mt-1">{fieldError("taxable_income")}</p>{/if}
          </div>
          <div>
            <label for="tx-amount" class="block text-sm font-medium text-neutral-700 mb-1">Tax Amount <span class="text-red-500">*</span></label>
            <input id="tx-amount" type="number" step="0.01" bind:value={form.tax_amount} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums {fieldError('tax_amount') ? 'border-red-400' : ''}" />
            {#if fieldError("tax_amount")}<p class="text-xs text-red-500 mt-1">{fieldError("tax_amount")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tx-paid" class="block text-sm font-medium text-neutral-700 mb-1">Tax Paid</label>
            <input id="tx-paid" type="number" step="0.01" bind:value={form.tax_paid} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums {fieldError('tax_paid') ? 'border-red-400' : ''}" />
            {#if fieldError("tax_paid")}<p class="text-xs text-red-500 mt-1">{fieldError("tax_paid")}</p>{/if}
          </div>
          <div>
            <label for="tx-status" class="block text-sm font-medium text-neutral-700 mb-1">Filing Status</label>
            <select id="tx-status" bind:value={form.filing_status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(filingStatusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
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

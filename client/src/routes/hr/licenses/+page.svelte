<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { ProfessionalLicenseListItem, LicenseStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<ProfessionalLicenseListItem[]>([]);
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
  let form = $state({ employee: "", license_type: "", license_number: "", issuing_authority: "", jurisdiction: "", issue_date: "", expiry_date: "", status: "active" as LicenseStatus, is_mandatory: false, notes: "" });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<LicenseStatus, string> = { active: "Active", expired: "Expired", pending: "Pending Renewal", suspended: "Suspended" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<ProfessionalLicenseListItem>>("/hr/licenses/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() { form = { employee: "", license_type: "", license_number: "", issuing_authority: "", jurisdiction: "", issue_date: "", expiry_date: "", status: "active", is_mandatory: false, notes: "" }; fieldErrors = {}; editingId = null; }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: ProfessionalLicenseListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/licenses/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.license_type = d.license_type;
      form.license_number = d.license_number;
      form.issuing_authority = d.issuing_authority;
      form.jurisdiction = d.jurisdiction ?? "";
      form.issue_date = d.issue_date ?? "";
      form.expiry_date = d.expiry_date ?? "";
      form.status = d.status;
      form.is_mandatory = d.is_mandatory;
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { license_type: form.license_type, license_number: form.license_number, issuing_authority: form.issuing_authority, jurisdiction: form.jurisdiction, status: form.status, is_mandatory: form.is_mandatory, notes: form.notes };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.issue_date) payload.issue_date = form.issue_date;
      if (form.expiry_date) payload.expiry_date = form.expiry_date;
      if (isEditing) { await api.patch(`/hr/licenses/${editingId}/`, payload); toast.success("License updated"); }
      else { await api.post("/hr/licenses/", payload); toast.success("License created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Professional Licenses</h1>
      <p class="mt-1 text-sm text-neutral-500">Regulatory and professional licences held by employees</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add License
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search licenses..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No licenses match your filters" : "No professional licenses recorded yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">License Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">License #</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Authority</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Expires</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Mandatory</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.license_type}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-500 text-xs font-mono">{item.license_number}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.issuing_authority}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.expiry_date ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-center">{#if item.is_mandatory}<span class="inline-block w-2 h-2 rounded-full bg-neutral-900"></span>{:else}<span class="inline-block w-2 h-2 rounded-full bg-neutral-200"></span>{/if}</td>
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
        <span>{totalCount} license{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit License" : "New License"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="lic-type" class="block text-sm font-medium text-neutral-700 mb-1">License Type <span class="text-red-500">*</span></label>
          <input id="lic-type" type="text" bind:value={form.license_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('license_type') ? 'border-red-400' : ''}" placeholder="e.g. Civil Engineering License" />
          {#if fieldError("license_type")}<p class="text-xs text-red-500 mt-1">{fieldError("license_type")}</p>{/if}
        </div>
        {#if !isEditing}
          <div>
            <label for="lic-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="lic-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div>
          <label for="lic-num" class="block text-sm font-medium text-neutral-700 mb-1">License Number <span class="text-red-500">*</span></label>
          <input id="lic-num" type="text" bind:value={form.license_number} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('license_number') ? 'border-red-400' : ''}" />
          {#if fieldError("license_number")}<p class="text-xs text-red-500 mt-1">{fieldError("license_number")}</p>{/if}
        </div>
        <div>
          <label for="lic-auth" class="block text-sm font-medium text-neutral-700 mb-1">Issuing Authority <span class="text-red-500">*</span></label>
          <input id="lic-auth" type="text" bind:value={form.issuing_authority} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('issuing_authority') ? 'border-red-400' : ''}" />
          {#if fieldError("issuing_authority")}<p class="text-xs text-red-500 mt-1">{fieldError("issuing_authority")}</p>{/if}
        </div>
        <div>
          <label for="lic-jur" class="block text-sm font-medium text-neutral-700 mb-1">Jurisdiction</label>
          <input id="lic-jur" type="text" bind:value={form.jurisdiction} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. UAE, Dubai Municipality" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="lic-issue" class="block text-sm font-medium text-neutral-700 mb-1">Issue Date <span class="text-red-500">*</span></label>
            <DateInput id="lic-issue" bind:value={form.issue_date} />
            {#if fieldError("issue_date")}<p class="text-xs text-red-500 mt-1">{fieldError("issue_date")}</p>{/if}
          </div>
          <div>
            <label for="lic-exp" class="block text-sm font-medium text-neutral-700 mb-1">Expiry Date</label>
            <DateInput id="lic-exp" bind:value={form.expiry_date} />
          </div>
        </div>
        <div>
          <label for="lic-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
          <select id="lic-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
        <label class="flex items-center gap-2 text-sm text-neutral-700">
          <input type="checkbox" bind:checked={form.is_mandatory} class="rounded border-neutral-300" />
          Mandatory for role
        </label>
        <div>
          <label for="lic-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="lic-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { CertificationExpiryAlertListItem, ExpiryAlertStatus, ExpiryAlertType, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<CertificationExpiryAlertListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");
  let filterType = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    alert_type: "certification" as ExpiryAlertType,
    reference_name: "",
    reference_id: "",
    expiry_date: "",
    alert_date: "",
    days_before_expiry: "30",
    status: "pending" as ExpiryAlertStatus,
    renewal_date: "",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<ExpiryAlertStatus, string> = { pending: "Pending", sent: "Sent", acknowledged: "Acknowledged", renewed: "Renewed", expired: "Expired" };
  const typeLabels: Record<ExpiryAlertType, string> = { certification: "Certification", license: "Professional License", training: "Training Completion" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      if (filterType) params.alert_type = filterType;
      const res = await api.get<PaginatedResponse<CertificationExpiryAlertListItem>>("/hr/certification-expiry-alerts/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", alert_type: "certification", reference_name: "", reference_id: "", expiry_date: "", alert_date: "", days_before_expiry: "30", status: "pending", renewal_date: "", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: CertificationExpiryAlertListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/certification-expiry-alerts/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.alert_type = d.alert_type;
      form.reference_name = d.reference_name ?? "";
      form.reference_id = d.reference_id != null ? String(d.reference_id) : "";
      form.expiry_date = d.expiry_date ?? "";
      form.alert_date = d.alert_date ?? "";
      form.days_before_expiry = String(d.days_before_expiry ?? 30);
      form.status = d.status;
      form.renewal_date = d.renewal_date ?? "";
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { alert_type: form.alert_type, reference_name: form.reference_name, status: form.status, days_before_expiry: Number(form.days_before_expiry), notes: form.notes };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.reference_id) payload.reference_id = Number(form.reference_id);
      if (form.expiry_date) payload.expiry_date = form.expiry_date;
      if (form.alert_date) payload.alert_date = form.alert_date;
      if (form.renewal_date) payload.renewal_date = form.renewal_date;
      if (isEditing) { await api.patch(`/hr/certification-expiry-alerts/${editingId}/`, payload); toast.success("Alert updated"); }
      else { await api.post("/hr/certification-expiry-alerts/", payload); toast.success("Alert created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Certification Expiry Alerts</h1>
      <p class="mt-1 text-sm text-neutral-500">Track expiring certifications, licenses, and training</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Alert
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search alerts..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterType} onchange={(e) => { filterType = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      {#each Object.entries(typeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus || filterType ? "No alerts match your filters" : "No expiry alerts configured yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Reference</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Expires</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Alert Date</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Renewed</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.reference_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{typeLabels[item.alert_type]}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.expiry_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.alert_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.renewal_date ?? "\u2014"}</td>
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
        <span>{totalCount} alert{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Alert" : "New Expiry Alert"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="ea-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="ea-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div>
          <label for="ea-type" class="block text-sm font-medium text-neutral-700 mb-1">Alert Type</label>
          <select id="ea-type" bind:value={form.alert_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(typeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
        <div>
          <label for="ea-ref" class="block text-sm font-medium text-neutral-700 mb-1">Reference Name <span class="text-red-500">*</span></label>
          <input id="ea-ref" type="text" bind:value={form.reference_name} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('reference_name') ? 'border-red-400' : ''}" />
          {#if fieldError("reference_name")}<p class="text-xs text-red-500 mt-1">{fieldError("reference_name")}</p>{/if}
        </div>
        <div>
          <label for="ea-refid" class="block text-sm font-medium text-neutral-700 mb-1">Reference ID</label>
          <input id="ea-refid" type="number" bind:value={form.reference_id} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ea-expiry" class="block text-sm font-medium text-neutral-700 mb-1">Expiry Date <span class="text-red-500">*</span></label>
            <DateInput id="ea-expiry" bind:value={form.expiry_date} />
            {#if fieldError("expiry_date")}<p class="text-xs text-red-500 mt-1">{fieldError("expiry_date")}</p>{/if}
          </div>
          <div>
            <label for="ea-alert" class="block text-sm font-medium text-neutral-700 mb-1">Alert Date <span class="text-red-500">*</span></label>
            <DateInput id="ea-alert" bind:value={form.alert_date} />
            {#if fieldError("alert_date")}<p class="text-xs text-red-500 mt-1">{fieldError("alert_date")}</p>{/if}
          </div>
        </div>
        <div>
          <label for="ea-days" class="block text-sm font-medium text-neutral-700 mb-1">Days Before Expiry</label>
          <input id="ea-days" type="number" bind:value={form.days_before_expiry} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="ea-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
          <select id="ea-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
        <div>
          <label for="ea-renewal" class="block text-sm font-medium text-neutral-700 mb-1">Renewal Date</label>
          <DateInput id="ea-renewal" bind:value={form.renewal_date} />
        </div>
        <div>
          <label for="ea-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="ea-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { PayslipListItem, PayslipStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<PayslipListItem[]>([]);
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
  let deletingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    payroll_run: "",
    period_start: "",
    period_end: "",
    basic_salary: "",
    total_allowances: "",
    total_deductions: "",
    gross_salary: "",
    net_salary: "",
    status: "draft" as PayslipStatus,
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<PayslipStatus, string> = { draft: "Draft", generated: "Generated", sent: "Sent", acknowledged: "Acknowledged" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<PayslipListItem>>("/hr/payslips/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", payroll_run: "", period_start: "", period_end: "", basic_salary: "", total_allowances: "", total_deductions: "", gross_salary: "", net_salary: "", status: "draft" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: PayslipListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/payslips/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.payroll_run = d.payroll_run != null ? String(d.payroll_run) : "";
      form.period_start = d.period_start ?? "";
      form.period_end = d.period_end ?? "";
      form.basic_salary = d.basic_salary ?? "";
      form.total_allowances = d.total_allowances ?? "";
      form.total_deductions = d.total_deductions ?? "";
      form.gross_salary = d.gross_salary ?? "";
      form.net_salary = d.net_salary ?? "";
      form.status = d.status;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { status: form.status };
      if (form.employee && !isEditing) payload.employee = Number(form.employee);
      if (form.payroll_run) payload.payroll_run = Number(form.payroll_run);
      if (form.period_start) payload.period_start = form.period_start;
      if (form.period_end) payload.period_end = form.period_end;
      if (form.basic_salary) payload.basic_salary = form.basic_salary;
      if (form.total_allowances) payload.total_allowances = form.total_allowances;
      if (form.total_deductions) payload.total_deductions = form.total_deductions;
      if (form.gross_salary) payload.gross_salary = form.gross_salary;
      if (form.net_salary) payload.net_salary = form.net_salary;
      payload.currency = currency.config.code;
      if (isEditing) { await api.patch(`/hr/payslips/${editingId}/`, payload); toast.success("Payslip updated"); }
      else { await api.post("/hr/payslips/", payload); toast.success("Payslip created"); }
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

  async function handleDelete(item: PayslipListItem) {
    if (!confirm(`Delete payslip for ${item.employee_name} (${item.period_start} to ${item.period_end})?`)) return;
    deletingId = item.id;
    try {
      await api.delete(`/hr/payslips/${item.id}/`);
      toast.success("Payslip deleted");
      if (items.length === 1 && currentPage > 1) currentPage -= 1;
      await fetchItems();
    } catch {
      toast.error("Delete failed", "Could not delete payslip.");
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
    { employee: "1", payroll_run: "", period_start: "2026-03-01", period_end: "2026-03-31", basic_salary: "15000", total_allowances: "7500", total_deductions: "1950", gross_salary: "22500", net_salary: "20550", status: "draft" as PayslipStatus },
    { employee: "1", payroll_run: "", period_start: "2026-02-01", period_end: "2026-02-28", basic_salary: "22000", total_allowances: "9000", total_deductions: "3100", gross_salary: "31000", net_salary: "27900", status: "generated" as PayslipStatus },
    { employee: "1", payroll_run: "", period_start: "2026-01-01", period_end: "2026-01-31", basic_salary: "8500", total_allowances: "3500", total_deductions: "800", gross_salary: "12000", net_salary: "11200", status: "sent" as PayslipStatus },
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
        <span class="text-indigo-600">Payslips</span>
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payslips</h1>
      <p class="mt-1 max-w-2xl text-sm text-neutral-500">Employee pay statements.</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Generate Payslip
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search payslips..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No payslips match your filters" : "No payslips yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Period</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Gross</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Net</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Payroll Run</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.period_start} – {item.period_end}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right tabular-nums">{currency.config.code} {item.gross_salary}</td>
              <td class="px-5 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{currency.config.code} {item.net_salary}</td>
              <td class="px-5 py-3.5 text-neutral-500">{item.payroll_run_name ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-center">
                <StatusBadge status={item.status} />
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
        <span>{totalCount} payslip{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Payslip" : "Generate Payslip"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="ps-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="ps-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div>
          <label for="ps-run" class="block text-sm font-medium text-neutral-700 mb-1">Payroll Run ID</label>
          <input id="ps-run" type="number" bind:value={form.payroll_run} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Optional" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ps-start" class="block text-sm font-medium text-neutral-700 mb-1">Period Start <span class="text-red-500">*</span></label>
            <DateInput id="ps-start" bind:value={form.period_start} />
            {#if fieldError("period_start")}<p class="text-xs text-red-500 mt-1">{fieldError("period_start")}</p>{/if}
          </div>
          <div>
            <label for="ps-end" class="block text-sm font-medium text-neutral-700 mb-1">Period End <span class="text-red-500">*</span></label>
            <DateInput id="ps-end" bind:value={form.period_end} />
            {#if fieldError("period_end")}<p class="text-xs text-red-500 mt-1">{fieldError("period_end")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ps-basic" class="block text-sm font-medium text-neutral-700 mb-1">Basic Salary</label>
            <input id="ps-basic" type="number" step="0.01" bind:value={form.basic_salary} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="ps-allow" class="block text-sm font-medium text-neutral-700 mb-1">Total Allowances</label>
            <input id="ps-allow" type="number" step="0.01" bind:value={form.total_allowances} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="ps-ded" class="block text-sm font-medium text-neutral-700 mb-1">Deductions</label>
            <input id="ps-ded" type="number" step="0.01" bind:value={form.total_deductions} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="ps-gross" class="block text-sm font-medium text-neutral-700 mb-1">Gross</label>
            <input id="ps-gross" type="number" step="0.01" bind:value={form.gross_salary} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="ps-net" class="block text-sm font-medium text-neutral-700 mb-1">Net</label>
            <input id="ps-net" type="number" step="0.01" bind:value={form.net_salary} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div>
          <label for="ps-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
          <select id="ps-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button type="button" onclick={devFill} class="px-4 py-2 text-sm font-semibold text-white bg-orange-500 rounded-lg hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : isEditing ? "Update" : "Generate"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .animate-slide-in-right { animation: slideInRight 0.25s ease-out both; }
</style>

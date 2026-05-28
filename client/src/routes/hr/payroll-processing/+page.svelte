<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { PayrollRunListItem, PayrollRunStatus, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<PayrollRunListItem[]>([]);
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
    name: "",
    period_start: "",
    period_end: "",
    run_date: "",
    status: "draft" as PayrollRunStatus,
    total_gross: "",
    total_deductions: "",
    total_net: "",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<PayrollRunStatus, string> = { draft: "Draft", processing: "Processing", completed: "Completed", cancelled: "Cancelled" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<PayrollRunListItem>>("/hr/payroll-runs/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { name: "", period_start: "", period_end: "", run_date: "", status: "draft", total_gross: "", total_deductions: "", total_net: "", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: PayrollRunListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/payroll-runs/${item.id}/`);
      form.name = d.name ?? "";
      form.period_start = d.period_start ?? "";
      form.period_end = d.period_end ?? "";
      form.run_date = d.run_date ?? "";
      form.status = d.status;
      form.total_gross = d.total_gross ?? "";
      form.total_deductions = d.total_deductions ?? "";
      form.total_net = d.total_net ?? "";
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { name: form.name, status: form.status, notes: form.notes };
      if (form.period_start) payload.period_start = form.period_start;
      if (form.period_end) payload.period_end = form.period_end;
      if (form.run_date) payload.run_date = form.run_date;
      if (form.total_gross) payload.total_gross = form.total_gross;
      if (form.total_deductions) payload.total_deductions = form.total_deductions;
      if (form.total_net) payload.total_net = form.total_net;
      payload.currency = currency.config.code;
      if (isEditing) { await api.patch(`/hr/payroll-runs/${editingId}/`, payload); toast.success("Payroll run updated"); }
      else { await api.post("/hr/payroll-runs/", payload); toast.success("Payroll run created"); }
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

  async function handleDelete(item: PayrollRunListItem) {
    if (!confirm(`Delete payroll run "${item.name}"?`)) return;
    deletingId = item.id;
    try {
      await api.delete(`/hr/payroll-runs/${item.id}/`);
      toast.success("Payroll run deleted");
      if (items.length === 1 && currentPage > 1) currentPage -= 1;
      await fetchItems();
    } catch {
      toast.error("Delete failed", "Could not delete payroll run.");
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
    { name: "March 2026 — Monthly Payroll", period_start: "2026-03-01", period_end: "2026-03-31", run_date: "2026-03-28", status: "draft" as PayrollRunStatus, total_gross: "485000", total_deductions: "73000", total_net: "412000", notes: "Includes new hires from Marina Heights Phase 3" },
    { name: "February 2026 — Monthly Payroll", period_start: "2026-02-01", period_end: "2026-02-28", run_date: "2026-02-26", status: "completed" as PayrollRunStatus, total_gross: "478000", total_deductions: "72000", total_net: "406000", notes: "All payments processed and confirmed" },
    { name: "Q1 2026 Bonus Run", period_start: "2026-01-01", period_end: "2026-03-31", run_date: "2026-04-05", status: "draft" as PayrollRunStatus, total_gross: "125000", total_deductions: "19000", total_net: "106000", notes: "Quarterly performance bonuses for site teams" },
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
        <span class="text-indigo-600">Payroll Processing</span>
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payroll Runs</h1>
      <p class="mt-1 max-w-2xl text-sm text-neutral-500">Run and manage payroll cycles.</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      New Payroll Run
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search payroll runs..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No runs match your filters" : "No payroll runs yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Name</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Period</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Run Date</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Total Net</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Processed By</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.period_start} – {item.period_end}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.run_date ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{currency.config.code} {item.total_net}</td>
              <td class="px-5 py-3.5 text-neutral-500">{item.processed_by_name ?? "\u2014"}</td>
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
        <span>{totalCount} run{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Payroll Run" : "New Payroll Run"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="pr-name" class="block text-sm font-medium text-neutral-700 mb-1">Name <span class="text-red-500">*</span></label>
          <input id="pr-name" type="text" bind:value={form.name} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('name') ? 'border-red-400' : ''}" />
          {#if fieldError("name")}<p class="text-xs text-red-500 mt-1">{fieldError("name")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pr-start" class="block text-sm font-medium text-neutral-700 mb-1">Period Start <span class="text-red-500">*</span></label>
            <DateInput id="pr-start" bind:value={form.period_start} />
            {#if fieldError("period_start")}<p class="text-xs text-red-500 mt-1">{fieldError("period_start")}</p>{/if}
          </div>
          <div>
            <label for="pr-end" class="block text-sm font-medium text-neutral-700 mb-1">Period End <span class="text-red-500">*</span></label>
            <DateInput id="pr-end" bind:value={form.period_end} />
            {#if fieldError("period_end")}<p class="text-xs text-red-500 mt-1">{fieldError("period_end")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="pr-rundate" class="block text-sm font-medium text-neutral-700 mb-1">Run Date</label>
            <DateInput id="pr-rundate" bind:value={form.run_date} />
          </div>
          <div>
            <label for="pr-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="pr-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="pr-gross" class="block text-sm font-medium text-neutral-700 mb-1">Gross</label>
            <input id="pr-gross" type="number" step="0.01" bind:value={form.total_gross} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="pr-ded" class="block text-sm font-medium text-neutral-700 mb-1">Deductions</label>
            <input id="pr-ded" type="number" step="0.01" bind:value={form.total_deductions} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="pr-net" class="block text-sm font-medium text-neutral-700 mb-1">Net</label>
            <input id="pr-net" type="number" step="0.01" bind:value={form.total_net} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div>
          <label for="pr-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="pr-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

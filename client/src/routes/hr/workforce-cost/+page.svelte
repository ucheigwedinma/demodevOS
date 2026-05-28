<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { WorkforceCostReportListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<WorkforceCostReportListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    period_start: "",
    period_end: "",
    department: "",
    total_salary: "0",
    total_allowances: "0",
    total_bonuses: "0",
    total_benefits: "0",
    total_overtime: "0",
    headcount: "0",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      const res = await api.get<PaginatedResponse<WorkforceCostReportListItem>>("/hr/workforce-cost-reports/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { period_start: "", period_end: "", department: "", total_salary: "0", total_allowances: "0", total_bonuses: "0", total_benefits: "0", total_overtime: "0", headcount: "0", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: WorkforceCostReportListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/workforce-cost-reports/${item.id}/`);
      form.period_start = d.period_start ?? "";
      form.period_end = d.period_end ?? "";
      form.department = d.department ?? "";
      form.total_salary = d.total_salary ?? "0";
      form.total_allowances = d.total_allowances ?? "0";
      form.total_bonuses = d.total_bonuses ?? "0";
      form.total_benefits = d.total_benefits ?? "0";
      form.total_overtime = d.total_overtime ?? "0";
      form.headcount = String(d.headcount ?? 0);
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        period_start: form.period_start, period_end: form.period_end,
        total_salary: form.total_salary, total_allowances: form.total_allowances,
        total_bonuses: form.total_bonuses, total_benefits: form.total_benefits,
        total_overtime: form.total_overtime, headcount: Number(form.headcount),
      };
      if (form.department) payload.department = form.department;
      if (form.notes) payload.notes = form.notes;
      if (isEditing) { await api.patch(`/hr/workforce-cost-reports/${editingId}/`, payload); toast.success("Report updated"); }
      else { await api.post("/hr/workforce-cost-reports/", payload); toast.success("Report created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Workforce Cost</h1>
      <p class="mt-1 text-sm text-neutral-500">Analyze total workforce cost breakdowns by period and department</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Report
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search by department..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery ? "No reports match your search" : "No cost reports yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Period</th>
            <th class="text-left px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Salary</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Allowances</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Bonuses</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Benefits</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Total Cost</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">HC</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Cost/Emp</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-4 py-3.5 text-neutral-600 text-xs">{item.period_start} – {item.period_end}</td>
              <td class="px-4 py-3.5 font-medium text-neutral-900">{item.department || "\u2014"}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{currency.config.code} {item.total_salary}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{currency.config.code} {item.total_allowances}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{currency.config.code} {item.total_bonuses}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{currency.config.code} {item.total_benefits}</td>
              <td class="px-4 py-3.5 text-neutral-900 text-right tabular-nums font-semibold">{currency.config.code} {item.total_cost}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.headcount}</td>
              <td class="px-4 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{currency.config.code} {item.cost_per_employee}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} report{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Report" : "New Cost Report"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="wc-ps" class="block text-sm font-medium text-neutral-700 mb-1">Period Start <span class="text-red-500">*</span></label>
            <DateInput id="wc-ps" bind:value={form.period_start} />
            {#if fieldError("period_start")}<p class="text-xs text-red-500 mt-1">{fieldError("period_start")}</p>{/if}
          </div>
          <div>
            <label for="wc-pe" class="block text-sm font-medium text-neutral-700 mb-1">Period End <span class="text-red-500">*</span></label>
            <DateInput id="wc-pe" bind:value={form.period_end} />
            {#if fieldError("period_end")}<p class="text-xs text-red-500 mt-1">{fieldError("period_end")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="wc-dept" class="block text-sm font-medium text-neutral-700 mb-1">Department</label>
            <input id="wc-dept" type="text" bind:value={form.department} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="wc-hc" class="block text-sm font-medium text-neutral-700 mb-1">Headcount</label>
            <input id="wc-hc" type="number" bind:value={form.headcount} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="wc-sal" class="block text-sm font-medium text-neutral-700 mb-1">Total Salary</label>
            <input id="wc-sal" type="number" step="0.01" bind:value={form.total_salary} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="wc-all" class="block text-sm font-medium text-neutral-700 mb-1">Total Allowances</label>
            <input id="wc-all" type="number" step="0.01" bind:value={form.total_allowances} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="wc-bon" class="block text-sm font-medium text-neutral-700 mb-1">Bonuses</label>
            <input id="wc-bon" type="number" step="0.01" bind:value={form.total_bonuses} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="wc-ben" class="block text-sm font-medium text-neutral-700 mb-1">Benefits</label>
            <input id="wc-ben" type="number" step="0.01" bind:value={form.total_benefits} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="wc-ot" class="block text-sm font-medium text-neutral-700 mb-1">Overtime</label>
            <input id="wc-ot" type="number" step="0.01" bind:value={form.total_overtime} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div>
          <label for="wc-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="wc-notes" bind:value={form.notes} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

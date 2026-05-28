<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { HiringFunnelMetricListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<HiringFunnelMetricListItem[]>([]);
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
    requisitions_opened: "0",
    applications_received: "0",
    candidates_screened: "0",
    candidates_interviewed: "0",
    offers_made: "0",
    offers_accepted: "0",
    avg_time_to_hire_days: "0",
    avg_cost_per_hire: "0",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      const res = await api.get<PaginatedResponse<HiringFunnelMetricListItem>>("/hr/hiring-funnel-metrics/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { period_start: "", period_end: "", department: "", requisitions_opened: "0", applications_received: "0", candidates_screened: "0", candidates_interviewed: "0", offers_made: "0", offers_accepted: "0", avg_time_to_hire_days: "0", avg_cost_per_hire: "0", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: HiringFunnelMetricListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/hiring-funnel-metrics/${item.id}/`);
      form.period_start = d.period_start ?? "";
      form.period_end = d.period_end ?? "";
      form.department = d.department ?? "";
      form.requisitions_opened = String(d.requisitions_opened ?? 0);
      form.applications_received = String(d.applications_received ?? 0);
      form.candidates_screened = String(d.candidates_screened ?? 0);
      form.candidates_interviewed = String(d.candidates_interviewed ?? 0);
      form.offers_made = String(d.offers_made ?? 0);
      form.offers_accepted = String(d.offers_accepted ?? 0);
      form.avg_time_to_hire_days = d.avg_time_to_hire_days ?? "0";
      form.avg_cost_per_hire = d.avg_cost_per_hire ?? "0";
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        period_start: form.period_start, period_end: form.period_end,
        requisitions_opened: Number(form.requisitions_opened),
        applications_received: Number(form.applications_received),
        candidates_screened: Number(form.candidates_screened),
        candidates_interviewed: Number(form.candidates_interviewed),
        offers_made: Number(form.offers_made),
        offers_accepted: Number(form.offers_accepted),
        avg_time_to_hire_days: form.avg_time_to_hire_days,
        avg_cost_per_hire: form.avg_cost_per_hire,
      };
      if (form.department) payload.department = form.department;
      if (form.notes) payload.notes = form.notes;
      if (isEditing) { await api.patch(`/hr/hiring-funnel-metrics/${editingId}/`, payload); toast.success("Metric updated"); }
      else { await api.post("/hr/hiring-funnel-metrics/", payload); toast.success("Metric created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Hiring Funnel Metrics</h1>
      <p class="mt-1 text-sm text-neutral-500">Measure hiring pipeline efficiency and conversion rates</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Metric
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
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery ? "No metrics match your search" : "No hiring funnel metrics yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Period</th>
            <th class="text-left px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Reqs</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Apps</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Screened</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Interviewed</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Offers</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Accepted</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Accept %</th>
            <th class="text-right px-4 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Avg Days</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-4 py-3.5 text-neutral-600 text-xs">{item.period_start} – {item.period_end}</td>
              <td class="px-4 py-3.5 font-medium text-neutral-900">{item.department || "\u2014"}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.requisitions_opened}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.applications_received}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.candidates_screened}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.candidates_interviewed}</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.offers_made}</td>
              <td class="px-4 py-3.5 text-neutral-900 text-right tabular-nums font-medium">{item.offers_accepted}</td>
              <td class="px-4 py-3.5 text-right tabular-nums font-medium text-neutral-900">{item.offer_acceptance_rate}%</td>
              <td class="px-4 py-3.5 text-neutral-600 text-right tabular-nums">{item.avg_time_to_hire_days}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} metric{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Metric" : "New Hiring Funnel Metric"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hf-ps" class="block text-sm font-medium text-neutral-700 mb-1">Period Start <span class="text-red-500">*</span></label>
            <DateInput id="hf-ps" bind:value={form.period_start} />
            {#if fieldError("period_start")}<p class="text-xs text-red-500 mt-1">{fieldError("period_start")}</p>{/if}
          </div>
          <div>
            <label for="hf-pe" class="block text-sm font-medium text-neutral-700 mb-1">Period End <span class="text-red-500">*</span></label>
            <DateInput id="hf-pe" bind:value={form.period_end} />
            {#if fieldError("period_end")}<p class="text-xs text-red-500 mt-1">{fieldError("period_end")}</p>{/if}
          </div>
        </div>
        <div>
          <label for="hf-dept" class="block text-sm font-medium text-neutral-700 mb-1">Department</label>
          <input id="hf-dept" type="text" bind:value={form.department} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hf-reqs" class="block text-sm font-medium text-neutral-700 mb-1">Requisitions Opened</label>
            <input id="hf-reqs" type="number" bind:value={form.requisitions_opened} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hf-apps" class="block text-sm font-medium text-neutral-700 mb-1">Applications Received</label>
            <input id="hf-apps" type="number" bind:value={form.applications_received} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hf-scr" class="block text-sm font-medium text-neutral-700 mb-1">Candidates Screened</label>
            <input id="hf-scr" type="number" bind:value={form.candidates_screened} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hf-int" class="block text-sm font-medium text-neutral-700 mb-1">Candidates Interviewed</label>
            <input id="hf-int" type="number" bind:value={form.candidates_interviewed} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hf-off" class="block text-sm font-medium text-neutral-700 mb-1">Offers Made</label>
            <input id="hf-off" type="number" bind:value={form.offers_made} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hf-acc" class="block text-sm font-medium text-neutral-700 mb-1">Offers Accepted</label>
            <input id="hf-acc" type="number" bind:value={form.offers_accepted} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="hf-days" class="block text-sm font-medium text-neutral-700 mb-1">Avg Time to Hire (days)</label>
            <input id="hf-days" type="number" step="0.1" bind:value={form.avg_time_to_hire_days} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
          <div>
            <label for="hf-cost" class="block text-sm font-medium text-neutral-700 mb-1">Avg Cost per Hire</label>
            <input id="hf-cost" type="number" step="0.01" bind:value={form.avg_cost_per_hire} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums" />
          </div>
        </div>
        <div>
          <label for="hf-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="hf-notes" bind:value={form.notes} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

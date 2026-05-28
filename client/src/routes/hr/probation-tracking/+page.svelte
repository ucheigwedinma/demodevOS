<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { ProbationRecordListItem, ProbationStatus, ProbationRecommendation, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<ProbationRecordListItem[]>([]);
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
  let form = $state({ employee: "", start_date: "", end_date: "", extended_end_date: "", status: "in_progress" as ProbationStatus, review_date: "", next_review_date: "", reviewer: "", performance_rating: "", recommendation: "" as ProbationRecommendation | "", notes: "", outcome_notes: "" });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<ProbationStatus, string> = { in_progress: "In Progress", passed: "Passed", failed: "Failed", extended: "Extended" };
  const recommendationLabels: Record<string, string> = { confirm: "Confirm", extend: "Extend", terminate: "Terminate" };

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<ProbationRecordListItem>>("/hr/probation-records/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() { form = { employee: "", start_date: "", end_date: "", extended_end_date: "", status: "in_progress", review_date: "", next_review_date: "", reviewer: "", performance_rating: "", recommendation: "", notes: "", outcome_notes: "" }; fieldErrors = {}; editingId = null; }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: ProbationRecordListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/probation-records/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.start_date = d.start_date ?? "";
      form.end_date = d.end_date ?? "";
      form.extended_end_date = d.extended_end_date ?? "";
      form.status = d.status;
      form.review_date = d.review_date ?? "";
      form.next_review_date = d.next_review_date ?? "";
      form.reviewer = d.reviewer ? String(d.reviewer) : "";
      form.performance_rating = d.performance_rating ? String(d.performance_rating) : "";
      form.recommendation = d.recommendation || "";
      form.notes = d.notes;
      form.outcome_notes = d.outcome_notes;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { status: form.status, notes: form.notes, outcome_notes: form.outcome_notes };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.start_date) payload.start_date = form.start_date;
      if (form.end_date) payload.end_date = form.end_date;
      if (form.extended_end_date) payload.extended_end_date = form.extended_end_date;
      if (form.review_date) payload.review_date = form.review_date;
      if (form.next_review_date) payload.next_review_date = form.next_review_date;
      if (form.reviewer) payload.reviewer = Number(form.reviewer);
      if (form.performance_rating) payload.performance_rating = Number(form.performance_rating);
      if (form.recommendation) payload.recommendation = form.recommendation;
      if (isEditing) { await api.patch(`/hr/probation-records/${editingId}/`, payload); toast.success("Probation record updated"); }
      else { await api.post("/hr/probation-records/", payload); toast.success("Probation record created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Probation Tracking</h1>
      <p class="mt-1 text-sm text-neutral-500">Monitor probation periods and review outcomes</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Record
    </button>
  </div>

  <div class="flex items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search employees..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No records match your filters" : "No probation records yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Start</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">End</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Reviewer</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Rating</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Recommendation</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{formatDate(item.start_date)}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{formatDate(item.extended_end_date || item.end_date)}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.reviewer_name ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-center text-neutral-600 tabular-nums">{item.performance_rating ? `${item.performance_rating}/5` : "\u2014"}</td>
              <td class="px-5 py-3.5 text-center text-neutral-600">{item.recommendation ? recommendationLabels[item.recommendation] ?? item.recommendation : "\u2014"}</td>
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
        <span>{totalCount} record{totalCount !== 1 ? 's' : ''}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Probation Record" : "New Probation Record"}</h2>
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
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pr-start" class="block text-sm font-medium text-neutral-700 mb-1">Start Date <span class="text-red-500">*</span></label>
            <DateInput id="pr-start" bind:value={form.start_date} />
            {#if fieldError("start_date")}<p class="text-xs text-red-500 mt-1">{fieldError("start_date")}</p>{/if}
          </div>
          <div>
            <label for="pr-end" class="block text-sm font-medium text-neutral-700 mb-1">End Date <span class="text-red-500">*</span></label>
            <DateInput id="pr-end" bind:value={form.end_date} />
            {#if fieldError("end_date")}<p class="text-xs text-red-500 mt-1">{fieldError("end_date")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pr-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="pr-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="pr-ext" class="block text-sm font-medium text-neutral-700 mb-1">Extended End Date</label>
            <DateInput id="pr-ext" bind:value={form.extended_end_date} />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pr-review" class="block text-sm font-medium text-neutral-700 mb-1">Review Date</label>
            <DateInput id="pr-review" bind:value={form.review_date} />
          </div>
          <div>
            <label for="pr-next" class="block text-sm font-medium text-neutral-700 mb-1">Next Review</label>
            <DateInput id="pr-next" bind:value={form.next_review_date} />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="pr-rating" class="block text-sm font-medium text-neutral-700 mb-1">Performance Rating (1-5)</label>
            <input id="pr-rating" type="number" min="1" max="5" bind:value={form.performance_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="pr-rec" class="block text-sm font-medium text-neutral-700 mb-1">Recommendation</label>
            <select id="pr-rec" bind:value={form.recommendation} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">None</option>
              {#each Object.entries(recommendationLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div>
          <label for="pr-reviewer" class="block text-sm font-medium text-neutral-700 mb-1">Reviewer User ID</label>
          <input id="pr-reviewer" type="number" bind:value={form.reviewer} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="pr-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="pr-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="pr-outcome" class="block text-sm font-medium text-neutral-700 mb-1">Outcome Notes</label>
          <textarea id="pr-outcome" bind:value={form.outcome_notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

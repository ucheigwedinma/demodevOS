<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { ManagerEvaluationListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<ManagerEvaluationListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({ employee: "", review: "", evaluation_date: "", overall_rating: "", leadership_rating: "", communication_rating: "", technical_rating: "", teamwork_rating: "", strengths: "", areas_for_improvement: "", goals_for_next_period: "", comments: "" });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      const res = await api.get<PaginatedResponse<ManagerEvaluationListItem>>("/hr/manager-evaluations/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() { form = { employee: "", review: "", evaluation_date: "", overall_rating: "", leadership_rating: "", communication_rating: "", technical_rating: "", teamwork_rating: "", strengths: "", areas_for_improvement: "", goals_for_next_period: "", comments: "" }; fieldErrors = {}; editingId = null; }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: ManagerEvaluationListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/manager-evaluations/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.review = String(d.review ?? "");
      form.evaluation_date = d.evaluation_date;
      form.overall_rating = String(d.overall_rating);
      form.leadership_rating = String(d.leadership_rating ?? "");
      form.communication_rating = String(d.communication_rating ?? "");
      form.technical_rating = String(d.technical_rating ?? "");
      form.teamwork_rating = String(d.teamwork_rating ?? "");
      form.strengths = d.strengths ?? "";
      form.areas_for_improvement = d.areas_for_improvement ?? "";
      form.goals_for_next_period = d.goals_for_next_period ?? "";
      form.comments = d.comments ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { evaluation_date: form.evaluation_date, overall_rating: Number(form.overall_rating), strengths: form.strengths, areas_for_improvement: form.areas_for_improvement, goals_for_next_period: form.goals_for_next_period, comments: form.comments };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.review) payload.review = Number(form.review);
      if (form.leadership_rating) payload.leadership_rating = Number(form.leadership_rating);
      if (form.communication_rating) payload.communication_rating = Number(form.communication_rating);
      if (form.technical_rating) payload.technical_rating = Number(form.technical_rating);
      if (form.teamwork_rating) payload.teamwork_rating = Number(form.teamwork_rating);
      if (isEditing) { await api.patch(`/hr/manager-evaluations/${editingId}/`, payload); toast.success("Evaluation updated"); }
      else { await api.post("/hr/manager-evaluations/", payload); toast.success("Evaluation created"); }
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

  function ratingStars(r: number | null): string { return r ? "\u2605".repeat(r) + "\u2606".repeat(5 - r) : "\u2014"; }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(v: string) { searchQuery = v; clearTimeout(debounceTimer); debounceTimer = setTimeout(() => { currentPage = 1; fetchItems(); }, 300); }
  function goToPage(p: number) { if (p >= 1 && p <= totalPages) { currentPage = p; fetchItems(); } }
  function fieldError(f: string): string { return fieldErrors[f]?.[0] ?? ""; }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Manager Evaluations</h1>
      <p class="mt-1 text-sm text-neutral-500">Structured evaluations from managers for direct reports</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      New Evaluation
    </button>
  </div>

  <div class="flex items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search evaluations..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery ? "No evaluations match your search" : "No manager evaluations yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Evaluator</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Date</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Overall</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Leadership</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Technical</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Teamwork</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.evaluator_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.evaluation_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.overall_rating)}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.leadership_rating)}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.technical_rating)}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.teamwork_rating)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} evaluation{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Evaluation" : "New Evaluation"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="me-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="me-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div>
          <label for="me-date" class="block text-sm font-medium text-neutral-700 mb-1">Evaluation Date <span class="text-red-500">*</span></label>
          <DateInput id="me-date" bind:value={form.evaluation_date} />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="me-overall" class="block text-sm font-medium text-neutral-700 mb-1">Overall Rating (1–5) <span class="text-red-500">*</span></label>
            <input id="me-overall" type="number" min="1" max="5" bind:value={form.overall_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('overall_rating') ? 'border-red-400' : ''}" />
          </div>
          <div>
            <label for="me-lead" class="block text-sm font-medium text-neutral-700 mb-1">Leadership (1–5)</label>
            <input id="me-lead" type="number" min="1" max="5" bind:value={form.leadership_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="me-comm" class="block text-sm font-medium text-neutral-700 mb-1">Communication</label>
            <input id="me-comm" type="number" min="1" max="5" bind:value={form.communication_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="me-tech" class="block text-sm font-medium text-neutral-700 mb-1">Technical</label>
            <input id="me-tech" type="number" min="1" max="5" bind:value={form.technical_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="me-team" class="block text-sm font-medium text-neutral-700 mb-1">Teamwork</label>
            <input id="me-team" type="number" min="1" max="5" bind:value={form.teamwork_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="me-strengths" class="block text-sm font-medium text-neutral-700 mb-1">Strengths</label>
          <textarea id="me-strengths" bind:value={form.strengths} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="me-improve" class="block text-sm font-medium text-neutral-700 mb-1">Areas for Improvement</label>
          <textarea id="me-improve" bind:value={form.areas_for_improvement} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="me-goals" class="block text-sm font-medium text-neutral-700 mb-1">Goals for Next Period</label>
          <textarea id="me-goals" bind:value={form.goals_for_next_period} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="me-comments" class="block text-sm font-medium text-neutral-700 mb-1">Comments</label>
          <textarea id="me-comments" bind:value={form.comments} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

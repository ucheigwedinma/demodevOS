<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { PeerReviewListItem, PeerReviewStatus, PaginatedResponse } from "$lib/types";

  let items = $state<PeerReviewListItem[]>([]);
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
  let form = $state({ employee: "", review: "", overall_rating: "", collaboration_rating: "", communication_rating: "", strengths: "", areas_for_improvement: "", comments: "", is_anonymous: false });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<PeerReviewStatus, string> = { pending: "Pending", submitted: "Submitted", declined: "Declined" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      const res = await api.get<PaginatedResponse<PeerReviewListItem>>("/hr/peer-reviews/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() { form = { employee: "", review: "", overall_rating: "", collaboration_rating: "", communication_rating: "", strengths: "", areas_for_improvement: "", comments: "", is_anonymous: false }; fieldErrors = {}; editingId = null; }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: PeerReviewListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/peer-reviews/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.review = String(d.review ?? "");
      form.overall_rating = String(d.overall_rating ?? "");
      form.collaboration_rating = String(d.collaboration_rating ?? "");
      form.communication_rating = String(d.communication_rating ?? "");
      form.strengths = d.strengths ?? "";
      form.areas_for_improvement = d.areas_for_improvement ?? "";
      form.comments = d.comments ?? "";
      form.is_anonymous = d.is_anonymous;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { strengths: form.strengths, areas_for_improvement: form.areas_for_improvement, comments: form.comments, is_anonymous: form.is_anonymous };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.review) payload.review = Number(form.review);
      if (form.overall_rating) payload.overall_rating = Number(form.overall_rating);
      if (form.collaboration_rating) payload.collaboration_rating = Number(form.collaboration_rating);
      if (form.communication_rating) payload.communication_rating = Number(form.communication_rating);
      if (isEditing) { await api.patch(`/hr/peer-reviews/${editingId}/`, payload); toast.success("Peer review updated"); }
      else { await api.post("/hr/peer-reviews/", payload); toast.success("Peer review submitted"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Peer Reviews</h1>
      <p class="mt-1 text-sm text-neutral-500">Peer-to-peer feedback and evaluations</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      New Peer Review
    </button>
  </div>

  <div class="flex items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search peer reviews..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus ? "No peer reviews match your filters" : "No peer reviews yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Reviewer</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Overall</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Collaboration</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Communication</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.reviewer_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.overall_rating)}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.collaboration_rating)}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-sm tracking-wide">{ratingStars(item.communication_rating)}</td>
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
        <span>{totalCount} review{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Peer Review" : "New Peer Review"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="peer-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="peer-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="peer-overall" class="block text-sm font-medium text-neutral-700 mb-1">Overall (1–5)</label>
            <input id="peer-overall" type="number" min="1" max="5" bind:value={form.overall_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="peer-collab" class="block text-sm font-medium text-neutral-700 mb-1">Collaboration</label>
            <input id="peer-collab" type="number" min="1" max="5" bind:value={form.collaboration_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="peer-comm" class="block text-sm font-medium text-neutral-700 mb-1">Communication</label>
            <input id="peer-comm" type="number" min="1" max="5" bind:value={form.communication_rating} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="peer-strengths" class="block text-sm font-medium text-neutral-700 mb-1">Strengths</label>
          <textarea id="peer-strengths" bind:value={form.strengths} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="peer-improve" class="block text-sm font-medium text-neutral-700 mb-1">Areas for Improvement</label>
          <textarea id="peer-improve" bind:value={form.areas_for_improvement} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="peer-comments" class="block text-sm font-medium text-neutral-700 mb-1">Comments</label>
          <textarea id="peer-comments" bind:value={form.comments} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div class="flex items-center gap-2">
          <input id="peer-anon" type="checkbox" bind:checked={form.is_anonymous} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
          <label for="peer-anon" class="text-sm font-medium text-neutral-700">Submit anonymously</label>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : isEditing ? "Update" : "Submit"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }
  .animate-slide-in-right { animation: slideInRight 0.25s ease-out both; }
</style>

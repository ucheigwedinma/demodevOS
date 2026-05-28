<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { ExitInterviewListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<ExitInterviewListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterSatisfaction = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    exit_record: "",
    interview_date: "",
    overall_satisfaction: "3",
    reason_for_leaving: "",
    feedback: "",
    would_recommend: false,
    would_rejoin: false,
    key_concerns: "",
    suggestions: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const satisfactionLabels: Record<string, string> = { "1": "Very Dissatisfied", "2": "Dissatisfied", "3": "Neutral", "4": "Satisfied", "5": "Very Satisfied" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterSatisfaction) params.overall_satisfaction = filterSatisfaction;
      const res = await api.get<PaginatedResponse<ExitInterviewListItem>>("/hr/exit-interviews/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", exit_record: "", interview_date: "", overall_satisfaction: "3", reason_for_leaving: "", feedback: "", would_recommend: false, would_rejoin: false, key_concerns: "", suggestions: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: ExitInterviewListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/exit-interviews/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.exit_record = String(d.exit_record ?? "");
      form.interview_date = d.interview_date ?? "";
      form.overall_satisfaction = String(d.overall_satisfaction ?? "3");
      form.reason_for_leaving = d.reason_for_leaving ?? "";
      form.feedback = d.feedback ?? "";
      form.would_recommend = d.would_recommend ?? false;
      form.would_rejoin = d.would_rejoin ?? false;
      form.key_concerns = d.key_concerns ?? "";
      form.suggestions = d.suggestions ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        overall_satisfaction: Number(form.overall_satisfaction),
        reason_for_leaving: form.reason_for_leaving,
        would_recommend: form.would_recommend,
        would_rejoin: form.would_rejoin,
      };
      if (form.employee && !isEditing) payload.employee = Number(form.employee);
      if (form.exit_record) payload.exit_record = Number(form.exit_record);
      if (form.interview_date) payload.interview_date = form.interview_date;
      if (form.feedback) payload.feedback = form.feedback;
      if (form.key_concerns) payload.key_concerns = form.key_concerns;
      if (form.suggestions) payload.suggestions = form.suggestions;
      if (isEditing) { await api.patch(`/hr/exit-interviews/${editingId}/`, payload); toast.success("Interview updated"); }
      else { await api.post("/hr/exit-interviews/", payload); toast.success("Interview created"); }
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

  function satisfactionDots(n: number): string {
    return "\u25CF".repeat(n) + "\u25CB".repeat(5 - n);
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Exit Interviews</h1>
      <p class="mt-1 text-sm text-neutral-500">Record and review employee exit interview feedback</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Interview
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search exit interviews..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterSatisfaction} onchange={(e) => { filterSatisfaction = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Ratings</option>
      {#each Object.entries(satisfactionLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterSatisfaction ? "No interviews match your filters" : "No exit interviews yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Interview Date</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Satisfaction</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Recommend</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Rejoin</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Interviewer</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.interview_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 tracking-wider text-xs font-medium">{satisfactionDots(item.overall_satisfaction)} <span class="ml-1 text-neutral-400">{item.overall_satisfaction}/5</span></td>
              <td class="px-5 py-3.5 text-center text-neutral-600">{item.would_recommend ? "Yes" : "No"}</td>
              <td class="px-5 py-3.5 text-center text-neutral-600">{item.would_rejoin ? "Yes" : "No"}</td>
              <td class="px-5 py-3.5 text-neutral-500">{item.interviewer_name ?? "\u2014"}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} interview{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Exit Interview" : "New Exit Interview"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="ei-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="ei-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ei-date" class="block text-sm font-medium text-neutral-700 mb-1">Interview Date <span class="text-red-500">*</span></label>
            <DateInput id="ei-date" bind:value={form.interview_date} />
            {#if fieldError("interview_date")}<p class="text-xs text-red-500 mt-1">{fieldError("interview_date")}</p>{/if}
          </div>
          <div>
            <label for="ei-exit" class="block text-sm font-medium text-neutral-700 mb-1">Exit Record ID</label>
            <input id="ei-exit" type="number" bind:value={form.exit_record} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="ei-sat" class="block text-sm font-medium text-neutral-700 mb-1">Overall Satisfaction <span class="text-red-500">*</span></label>
          <select id="ei-sat" bind:value={form.overall_satisfaction} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(satisfactionLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
        <div>
          <label for="ei-reason" class="block text-sm font-medium text-neutral-700 mb-1">Reason for Leaving <span class="text-red-500">*</span></label>
          <textarea id="ei-reason" bind:value={form.reason_for_leaving} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none {fieldError('reason_for_leaving') ? 'border-red-400' : ''}"></textarea>
          {#if fieldError("reason_for_leaving")}<p class="text-xs text-red-500 mt-1">{fieldError("reason_for_leaving")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" bind:checked={form.would_recommend} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
            <span class="text-sm text-neutral-700">Would Recommend</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" bind:checked={form.would_rejoin} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
            <span class="text-sm text-neutral-700">Would Rejoin</span>
          </label>
        </div>
        <div>
          <label for="ei-fb" class="block text-sm font-medium text-neutral-700 mb-1">General Feedback</label>
          <textarea id="ei-fb" bind:value={form.feedback} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="ei-concerns" class="block text-sm font-medium text-neutral-700 mb-1">Key Concerns</label>
          <textarea id="ei-concerns" bind:value={form.key_concerns} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="ei-sug" class="block text-sm font-medium text-neutral-700 mb-1">Suggestions</label>
          <textarea id="ei-sug" bind:value={form.suggestions} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import EmployeeSelect from "$lib/components/EmployeeSelect.svelte";
  import type { TrainingCompletionListItem, TrainingResult, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let items = $state<TrainingCompletionListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterResult = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    employee: "",
    course: "",
    enrollment: "",
    completion_date: "",
    result: "pass" as TrainingResult,
    score: "",
    certificate_number: "",
    certificate_expiry: "",
    hours_completed: "",
    verified_by: "",
    notes: "",
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const resultLabels: Record<TrainingResult, string> = { pass: "Pass", fail: "Fail", distinction: "Distinction" };
  const resultBadge: Record<TrainingResult, string> = { pass: "bg-neutral-900 text-white", fail: "bg-neutral-400 text-white", distinction: "bg-neutral-200 text-neutral-700" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterResult) params.result = filterResult;
      const res = await api.get<PaginatedResponse<TrainingCompletionListItem>>("/hr/training-completions/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { employee: "", course: "", enrollment: "", completion_date: "", result: "pass", score: "", certificate_number: "", certificate_expiry: "", hours_completed: "", verified_by: "", notes: "" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: TrainingCompletionListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/training-completions/${item.id}/`);
      form.employee = String(d.employee ?? "");
      form.course = d.course != null ? String(d.course) : "";
      form.enrollment = d.enrollment != null ? String(d.enrollment) : "";
      form.completion_date = d.completion_date ?? "";
      form.result = d.result;
      form.score = d.score ?? "";
      form.certificate_number = d.certificate_number ?? "";
      form.certificate_expiry = d.certificate_expiry ?? "";
      form.hours_completed = d.hours_completed ?? "";
      form.verified_by = d.verified_by != null ? String(d.verified_by) : "";
      form.notes = d.notes ?? "";
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { result: form.result, certificate_number: form.certificate_number, notes: form.notes };
      if (form.employee) payload.employee = Number(form.employee);
      if (form.course) payload.course = Number(form.course);
      if (form.enrollment) payload.enrollment = Number(form.enrollment);
      if (form.completion_date) payload.completion_date = form.completion_date;
      if (form.score) payload.score = form.score;
      if (form.certificate_expiry) payload.certificate_expiry = form.certificate_expiry;
      if (form.hours_completed) payload.hours_completed = form.hours_completed;
      if (form.verified_by) payload.verified_by = Number(form.verified_by);
      if (isEditing) { await api.patch(`/hr/training-completions/${editingId}/`, payload); toast.success("Completion updated"); }
      else { await api.post("/hr/training-completions/", payload); toast.success("Completion recorded"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Training Completion</h1>
      <p class="mt-1 text-sm text-neutral-500">Completed training records and certificates</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Record Completion
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search completions..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterResult} onchange={(e) => { filterResult = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Results</option>
      {#each Object.entries(resultLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterResult ? "No completions match your filters" : "No training completions recorded yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Course</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Completed</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Score</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Hours</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Certificate</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Result</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.course_title ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.completion_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right">{item.score ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right">{item.hours_completed ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-500 text-xs font-mono">{item.certificate_number || "\u2014"}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {resultBadge[item.result]}">{resultLabels[item.result]}</span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} completion{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Completion" : "Record Completion"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        {#if !isEditing}
          <div>
            <label for="tcomp-emp" class="block text-sm font-medium text-neutral-700 mb-1">Employee <span class="text-red-500">*</span></label>
            <EmployeeSelect id="tcomp-emp" bind:value={form.employee} hasError={!!fieldError('employee')} />
            {#if fieldError("employee")}<p class="text-xs text-red-500 mt-1">{fieldError("employee")}</p>{/if}
          </div>
        {/if}
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tcomp-course" class="block text-sm font-medium text-neutral-700 mb-1">Course ID</label>
            <input id="tcomp-course" type="number" bind:value={form.course} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="tcomp-enroll" class="block text-sm font-medium text-neutral-700 mb-1">Enrollment ID</label>
            <input id="tcomp-enroll" type="number" bind:value={form.enrollment} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="tcomp-date" class="block text-sm font-medium text-neutral-700 mb-1">Completion Date <span class="text-red-500">*</span></label>
          <DateInput id="tcomp-date" bind:value={form.completion_date} />
          {#if fieldError("completion_date")}<p class="text-xs text-red-500 mt-1">{fieldError("completion_date")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tcomp-result" class="block text-sm font-medium text-neutral-700 mb-1">Result</label>
            <select id="tcomp-result" bind:value={form.result} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(resultLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="tcomp-score" class="block text-sm font-medium text-neutral-700 mb-1">Score</label>
            <input id="tcomp-score" type="number" step="0.01" bind:value={form.score} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div>
          <label for="tcomp-hours" class="block text-sm font-medium text-neutral-700 mb-1">Hours Completed</label>
          <input id="tcomp-hours" type="number" step="0.1" bind:value={form.hours_completed} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="tcomp-cert" class="block text-sm font-medium text-neutral-700 mb-1">Certificate Number</label>
          <input id="tcomp-cert" type="text" bind:value={form.certificate_number} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="tcomp-expiry" class="block text-sm font-medium text-neutral-700 mb-1">Certificate Expiry</label>
          <DateInput id="tcomp-expiry" bind:value={form.certificate_expiry} />
        </div>
        <div>
          <label for="tcomp-verified" class="block text-sm font-medium text-neutral-700 mb-1">Verified By (User ID)</label>
          <input id="tcomp-verified" type="number" bind:value={form.verified_by} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="tcomp-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="tcomp-notes" bind:value={form.notes} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

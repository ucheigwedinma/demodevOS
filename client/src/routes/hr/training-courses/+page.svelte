<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { TrainingCourseListItem, CourseFormat, CourseLevel, CourseStatus, PaginatedResponse } from "$lib/types";

  let items = $state<TrainingCourseListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");
  let filterFormat = $state("");

  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);

  let form = $state({
    title: "",
    code: "",
    description: "",
    provider: "",
    format: "in_person" as CourseFormat,
    level: "beginner" as CourseLevel,
    duration_hours: "",
    max_participants: "",
    cost_per_participant: "",
    prerequisites: "",
    learning_objectives: "",
    syllabus: "",
    is_mandatory: false,
    status: "draft" as CourseStatus,
  });

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<CourseStatus, string> = { draft: "Draft", active: "Active", archived: "Archived" };
  const formatLabels: Record<CourseFormat, string> = { in_person: "In-Person", online: "Online", hybrid: "Hybrid", self_paced: "Self-Paced", workshop: "Workshop" };
  const levelLabels: Record<CourseLevel, string> = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      if (filterFormat) params.format = filterFormat;
      const res = await api.get<PaginatedResponse<TrainingCourseListItem>>("/hr/training-courses/", params);
      items = res.results;
      totalCount = res.count;
    } catch { items = []; totalCount = 0; } finally { loading = false; }
  }

  function resetForm() {
    form = { title: "", code: "", description: "", provider: "", format: "in_person", level: "beginner", duration_hours: "", max_participants: "", cost_per_participant: "", prerequisites: "", learning_objectives: "", syllabus: "", is_mandatory: false, status: "draft" };
    fieldErrors = {}; editingId = null;
  }
  function openCreate() { resetForm(); showSlideOver = true; }

  async function openEdit(item: TrainingCourseListItem) {
    resetForm(); editingId = item.id;
    try {
      const d = await api.get<any>(`/hr/training-courses/${item.id}/`);
      form.title = d.title;
      form.code = d.code ?? "";
      form.description = d.description ?? "";
      form.provider = d.provider ?? "";
      form.format = d.format;
      form.level = d.level;
      form.duration_hours = d.duration_hours ?? "";
      form.max_participants = d.max_participants != null ? String(d.max_participants) : "";
      form.cost_per_participant = d.cost_per_participant ?? "";
      form.prerequisites = d.prerequisites ?? "";
      form.learning_objectives = d.learning_objectives ?? "";
      form.syllabus = d.syllabus ?? "";
      form.is_mandatory = d.is_mandatory ?? false;
      form.status = d.status;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true; fieldErrors = {};
    try {
      const payload: Record<string, unknown> = { title: form.title, code: form.code, description: form.description, provider: form.provider, format: form.format, level: form.level, currency: currency.config.code, prerequisites: form.prerequisites, learning_objectives: form.learning_objectives, syllabus: form.syllabus, is_mandatory: form.is_mandatory, status: form.status };
      if (form.duration_hours) payload.duration_hours = form.duration_hours;
      if (form.max_participants) payload.max_participants = Number(form.max_participants);
      if (form.cost_per_participant) payload.cost_per_participant = form.cost_per_participant;
      if (isEditing) { await api.patch(`/hr/training-courses/${editingId}/`, payload); toast.success("Course updated"); }
      else { await api.post("/hr/training-courses/", payload); toast.success("Course created"); }
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
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Training Courses</h1>
      <p class="mt-1 text-sm text-neutral-500">Reusable training course catalogue</p>
    </div>
    <button onclick={openCreate} class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Course
    </button>
  </div>

  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search courses..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
    <select value={filterFormat} onchange={(e) => { filterFormat = e.currentTarget.value; currentPage = 1; fetchItems(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Formats</option>
      {#each Object.entries(formatLabels) as [k, v]}<option value={k}>{v}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if items.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">{searchQuery || filterStatus || filterFormat ? "No courses match your filters" : "No training courses created yet"}</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Course</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Provider</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Format</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Level</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Duration (h)</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Cost</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as item}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(item)}>
              <td class="px-5 py-3.5">
                <div class="font-medium text-neutral-900">{item.title}</div>
                {#if item.code}<div class="text-xs text-neutral-400 font-mono">{item.code}</div>{/if}
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{item.provider || "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{formatLabels[item.format]}</td>
              <td class="px-5 py-3.5 text-neutral-600">{levelLabels[item.level]}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right">{item.duration_hours ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right">{item.cost_per_participant ? currency.format(item.cost_per_participant) : "\u2014"}</td>
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
        <span>{totalCount} course{totalCount !== 1 ? "s" : ""}</span>
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
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Course" : "New Course"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100" aria-label="Close"><svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg></button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="tc-title" class="block text-sm font-medium text-neutral-700 mb-1">Title <span class="text-red-500">*</span></label>
          <input id="tc-title" type="text" bind:value={form.title} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('title') ? 'border-red-400' : ''}" />
          {#if fieldError("title")}<p class="text-xs text-red-500 mt-1">{fieldError("title")}</p>{/if}
        </div>
        <div>
          <label for="tc-code" class="block text-sm font-medium text-neutral-700 mb-1">Code</label>
          <input id="tc-code" type="text" bind:value={form.code} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div>
          <label for="tc-provider" class="block text-sm font-medium text-neutral-700 mb-1">Provider</label>
          <input id="tc-provider" type="text" bind:value={form.provider} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tc-format" class="block text-sm font-medium text-neutral-700 mb-1">Format</label>
            <select id="tc-format" bind:value={form.format} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(formatLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="tc-level" class="block text-sm font-medium text-neutral-700 mb-1">Level</label>
            <select id="tc-level" bind:value={form.level} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(levelLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tc-dur" class="block text-sm font-medium text-neutral-700 mb-1">Duration (hours)</label>
            <input id="tc-dur" type="number" step="0.1" bind:value={form.duration_hours} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="tc-max" class="block text-sm font-medium text-neutral-700 mb-1">Max Participants</label>
            <input id="tc-max" type="number" bind:value={form.max_participants} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tc-cost" class="block text-sm font-medium text-neutral-700 mb-1">Cost per Participant</label>
            <input id="tc-cost" type="number" step="0.01" bind:value={form.cost_per_participant} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </div>
          <div>
            <label for="tc-curr" class="block text-sm font-medium text-neutral-700 mb-1">Currency</label>
            <p id="tc-curr" class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-neutral-50 text-neutral-700">{currency.config.code}</p>
          </div>
        </div>
        <div>
          <label for="tc-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
          <select id="tc-status" bind:value={form.status} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each Object.entries(statusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
          </select>
        </div>
        <div class="flex items-center gap-2">
          <input id="tc-mandatory" type="checkbox" bind:checked={form.is_mandatory} class="rounded border-neutral-300" />
          <label for="tc-mandatory" class="text-sm font-medium text-neutral-700">Mandatory</label>
        </div>
        <div>
          <label for="tc-prereq" class="block text-sm font-medium text-neutral-700 mb-1">Prerequisites</label>
          <textarea id="tc-prereq" bind:value={form.prerequisites} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="tc-obj" class="block text-sm font-medium text-neutral-700 mb-1">Learning Objectives</label>
          <textarea id="tc-obj" bind:value={form.learning_objectives} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="tc-syll" class="block text-sm font-medium text-neutral-700 mb-1">Syllabus</label>
          <textarea id="tc-syll" bind:value={form.syllabus} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="tc-desc" class="block text-sm font-medium text-neutral-700 mb-1">Description</label>
          <textarea id="tc-desc" bind:value={form.description} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
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

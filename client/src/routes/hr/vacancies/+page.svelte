<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { HRVacancyListItem, HRVacancyStatus, HRVacancyPriority, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let vacancies = $state<HRVacancyListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterStatus = $state("");
  let filterPriority = $state("");

  // Slide-over
  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let form = $state({
    title: "",
    position: "" as string,
    priority: "medium" as HRVacancyPriority,
    target_fill_date: "",
    reason: "",
    notes: "",
  });
  let positionOptions = $state<{ id: number; title: string; code: string }[]>([]);

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  const statusLabels: Record<HRVacancyStatus, string> = { open: "Open", on_hold: "On Hold", filled: "Filled", cancelled: "Cancelled" };
  const priorityLabels: Record<HRVacancyPriority, string> = { low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };
  const priorityDot: Record<HRVacancyPriority, string> = { low: "bg-neutral-200", medium: "bg-neutral-400", high: "bg-neutral-600", urgent: "bg-neutral-900" };

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function fetchVacancies() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterStatus) params.status = filterStatus;
      if (filterPriority) params.priority = filterPriority;
      const res = await api.get<PaginatedResponse<HRVacancyListItem>>("/hr/vacancies/", params);
      vacancies = res.results;
      totalCount = res.count;
    } catch {
      vacancies = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    form = { title: "", position: "", priority: "medium", target_fill_date: "", reason: "", notes: "" };
    fieldErrors = {};
    editingId = null;
  }

  async function openCreate() {
    resetForm();
    try {
      const res = await api.get<{ results: { id: number; title: string; code: string }[] }>("/hr/positions/", { page_size: "200", status: "active" });
      positionOptions = res.results;
    } catch { positionOptions = []; }
    showSlideOver = true;
  }

  async function openEdit(vacancy: HRVacancyListItem) {
    resetForm();
    editingId = vacancy.id;
    form.title = vacancy.title;
    form.position = String(vacancy.position);
    form.priority = vacancy.priority;
    form.target_fill_date = vacancy.target_fill_date ?? "";
    try {
      const [posRes, detail] = await Promise.all([
        api.get<{ results: { id: number; title: string; code: string }[] }>("/hr/positions/", { page_size: "200", status: "active" }),
        api.get<{ reason: string; notes: string }>(`/hr/vacancies/${vacancy.id}/`),
      ]);
      positionOptions = posRes.results;
      form.reason = detail.reason;
      form.notes = detail.notes;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        position: form.position ? Number(form.position) : undefined,
        priority: form.priority,
        reason: form.reason,
        notes: form.notes,
      };
      if (form.target_fill_date) payload.target_fill_date = form.target_fill_date;

      if (isEditing) {
        await api.patch(`/hr/vacancies/${editingId}/`, payload);
        toast.success("Vacancy updated");
      } else {
        await api.post("/hr/vacancies/", payload);
        toast.success("Vacancy created");
      }
      showSlideOver = false;
      resetForm();
      fetchVacancies();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
      } else {
        toast.error("Failed to save vacancy");
      }
    } finally {
      saving = false;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; fetchVacancies(); }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchVacancies();
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const VACANCY_SAMPLES = [
    {
      title: "Senior Quantity Surveyor — Tower D", priority: "high" as HRVacancyPriority, target_fill_date: "2025-05-30",
      reason: "Replacement — previous holder promoted to Cost Manager",
      notes: "Critical role for upcoming tender submissions. Prefer candidates with FIDIC experience and CostX proficiency.",
    },
    {
      title: "HSE Officer — Phase 2 Sites", priority: "urgent" as HRVacancyPriority, target_fill_date: "2025-04-15",
      reason: "Team expansion to support new project pipeline",
      notes: "NEBOSH-certified required. Must be available for multi-site deployment across 3 active construction zones.",
    },
    {
      title: "Marketing Coordinator", priority: "medium" as HRVacancyPriority, target_fill_date: "2025-06-30",
      reason: "New position approved in FY budget",
      notes: "Focus on digital campaigns and broker channel marketing. Adobe Creative Suite and social media management experience preferred.",
    },
  ];
  let vacDevIdx = 0;
  function devFillVacancy() {
    const s = VACANCY_SAMPLES[vacDevIdx % VACANCY_SAMPLES.length];
    vacDevIdx++;
    form.title = s.title;
    form.position = positionOptions.length > 0 ? String(positionOptions[vacDevIdx % positionOptions.length].id) : "";
    form.priority = s.priority;
    form.target_fill_date = s.target_fill_date;
    form.reason = s.reason;
    form.notes = s.notes;
  }

  // Quick counts
  let openCount = $derived(vacancies.filter((v) => v.status === "open").length);

  $effect(() => {
    fetchVacancies();
  });
</script>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Vacancy Tracker</h1>
      <p class="mt-1 text-sm text-neutral-500">Open positions requiring recruitment</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Post Vacancy
    </button>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search vacancies..." value={searchQuery} oninput={(e) => handleSearch(e.currentTarget.value)} class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
    </div>
    <select value={filterStatus} onchange={(e) => { filterStatus = e.currentTarget.value; currentPage = 1; fetchVacancies(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Status</option>
      {#each Object.entries(statusLabels) as [k, v]}
        <option value={k}>{v}</option>
      {/each}
    </select>
    <select value={filterPriority} onchange={(e) => { filterPriority = e.currentTarget.value; currentPage = 1; fetchVacancies(); }} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Priority</option>
      {#each Object.entries(priorityLabels) as [k, v]}
        <option value={k}>{v}</option>
      {/each}
    </select>
  </div>

  <!-- Table -->
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if vacancies.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">{searchQuery || filterStatus || filterPriority ? "No vacancies match your filters" : "No vacancies posted yet"}</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/50">
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Title</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Position</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Priority</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Hiring Manager</th>
              <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Opened</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Days Open</th>
              <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each vacancies as vacancy}
              <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(vacancy)}>
                <td class="px-5 py-3.5 font-medium text-neutral-900">{vacancy.title}</td>
                <td class="px-5 py-3.5">
                  <span class="text-neutral-600">{vacancy.position_title}</span>
                  <span class="font-mono text-xs text-neutral-400 ml-1">{vacancy.position_code}</span>
                </td>
                <td class="px-5 py-3.5 text-neutral-600">{vacancy.department_name}</td>
                <td class="px-5 py-3.5 text-center">
                  <span class="inline-flex items-center gap-1.5 text-xs">
                    <span class="w-2 h-2 rounded-full {priorityDot[vacancy.priority] ?? ''}"></span>
                    {priorityLabels[vacancy.priority] ?? vacancy.priority}
                  </span>
                </td>
                <td class="px-5 py-3.5 text-neutral-600">{vacancy.hiring_manager_name ?? "\u2014"}</td>
                <td class="px-5 py-3.5 text-neutral-600 text-xs">{formatDate(vacancy.opened_date)}</td>
                <td class="px-5 py-3.5 text-center text-neutral-600">{vacancy.days_open ?? "\u2014"}</td>
                <td class="px-5 py-3.5 text-center">
                  <StatusBadge status={vacancy.status} />
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>

    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} vacanc{totalCount !== 1 ? 'ies' : 'y'}</span>
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

<!-- Slide-over -->
{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Vacancy" : "Post Vacancy"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="p-1 rounded hover:bg-neutral-100">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="vac-title" class="block text-sm font-medium text-neutral-700 mb-1">Title <span class="text-red-500">*</span></label>
          <input id="vac-title" type="text" bind:value={form.title} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('title') ? 'border-red-400' : ''}" />
          {#if fieldError("title")}<p class="text-xs text-red-500 mt-1">{fieldError("title")}</p>{/if}
        </div>
        <div>
          <label for="vac-pos" class="block text-sm font-medium text-neutral-700 mb-1">Position <span class="text-red-500">*</span></label>
          <select id="vac-pos" bind:value={form.position} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Select position</option>
            {#each positionOptions as pos}
              <option value={String(pos.id)}>{pos.code} — {pos.title}</option>
            {/each}
          </select>
          {#if fieldError("position")}<p class="text-xs text-red-500 mt-1">{fieldError("position")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="vac-priority" class="block text-sm font-medium text-neutral-700 mb-1">Priority</label>
            <select id="vac-priority" bind:value={form.priority} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each Object.entries(priorityLabels) as [k, v]}
                <option value={k}>{v}</option>
              {/each}
            </select>
          </div>
          <div>
            <label for="vac-target" class="block text-sm font-medium text-neutral-700 mb-1">Target Fill Date</label>
            <DateInput id="vac-target" bind:value={form.target_fill_date} />
          </div>
        </div>
        <div>
          <label for="vac-reason" class="block text-sm font-medium text-neutral-700 mb-1">Reason</label>
          <textarea id="vac-reason" bind:value={form.reason} rows={2} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div>
          <label for="vac-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="vac-notes" bind:value={form.notes} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillVacancy} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {saving ? "Saving..." : isEditing ? "Update" : "Post"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>

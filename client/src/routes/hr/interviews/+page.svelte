<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    InterviewListItem,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // --- Interviews Table ---
  let interviews = $state<InterviewListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let statusFilter = $state("");
  let typeFilter = $state("");

  // --- Reference Data ---
  let candidates = $state<{ id: number; full_name: string }[]>([]);

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    candidate: "",
    interview_type: "",
    interviewer: "",
    scheduled_date: "",
    scheduled_time: "",
    duration_minutes: "60",
    location: "",
    meeting_link: "",
    notes: "",
  });

  function fieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      candidate: "",
      interview_type: "",
      interviewer: "",
      scheduled_date: "",
      scheduled_time: "",
      duration_minutes: "60",
      location: "",
      meeting_link: "",
      notes: "",
    };
    createErrors = {};
  }

  // --- Derived ---
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });

  // --- Helpers ---
  function formatDate(dateStr: string): string {
    if (!dateStr) return "";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatTime(timeStr: string): string {
    if (!timeStr) return "";
    const parts = timeStr.split(":");
    let hours = parseInt(parts[0], 10);
    const minutes = parts[1];
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    if (hours === 0) hours = 12;
    return `${hours}:${minutes} ${ampm}`;
  }

  // --- Data Fetching ---
  async function fetchInterviews() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.interview_type = typeFilter;

      const res = await api.get<PaginatedResponse<InterviewListItem>>(
        "/hr/interviews/",
        params,
      );
      interviews = res.results;
      totalCount = res.count;
    } catch {
      interviews = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchCandidates() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; full_name: string }>>(
        "/hr/candidates/",
        { page_size: "200" },
      );
      candidates = res.results;
    } catch {
      candidates = [];
    }
  }

  // --- Event Handlers ---
  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchInterviews();
  }

  function handleTypeChange(value: string) {
    typeFilter = value;
    currentPage = 1;
    fetchInterviews();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchInterviews();
  }

  async function handleCreateInterview(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        candidate: Number(createForm.candidate),
        interview_type: createForm.interview_type,
        interviewer: Number(createForm.interviewer),
        scheduled_date: createForm.scheduled_date,
        scheduled_time: createForm.scheduled_time,
        duration_minutes: Number(createForm.duration_minutes) || 60,
        location: createForm.location || "",
        meeting_link: createForm.meeting_link || "",
        notes: createForm.notes || "",
      };

      await api.post<InterviewListItem>("/hr/interviews/", payload);
      toast.success("Interview scheduled", "The interview has been added to the calendar");
      showSlideOver = false;
      resetCreateForm();
      fetchInterviews();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not schedule the interview");
      }
    }
    saving = false;
  }

  async function handleComplete(id: number) {
    try {
      await api.post(`/hr/interviews/${id}/complete/`, {});
      toast.success("Interview completed", "The interview has been marked as completed");
      fetchInterviews();
    } catch {
      toast.error("Something went wrong", "Could not complete the interview");
    }
  }

  async function handleCancel(id: number) {
    try {
      await api.post(`/hr/interviews/${id}/cancel/`, {});
      toast.success("Interview cancelled", "The interview has been cancelled");
      fetchInterviews();
    } catch {
      toast.error("Something went wrong", "Could not cancel the interview");
    }
  }

  function openSlideOver() {
    resetCreateForm();
    fetchCandidates();
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  $effect(() => {
    fetchInterviews();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Interview Scheduling</h1>
      <p class="mt-1 text-sm text-neutral-500">Manage interview sessions and track completion</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Schedule Interview
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="scheduled">Scheduled</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
          <option value="no_show">No Show</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Interview Type</span>
        <input
          type="text"
          placeholder="Filter by type..."
          value={typeFilter}
          oninput={(e) => handleTypeChange((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if interviews.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No interviews found</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Schedule your first interview
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Candidate</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Interviewer</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Time</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Duration</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Location</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Evaluated</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each interviews as interview}
              <tr class="hover:bg-neutral-50 transition-colors">
                <!-- Candidate -->
                <td class="px-5 py-4 text-sm font-medium text-neutral-900 whitespace-nowrap">
                  {interview.candidate_name}
                </td>

                <!-- Type -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap capitalize">
                  {interview.interview_type}
                </td>

                <!-- Interviewer -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {interview.interviewer_name}
                </td>

                <!-- Date -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {formatDate(interview.scheduled_date)}
                </td>

                <!-- Time -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap tabular-nums">
                  {formatTime(interview.scheduled_time)}
                </td>

                <!-- Duration -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap tabular-nums">
                  {interview.duration_minutes} min
                </td>

                <!-- Location -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {interview.location || "\u2014"}
                </td>

                <!-- Status -->
                <td class="px-5 py-4 whitespace-nowrap">
                  <StatusBadge status={interview.status} />
                </td>

                <!-- Evaluated -->
                <td class="px-5 py-4 text-center whitespace-nowrap">
                  {#if interview.has_evaluation}
                    <svg class="w-5 h-5 text-neutral-900 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  {:else}
                    <span class="text-neutral-300 text-sm">&mdash;</span>
                  {/if}
                </td>

                <!-- Actions -->
                <td class="px-5 py-4 text-right whitespace-nowrap">
                  {#if interview.status === "scheduled"}
                    <div class="flex items-center justify-end gap-2">
                      <button
                        onclick={(e) => { e.stopPropagation(); handleComplete(interview.id); }}
                        class="px-2.5 py-1 text-xs font-medium rounded-md bg-neutral-900 text-white hover:bg-neutral-800 transition-colors"
                      >
                        Complete
                      </button>
                      <button
                        onclick={(e) => { e.stopPropagation(); handleCancel(interview.id); }}
                        class="px-2.5 py-1 text-xs font-medium rounded-md border border-neutral-200 text-neutral-600 hover:bg-neutral-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-400">
          Showing {(currentPage - 1) * pageSize + 1}&ndash;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        {#if totalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === currentPage
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'border-neutral-200 hover:bg-neutral-50'}"
              >
                {pg}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<!-- ============================================ -->
<!-- SLIDE-OVER: Schedule Interview               -->
<!-- ============================================ -->
{#if showSlideOver}
  <!-- Backdrop -->
  <button
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeSlideOver}
    tabindex="-1"
    aria-label="Close panel"
  ></button>

  <!-- Panel -->
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg flex flex-col bg-white shadow-2xl slide-over-enter">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
      <h2 class="text-lg font-semibold text-neutral-900">Schedule Interview</h2>
      <button
        onclick={closeSlideOver}
        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="create-interview-form" onsubmit={handleCreateInterview} class="space-y-5">
        <!-- Candidate -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Candidate <span class="text-neutral-400">*</span></span>
          <select
            bind:value={createForm.candidate}
            required
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Select a candidate</option>
            {#each candidates as candidate}
              <option value={String(candidate.id)}>{candidate.full_name}</option>
            {/each}
          </select>
          {#if fieldError("candidate")}<p class="mt-1 text-xs text-red-500">{fieldError("candidate")}</p>{/if}
        </label>

        <!-- Interview Type -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Interview Type <span class="text-neutral-400">*</span></span>
          <input
            type="text"
            bind:value={createForm.interview_type}
            required
            placeholder="e.g. Technical, Behavioral, Panel"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("interview_type")}<p class="mt-1 text-xs text-red-500">{fieldError("interview_type")}</p>{/if}
        </label>

        <!-- Interviewer -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Interviewer <span class="text-neutral-400">*</span> <span class="text-neutral-400 font-normal">(user ID)</span></span>
          <input
            type="number"
            bind:value={createForm.interviewer}
            required
            min="1"
            placeholder="User ID"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
          />
          {#if fieldError("interviewer")}<p class="mt-1 text-xs text-red-500">{fieldError("interviewer")}</p>{/if}
        </label>

        <!-- Date & Time (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Date <span class="text-neutral-400">*</span></span>
            <DateInput bind:value={createForm.scheduled_date} required />
            {#if fieldError("scheduled_date")}<p class="mt-1 text-xs text-red-500">{fieldError("scheduled_date")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Time <span class="text-neutral-400">*</span></span>
            <input
              type="time"
              bind:value={createForm.scheduled_time}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("scheduled_time")}<p class="mt-1 text-xs text-red-500">{fieldError("scheduled_time")}</p>{/if}
          </label>
        </div>

        <!-- Duration -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Duration <span class="text-neutral-400 font-normal">(minutes)</span></span>
          <input
            type="number"
            bind:value={createForm.duration_minutes}
            min="5"
            step="5"
            placeholder="60"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
          />
          {#if fieldError("duration_minutes")}<p class="mt-1 text-xs text-red-500">{fieldError("duration_minutes")}</p>{/if}
        </label>

        <!-- Location -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Location</span>
          <input
            type="text"
            bind:value={createForm.location}
            placeholder="e.g. Conference Room A, Office 302"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("location")}<p class="mt-1 text-xs text-red-500">{fieldError("location")}</p>{/if}
        </label>

        <!-- Meeting Link -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Meeting Link <span class="text-neutral-400 font-normal">(optional)</span></span>
          <input
            type="url"
            bind:value={createForm.meeting_link}
            placeholder="https://meet.google.com/..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("meeting_link")}<p class="mt-1 text-xs text-red-500">{fieldError("meeting_link")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional details about this interview..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("notes")}<p class="mt-1 text-xs text-red-500">{fieldError("notes")}</p>{/if}
        </label>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100 shrink-0">
      <button
        type="button"
        onclick={closeSlideOver}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="create-interview-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Scheduling..." : "Schedule Interview"}
      </button>
    </div>
  </div>
{/if}

<svelte:window onkeydown={(e) => { if (e.key === "Escape" && showSlideOver) closeSlideOver(); }} />

<style>
  .slide-over-enter {
    animation: slide-in-right 0.25s ease-out;
  }

  @keyframes slide-in-right {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
</style>

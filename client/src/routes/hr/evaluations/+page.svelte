<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CandidateEvaluationListItem,
    CandidateListItem,
    InterviewListItem,
    EvaluationRecommendation,
    PaginatedResponse,
  } from "$lib/types";

  // ---------------------------------------------------------------------------
  // List state
  // ---------------------------------------------------------------------------
  let evaluations = $state<CandidateEvaluationListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // ---------------------------------------------------------------------------
  // Filters
  // ---------------------------------------------------------------------------
  let search = $state("");
  let recommendationFilter = $state("");

  // ---------------------------------------------------------------------------
  // Reference data for slide-over
  // ---------------------------------------------------------------------------
  let candidates = $state<CandidateListItem[]>([]);
  let interviews = $state<InterviewListItem[]>([]);
  let lookupsLoaded = $state(false);

  // ---------------------------------------------------------------------------
  // Slide-over
  // ---------------------------------------------------------------------------
  let showSlideOver = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    candidate: "",
    interview: "",
    overall_rating: "3",
    recommendation: "maybe" as string,
    strengths: "",
    concerns: "",
    notes: "",
  });

  function fieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      candidate: "",
      interview: "",
      overall_rating: "3",
      recommendation: "maybe",
      strengths: "",
      concerns: "",
      notes: "",
    };
    createErrors = {};
  }

  // ---------------------------------------------------------------------------
  // Derived helpers
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // Recommendation labels & badge classes
  // ---------------------------------------------------------------------------
  const recommendationLabels: Record<string, string> = {
    strongly_hire: "Strongly Hire",
    hire: "Hire",
    maybe: "Maybe",
    no_hire: "No Hire",
    strongly_no_hire: "Strongly No Hire",
  };

  const recommendationBadgeClasses: Record<string, string> = {
    strongly_hire: "bg-neutral-900 text-white",
    hire: "bg-neutral-700 text-white",
    maybe: "bg-neutral-300 text-neutral-700",
    no_hire: "bg-neutral-200 text-neutral-500",
    strongly_no_hire: "bg-neutral-100 text-neutral-400",
  };

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function formatDate(dateStr: string): string {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------
  let debounceTimer: ReturnType<typeof setTimeout>;

  async function fetchEvaluations() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (recommendationFilter) params.recommendation = recommendationFilter;

      const res = await api.get<PaginatedResponse<CandidateEvaluationListItem>>(
        "/hr/evaluations/",
        params,
      );
      evaluations = res.results;
      totalCount = res.count;
    } catch {
      evaluations = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchLookups() {
    if (lookupsLoaded) return;
    try {
      const [candRes, intRes] = await Promise.all([
        api.get<PaginatedResponse<CandidateListItem>>("/hr/candidates/", { page_size: "200" }),
        api.get<PaginatedResponse<InterviewListItem>>("/hr/interviews/", { page_size: "200" }),
      ]);
      candidates = candRes.results;
      interviews = intRes.results;
      lookupsLoaded = true;
    } catch {
      // Silently fail; selects will remain empty
    }
  }

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------
  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchEvaluations();
    }, 300);
  }

  function handleRecommendationChange(value: string) {
    recommendationFilter = value;
    currentPage = 1;
    fetchEvaluations();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchEvaluations();
  }

  function openSlideOver() {
    resetCreateForm();
    showSlideOver = true;
    fetchLookups();
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  async function handleCreateEvaluation(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        candidate: Number(createForm.candidate),
        overall_rating: Number(createForm.overall_rating),
        recommendation: createForm.recommendation,
        strengths: createForm.strengths || "",
        concerns: createForm.concerns || "",
        notes: createForm.notes || "",
      };
      if (createForm.interview) payload.interview = Number(createForm.interview);

      const result = await api.post<CandidateEvaluationListItem>("/hr/evaluations/", payload);
      toast.success("Evaluation created", `Evaluation for ${result.candidate_name} has been added`);
      showSlideOver = false;
      resetCreateForm();
      fetchEvaluations();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the evaluation");
      }
    } finally {
      saving = false;
    }
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  $effect(() => {
    fetchEvaluations();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Candidate Evaluation</h1>
      <p class="mt-1 text-sm text-neutral-500">Review and rate interview performance</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Evaluation
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Candidate or evaluator name..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Recommendation</span>
        <select
          value={recommendationFilter}
          onchange={(e) => handleRecommendationChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Recommendations</option>
          <option value="strongly_hire">Strongly Hire</option>
          <option value="hire">Hire</option>
          <option value="maybe">Maybe</option>
          <option value="no_hire">No Hire</option>
          <option value="strongly_no_hire">Strongly No Hire</option>
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if evaluations.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z"
            />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No evaluations found</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Add your first evaluation
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Candidate</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Evaluator</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Rating</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Recommendation</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each evaluations as evaluation (evaluation.id)}
              <tr class="hover:bg-neutral-50 transition-colors">
                <!-- Candidate -->
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{evaluation.candidate_name}</div>
                </td>

                <!-- Evaluator -->
                <td class="px-5 py-4">
                  <div class="text-sm text-neutral-600">{evaluation.evaluator_name}</div>
                </td>

                <!-- Rating (filled/unfilled circles) -->
                <td class="px-5 py-4">
                  <div class="flex items-center gap-1">
                    {#each Array(5) as _, i}
                      <span
                        class="inline-block w-2.5 h-2.5 rounded-full {i < evaluation.overall_rating ? 'bg-neutral-900' : 'bg-neutral-200'}"
                      ></span>
                    {/each}
                  </div>
                </td>

                <!-- Recommendation -->
                <td class="px-5 py-4">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {recommendationBadgeClasses[evaluation.recommendation] ?? 'bg-neutral-100 text-neutral-600'}">
                    {recommendationLabels[evaluation.recommendation] ?? evaluation.recommendation}
                  </span>
                </td>

                <!-- Date -->
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(evaluation.evaluated_at)}
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
<!-- SLIDE-OVER: New Evaluation                    -->
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
      <h2 class="text-lg font-semibold text-neutral-900">New Evaluation</h2>
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
      <form id="create-evaluation-form" onsubmit={handleCreateEvaluation} class="space-y-5">
        <!-- Candidate -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Candidate</span>
          <select
            bind:value={createForm.candidate}
            required
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Select candidate</option>
            {#each candidates as candidate}
              <option value={String(candidate.id)}>{candidate.full_name}</option>
            {/each}
          </select>
          {#if fieldError("candidate")}<p class="mt-1 text-xs text-red-500">{fieldError("candidate")}</p>{/if}
        </label>

        <!-- Interview (optional) -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Interview <span class="text-neutral-400 font-normal">(optional)</span></span>
          <select
            bind:value={createForm.interview}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">None</option>
            {#each interviews as interview}
              <option value={String(interview.id)}>
                {interview.candidate_name} &mdash; {interview.interview_type} ({interview.scheduled_date})
              </option>
            {/each}
          </select>
          {#if fieldError("interview")}<p class="mt-1 text-xs text-red-500">{fieldError("interview")}</p>{/if}
        </label>

        <!-- Overall Rating -->
        <div>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Overall Rating</span>
          <div class="flex items-center gap-3">
            {#each [1, 2, 3, 4, 5] as rating}
              <label class="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="radio"
                  name="overall_rating"
                  value={String(rating)}
                  checked={createForm.overall_rating === String(rating)}
                  onchange={() => (createForm.overall_rating = String(rating))}
                  class="sr-only"
                />
                <span
                  class="inline-flex items-center justify-center w-9 h-9 rounded-lg border text-sm font-medium transition-colors {createForm.overall_rating === String(rating)
                    ? 'bg-neutral-900 text-white border-neutral-900'
                    : 'bg-white text-neutral-600 border-neutral-200 hover:bg-neutral-50'}"
                >
                  {rating}
                </span>
              </label>
            {/each}
          </div>
          {#if fieldError("overall_rating")}<p class="mt-1 text-xs text-red-500">{fieldError("overall_rating")}</p>{/if}
        </div>

        <!-- Recommendation -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Recommendation</span>
          <select
            bind:value={createForm.recommendation}
            required
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="strongly_hire">Strongly Hire</option>
            <option value="hire">Hire</option>
            <option value="maybe">Maybe</option>
            <option value="no_hire">No Hire</option>
            <option value="strongly_no_hire">Strongly No Hire</option>
          </select>
          {#if fieldError("recommendation")}<p class="mt-1 text-xs text-red-500">{fieldError("recommendation")}</p>{/if}
        </label>

        <!-- Strengths -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Strengths</span>
          <textarea
            bind:value={createForm.strengths}
            rows="3"
            placeholder="Key strengths observed during the evaluation..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("strengths")}<p class="mt-1 text-xs text-red-500">{fieldError("strengths")}</p>{/if}
        </label>

        <!-- Concerns -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Concerns</span>
          <textarea
            bind:value={createForm.concerns}
            rows="3"
            placeholder="Areas of concern or improvement..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("concerns")}<p class="mt-1 text-xs text-red-500">{fieldError("concerns")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional notes..."
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
        form="create-evaluation-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Creating..." : "Add Evaluation"}
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

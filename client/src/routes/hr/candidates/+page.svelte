<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CandidateListItem,
    CandidateStage,
    PaginatedResponse,
  } from "$lib/types";

  // --- Candidates Table ---
  let candidates = $state<CandidateListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let stageFilter = $state("");
  let sourceFilter = $state("");

  // --- Reference Data ---
  let jobListings = $state<{ id: number; title: string }[]>([]);

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    job_listing: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    source: "",
    current_title: "",
    current_employer: "",
    expected_salary: "",
    notes: "",
  });

  // --- Advance Stage Dropdown ---
  let advanceOpenId = $state<number | null>(null);

  function fieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      job_listing: "",
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      source: "",
      current_title: "",
      current_employer: "",
      expected_salary: "",
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

  // --- Stage badge styling ---
  const stageBadgeClasses: Record<CandidateStage, string> = {
    applied: "bg-neutral-100 text-neutral-600",
    screening: "bg-neutral-200 text-neutral-600",
    shortlisted: "bg-neutral-300 text-neutral-700",
    interviewing: "bg-neutral-400 text-neutral-800",
    evaluated: "bg-neutral-500 text-white",
    offer_pending: "bg-neutral-600 text-white",
    hired: "bg-neutral-900 text-white",
    rejected: "bg-neutral-200 text-neutral-400",
    withdrawn: "bg-neutral-100 text-neutral-400",
  };

  const stageLabels: Record<CandidateStage, string> = {
    applied: "Applied",
    screening: "Screening",
    shortlisted: "Shortlisted",
    interviewing: "Interviewing",
    evaluated: "Evaluated",
    offer_pending: "Offer Pending",
    hired: "Hired",
    rejected: "Rejected",
    withdrawn: "Withdrawn",
  };

  // Stages that can be advanced to (excludes terminal states)
  const advanceableStages: CandidateStage[] = [
    "applied",
    "screening",
    "shortlisted",
    "interviewing",
    "evaluated",
    "offer_pending",
    "hired",
  ];

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

  function formatRating(rating: number | null): string {
    if (rating === null || rating === undefined) return "\u2014";
    return `${rating.toFixed(1)} / 5`;
  }

  // --- Data Fetching ---
  async function fetchCandidates() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (stageFilter) params.stage = stageFilter;
      if (sourceFilter) params.source = sourceFilter;

      const res = await api.get<PaginatedResponse<CandidateListItem>>(
        "/hr/candidates/",
        params,
      );
      candidates = res.results;
      totalCount = res.count;
    } catch {
      candidates = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchJobListings() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; title: string }>>(
        "/hr/job-listings/",
        { page_size: "200", status: "active" },
      );
      jobListings = res.results;
    } catch {
      jobListings = [];
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchCandidates();
    }, 300);
  }

  function handleStageChange(value: string) {
    stageFilter = value;
    currentPage = 1;
    fetchCandidates();
  }

  function handleSourceInput(value: string) {
    sourceFilter = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchCandidates();
    }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchCandidates();
  }

  async function handleCreateCandidate(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        email: createForm.email || null,
        phone: createForm.phone || null,
        source: createForm.source || "",
        current_title: createForm.current_title || "",
        current_employer: createForm.current_employer || "",
        expected_salary: createForm.expected_salary || null,
        currency: currency.config.code,
        notes: createForm.notes || "",
      };
      if (createForm.job_listing) payload.job_listing = Number(createForm.job_listing);

      const result = await api.post<CandidateListItem>("/hr/candidates/", payload);
      toast.success("Candidate added", `${result.full_name} has been added to the pipeline`);
      showSlideOver = false;
      resetCreateForm();
      fetchCandidates();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the candidate");
      }
    }
    saving = false;
  }

  async function handleAdvanceStage(candidateId: number, stage: CandidateStage) {
    advanceOpenId = null;
    try {
      await api.post(`/hr/candidates/${candidateId}/advance_stage/`, { stage });
      toast.success("Stage updated", `Candidate moved to ${stageLabels[stage]}`);
      fetchCandidates();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Could not advance", err.message);
      } else {
        toast.error("Something went wrong", "Could not update the stage");
      }
    }
  }

  async function handleReject(candidateId: number) {
    try {
      await api.post(`/hr/candidates/${candidateId}/reject/`, {});
      toast.success("Candidate rejected", "The candidate has been marked as rejected");
      fetchCandidates();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Could not reject", err.message);
      } else {
        toast.error("Something went wrong", "Could not reject the candidate");
      }
    }
  }

  async function handleWithdraw(candidateId: number) {
    try {
      await api.post(`/hr/candidates/${candidateId}/withdraw/`, {});
      toast.success("Candidate withdrawn", "The candidate has been marked as withdrawn");
      fetchCandidates();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Could not withdraw", err.message);
      } else {
        toast.error("Something went wrong", "Could not withdraw the candidate");
      }
    }
  }

  function openSlideOver() {
    resetCreateForm();
    fetchJobListings();
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  function toggleAdvanceDropdown(candidateId: number) {
    advanceOpenId = advanceOpenId === candidateId ? null : candidateId;
  }

  // --- Initialize ---
  $effect(() => {
    fetchCandidates();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Candidate Pipeline</h1>
      <p class="mt-1 text-sm text-neutral-500">Track and manage applicants through the hiring process</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Add Candidate
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Name, email, or phone..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Stage</span>
        <select
          value={stageFilter}
          onchange={(e) => handleStageChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Stages</option>
          <option value="applied">Applied</option>
          <option value="screening">Screening</option>
          <option value="shortlisted">Shortlisted</option>
          <option value="interviewing">Interviewing</option>
          <option value="evaluated">Evaluated</option>
          <option value="offer_pending">Offer Pending</option>
          <option value="hired">Hired</option>
          <option value="rejected">Rejected</option>
          <option value="withdrawn">Withdrawn</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Source</span>
        <input
          type="text"
          placeholder="Filter by source..."
          value={sourceFilter}
          oninput={(e) => handleSourceInput((e.target as HTMLInputElement).value)}
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
    {:else if candidates.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
            />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No candidates found</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Add your first candidate
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Position</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Source</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Stage</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Applied Date</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Avg Rating</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each candidates as candidate (candidate.id)}
              <tr class="hover:bg-neutral-50 transition-colors">
                <!-- Name -->
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{candidate.full_name}</div>
                  {#if candidate.current_title || candidate.current_employer}
                    <div class="text-xs text-neutral-400 mt-0.5">
                      {#if candidate.current_title}{candidate.current_title}{/if}{#if candidate.current_title && candidate.current_employer} at {/if}{#if candidate.current_employer}{candidate.current_employer}{/if}
                    </div>
                  {/if}
                </td>

                <!-- Email -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {candidate.email || "\u2014"}
                </td>

                <!-- Position -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {candidate.listing_title ?? "\u2014"}
                </td>

                <!-- Source -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {candidate.source || "\u2014"}
                </td>

                <!-- Stage -->
                <td class="px-5 py-4">
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {stageBadgeClasses[candidate.stage] ?? 'bg-neutral-100 text-neutral-600'}">
                    {stageLabels[candidate.stage] ?? candidate.stage}
                  </span>
                </td>

                <!-- Applied Date -->
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(candidate.applied_date)}
                </td>

                <!-- Avg Rating -->
                <td class="px-5 py-4 text-sm text-neutral-600 text-right tabular-nums">
                  {formatRating(candidate.avg_rating)}
                </td>

                <!-- Status Badge -->
                <td class="px-5 py-4">
                  {#if candidate.stage === "hired"}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-900 text-white">
                      Hired
                    </span>
                  {:else if candidate.stage === "rejected"}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-200 text-neutral-400">
                      Rejected
                    </span>
                  {:else if candidate.stage === "withdrawn"}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-400">
                      Withdrawn
                    </span>
                  {:else}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700">
                      Active
                    </span>
                  {/if}
                </td>

                <!-- Actions -->
                <td class="px-5 py-4 text-right">
                  {#if candidate.stage !== "hired" && candidate.stage !== "rejected" && candidate.stage !== "withdrawn"}
                    <div class="flex items-center justify-end gap-1.5">
                      <!-- Advance Stage -->
                      <div class="relative">
                        <button
                          onclick={(event) => { event.stopPropagation(); toggleAdvanceDropdown(candidate.id); }}
                          class="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-700 hover:bg-neutral-50 transition-colors"
                          title="Advance stage"
                        >
                          Advance
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                          </svg>
                        </button>
                        {#if advanceOpenId === candidate.id}
                          <div class="absolute right-0 top-full mt-1 z-30 w-44 bg-white rounded-lg border border-neutral-200 shadow-lg py-1">
                            {#each advanceableStages as stage}
                              {#if stage !== candidate.stage}
                                <button
                                  onclick={(event) => { event.stopPropagation(); handleAdvanceStage(candidate.id, stage); }}
                                  class="w-full text-left px-3 py-2 text-xs text-neutral-700 hover:bg-neutral-50 transition-colors flex items-center gap-2"
                                >
                                  <span class="inline-block w-2 h-2 rounded-full {stageBadgeClasses[stage].split(' ')[0]}"></span>
                                  {stageLabels[stage]}
                                </button>
                              {/if}
                            {/each}
                          </div>
                        {/if}
                      </div>

                      <!-- Reject -->
                      <button
                        onclick={(event) => { event.stopPropagation(); handleReject(candidate.id); }}
                        class="inline-flex items-center px-2.5 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-700 transition-colors"
                        title="Reject candidate"
                      >
                        Reject
                      </button>

                      <!-- Withdraw -->
                      <button
                        onclick={(event) => { event.stopPropagation(); handleWithdraw(candidate.id); }}
                        class="inline-flex items-center px-2.5 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-700 transition-colors"
                        title="Withdraw candidate"
                      >
                        Withdraw
                      </button>
                    </div>
                  {:else}
                    <span class="text-xs text-neutral-400">\u2014</span>
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
<!-- SLIDE-OVER: Add Candidate                     -->
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
      <h2 class="text-lg font-semibold text-neutral-900">Add Candidate</h2>
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
      <form id="create-candidate-form" onsubmit={handleCreateCandidate} class="space-y-5">
        <!-- Job Listing -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Job Listing</span>
          <select
            bind:value={createForm.job_listing}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Select a job listing</option>
            {#each jobListings as listing}
              <option value={String(listing.id)}>{listing.title}</option>
            {/each}
          </select>
          {#if fieldError("job_listing")}<p class="mt-1 text-xs text-red-500">{fieldError("job_listing")}</p>{/if}
        </label>

        <!-- Name (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">First Name</span>
            <input
              type="text"
              bind:value={createForm.first_name}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("first_name")}<p class="mt-1 text-xs text-red-500">{fieldError("first_name")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Last Name</span>
            <input
              type="text"
              bind:value={createForm.last_name}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("last_name")}<p class="mt-1 text-xs text-red-500">{fieldError("last_name")}</p>{/if}
          </label>
        </div>

        <!-- Email & Phone (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Email</span>
            <input
              type="email"
              bind:value={createForm.email}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("email")}<p class="mt-1 text-xs text-red-500">{fieldError("email")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Phone</span>
            <input
              type="tel"
              bind:value={createForm.phone}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("phone")}<p class="mt-1 text-xs text-red-500">{fieldError("phone")}</p>{/if}
          </label>
        </div>

        <!-- Source -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Source</span>
          <input
            type="text"
            bind:value={createForm.source}
            placeholder="e.g. LinkedIn, Referral, Website..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("source")}<p class="mt-1 text-xs text-red-500">{fieldError("source")}</p>{/if}
        </label>

        <!-- Current Title & Current Employer (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Current Title</span>
            <input
              type="text"
              bind:value={createForm.current_title}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("current_title")}<p class="mt-1 text-xs text-red-500">{fieldError("current_title")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Current Employer</span>
            <input
              type="text"
              bind:value={createForm.current_employer}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("current_employer")}<p class="mt-1 text-xs text-red-500">{fieldError("current_employer")}</p>{/if}
          </label>
        </div>

        <!-- Expected Salary & Currency (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Expected Salary</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.expected_salary}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if fieldError("expected_salary")}<p class="mt-1 text-xs text-red-500">{fieldError("expected_salary")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Currency</span>
            <p class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-neutral-50 text-neutral-700">
              {currency.config.code}
            </p>
          </label>
        </div>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional details..."
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
        form="create-candidate-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Adding..." : "Add Candidate"}
      </button>
    </div>
  </div>
{/if}

<svelte:window
  onkeydown={(e) => { if (e.key === "Escape" && showSlideOver) closeSlideOver(); }}
  onclick={() => { if (advanceOpenId !== null) advanceOpenId = null; }}
/>

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

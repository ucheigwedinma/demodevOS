<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // --- Types ---
  interface JobListingListItem {
    id: number;
    title: string;
    requisition_number: string;
    requisition_title: string;
    location: string;
    employment_type: string;
    status: string;
    status_display: string;
    posted_date: string;
    closing_date: string;
    candidate_count: number;
    salary_display: string;
    salary_min: string | null;
    salary_max: string | null;
    currency: string;
    is_internal: boolean;
    is_external: boolean;
    description: string;
    requirements: string;
    notes: string;
  }

  interface RequisitionOption {
    id: number;
    requisition_number: string;
    title: string;
  }

  // --- Table State ---
  let listings = $state<JobListingListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let statusFilter = $state("");

  // --- Reference Data ---
  let requisitions = $state<RequisitionOption[]>([]);

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    requisition: "",
    title: "",
    description: "",
    requirements: "",
    location: "",
    employment_type: "",
    salary_display: "hidden" as string,
    salary_min: "",
    salary_max: "",
    is_internal: false,
    is_external: true,
    closing_date: "",
    notes: "",
  });

  function fieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      requisition: "",
      title: "",
      description: "",
      requirements: "",
      location: "",
      employment_type: "",
      salary_display: "hidden",
      salary_min: "",
      salary_max: "",
      is_internal: false,
      is_external: true,
      closing_date: "",
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
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  // --- Data Fetching ---
  async function fetchListings() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;

      const res = await api.get<PaginatedResponse<JobListingListItem>>(
        "/hr/job-listings/",
        params,
      );
      listings = res.results;
      totalCount = res.count;
    } catch {
      listings = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchRequisitions() {
    try {
      const res = await api.get<PaginatedResponse<RequisitionOption>>(
        "/hr/requisitions/",
        { page_size: "200" },
      );
      requisitions = res.results;
    } catch {
      requisitions = [];
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchListings();
    }, 300);
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchListings();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchListings();
  }

  async function handleCloseListing(id: number) {
    try {
      await api.post(`/hr/job-listings/${id}/close/`, {});
      toast.success("Listing closed", "The job listing has been closed");
      fetchListings();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Could not close listing", err.message);
      } else {
        toast.error("Something went wrong", "Could not close the listing");
      }
    }
  }

  async function handleArchiveListing(id: number) {
    try {
      await api.post(`/hr/job-listings/${id}/archive/`, {});
      toast.success("Listing archived", "The job listing has been archived");
      fetchListings();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Could not archive listing", err.message);
      } else {
        toast.error("Something went wrong", "Could not archive the listing");
      }
    }
  }

  async function handleCreateListing(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        title: createForm.title,
        description: createForm.description || "",
        requirements: createForm.requirements || "",
        location: createForm.location || "",
        employment_type: createForm.employment_type || "",
        salary_display: createForm.salary_display,
        currency: currency.config.code,
        is_internal: createForm.is_internal,
        is_external: createForm.is_external,
        notes: createForm.notes || "",
      };
      if (createForm.requisition) payload.requisition = Number(createForm.requisition);
      if (createForm.salary_min) payload.salary_min = createForm.salary_min;
      if (createForm.salary_max) payload.salary_max = createForm.salary_max;
      if (createForm.closing_date) payload.closing_date = createForm.closing_date;

      const result = await api.post<JobListingListItem>("/hr/job-listings/", payload);
      toast.success("Listing created", `"${result.title}" has been added`);
      showSlideOver = false;
      resetCreateForm();
      fetchListings();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the listing");
      }
    }
    saving = false;
  }

  function openSlideOver() {
    resetCreateForm();
    fetchRequisitions();
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  $effect(() => {
    fetchListings();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Job Listings</h1>
      <p class="mt-1 text-sm text-neutral-500">Published job openings and their reach</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Create Listing
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Title, location, or requisition..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="closed">Closed</option>
          <option value="archived">Archived</option>
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
    {:else if listings.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0M12 12.75h.008v.008H12v-.008Z"
            />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No job listings found</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Create your first listing
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Requisition</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Location</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Posted Date</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Closing Date</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Candidates</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each listings as listing}
              <tr class="hover:bg-neutral-50 transition-colors">
                <!-- Title -->
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{listing.title}</div>
                </td>

                <!-- Requisition -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {listing.requisition_number || "\u2014"}
                </td>

                <!-- Location -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {listing.location || "\u2014"}
                </td>

                <!-- Type -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {listing.employment_type || "\u2014"}
                </td>

                <!-- Posted Date -->
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(listing.posted_date)}
                </td>

                <!-- Closing Date -->
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(listing.closing_date)}
                </td>

                <!-- Candidates -->
                <td class="px-5 py-4 text-right">
                  <span class="inline-flex items-center justify-center min-w-8 px-2 py-0.5 rounded-full text-xs font-medium tabular-nums bg-neutral-100 text-neutral-700">
                    {listing.candidate_count}
                  </span>
                </td>

                <!-- Status -->
                <td class="px-5 py-4">
                  <StatusBadge status={listing.status} label={listing.status_display} />
                </td>

                <!-- Actions -->
                <td class="px-5 py-4 text-right">
                  {#if listing.status === "active"}
                    <div class="inline-flex items-center gap-2">
                      <button
                        onclick={(event) => { event.stopPropagation(); handleCloseListing(listing.id); }}
                        class="px-2.5 py-1 text-xs font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors"
                      >
                        Close
                      </button>
                      <button
                        onclick={(event) => { event.stopPropagation(); handleArchiveListing(listing.id); }}
                        class="px-2.5 py-1 text-xs font-medium text-neutral-400 bg-neutral-50 rounded-md hover:bg-neutral-100 hover:text-neutral-600 transition-colors"
                      >
                        Archive
                      </button>
                    </div>
                  {:else}
                    <span class="text-neutral-300">\u2014</span>
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
<!-- SLIDE-OVER: Create Listing                    -->
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
      <h2 class="text-lg font-semibold text-neutral-900">Create Listing</h2>
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
      <form id="create-listing-form" onsubmit={handleCreateListing} class="space-y-5">
        <!-- Requisition -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requisition</span>
          <select
            bind:value={createForm.requisition}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Select requisition</option>
            {#each requisitions as req}
              <option value={String(req.id)}>{req.requisition_number} - {req.title}</option>
            {/each}
          </select>
          {#if fieldError("requisition")}<p class="mt-1 text-xs text-red-500">{fieldError("requisition")}</p>{/if}
        </label>

        <!-- Title -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
          <input
            type="text"
            bind:value={createForm.title}
            required
            placeholder="e.g. Senior Frontend Engineer"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("title")}<p class="mt-1 text-xs text-red-500">{fieldError("title")}</p>{/if}
        </label>

        <!-- Description -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description</span>
          <textarea
            bind:value={createForm.description}
            rows="4"
            placeholder="Describe the role, responsibilities, and team..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("description")}<p class="mt-1 text-xs text-red-500">{fieldError("description")}</p>{/if}
        </label>

        <!-- Requirements -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requirements</span>
          <textarea
            bind:value={createForm.requirements}
            rows="4"
            placeholder="List the qualifications, skills, and experience..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if fieldError("requirements")}<p class="mt-1 text-xs text-red-500">{fieldError("requirements")}</p>{/if}
        </label>

        <!-- Location & Employment Type (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Location</span>
            <input
              type="text"
              bind:value={createForm.location}
              placeholder="e.g. Dubai, UAE"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("location")}<p class="mt-1 text-xs text-red-500">{fieldError("location")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Employment Type</span>
            <input
              type="text"
              bind:value={createForm.employment_type}
              placeholder="e.g. Full-time"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("employment_type")}<p class="mt-1 text-xs text-red-500">{fieldError("employment_type")}</p>{/if}
          </label>
        </div>

        <!-- Salary Display -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Salary Display</span>
          <select
            bind:value={createForm.salary_display}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="hidden">Hidden</option>
            <option value="range">Range</option>
            <option value="exact">Exact</option>
          </select>
          {#if fieldError("salary_display")}<p class="mt-1 text-xs text-red-500">{fieldError("salary_display")}</p>{/if}
        </label>

        <!-- Salary Min & Salary Max (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Salary Min</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.salary_min}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if fieldError("salary_min")}<p class="mt-1 text-xs text-red-500">{fieldError("salary_min")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Salary Max</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.salary_max}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if fieldError("salary_max")}<p class="mt-1 text-xs text-red-500">{fieldError("salary_max")}</p>{/if}
          </label>
        </div>

        <!-- Currency -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Currency</span>
          <p class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-neutral-50 text-neutral-700">
            {currency.config.code}
          </p>
        </label>

        <!-- Visibility checkboxes (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label class="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={createForm.is_internal}
              class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 focus:ring-offset-0"
            />
            <span class="text-sm font-medium text-neutral-700">Internal posting</span>
          </label>
          <label class="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={createForm.is_external}
              class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 focus:ring-offset-0"
            />
            <span class="text-sm font-medium text-neutral-700">External posting</span>
          </label>
        </div>

        <!-- Closing Date -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Closing Date</span>
          <DateInput bind:value={createForm.closing_date} />
          {#if fieldError("closing_date")}<p class="mt-1 text-xs text-red-500">{fieldError("closing_date")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
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
        form="create-listing-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Creating..." : "Create Listing"}
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

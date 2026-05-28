<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    LeadListItem,
    LeadPropertyMatch,
    PaginatedResponse,
    PropertyMatchCandidateType,
    PropertyMatchOverview,
    PropertyMatchStatus,
  } from "$lib/types";

  let overview = $state<PropertyMatchOverview | null>(null);
  let overviewLoading = $state(true);

  let matches = $state<LeadPropertyMatch[]>([]);
  let matchesLoading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  const pageSize = 20;

  let leads = $state<LeadListItem[]>([]);
  let filters = $state({
    lead_id: "",
    candidate_type: "" as "" | PropertyMatchCandidateType,
    status: "" as "" | PropertyMatchStatus,
    min_score: "",
    is_active: "true",
  });

  let debounceTimer: ReturnType<typeof setTimeout>;
  let refreshing = $state(false);
  let updatingMatchId = $state<number | null>(null);

  const statusBadge: Record<PropertyMatchStatus, string> = {
    suggested: "bg-sky-100 text-sky-700",
    viewed: "bg-neutral-100 text-neutral-700",
    shortlisted: "bg-emerald-100 text-emerald-700",
    dismissed: "bg-rose-100 text-rose-700",
    converted: "bg-violet-100 text-violet-700",
  };

  const candidateBadge: Record<PropertyMatchCandidateType, string> = {
    unit: "bg-amber-100 text-amber-700",
    project: "bg-indigo-100 text-indigo-700",
  };

  function toNumber(v: unknown): number {
    const parsed = Number(v ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i += 1) pages.push(i);
    return pages;
  });

  async function fetchLeadOptions() {
    try {
      const res = await api.get<PaginatedResponse<LeadListItem>>("/crm/leads/", {
        page: "1",
        page_size: "200",
        status: "active",
        ordering: "-updated_at",
      });
      leads = res.results;
    } catch (err) {
      console.error("[crm/property-matching]", err);
      leads = [];
    }
  }

  async function fetchOverview() {
    overviewLoading = true;
    try {
      const params: Record<string, string> = {};
      if (filters.lead_id) params.lead_id = filters.lead_id;
      overview = await api.get<PropertyMatchOverview>("/crm/property-matches/overview/", params);
    } catch (err) {
      console.error("[crm/property-matching]", err);
      overview = null;
    } finally {
      overviewLoading = false;
    }
  }

  async function fetchMatches() {
    matchesLoading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (filters.lead_id) params.lead_id = filters.lead_id;
      if (filters.candidate_type) params.candidate_type = filters.candidate_type;
      if (filters.status) params.status = filters.status;
      if (filters.min_score) params.min_score = filters.min_score;
      if (filters.is_active) params.is_active = filters.is_active;

      const res = await api.get<PaginatedResponse<LeadPropertyMatch>>("/crm/property-matches/", params);
      matches = res.results;
      totalCount = res.count;
    } catch (err) {
      console.error("[crm/property-matching]", err);
      matches = [];
      totalCount = 0;
    } finally {
      matchesLoading = false;
    }
  }

  async function refreshMatches() {
    if (!filters.lead_id) {
      toast.error("Lead required", "Select a lead to run manual refresh.");
      return;
    }
    refreshing = true;
    try {
      const res = await api.post<{ active_count: number }>("/crm/property-matches/refresh/", {
        lead_id: Number(filters.lead_id),
      });
      toast.success("Matches refreshed", `${res.active_count} active suggestion(s) available.`);
      currentPage = 1;
      await Promise.all([fetchOverview(), fetchMatches()]);
    } catch (err) {
      console.error("[crm/property-matching]", err);
      toast.error("Refresh failed", "Could not recompute matches. Try again.");
    } finally {
      refreshing = false;
    }
  }

  async function updateMatchStatus(matchId: number, nextStatus: PropertyMatchStatus) {
    updatingMatchId = matchId;
    try {
      await api.patch(`/crm/property-matches/${matchId}/`, { status: nextStatus });
      toast.success("Match updated", `Status changed to ${nextStatus.replaceAll("_", " ")}.`);
      await Promise.all([fetchOverview(), fetchMatches()]);
    } catch (err) {
      console.error("[crm/property-matching]", err);
      toast.error("Update failed", "Could not update this match.");
    } finally {
      updatingMatchId = null;
    }
  }

  function handleFilterChange() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      void Promise.all([fetchOverview(), fetchMatches()]);
    }, 250);
  }

  function gotoPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    void fetchMatches();
  }

  onMount(() => {
    void fetchLeadOptions();
    void Promise.all([fetchOverview(), fetchMatches()]);
  });
</script>

<div class="space-y-6">
  <section class="space-y-1">
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-cyan-400">CRM</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Property Matching Engine</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Intelligent lead matching across available units and projects using budget, location, unit type, and payment eligibility.
    </p>
  </section>

  <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-3">
    <div class="rounded-xl border border-[#cfe3f6] bg-[#edf6ff] p-4">
      <p class="text-xs uppercase tracking-wider text-neutral-400">Total Matches</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{overviewLoading ? "--" : (overview?.total_matches ?? 0)}</p>
    </div>
    <div class="rounded-xl border border-[#cfe3f6] bg-[#edf6ff] p-4">
      <p class="text-xs uppercase tracking-wider text-neutral-400">Suggested</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{overviewLoading ? "--" : (overview?.suggested_matches ?? 0)}</p>
    </div>
    <div class="rounded-xl border border-[#cfe3f6] bg-[#edf6ff] p-4">
      <p class="text-xs uppercase tracking-wider text-neutral-400">Shortlisted</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{overviewLoading ? "--" : (overview?.shortlisted_matches ?? 0)}</p>
    </div>
    <div class="rounded-xl border border-[#cfe3f6] bg-[#edf6ff] p-4">
      <p class="text-xs uppercase tracking-wider text-neutral-400">Unit / Project</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">
        {overviewLoading ? "--" : `${overview?.unit_matches ?? 0} / ${overview?.project_matches ?? 0}`}
      </p>
    </div>
    <div class="rounded-xl border border-[#cfe3f6] bg-[#edf6ff] p-4">
      <p class="text-xs uppercase tracking-wider text-neutral-400">Avg. Score</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-900">{overviewLoading ? "--" : `${toNumber(overview?.average_score).toFixed(2)}%`}</p>
    </div>
  </section>

  <section class="rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5 space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
      <label class="block">
        <span class="block text-xs font-medium text-neutral-500 mb-1">Lead</span>
        <select
          bind:value={filters.lead_id}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          onchange={handleFilterChange}
        >
          <option value="">All leads</option>
          {#each leads as lead}
            <option value={lead.id}>{lead.full_name}</option>
          {/each}
        </select>
      </label>

      <label class="block">
        <span class="block text-xs font-medium text-neutral-500 mb-1">Candidate Type</span>
        <select
          bind:value={filters.candidate_type}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          onchange={handleFilterChange}
        >
          <option value="">All types</option>
          <option value="unit">Unit</option>
          <option value="project">Project</option>
        </select>
      </label>

      <label class="block">
        <span class="block text-xs font-medium text-neutral-500 mb-1">Status</span>
        <select
          bind:value={filters.status}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          onchange={handleFilterChange}
        >
          <option value="">All statuses</option>
          <option value="suggested">Suggested</option>
          <option value="viewed">Viewed</option>
          <option value="shortlisted">Shortlisted</option>
          <option value="dismissed">Dismissed</option>
          <option value="converted">Converted</option>
        </select>
      </label>

      <label class="block">
        <span class="block text-xs font-medium text-neutral-500 mb-1">Min Score</span>
        <input
          bind:value={filters.min_score}
          type="number"
          min="0"
          max="100"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          oninput={handleFilterChange}
        />
      </label>

      <label class="block">
        <span class="block text-xs font-medium text-neutral-500 mb-1">Active</span>
        <select
          bind:value={filters.is_active}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          onchange={handleFilterChange}
        >
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </label>
    </div>

    <div class="flex items-center justify-end">
      <button
        onclick={refreshMatches}
        disabled={refreshing || !filters.lead_id}
        class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {#if refreshing}Refreshing...{:else}Refresh Lead Matches{/if}
      </button>
    </div>
  </section>

  <section class="rounded-2xl border border-neutral-200 bg-white overflow-hidden">
    <header class="px-5 py-4 border-b border-neutral-200">
      <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Match Results</h2>
    </header>

    {#if matchesLoading}
      <div class="p-6 text-sm text-neutral-500">Loading matches...</div>
    {:else if matches.length === 0}
      <div class="p-8 text-center text-sm text-neutral-500">No matches found for the current filter set.</div>
    {:else}
      <div class="divide-y divide-neutral-200">
        {#each matches as match}
          <article class="p-5 space-y-3">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="space-y-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {candidateBadge[match.candidate_type]}">
                    {match.candidate_type_display}
                  </span>
                  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {statusBadge[match.status]}">
                    {match.status_display}
                  </span>
                </div>
                <p class="text-sm font-semibold text-neutral-900">
                  {match.lead_name} -> {match.unit_number ?? match.project_name ?? match.property_name}
                </p>
                <p class="text-xs text-neutral-500">{match.reason_summary}</p>
              </div>
              <div class="text-right">
                <p class="text-xs uppercase tracking-wider text-neutral-400">Match Score</p>
                <p class="text-2xl font-semibold text-neutral-900">{toNumber(match.match_score).toFixed(2)}%</p>
              </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div class="rounded-lg border border-neutral-200 p-2">
                <p class="text-neutral-400">Budget</p>
                <p class="font-medium text-neutral-800">{match.score_breakdown.budget} / 40</p>
              </div>
              <div class="rounded-lg border border-neutral-200 p-2">
                <p class="text-neutral-400">Location</p>
                <p class="font-medium text-neutral-800">{match.score_breakdown.location} / 25</p>
              </div>
              <div class="rounded-lg border border-neutral-200 p-2">
                <p class="text-neutral-400">Unit Type</p>
                <p class="font-medium text-neutral-800">{match.score_breakdown.unit_type} / 20</p>
              </div>
              <div class="rounded-lg border border-neutral-200 p-2">
                <p class="text-neutral-400">Payment</p>
                <p class="font-medium text-neutral-800">{match.score_breakdown.payment_eligibility} / 15</p>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <button
                onclick={() => updateMatchStatus(match.id, "shortlisted")}
                disabled={updatingMatchId === match.id || match.status === "shortlisted"}
                class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100 disabled:opacity-40"
              >
                Shortlist
              </button>
              <button
                onclick={() => updateMatchStatus(match.id, "dismissed")}
                disabled={updatingMatchId === match.id || match.status === "dismissed"}
                class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-40"
              >
                Dismiss
              </button>
              <button
                onclick={() => updateMatchStatus(match.id, "viewed")}
                disabled={updatingMatchId === match.id || match.status === "viewed"}
                class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100 disabled:opacity-40"
              >
                Mark Viewed
              </button>
            </div>
          </article>
        {/each}
      </div>

      <footer class="px-5 py-4 border-t border-neutral-200 flex items-center justify-between">
        <p class="text-sm text-neutral-500">
          Showing <span class="font-medium text-neutral-900">{matches.length}</span> of
          <span class="font-medium text-neutral-900">{totalCount}</span> matches
        </p>
        <nav class="flex items-center gap-1">
          <button onclick={() => gotoPage(currentPage - 1)} disabled={currentPage <= 1} class="px-3 py-1.5 rounded border border-neutral-200 text-sm disabled:opacity-40">Prev</button>
          {#each pageNumbers as pageNum}
            <button
              onclick={() => gotoPage(pageNum)}
              class="px-3 py-1.5 rounded border text-sm {pageNum === currentPage ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 text-neutral-700'}"
            >
              {pageNum}
            </button>
          {/each}
          <button onclick={() => gotoPage(currentPage + 1)} disabled={currentPage >= totalPages} class="px-3 py-1.5 rounded border border-neutral-200 text-sm disabled:opacity-40">Next</button>
        </nav>
      </footer>
    {/if}
  </section>
</div>

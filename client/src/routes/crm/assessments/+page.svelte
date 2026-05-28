<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { can } from "$lib/permissions";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    FinancialAssessmentDetail,
    FinancialAssessmentListItem,
    LeadListItem,
    PaginatedResponse,
  } from "$lib/types";

  // --- Assessments Table ---
  let assessments = $state<FinancialAssessmentListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let listError = $state<string | null>(null);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let statusFilter = $state("");
  let riskLevelFilter = $state("");
  let mortgageFilter = $state("");

  // --- New Assessment Modal ---
  let showModal = $state(false);
  let savingAssessment = $state(false);
  let selectedLeadId = $state<number | null>(null);
  let availableLeads = $state<LeadListItem[]>([]);
  let leadsLoading = $state(false);
  let leadSearch = $state("");

  // --- Detail Drawer ---
  let showDetailDrawer = $state(false);
  let detailLoading = $state(false);
  let detailError = $state("");
  let selectedAssessmentId = $state<number | null>(null);
  let selectedAssessment = $state<FinancialAssessmentDetail | null>(null);
  let computingScores = $state(false);
  let completingAssessment = $state(false);
  let deletingAssessment = $state(false);

  // --- Derived ---
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const canCreateAssessment = $derived(can("crm.all", "create"));
  const canEditAssessment = $derived(can("crm.all", "edit"));
  const canDeleteAssessment = $derived(can("crm.all", "delete"));

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

  // KPI derivations
  let completedCount = $derived(
    assessments.filter((a) => a.status === "completed").length,
  );
  let highRiskCount = $derived(
    assessments.filter((a) => a.risk_level === "high" || a.risk_level === "critical").length,
  );
  let preQualifiedCount = $derived(
    assessments.filter((a) => a.mortgage_prequalified).length,
  );

  // Filter leads that already have an assessment
  let existingLeadIds = $derived(new Set(assessments.map((a) => a.lead_id)));

  let filteredAvailableLeads = $derived.by(() => {
    let filtered = availableLeads.filter((l) => !existingLeadIds.has(l.id));
    if (leadSearch.trim()) {
      const q = leadSearch.trim().toLowerCase();
      filtered = filtered.filter(
        (l) =>
          l.full_name.toLowerCase().includes(q) ||
          l.email.toLowerCase().includes(q),
      );
    }
    return filtered;
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

  function fmtAmount(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return currency.format(parseFloat(value));
  }

  function formatBudget(min: string | null, max: string | null): string {
    if (!min && !max) return "\u2014";
    const parts: string[] = [];
    if (min) parts.push(currency.format(parseFloat(min)));
    if (max) parts.push(currency.format(parseFloat(max)));
    return parts.join(" \u2013 ");
  }

  function formatPipelineStage(stage: string): string {
    const map: Record<string, string> = {
      inquiry: "Inquiry",
      qualified: "Qualified",
      site_visit: "Site Visit",
      offer_made: "Offer Made",
      reservation: "Reservation",
      spa_issued: "SPA Issued",
      closed: "Closed",
    };
    return map[stage] ?? stage;
  }

  function formatPercent(value: string | number | null | undefined): string {
    if (value === null || value === undefined || value === "") return "\u2014";
    const parsed = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(parsed)) return "\u2014";
    return `${parsed}%`;
  }

  function gaugeOffset(score: number | null): number {
    if (score == null) return 251.2;
    const clamped = Math.max(0, Math.min(100, score));
    return 251.2 - (251.2 * clamped) / 100;
  }

  // --- Data Fetching ---
  async function fetchAssessments() {
    loading = true;
    listError = null;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (riskLevelFilter) params.risk_level = riskLevelFilter;
      if (mortgageFilter) params.mortgage_prequalified = mortgageFilter;

      const res = await api.get<PaginatedResponse<FinancialAssessmentListItem>>(
        "/crm/assessments/",
        params,
      );
      assessments = res.results;
      totalCount = res.count;
    } catch (err) {
      console.error("[crm/assessments]", err);
      assessments = [];
      totalCount = 0;
      listError = err instanceof Error ? err.message : "Could not load assessments.";
    } finally {
      loading = false;
    }
  }

  async function fetchAssessmentDetail(id: number) {
    detailLoading = true;
    detailError = "";
    try {
      selectedAssessment = await api.get<FinancialAssessmentDetail>(`/crm/assessments/${id}/`);
    } catch (err) {
      console.error("[crm/assessments]", err);
      selectedAssessment = null;
      if (err instanceof ApiError && err.status === 404) {
        detailError = "Assessment not found.";
      } else {
        detailError = "Could not load assessment details.";
        toast.error("Error", "Could not load assessment details");
      }
    } finally {
      detailLoading = false;
    }
  }

  async function openDetailDrawer(id: number) {
    selectedAssessmentId = id;
    showDetailDrawer = true;
    await fetchAssessmentDetail(id);
  }

  function closeDetailDrawer() {
    showDetailDrawer = false;
    selectedAssessmentId = null;
    selectedAssessment = null;
    detailError = "";
    if ($page.url.searchParams.has("open")) {
      goto("/crm/assessments", { replaceState: true, noScroll: true, keepFocus: true });
    }
  }

  async function refreshDetailDrawer() {
    if (!selectedAssessmentId) return;
    await Promise.all([fetchAssessmentDetail(selectedAssessmentId), fetchAssessments()]);
  }

  async function computeAssessmentScores() {
    if (!selectedAssessmentId || !canEditAssessment) return;
    computingScores = true;
    try {
      await api.post(`/crm/assessments/${selectedAssessmentId}/compute_scores/`, {});
      toast.success("Scores computed", "Affordability and risk scores have been recalculated");
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/assessments]", err);
      toast.error("Failed to compute scores", "Please try again later");
    } finally {
      computingScores = false;
    }
  }

  async function completeAssessment() {
    if (!selectedAssessmentId || !canEditAssessment) return;
    completingAssessment = true;
    try {
      await api.post(`/crm/assessments/${selectedAssessmentId}/complete/`, {});
      toast.success("Assessment completed", "Assessment has been marked as completed");
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/assessments]", err);
      toast.error("Failed to complete", "Please try again later");
    } finally {
      completingAssessment = false;
    }
  }

  async function deleteAssessment() {
    if (!selectedAssessmentId || !canDeleteAssessment || deletingAssessment) return;
    if (!confirm("Delete this financial assessment? This action cannot be undone.")) return;
    deletingAssessment = true;
    try {
      await api.delete(`/crm/assessments/${selectedAssessmentId}/`);
      toast.success("Assessment deleted", "The financial assessment has been removed.");
      closeDetailDrawer();
      await fetchAssessments();
    } catch (err) {
      console.error("[crm/assessments]", err);
      toast.error("Delete failed", "Could not delete this assessment.");
    } finally {
      deletingAssessment = false;
    }
  }

  async function fetchAvailableLeads() {
    leadsLoading = true;
    try {
      const res = await api.get<PaginatedResponse<LeadListItem>>(
        "/crm/leads/",
        { status: "active", page_size: "100" },
      );
      availableLeads = res.results;
    } catch (err) {
      console.error("[crm/assessments]", err);
      availableLeads = [];
    } finally {
      leadsLoading = false;
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchAssessments();
    }, 300);
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchAssessments();
  }

  function handleRiskLevelChange(value: string) {
    riskLevelFilter = value;
    currentPage = 1;
    fetchAssessments();
  }

  function handleMortgageChange(value: string) {
    mortgageFilter = value;
    currentPage = 1;
    fetchAssessments();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchAssessments();
  }

  function openModal() {
    if (!canCreateAssessment) return;
    selectedLeadId = null;
    leadSearch = "";
    showModal = true;
    fetchAvailableLeads();
  }

  function closeModal() {
    showModal = false;
    selectedLeadId = null;
    leadSearch = "";
  }

  async function handleCreateAssessment(e: Event) {
    e.preventDefault();
    if (!canCreateAssessment) return;
    if (!selectedLeadId) return;

    savingAssessment = true;
    try {
      const result = await api.post<FinancialAssessmentListItem>(
        "/crm/assessments/",
        { lead: selectedLeadId },
      );
      toast.success("Assessment created", `Financial assessment for ${result.lead_name} has been created`);
      closeModal();
      await fetchAssessments();
      void openDetailDrawer(result.id);
    } catch (err) {
      console.error("[crm/assessments]", err);
      if (err instanceof ApiError) {
        const msg = err.fieldErrors?.lead?.[0] || err.fieldErrors?.non_field_errors?.[0] || "Could not create the assessment";
        toast.error("Validation error", msg);
      } else {
        toast.error("Something went wrong", "Could not create the assessment");
      }
    } finally {
      savingAssessment = false;
    }
  }

  // --- Initialize ---
  onMount(() => {
    void fetchAssessments();
  });

  $effect(() => {
    const openParam = $page.url.searchParams.get("open");
    if (!openParam) return;
    const id = Number(openParam);
    if (!Number.isInteger(id) || id <= 0) return;
    if (showDetailDrawer && selectedAssessmentId === id) return;
    void openDetailDrawer(id);
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-neutral-500">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Financial Pre-Assessments</h1>
      <p class="mt-1 text-sm text-neutral-500">Affordability scoring, risk assessment, and mortgage pre-qualification</p>
    </div>
    {#if canCreateAssessment}
      <button
        onclick={openModal}
        class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New Assessment
      </button>
    {/if}
  </div>

  <!-- KPI Strip -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
    <div class="bg-neutral-400 rounded-lg border border-neutral-400 p-5">
      <p class="text-xs font-medium uppercase tracking-wider text-neutral-100">Total Assessments</p>
      <p class="mt-2 text-2xl font-semibold text-white tabular-nums">{totalCount.toLocaleString()}</p>
    </div>
    <div class="bg-neutral-400 rounded-lg border border-neutral-400 p-5">
      <p class="text-xs font-medium uppercase tracking-wider text-neutral-100">Completed</p>
      <p class="mt-2 text-2xl font-semibold text-white tabular-nums">{completedCount.toLocaleString()}</p>
    </div>
    <div class="bg-neutral-400 rounded-lg border border-neutral-400 p-5">
      <p class="text-xs font-medium uppercase tracking-wider text-neutral-100">High Risk</p>
      <p class="mt-2 text-2xl font-semibold text-white tabular-nums">{highRiskCount.toLocaleString()}</p>
    </div>
    <div class="bg-neutral-400 rounded-lg border border-neutral-400 p-5">
      <p class="text-xs font-medium uppercase tracking-wider text-neutral-100">Pre-Qualified</p>
      <p class="mt-2 text-2xl font-semibold text-white tabular-nums">{preQualifiedCount.toLocaleString()}</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Lead name or email..."
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
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="expired">Expired</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Risk Level</span>
        <select
          value={riskLevelFilter}
          onchange={(e) => handleRiskLevelChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Mortgage Pre-Qualified</span>
        <select
          value={mortgageFilter}
          onchange={(e) => handleMortgageChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
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
    {:else if listError}
      <div class="p-6">
        <DataStateBanner
          title="Couldn't load assessments"
          message={listError}
          onretry={fetchAssessments}
        />
      </div>
    {:else if assessments.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z"
            />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No assessments yet</p>
        {#if canCreateAssessment}
          <button
            onclick={openModal}
            class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
          >
            Create your first assessment
          </button>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Lead</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Pipeline Stage</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Status</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Affordability</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Risk</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Mortgage</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Budget Range</th>
              <th class="px-5 py-3.5 text-left text-xs uppercase tracking-wider text-neutral-400 font-medium">Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each assessments as assessment}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openDetailDrawer(assessment.id)}
              >
                <!-- Lead -->
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{assessment.lead_name}</div>
                  <div class="text-xs text-neutral-400 mt-0.5">{assessment.lead_email}</div>
                </td>

                <!-- Pipeline Stage -->
                <td class="px-5 py-4">
                  <StatusBadge status={assessment.lead_pipeline_stage} label={formatPipelineStage(assessment.lead_pipeline_stage)} />
                </td>

                <!-- Status -->
                <td class="px-5 py-4">
                  <StatusBadge status={assessment.status} label={assessment.status_display} />
                </td>

                <!-- Affordability -->
                <td class="px-5 py-4">
                  {#if assessment.affordability_score !== null}
                    <div class="flex items-center gap-2">
                      <div class="w-16 h-2 bg-neutral-100 rounded-full overflow-hidden">
                        <div
                          class="h-full rounded-full {assessment.affordability_score >= 70 ? 'bg-neutral-900' : assessment.affordability_score >= 40 ? 'bg-neutral-500' : 'bg-neutral-300'}"
                          style="width: {assessment.affordability_score}%;"
                        ></div>
                      </div>
                      <span class="text-xs font-medium text-neutral-700 tabular-nums">{assessment.affordability_score}</span>
                    </div>
                  {:else}
                    <span class="text-sm text-neutral-300">&mdash;</span>
                  {/if}
                </td>

                <!-- Risk -->
                <td class="px-5 py-4">
                  {#if assessment.risk_level}
                    <StatusBadge status={assessment.risk_level} label={assessment.risk_level_display} />
                  {:else}
                    <span class="text-sm text-neutral-300">&mdash;</span>
                  {/if}
                </td>

                <!-- Mortgage -->
                <td class="px-5 py-4">
                  {#if assessment.mortgage_prequalified}
                    <div class="flex items-center gap-1.5">
                      <svg class="w-4 h-4 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                      {#if assessment.mortgage_prequalification_amount}
                        <span class="text-xs text-neutral-500 tabular-nums">{currency.format(parseFloat(assessment.mortgage_prequalification_amount))}</span>
                      {/if}
                    </div>
                  {:else}
                    <span class="text-sm text-neutral-300">&mdash;</span>
                  {/if}
                </td>

                <!-- Budget Range -->
                <td class="px-5 py-4 text-sm text-neutral-600 tabular-nums">
                  {formatBudget(assessment.lead_budget_min, assessment.lead_budget_max)}
                </td>

                <!-- Date -->
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(assessment.assessment_date)}
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
<!-- DRAWER: Assessment Detail                    -->
<!-- ============================================ -->
{#if showDetailDrawer}
  <button
    class="fixed inset-0 z-998 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeDetailDrawer}
    tabindex="-1"
    aria-label="Close panel"
  ></button>

  <aside class="fixed inset-y-0 right-0 z-999 w-full max-w-5xl flex flex-col bg-white shadow-2xl slide-over-enter">
    <div class="shrink-0 border-b border-neutral-100 px-6 py-4">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <h2 class="truncate text-xl font-semibold text-neutral-900">
            {selectedAssessment?.lead_name || "Assessment Detail"}
          </h2>
          {#if selectedAssessment}
            <div class="mt-2 flex items-center gap-2">
              <StatusBadge status={selectedAssessment.lead_pipeline_stage} label={formatPipelineStage(selectedAssessment.lead_pipeline_stage)} />
              <StatusBadge status={selectedAssessment.status} label={selectedAssessment.status_display} />
              {#if selectedAssessment.risk_level}
                <StatusBadge status={selectedAssessment.risk_level} label={selectedAssessment.risk_level_display} />
              {/if}
            </div>
          {/if}
        </div>

        <div class="flex items-center gap-2">
          {#if canEditAssessment}
            <button
              onclick={computeAssessmentScores}
              disabled={computingScores}
              class="px-3 py-2 border border-black bg-black text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {computingScores ? "Computing..." : "Compute"}
            </button>
            {#if selectedAssessment && selectedAssessment.status !== "completed"}
              <button
                onclick={completeAssessment}
                disabled={completingAssessment}
                class="px-3 py-2 border border-black bg-black text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
              >
                {completingAssessment ? "Completing..." : "Complete"}
              </button>
            {/if}
          {/if}
          {#if canDeleteAssessment}
            <button
              onclick={deleteAssessment}
              disabled={deletingAssessment}
              class="px-3 py-2 border border-red-600 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {deletingAssessment ? "Deleting..." : "Delete"}
            </button>
          {/if}
          <button
            onclick={closeDetailDrawer}
            class="p-1.5 rounded-lg border border-black bg-black text-white hover:bg-neutral-800 transition-colors"
            aria-label="Close"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      {#if detailLoading}
        <div class="space-y-4 animate-pulse">
          <div class="h-12 rounded-lg bg-neutral-100"></div>
          <div class="h-48 rounded-lg bg-neutral-100"></div>
          <div class="h-48 rounded-lg bg-neutral-100"></div>
          <div class="h-48 rounded-lg bg-neutral-100"></div>
        </div>
      {:else if detailError || !selectedAssessment}
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-5">
          <p class="text-sm text-neutral-600">{detailError || "Could not load assessment details."}</p>
        </div>
      {:else}
        <div class="space-y-5">
          <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <div class="bg-white rounded-xl border border-neutral-200 p-6 flex flex-col items-center">
              <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-4 self-start">Affordability Score</h3>
              <div class="relative w-28 h-28">
                <svg class="w-28 h-28 -rotate-90" viewBox="0 0 88 88">
                  <circle cx="44" cy="44" r="40" fill="none" stroke-width="6" class="stroke-neutral-100" />
                  <circle
                    cx="44" cy="44" r="40" fill="none" stroke-width="6"
                    class="stroke-neutral-900"
                    stroke-linecap="round"
                    stroke-dasharray="251.2"
                    stroke-dashoffset={gaugeOffset(selectedAssessment.affordability_score)}
                  />
                </svg>
                <div class="absolute inset-0 flex items-center justify-center">
                  {#if selectedAssessment.affordability_score != null}
                    <span class="text-2xl font-bold text-neutral-900 tabular-nums">{selectedAssessment.affordability_score}</span>
                  {:else}
                    <span class="text-xs text-neutral-400">N/A</span>
                  {/if}
                </div>
              </div>
              <div class="mt-3 text-center">
                {#if selectedAssessment.max_affordable_price}
                  <p class="text-xs text-neutral-400">Max Affordable Price</p>
                  <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.max_affordable_price)}</p>
                {:else}
                  <p class="text-xs text-neutral-400 mt-1">Not computed</p>
                {/if}
              </div>
            </div>

            <div class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-4">Risk Assessment</h3>
              <div class="flex flex-col items-center">
                {#if selectedAssessment.risk_level}
                  <StatusBadge status={selectedAssessment.risk_level} label={selectedAssessment.risk_level_display} size="md" />
                  {#if selectedAssessment.risk_score != null}
                    <p class="text-sm text-neutral-500 mt-3 tabular-nums">Score: {selectedAssessment.risk_score}/100</p>
                  {/if}
                {:else}
                  <span class="inline-flex items-center px-4 py-2 rounded-lg text-sm font-medium bg-neutral-100 text-neutral-400">
                    Not Assessed
                  </span>
                {/if}
              </div>
              {#if selectedAssessment.risk_factors.length > 0}
                <ul class="mt-4 space-y-1">
                  {#each selectedAssessment.risk_factors as factor}
                    <li class="flex items-start gap-2 text-xs text-neutral-500">
                      <span class="w-1 h-1 rounded-full bg-neutral-400 mt-1.5 shrink-0"></span>
                      {factor}
                    </li>
                  {/each}
                </ul>
              {/if}
            </div>

            <div class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-4">Mortgage Status</h3>
              <div class="flex items-center gap-2 mb-4">
                {#if selectedAssessment.mortgage_prequalified}
                  <svg class="w-5 h-5 text-neutral-900" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                  </svg>
                  <span class="text-sm font-medium text-neutral-900">Pre-Qualified</span>
                {:else}
                  <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                  </svg>
                  <span class="text-sm font-medium text-neutral-400">Not Pre-Qualified</span>
                {/if}
              </div>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between"><span class="text-neutral-400">Amount</span><span class="text-neutral-900 font-medium tabular-nums">{fmtAmount(selectedAssessment.mortgage_prequalification_amount)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Provider</span><span class="text-neutral-900">{selectedAssessment.mortgage_provider || "\u2014"}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Tenure</span><span class="text-neutral-900 tabular-nums">{selectedAssessment.mortgage_tenure_months ? `${selectedAssessment.mortgage_tenure_months} months` : "\u2014"}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Interest Rate</span><span class="text-neutral-900 tabular-nums">{formatPercent(selectedAssessment.mortgage_interest_rate)}</span></div>
              </div>
            </div>

            <div class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-4">Recommendation</h3>
              {#if selectedAssessment.recommended_plan}
                <div class="space-y-3">
                  <div>
                    <p class="text-xs text-neutral-400">Recommended Plan</p>
                    <p class="text-sm font-semibold text-neutral-900">{selectedAssessment.recommended_plan_display}</p>
                  </div>
                  <div>
                    <p class="text-xs text-neutral-400">Down Payment</p>
                    <p class="text-sm font-semibold text-neutral-900 tabular-nums">{formatPercent(selectedAssessment.recommended_down_payment_pct)}</p>
                  </div>
                  <div>
                    <p class="text-xs text-neutral-400">Monthly Payment</p>
                    <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.recommended_monthly_payment)}</p>
                  </div>
                </div>
              {:else}
                <p class="text-xs text-neutral-400">Run scoring to generate recommendation</p>
              {/if}
            </div>
          </div>

          <section class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Lead Snapshot</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3 text-sm">
              <div class="flex justify-between"><span class="text-neutral-400">Lead Name</span><span class="text-neutral-900">{selectedAssessment.lead_name}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Email</span><span class="text-neutral-900">{selectedAssessment.lead_email || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Phone</span><span class="text-neutral-900">{selectedAssessment.lead_phone || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Company</span><span class="text-neutral-900">{selectedAssessment.lead_company || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Pipeline Stage</span><span class="text-neutral-900">{selectedAssessment.lead_pipeline_stage_display}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Payment Capability</span><span class="text-neutral-900 capitalize">{selectedAssessment.lead_payment_capability?.replace(/_/g, " ") || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Budget Min</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.lead_budget_min)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Budget Max</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.lead_budget_max)}</span></div>
            </div>
          </section>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <section class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Financial Profile</h3>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between"><span class="text-neutral-400">Monthly Income</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.monthly_income)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Monthly Expenses</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.monthly_expenses)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Existing Liabilities</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.existing_liabilities)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Disposable Income</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.disposable_income)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Liquid Assets</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.liquid_assets)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Net Worth</span><span class="text-neutral-900 tabular-nums">{fmtAmount(selectedAssessment.net_worth)}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Debt-to-Income Ratio</span><span class="text-neutral-900 tabular-nums">{formatPercent(selectedAssessment.debt_to_income_ratio)}</span></div>
              </div>
            </section>

            <section class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Employment</h3>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between"><span class="text-neutral-400">Status</span><span class="text-neutral-900">{selectedAssessment.employment_status_display || "\u2014"}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Employer</span><span class="text-neutral-900">{selectedAssessment.employer_name || "\u2014"}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Duration</span><span class="text-neutral-900 tabular-nums">{selectedAssessment.employment_duration_months != null ? `${selectedAssessment.employment_duration_months} months` : "\u2014"}</span></div>
                <div>
                  <p class="text-neutral-400 mb-1">Mortgage Notes</p>
                  <p class="text-neutral-700 whitespace-pre-line">{selectedAssessment.mortgage_notes || "\u2014"}</p>
                </div>
              </div>
            </section>
          </div>

          <section class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Assessment Notes</h3>
            <p class="text-sm text-neutral-700 whitespace-pre-line">{selectedAssessment.notes || "No notes recorded."}</p>
          </section>

          <section class="bg-white rounded-xl border border-neutral-200 p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Payment Scenarios</h3>
              <span class="text-xs text-neutral-400">{selectedAssessment.scenarios.length} scenario(s)</span>
            </div>

            {#if selectedAssessment.scenarios.length === 0}
              <p class="text-sm text-neutral-400">No payment scenarios yet.</p>
            {:else}
              <div class="space-y-3">
                {#each selectedAssessment.scenarios as scenario}
                  <div class="rounded-xl border border-neutral-200 p-4">
                    <div class="flex items-center gap-2 flex-wrap mb-3">
                      <span class="text-sm font-semibold text-neutral-900">{scenario.label}</span>
                      <StatusBadge status={scenario.plan_type} label={scenario.plan_type_display} />
                      {#if scenario.is_recommended}
                        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-neutral-900 text-white">
                          Recommended
                        </span>
                      {/if}
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium {scenario.is_affordable ? 'bg-neutral-100 text-neutral-700' : 'bg-neutral-200 text-neutral-500'}">
                        {scenario.is_affordable ? "Affordable" : "Not Affordable"}
                      </span>
                    </div>

                    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-x-6 gap-y-3">
                      <div>
                        <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">Property Price</p>
                        <p class="text-sm text-neutral-900 tabular-nums mt-0.5">{fmtAmount(scenario.property_price)}</p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">Down Payment</p>
                        <p class="text-sm text-neutral-900 tabular-nums mt-0.5">
                          {scenario.down_payment_pct}% <span class="text-neutral-500">({fmtAmount(scenario.down_payment_amount)})</span>
                        </p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">Financed</p>
                        <p class="text-sm text-neutral-900 tabular-nums mt-0.5">{fmtAmount(scenario.financed_amount)}</p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">Interest / Tenure</p>
                        <p class="text-sm text-neutral-900 tabular-nums mt-0.5">
                          {scenario.interest_rate ?? "\u2014"}% <span class="text-neutral-400">/</span> {scenario.tenure_months}mo
                        </p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">Monthly Payment</p>
                        <p class="text-sm font-bold text-neutral-900 tabular-nums mt-0.5">{fmtAmount(scenario.monthly_payment)}</p>
                      </div>
                      <div>
                        <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">Total Cost</p>
                        <p class="text-sm text-neutral-900 tabular-nums mt-0.5">{fmtAmount(scenario.total_cost)}</p>
                      </div>
                    </div>

                    {#if scenario.notes}
                      <p class="text-xs text-neutral-400 mt-3 whitespace-pre-line">{scenario.notes}</p>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </section>

          <section class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Metadata</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 text-sm">
              <div class="flex justify-between"><span class="text-neutral-400">Assessed By</span><span class="text-neutral-900">{selectedAssessment.assessed_by_name || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Assessment Date</span><span class="text-neutral-900">{formatDate(selectedAssessment.assessment_date)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Created At</span><span class="text-neutral-900">{formatDate(selectedAssessment.created_at)}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Updated At</span><span class="text-neutral-900">{formatDate(selectedAssessment.updated_at)}</span></div>
            </div>
          </section>
        </div>
      {/if}
    </div>
  </aside>
{/if}

<!-- ============================================ -->
<!-- MODAL: New Assessment                         -->
<!-- ============================================ -->
{#if showModal && canCreateAssessment}
  <!-- Backdrop -->
  <button
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeModal}
    tabindex="-1"
    aria-label="Close modal"
  ></button>

  <!-- Modal Panel -->
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-md modal-enter" role="dialog" aria-modal="true" aria-label="New assessment">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100">
        <h2 class="text-lg font-semibold text-neutral-900">New Assessment</h2>
        <button
          onclick={closeModal}
          class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <form id="create-assessment-form" onsubmit={handleCreateAssessment} class="px-6 py-5">
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Select Lead</span>

          <!-- Lead search input -->
          <input
            type="text"
            placeholder="Search active leads..."
            value={leadSearch}
            oninput={(e) => { leadSearch = (e.target as HTMLInputElement).value; }}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent mb-2"
          />

          <!-- Lead list -->
          <div class="border border-neutral-200 rounded-lg max-h-56 overflow-y-auto">
            {#if leadsLoading}
              <div class="flex items-center justify-center py-8">
                <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
              </div>
            {:else if filteredAvailableLeads.length === 0}
              <div class="py-6 text-center text-sm text-neutral-400">
                {availableLeads.length === 0 ? "No active leads found" : "No matching leads without an existing assessment"}
              </div>
            {:else}
              {#each filteredAvailableLeads as lead}
                <button
                  type="button"
                  onclick={() => { selectedLeadId = lead.id; }}
                  class="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-neutral-50 transition-colors border-b border-neutral-100 last:border-b-0 {selectedLeadId === lead.id ? 'bg-neutral-50 ring-1 ring-inset ring-neutral-900' : ''}"
                >
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-neutral-900 truncate">{lead.full_name}</div>
                    <div class="text-xs text-neutral-400 truncate">{lead.email}</div>
                  </div>
                  {#if selectedLeadId === lead.id}
                    <svg class="w-4 h-4 text-neutral-900 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                  {/if}
                </button>
              {/each}
            {/if}
          </div>
        </label>
      </form>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100">
        <button
          type="button"
          onclick={closeModal}
          class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="create-assessment-form"
          disabled={savingAssessment || !selectedLeadId}
          class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {savingAssessment ? "Creating..." : "Create Assessment"}
        </button>
      </div>
    </div>
  </div>
{/if}

<svelte:window
  onkeydown={(e) => {
    if (e.key !== "Escape") return;
    if (showDetailDrawer) {
      closeDetailDrawer();
      return;
    }
    if (showModal) closeModal();
  }}
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

  .modal-enter {
    animation: modal-scale-in 0.2s ease-out;
  }

  @keyframes modal-scale-in {
    from {
      opacity: 0;
      transform: scale(0.95);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }
</style>

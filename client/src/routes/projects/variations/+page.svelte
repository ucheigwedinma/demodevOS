<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    PaginatedResponse,
    ProjectListItem,
    ProjectVariationOrder,
    ProjectVariationOrderStatus,
  } from "$lib/types";
  import NewVariationDrawer from "./NewVariationDrawer.svelte";

  const HIGH_VALUE_THRESHOLD = 100000;
  const PENDING_STATUSES: ProjectVariationOrderStatus[] = ["submitted", "under_review"];

  let loading = $state(true);

  let projects = $state<ProjectListItem[]>([]);
  let variationRows = $state<ProjectVariationOrder[]>([]);

  let showCreateDrawer = $state(false);

  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let statusFilter = $state<"" | ProjectVariationOrderStatus>("");
  let riskFilter = $state<"" | "low" | "medium" | "high" | "critical">("");
  let highValueOnly = $state(false);

  let currentPage = $state(1);
  let pageSize = $state(12);
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let fetchToken = 0;

  function toAmount(value: string | number | null | undefined): number {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtCurrency(value: string | number | null | undefined): string {
    return currency.formatCompact(toAmount(value));
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "--";
    return parsed.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function isPending(status: ProjectVariationOrderStatus): boolean {
    return PENDING_STATUSES.includes(status);
  }

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (firstField) return firstField;
      if (error.status === 403) return "You do not have permission for this action.";
    }
    return fallback;
  }

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 50,
  ): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;

    while (page <= maxPages) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        ...params,
        page: String(page),
      });

      if (Array.isArray(payload)) {
        rows.push(...payload);
        break;
      }

      rows.push(...(payload.results ?? []));
      if (!payload.next || payload.results.length === 0) break;
      page += 1;
    }

    return rows;
  }

  async function loadVariations() {
    loading = true;
    const token = ++fetchToken;

    try {
      const [projectRows, variationData] = await Promise.all([
        fetchAllPages<ProjectListItem>("/projects/", {
          ordering: "name",
          page_size: "200",
        }),
        fetchAllPages<ProjectVariationOrder>("/projects/variations/", {
          ordering: "-created_at",
          page_size: "200",
        }),
      ]);

      if (token !== fetchToken) return;

      projects = projectRows;
      variationRows = variationData;
    } catch (error) {
      if (token !== fetchToken) return;
      variationRows = [];
      projects = [];
      toast.error("Load failed", parseApiError(error, "Could not load variation orders."));
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    projectFilter = "";
    statusFilter = "";
    riskFilter = "";
    highValueOnly = false;
    currentPage = 1;
  }

  function onSearchInput(event: Event) {
    searchInput = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim().toLowerCase();
      currentPage = 1;
    }, 250);
  }

  const projectOptions = $derived.by(() => {
    const map = new Map<number, string>();
    for (const row of variationRows) {
      if (row.project && row.project_name) map.set(row.project, row.project_name);
    }
    return [...map.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => a.name.localeCompare(b.name));
  });

  const filteredRows = $derived.by(() => {
    return variationRows.filter((row) => {
      if (projectFilter && String(row.project ?? "") !== projectFilter) return false;
      if (statusFilter && row.status !== statusFilter) return false;
      if (riskFilter && row.project_risk_rating !== riskFilter) return false;
      if (highValueOnly && toAmount(row.contract_value) < HIGH_VALUE_THRESHOLD) return false;

      if (!searchQuery) return true;
      const haystack = `${row.variation_number} ${row.title} ${row.project_name ?? ""} ${row.change_summary}`.toLowerCase();
      return haystack.includes(searchQuery);
    });
  });

  const totalPages = $derived(Math.max(1, Math.ceil(filteredRows.length / pageSize)));
  const pageRows = $derived.by(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  });

  const startRow = $derived(filteredRows.length === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endRow = $derived(Math.min(currentPage * pageSize, filteredRows.length));

  const kpis = $derived.by(() => {
    const total = variationRows.length;
    const pending = variationRows.filter((row) => isPending(row.status)).length;
    const highValuePending = variationRows.filter(
      (row) => isPending(row.status) && toAmount(row.contract_value) >= HIGH_VALUE_THRESHOLD,
    ).length;
    const approvedValue = variationRows
      .filter((row) => row.status === "approved")
      .reduce((sum, row) => sum + toAmount(row.contract_value), 0);
    const pendingValue = variationRows
      .filter((row) => isPending(row.status))
      .reduce((sum, row) => sum + toAmount(row.contract_value), 0);
    const projectsImpacted = new Set(
      variationRows
        .map((row) => row.project)
        .filter((value): value is number => typeof value === "number"),
    ).size;

    return {
      total,
      pending,
      highValuePending,
      approvedValue,
      pendingValue,
      projectsImpacted,
    };
  });

  $effect(() => {
    void totalPages;
    if (currentPage > totalPages) currentPage = totalPages;
  });

  $effect(() => {
    void projectFilter;
    void statusFilter;
    void riskFilter;
    void highValueOnly;
    void searchQuery;
    currentPage = 1;
  });

  $effect(() => {
    void loadVariations();
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Variations</h1>
      <p class="mt-1 text-sm text-neutral-500">Register change orders, track pending approvals, and monitor value exposure.</p>
    </div>
    <div class="flex items-center gap-2">
      <button
        onclick={() => (showCreateDrawer = true)}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
      >
        + New Variation Order
      </button>
      <button
        onclick={() => loadVariations()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>
  </div>

  <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
    <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-600">Total Variations</p>
      <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{kpis.total}</p>
    </div>
    <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Pending Approval</p>
      <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{kpis.pending}</p>
    </div>
    <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">High-Value Pending</p>
      <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{kpis.highValuePending}</p>
    </div>
    <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Approved Value</p>
      <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{fmtCurrency(kpis.approvedValue)}</p>
    </div>
    <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Pending Value</p>
      <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{fmtCurrency(kpis.pendingValue)}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Projects Impacted</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{kpis.projectsImpacted}</p>
    </div>
  </div>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4 sm:p-5">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <input
          type="text"
          value={searchInput}
          oninput={onSearchInput}
          placeholder="Search number, title, project..."
          class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />

        <select
          bind:value={projectFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Projects</option>
          {#each projectOptions as option}
            <option value={String(option.id)}>{option.name}</option>
          {/each}
        </select>

        <select
          bind:value={statusFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="submitted">Submitted</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="superseded">Superseded</option>
          <option value="archived">Archived</option>
        </select>

        <select
          bind:value={riskFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Risk Ratings</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </div>

      <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
        <label class="inline-flex items-center gap-2 text-xs font-medium text-neutral-600">
          <input
            type="checkbox"
            bind:checked={highValueOnly}
            class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
          />
          High-value only (>= {fmtCurrency(HIGH_VALUE_THRESHOLD)})
        </label>
        <button
          onclick={resetFilters}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
        >
          Reset filters
        </button>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredRows.length === 0}
      <div class="px-6 py-14 text-center">
        <p class="text-sm text-neutral-500">No variation orders match the current filters.</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[980px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Variation Order</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Contract Value</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Risk Rating</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Requested</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each pageRows as row}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3">
                  <p class="text-sm font-semibold text-neutral-900">{row.variation_number}</p>
                  <p class="mt-0.5 text-xs text-neutral-500 max-w-[320px] truncate">{row.title}</p>
                </td>
                <td class="px-4 py-3">
                  <button
                    onclick={() => goto(`/projects/${row.project}`)}
                    class="text-sm font-medium text-neutral-700 hover:text-neutral-900"
                  >
                    {row.project_name}
                  </button>
                </td>
                <td class="px-4 py-3">
                  <StatusBadge status={row.status} />
                </td>
                <td class="px-4 py-3 text-right text-sm font-semibold tabular-nums text-neutral-900">
                  {fmtCurrency(row.contract_value)}
                </td>
                <td class="px-4 py-3">
                  <StatusBadge status={row.project_risk_rating} />
                </td>
                <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(row.requested_date)}</td>
                <td class="px-4 py-3 text-right">
                  {#if row.related_document}
                    <button
                      onclick={() => goto(`/documents/${row.related_document}`)}
                      class="text-xs font-medium text-neutral-600 hover:text-neutral-900"
                    >
                      Open Doc
                    </button>
                  {:else}
                    <span class="text-xs text-neutral-400">No Doc Link</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-4 py-3">
        <p class="text-xs text-neutral-500">
          Showing <span class="font-semibold text-neutral-700">{startRow}</span>-
          <span class="font-semibold text-neutral-700">{endRow}</span> of
          <span class="font-semibold text-neutral-700">{filteredRows.length}</span>
        </p>
        <div class="flex items-center gap-2">
          <button
            onclick={() => (currentPage = Math.max(1, currentPage - 1))}
            disabled={currentPage <= 1}
            class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>
          <span class="text-xs font-medium text-neutral-600">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
            disabled={currentPage >= totalPages}
            class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  </section>
</div>

<NewVariationDrawer
  open={showCreateDrawer}
  {projects}
  onclose={() => (showCreateDrawer = false)}
  onsaved={() => loadVariations()}
/>

<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { canCreateRepositoryDocument } from "$lib/permissions";
  import AddDocumentModal from "$lib/components/documents/AddDocumentModal.svelte";
  import DocumentRecordsTable from "$lib/components/documents/DocumentRecordsTable.svelte";
  import type { PaginatedResponse, ProjectListItem } from "$lib/types";

  const passthroughFilters = [
    "land",
    "unit",
    "vendor",
    "client",
    "business_unit_division",
    "business_unit_department",
    "project_risk_rating",
    "contract_value_min",
    "contract_value_max",
    "created_from",
    "created_to",
  ] as const;

  let searchQuery = $state("");
  let statusFilter = $state("");
  let categoryFilter = $state("");
  let projectFilter = $state("");
  let availableProjects = $state<ProjectListItem[]>([]);
  let showAddDocumentModal = $state(false);
  let repositoryRefreshKey = $state(0);
  const canAddRepositoryDocument = $derived(canCreateRepositoryDocument());

  $effect(() => {
    searchQuery = $page.url.searchParams.get("search") ?? "";
    statusFilter = $page.url.searchParams.get("status") ?? "";
    categoryFilter = $page.url.searchParams.get("category") ?? "";
    projectFilter = $page.url.searchParams.get("project") ?? "";
  });

  const repositoryQuery = $derived.by(() => {
    const query: Record<string, string> = {};
    if (searchQuery.trim()) query.search = searchQuery.trim();
    if (statusFilter) query.status = statusFilter;
    if (categoryFilter.trim()) query.category = categoryFilter.trim();
    if (projectFilter) query.project = projectFilter;

    for (const key of passthroughFilters) {
      const value = $page.url.searchParams.get(key);
      if (value) query[key] = value;
    }

    return query;
  });

  async function loadProjects() {
    try {
      const projectsRes = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
        page_size: "200",
        ordering: "name",
      });
      availableProjects = projectsRes.results;
    } catch {
      availableProjects = [];
    }
  }

  $effect(() => {
    loadProjects();
  });

  function handleDocumentCreated() {
    repositoryRefreshKey += 1;
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Document Repository</h1>
      <p class="mt-1 text-sm text-neutral-500">Structured controlled register with contextual and governance filters.</p>
    </div>
    <div class="flex items-center gap-2">
      {#if canAddRepositoryDocument}
        <button
          onclick={() => (showAddDocumentModal = true)}
          class="inline-flex items-center rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
        >
          + Add Document
        </button>
      {/if}
      <a
        href="/documents/dashboard"
        class="inline-flex items-center rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
      >
        Open Dashboard
      </a>
    </div>
  </div>

  <div class="bg-white rounded-xl border border-neutral-200 p-4 grid md:grid-cols-4 gap-3">
    <input
      type="text"
      bind:value={searchQuery}
      placeholder="Search by number or title"
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    />
    <select
      bind:value={statusFilter}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All statuses</option>
      <option value="draft">Draft</option>
      <option value="submitted">Submitted</option>
      <option value="under_review">Under Review</option>
      <option value="approved">Approved</option>
      <option value="rejected">Rejected</option>
      <option value="superseded">Superseded</option>
      <option value="archived">Archived</option>
    </select>
    <input
      type="text"
      bind:value={categoryFilter}
      placeholder="Category code (e.g. REG)"
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    />
    <select
      bind:value={projectFilter}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All projects</option>
      {#each availableProjects as project}
        <option value={String(project.id)}>{project.name}</option>
      {/each}
    </select>
  </div>

  <DocumentRecordsTable
    title="Repository Browser"
    subtitle="Controlled document list with contextual filtering"
    query={repositoryQuery}
    refreshKey={repositoryRefreshKey}
    pageSize={18}
    emptyMessage="No records match your current filter set."
    showHeader={true}
    showViewAll={false}
  />
</div>

{#if canAddRepositoryDocument}
  <AddDocumentModal
    open={showAddDocumentModal}
    onclose={() => (showAddDocumentModal = false)}
    oncreated={handleDocumentCreated}
  />
{/if}

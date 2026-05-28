<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    ServiceAccountItem,
    ServiceAccountOverview,
    ServiceAccountListResponse,
  } from "$lib/types";

  let accounts = $state<ServiceAccountItem[]>([]);
  let totalCount = $state(0);
  let overview = $state<ServiceAccountOverview>({ total: 0, active: 0, suspended: 0, revoked: 0 });
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let search = $state("");
  let statusFilter = $state("");
  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let startItem = $derived((currentPage - 1) * pageSize + 1);
  let endItem = $derived(Math.min(currentPage * pageSize, totalCount));

  // Create modal
  let showCreateModal = $state(false);
  let createName = $state("");
  let createDescription = $state("");
  let creating = $state(false);

  // Key result modal
  let showKeyModal = $state(false);
  let newKeyValue = $state("");
  let newKeyPrefix = $state("");

  // Delete confirmation
  let deletingId = $state<number | null>(null);

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const SERVICE_ACCOUNT_SAMPLES = [
    { name: "billing-sync", description: "Service account for nightly billing reconciliation between Stripe and the GL." },
    { name: "ci-deploy-bot", description: "GitHub Actions deployment bot — runs migrations and clears caches on staging/prod." },
    { name: "report-exporter", description: "Pulls scheduled report data and pushes to the customer's S3 bucket every morning." },
  ];
  let serviceAccountDevIdx = 0;
  function devFillServiceAccount() {
    const s = SERVICE_ACCOUNT_SAMPLES[serviceAccountDevIdx % SERVICE_ACCOUNT_SAMPLES.length];
    serviceAccountDevIdx++;
    createName = s.name;
    createDescription = s.description;
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "—";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function formatRelative(dateStr: string | null): string {
    if (!dateStr) return "Never";
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateStr);
  }

  async function fetchAccounts() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;

      const res = await api.get<ServiceAccountListResponse>("/iam/service-accounts/", params);
      accounts = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      accounts = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchAccounts();
    }, 300);
  }

  function handleFilterChange() {
    currentPage = 1;
    fetchAccounts();
  }

  function handleFilterReset() {
    search = "";
    statusFilter = "";
    currentPage = 1;
    fetchAccounts();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchAccounts();
  }

  async function handleCreate() {
    if (!createName.trim()) return;
    creating = true;
    try {
      await api.post("/iam/service-accounts/", {
        name: createName.trim(),
        description: createDescription.trim(),
      });
      showCreateModal = false;
      createName = "";
      createDescription = "";
      fetchAccounts();
    } finally {
      creating = false;
    }
  }

  async function handleGenerateKey(accountId: number) {
    try {
      const res = await api.post<{ key: string; prefix: string }>(
        `/iam/service-accounts/${accountId}/keys/`,
        { label: "Default" },
      );
      newKeyValue = res.key;
      newKeyPrefix = res.prefix;
      showKeyModal = true;
      fetchAccounts();
    } catch {
      // error handling
    }
  }

  async function handleDelete(accountId: number) {
    deletingId = accountId;
    try {
      await api.delete(`/iam/service-accounts/${accountId}/`);
      fetchAccounts();
    } finally {
      deletingId = null;
    }
  }

  async function handleStatusChange(accountId: number, newStatus: string) {
    try {
      await api.patch(`/iam/service-accounts/${accountId}/`, { status: newStatus });
      fetchAccounts();
    } catch {
      // error handling
    }
  }

  let hasFilters = $derived(!!search || !!statusFilter);

  $effect(() => {
    fetchAccounts();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Service Accounts</h1>
      <p class="mt-1 text-sm text-neutral-500">Manage non-human system and API accounts.</p>
    </div>
    <button
      onclick={() => (showCreateModal = true)}
      class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Service Account
    </button>
  </div>

  <!-- Overview Cards -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total</p>
      <p class="mt-2 text-2xl font-bold text-neutral-900">{overview.total}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Active</p>
      <p class="mt-2 text-2xl font-bold text-emerald-700">{overview.active}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Suspended</p>
      <p class="mt-2 text-2xl font-bold text-amber-700">{overview.suspended}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Revoked</p>
      <p class="mt-2 text-2xl font-bold text-red-700">{overview.revoked}</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="flex flex-wrap items-end gap-4">
      <div class="flex-1 min-w-[200px]">
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="sa-search">Search</label>
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            id="sa-search"
            type="text"
            class="w-full rounded-lg border border-neutral-300 pl-9 pr-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
            placeholder="Search by name or description..."
            value={search}
            oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          />
        </div>
      </div>

      <div class="w-40">
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="sa-status-filter">Status</label>
        <select
          id="sa-status-filter"
          bind:value={statusFilter}
          onchange={handleFilterChange}
          class="w-full appearance-none rounded-lg border border-neutral-300 px-3.5 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        >
          <option value="">All</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="revoked">Revoked</option>
        </select>
      </div>

      {#if hasFilters}
        <button
          onclick={handleFilterReset}
          class="text-sm font-medium text-neutral-500 hover:text-neutral-700 transition-colors pb-0.5"
        >
          Reset
        </button>
      {/if}
    </div>
  </div>

  <!-- Table -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if accounts.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-300 mb-3">
          <svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Zm-3 6h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" />
          </svg>
        </div>
        <p class="text-sm text-neutral-500">No service accounts found</p>
        {#if hasFilters}
          <button onclick={handleFilterReset} class="mt-2 text-sm font-medium text-neutral-900 hover:underline">
            Clear filters
          </button>
        {:else}
          <button onclick={() => (showCreateModal = true)} class="mt-2 text-sm font-medium text-neutral-900 hover:underline">
            Create your first service account
          </button>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Owner</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Active Keys</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Created</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each accounts as acct}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4">
                  <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-neutral-100 flex items-center justify-center">
                      <svg class="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Zm-3 6h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" />
                      </svg>
                    </div>
                    <div>
                      <div class="text-sm font-medium text-neutral-900">{acct.name}</div>
                      {#if acct.description}
                        <div class="text-xs text-neutral-400 mt-0.5 max-w-xs truncate">{acct.description}</div>
                      {/if}
                    </div>
                  </div>
                </td>
                <td class="px-5 py-4 text-sm text-neutral-600">{acct.owner_name || "—"}</td>
                <td class="px-5 py-4">
                  <StatusBadge status={acct.status} label={acct.status_display} />
                </td>
                <td class="px-5 py-4">
                  <span class="text-sm text-neutral-600">{acct.key_count}</span>
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">{formatRelative(acct.created_at)}</td>
                <td class="px-5 py-4">
                  <div class="flex items-center justify-end gap-1">
                    {#if acct.status === "active"}
                      <button
                        onclick={() => handleGenerateKey(acct.id)}
                        title="Generate API key"
                        class="p-1.5 rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
                        </svg>
                      </button>
                      <button
                        onclick={() => handleStatusChange(acct.id, "suspended")}
                        title="Suspend"
                        class="p-1.5 rounded-lg text-neutral-400 hover:bg-amber-50 hover:text-amber-700 transition-colors"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" />
                        </svg>
                      </button>
                    {:else if acct.status === "suspended"}
                      <button
                        onclick={() => handleStatusChange(acct.id, "active")}
                        title="Activate"
                        class="p-1.5 rounded-lg text-neutral-400 hover:bg-emerald-50 hover:text-emerald-700 transition-colors"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                        </svg>
                      </button>
                    {/if}
                    <button
                      onclick={() => handleDelete(acct.id)}
                      disabled={deletingId === acct.id}
                      title="Delete"
                      class="p-1.5 rounded-lg text-neutral-400 hover:bg-red-50 hover:text-red-700 transition-colors disabled:opacity-40"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-500">
          Showing {startItem}–{endItem} of {totalCount} {totalCount === 1 ? "entry" : "entries"}
        </p>
        <div class="flex items-center gap-4">
          <p class="text-sm text-neutral-400">
            Page {currentPage} of {totalPages}
          </p>
          {#if totalPages > 1}
            <div class="flex items-center gap-1">
              <button
                type="button"
                aria-label="Previous page"
                onclick={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1}
                class="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
              <button
                type="button"
                aria-label="Next page"
                onclick={() => goToPage(currentPage + 1)}
                disabled={currentPage >= totalPages}
                class="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</div>

<!-- Create Modal -->
{#if showCreateModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showCreateModal = false)} aria-label="Close"></button>
    <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md p-6 space-y-5">
      <h2 class="text-lg font-bold text-neutral-900">New Service Account</h2>

      <div>
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="sa-name">Name</label>
        <input
          id="sa-name"
          type="text"
          bind:value={createName}
          placeholder="e.g. CI/CD Pipeline"
          class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        />
      </div>

      <div>
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="sa-desc">Description</label>
        <textarea
          id="sa-desc"
          bind:value={createDescription}
          placeholder="What is this service account used for?"
          rows="3"
          class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow resize-none"
        ></textarea>
      </div>

      <div class="flex items-center gap-3 pt-2">
        {#if isDev}
          <button onclick={devFillServiceAccount} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button
          onclick={() => (showCreateModal = false)}
          class="rounded-lg px-4 py-2.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 transition-colors ml-auto"
        >
          Cancel
        </button>
        <button
          onclick={handleCreate}
          disabled={!createName.trim() || creating}
          class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60"
        >
          {creating ? "Creating..." : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- API Key Reveal Modal -->
{#if showKeyModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showKeyModal = false)} aria-label="Close"></button>
    <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 space-y-5">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
          <svg class="w-5 h-5 text-emerald-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
          </svg>
        </div>
        <div>
          <h2 class="text-lg font-bold text-neutral-900">API Key Generated</h2>
          <p class="text-sm text-neutral-500">Copy this key now. It won't be shown again.</p>
        </div>
      </div>

      <div class="rounded-lg bg-neutral-50 border border-neutral-200 p-4">
        <p class="text-xs font-medium text-neutral-400 mb-1.5">API Key</p>
        <code class="block text-sm text-neutral-900 font-mono break-all select-all">{newKeyValue}</code>
      </div>

      <p class="text-xs text-neutral-400">
        Key prefix: <span class="font-mono">{newKeyPrefix}...</span> — use this to identify the key later.
      </p>

      <div class="flex items-center justify-end gap-3 pt-2">
        <button
          onclick={() => {
            navigator.clipboard.writeText(newKeyValue);
          }}
          class="rounded-lg px-4 py-2.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
        >
          Copy to Clipboard
        </button>
        <button
          onclick={() => (showKeyModal = false)}
          class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
        >
          Done
        </button>
      </div>
    </div>
  </div>
{/if}

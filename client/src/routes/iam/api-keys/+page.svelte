<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { APIKeyDirectoryItem, APIKeyListResponse, APIKeyOverview } from "$lib/types";

  let keys = $state<APIKeyDirectoryItem[]>([]);
  let totalCount = $state(0);
  let overview = $state<APIKeyOverview>({ total: 0, active: 0, revoked: 0, expired: 0 });
  let loading = $state(true);

  let currentPage = $state(1);
  let pageSize = 25;
  let search = $state("");
  let statusFilter = $state("");

  let totalPages = $derived(Math.ceil(totalCount / pageSize));

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      search = val;
      currentPage = 1;
      fetchKeys();
    }, 300);
  }

  function handleStatusFilter(e: Event) {
    statusFilter = (e.target as HTMLSelectElement).value;
    currentPage = 1;
    fetchKeys();
  }

  function resetFilters() {
    search = "";
    statusFilter = "";
    currentPage = 1;
    fetchKeys();
  }

  async function fetchKeys() {
    loading = true;
    try {
      const params = new URLSearchParams();
      params.set("page", String(currentPage));
      params.set("page_size", String(pageSize));
      if (search) params.set("search", search);
      if (statusFilter) params.set("status", statusFilter);

      const res = await api.get<APIKeyListResponse>(`/iam/api-keys/?${params}`);
      keys = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      keys = [];
    } finally {
      loading = false;
    }
  }

  async function revokeKey(keyId: number) {
    const key = keys.find((k) => k.id === keyId);
    if (!key) return;
    try {
      await api.delete(`/iam/service-accounts/${key.service_account_id}/keys/${keyId}/`);
      fetchKeys();
    } catch {
      // silent
    }
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchKeys();
  }

  let hasFilters = $derived(!!search || !!statusFilter);

  function formatRelative(dateStr: string): string {
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
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  $effect(() => {
    fetchKeys();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">API Keys</h1>
    <p class="mt-1 text-sm text-neutral-500">Manage all API keys across service accounts.</p>
  </div>

  <!-- Overview Cards -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total</p>
      <p class="mt-2 text-2xl font-bold text-neutral-900">{overview.total}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Active</p>
      <p class="mt-2 text-2xl font-bold text-emerald-700">{overview.active}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Revoked</p>
      <p class="mt-2 text-2xl font-bold {overview.revoked > 0 ? 'text-neutral-700' : 'text-neutral-300'}">{overview.revoked}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Expired</p>
      <p class="mt-2 text-2xl font-bold {overview.expired > 0 ? 'text-amber-700' : 'text-neutral-300'}">{overview.expired}</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    <div class="px-6 py-4 flex flex-wrap items-center gap-3">
      <div class="flex-1 min-w-[200px] max-w-sm">
        <input
          type="text"
          placeholder="Search by prefix, label, or service account..."
          value={search}
          oninput={handleSearch}
          class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        />
      </div>
      <select
        value={statusFilter}
        onchange={handleStatusFilter}
        class="appearance-none rounded-lg border border-neutral-300 px-3.5 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
      >
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="revoked">Revoked</option>
        <option value="expired">Expired</option>
      </select>
      {#if hasFilters}
        <button
          onclick={resetFilters}
          class="text-xs font-medium text-neutral-500 hover:text-neutral-700 transition-colors"
        >
          Reset
        </button>
      {/if}
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if keys.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-300 mb-3">
          <svg class="mx-auto h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z" />
          </svg>
        </div>
        <p class="text-sm text-neutral-500">No API keys found</p>
        {#if hasFilters}
          <button onclick={resetFilters} class="mt-2 text-sm font-medium text-neutral-700 hover:text-neutral-900">Clear filters</button>
        {:else}
          <p class="mt-1 text-xs text-neutral-400">Create a service account and generate keys to get started.</p>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-y border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Key</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Service Account</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Scopes</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Last Used</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Created</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each keys as key}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4">
                  <div>
                    <span class="font-mono text-sm text-neutral-900">{key.prefix}...</span>
                    {#if key.label}
                      <p class="text-xs text-neutral-400 mt-0.5">{key.label}</p>
                    {/if}
                  </div>
                </td>
                <td class="px-5 py-4">
                  <a href="/iam/service-accounts" class="text-sm text-neutral-700 hover:text-neutral-900 transition-colors">{key.service_account_name}</a>
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {key.scopes.length > 0 ? key.scopes.join(", ") : "All"}
                </td>
                <td class="px-5 py-4">
                  <StatusBadge status={key.status_display.toLowerCase()} label={key.status_display} />
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {key.last_used_at ? formatRelative(key.last_used_at) : "Never"}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatRelative(key.created_at)}
                </td>
                <td class="px-5 py-4 text-right">
                  {#if key.status_display === "Active"}
                    <button
                      onclick={() => revokeKey(key.id)}
                      class="p-1.5 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                      title="Revoke key"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636" />
                      </svg>
                    </button>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {#if totalPages > 1}
        <div class="flex items-center justify-between px-6 py-4 border-t border-neutral-100">
          <p class="text-sm text-neutral-500">
            Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalCount)} of {totalCount} entries
          </p>
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              class="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              class="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
          </div>
        </div>
      {/if}
    {/if}
  </div>
</div>

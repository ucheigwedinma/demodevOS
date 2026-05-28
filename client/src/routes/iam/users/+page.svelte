<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { UserDirectoryItem, UserOverview, UserListResponse } from "$lib/types";

  let users = $state<UserDirectoryItem[]>([]);
  let brokenProfilePhotoUserIds = $state<Set<number>>(new Set());
  let totalCount = $state(0);
  let overview = $state<UserOverview>({ total: 0, active: 0, suspended: 0, locked: 0 });
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let search = $state("");
  let statusFilter = $state("");
  let departmentFilter = $state("");
  let roleFilter = $state("");

  let debounceTimer: ReturnType<typeof setTimeout>;

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

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "Never";
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

  async function fetchUsers() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (departmentFilter) params.department = departmentFilter;
      if (roleFilter) params.role = roleFilter;

      const res = await api.get<UserListResponse>("/iam/users/", params);
      users = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      users = [];
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
      fetchUsers();
    }, 300);
  }

  function handleFilterChange() {
    currentPage = 1;
    fetchUsers();
  }

  function handleFilterReset() {
    search = "";
    statusFilter = "";
    departmentFilter = "";
    roleFilter = "";
    currentPage = 1;
    fetchUsers();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchUsers();
  }

  function handleProfilePhotoError(userId: number) {
    const next = new Set(brokenProfilePhotoUserIds);
    next.add(userId);
    brokenProfilePhotoUserIds = next;
  }

  let hasFilters = $derived(!!search || !!statusFilter || !!departmentFilter || !!roleFilter);

  // Delete
  let deleteTarget = $state<UserDirectoryItem | null>(null);
  let deleting = $state(false);

  async function handleDelete() {
    if (!deleteTarget) return;
    deleting = true;
    try {
      await api.delete(`/iam/users/${deleteTarget.id}/`);
      deleteTarget = null;
      fetchUsers();
    } catch {
      // stay on modal
    } finally {
      deleting = false;
    }
  }

  $effect(() => {
    fetchUsers();
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Core Identity Registry</h1>
      <p class="mt-1 text-sm text-neutral-500">Manage all system users.</p>
    </div>
    <a
      href="/iam/users/invite"
      class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      Invite User
    </a>
  </div>

  <!-- Overview Cards -->
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Users</p>
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
      <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Locked</p>
      <p class="mt-2 text-2xl font-bold text-red-700">{overview.locked}</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="flex flex-wrap items-end gap-4">
      <!-- Search -->
      <div class="flex-1 min-w-[200px]">
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="search">Search</label>
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            id="search"
            type="text"
            class="w-full rounded-lg border border-neutral-300 pl-9 pr-3.5 py-2 text-sm placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
            placeholder="Search by name, email, phone..."
            value={search}
            oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          />
        </div>
      </div>

      <!-- Status filter -->
      <div class="w-40">
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="status-filter">Status</label>
        <select
          id="status-filter"
          bind:value={statusFilter}
          onchange={handleFilterChange}
          class="w-full appearance-none rounded-lg border border-neutral-300 px-3.5 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        >
          <option value="">All</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="locked">Locked</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      <!-- Reset -->
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
    {:else if users.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-300 mb-3">
          <svg class="mx-auto h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
          </svg>
        </div>
        <p class="text-sm text-neutral-500">No users found</p>
        {#if hasFilters}
          <button onclick={handleFilterReset} class="mt-2 text-sm font-medium text-neutral-900 hover:underline">
            Clear filters
          </button>
        {:else}
          <a href="/iam/users/invite" class="mt-2 text-sm font-medium text-neutral-900 hover:underline">
            Invite your first user
          </a>
        {/if}
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">ID</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">User</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Identity</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Phone</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Role</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Department</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Last Login</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">MFA</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each users as user}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4">
                  <span class="text-xs font-mono text-neutral-400">{user.profile_id}</span>
                </td>
                <td class="px-5 py-4">
                  <div class="flex items-center gap-3">
                    {#if user.profile_photo && !brokenProfilePhotoUserIds.has(user.id)}
                      <img
                        src={user.profile_photo}
                        alt={user.full_name}
                        class="w-8 h-8 rounded-full object-cover"
                        onerror={() => handleProfilePhotoError(user.id)}
                      />
                    {:else}
                      <div class="w-8 h-8 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-semibold text-neutral-500">
                        {user.full_name?.[0]?.toUpperCase() ?? "?"}
                      </div>
                    {/if}
                    <div>
                      <div class="text-sm font-medium text-neutral-900">{user.full_name}</div>
                      <div class="text-xs text-neutral-400 mt-0.5">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td class="px-5 py-4">
                  <span class="text-sm text-neutral-600">{user.identity_type_display}</span>
                  {#if user.partner_type}
                    <span class="block text-xs text-neutral-400 mt-0.5">{user.partner_type_display}</span>
                  {/if}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-600">{user.phone || "—"}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{user.role_name || "—"}</td>
                <td class="px-5 py-4 text-sm text-neutral-600">{user.department_name || "—"}</td>
                <td class="px-5 py-4">
                  <StatusBadge status={user.user_status} label={user.user_status_display} />
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">{formatRelative(user.last_login)}</td>
                <td class="px-5 py-4">
                  {#if user.mfa_enabled}
                    <span class="inline-flex items-center gap-1 text-xs font-medium text-emerald-700">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
                      </svg>
                      On
                    </span>
                  {:else}
                    <span class="text-xs text-neutral-400">Off</span>
                  {/if}
                </td>
                <td class="px-5 py-4 text-right">
                  <button
                    onclick={() => deleteTarget = user}
                    class="p-1.5 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    title="Delete user"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                    </svg>
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {#if totalPages > 1}
        <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
          <p class="text-sm text-neutral-500">
            Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
          </p>
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
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="w-9 h-9 rounded-lg text-sm font-medium transition-colors
                       {pg === currentPage
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700'}"
              >
                {pg}
              </button>
            {/each}
            <button
              type="button"
              aria-label="Next page"
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              class="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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

<!-- Delete Confirmation Modal -->
{#if deleteTarget}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm"
      onclick={() => deleteTarget = null}
      aria-label="Close modal"
    ></button>

    <!-- Modal -->
    <div class="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <div class="flex items-start gap-4">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50">
          <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-sm font-semibold text-neutral-900">Delete user</h3>
          <p class="mt-1.5 text-sm text-neutral-500">
            Are you sure you want to permanently delete <span class="font-medium text-neutral-700">{deleteTarget.full_name}</span>?
            This action cannot be undone. The user's account and profile will be removed.
          </p>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-3">
        <button
          onclick={() => deleteTarget = null}
          disabled={deleting}
          class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={handleDelete}
          disabled={deleting}
          class="rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-50"
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

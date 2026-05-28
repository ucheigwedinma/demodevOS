<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { UserDirectoryItem, UserOverview, UserListResponse } from "$lib/types";

  let users = $state<UserDirectoryItem[]>([]);
  let overview = $state<UserOverview>({ total: 0, active: 0, suspended: 0, locked: 0 });
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let search = $state("");
  let statusFilter = $state("");
  let actionInFlight = $state<number | null>(null);
  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  const STATUS_TABS = [
    { value: "", label: "All" },
    { value: "active", label: "Active" },
    { value: "suspended", label: "Suspended" },
    { value: "locked", label: "Locked" },
    { value: "pending", label: "Pending" },
  ];

  async function fetchUsers() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
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

  async function suspend(userId: number) {
    actionInFlight = userId;
    try {
      await api.post(`/iam/users/${userId}/suspend/`, {});
      toast.success("Suspended", "User account suspended.");
      await fetchUsers();
    } catch {
      toast.error("Action failed", "Could not suspend user.");
    } finally {
      actionInFlight = null;
    }
  }

  async function activate(userId: number) {
    actionInFlight = userId;
    try {
      await api.post(`/iam/users/${userId}/activate/`, {});
      toast.success("Activated", "User account reactivated.");
      await fetchUsers();
    } catch {
      toast.error("Action failed", "Could not activate user.");
    } finally {
      actionInFlight = null;
    }
  }

  function onSearchInput(e: Event) {
    clearTimeout(debounceTimer);
    const value = (e.target as HTMLInputElement).value;
    debounceTimer = setTimeout(() => { search = value; currentPage = 1; }, 300);
  }

  $effect(() => { void search; void statusFilter; void currentPage; fetchUsers(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">User Status</h1>
    <p class="mt-1 text-sm text-neutral-500">Monitor account status across the organization. Suspend or reactivate users as needed.</p>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">Total</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.total}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-green-600 uppercase tracking-wider">Active</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.active}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-yellow-600 uppercase tracking-wider">Suspended</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.suspended}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-red-600 uppercase tracking-wider">Locked</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.locked}</p>
    </div>
  </div>

  <div class="flex gap-2 flex-wrap">
    {#each STATUS_TABS as tab}
      <button onclick={() => { statusFilter = tab.value; currentPage = 1; }}
        class="rounded-lg px-4 py-2 text-sm font-medium transition-colors
               {statusFilter === tab.value ? 'bg-neutral-800 text-white' : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50'}">
        {tab.label}
      </button>
    {/each}
  </div>

  <div class="relative max-w-sm">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
    <input type="text" placeholder="Search users..." oninput={onSearchInput}
      class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 placeholder:text-neutral-400" />
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if users.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No users found</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Try adjusting the filter or search.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Department</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each users as u}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4 font-medium text-neutral-800">{u.full_name}</td>
              <td class="px-5 py-4 text-neutral-600">{u.email}</td>
              <td class="px-5 py-4 text-neutral-600">{u.department_name || "—"}</td>
              <td class="px-5 py-4 text-center">
                <StatusBadge status={u.user_status} label={u.user_status_display} />
              </td>
              <td class="px-5 py-4 text-right">
                {#if u.user_status === "active"}
                  <button onclick={() => suspend(u.id)} disabled={actionInFlight === u.id}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-yellow-700 bg-yellow-50 hover:bg-yellow-100 transition-colors disabled:opacity-50">
                    {actionInFlight === u.id ? "..." : "Suspend"}
                  </button>
                {:else if u.user_status === "suspended" || u.user_status === "locked"}
                  <button onclick={() => activate(u.id)} disabled={actionInFlight === u.id}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50">
                    {actionInFlight === u.id ? "..." : "Reactivate"}
                  </button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  {#if totalCount > pageSize}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">Page {currentPage} of {totalPages} · {totalCount} total</p>
      <div class="flex items-center gap-1">
        <button onclick={() => currentPage--} disabled={currentPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 transition-colors" aria-label="Previous page">‹</button>
        <button onclick={() => currentPage++} disabled={currentPage >= totalPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 transition-colors" aria-label="Next page">›</button>
      </div>
    </div>
  {/if}
</div>

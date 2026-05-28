<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse } from "$lib/types";

  interface UserEntry {
    id: number;
    full_name: string;
    email: string;
    role_name: string;
    user_status: string;
    user_status_display: string;
    department_name: string;
    job_title: string;
  }

  interface UserListResponse {
    count: number;
    results: UserEntry[];
    overview: { total: number; active: number; suspended: number; locked: number };
  }

  let loading = $state(true);
  let users = $state<UserEntry[]>([]);
  let roles = $state<RoleListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let roleFilter = $state("");
  let saving = $state<number | null>(null);

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  // Track pending role changes (userId → roleId)
  let pendingChanges = $state<Record<number, number | null>>({});
  const hasChanges = $derived(Object.keys(pendingChanges).length > 0);

  function pageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | "...")[] = [1];
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  async function loadData() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(PAGE_SIZE) };
      if (searchQuery) params.search = searchQuery;
      if (roleFilter) params.role = roleFilter;

      const [userRes, roleRes] = await Promise.all([
        api.get<UserListResponse>("/iam/users/", params),
        roles.length ? Promise.resolve({ results: roles } as PaginatedResponse<RoleListItem>) : api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", { page_size: "200", ordering: "name" }),
      ]);

      users = userRes.results;
      totalCount = userRes.count;
      roles = roleRes.results;
    } catch {
      toast.error("Load failed", "Could not load users.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void searchQuery;
    void roleFilter;
    void currentPage;
    loadData();
  });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
      currentPage = 1;
    }, 300);
  }

  function currentRoleId(user: UserEntry): number | null {
    const role = roles.find((r) => r.name === user.role_name);
    return role?.id ?? null;
  }

  function onRoleSelect(userId: number, e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    const newRoleId = value ? parseInt(value, 10) : null;
    const user = users.find((u) => u.id === userId);
    if (!user) return;

    const originalRoleId = currentRoleId(user);
    if (newRoleId === originalRoleId) {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete pendingChanges[userId];
      pendingChanges = { ...pendingChanges };
    } else {
      pendingChanges = { ...pendingChanges, [userId]: newRoleId };
    }
  }

  async function saveAssignment(userId: number) {
    if (!(userId in pendingChanges)) return;
    saving = userId;
    try {
      await api.patch(`/iam/users/${userId}/`, { assigned_role_id: pendingChanges[userId] });
      toast.success("Updated", "Role assignment saved.");
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete pendingChanges[userId];
      pendingChanges = { ...pendingChanges };
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Could not update role assignment.");
      }
    } finally {
      saving = null;
    }
  }

  async function saveAll() {
    const entries = Object.entries(pendingChanges);
    if (entries.length === 0) return;
    saving = -1;
    try {
      await Promise.all(
        entries.map(([uid, roleId]) =>
          api.patch(`/iam/users/${uid}/`, { assigned_role_id: roleId })
        )
      );
      toast.success("Updated", `${entries.length} role ${entries.length === 1 ? "assignment" : "assignments"} saved.`);
      pendingChanges = {};
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Could not update some role assignments.");
      }
    } finally {
      saving = null;
    }
  }

  function displayRole(userId: number, user: UserEntry): number | null {
    if (userId in pendingChanges) return pendingChanges[userId];
    return currentRoleId(user);
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <a href="/iam/roles" class="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-3">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to Roles
      </a>
      <h1 class="text-2xl font-bold text-neutral-900">Role Assignment</h1>
      <p class="mt-1 text-sm text-neutral-500">Assign and manage role mappings across users.</p>
    </div>
    {#if hasChanges}
      <button
        onclick={saveAll}
        disabled={saving !== null}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
      >
        {saving === -1 ? "Saving..." : `Save ${Object.keys(pendingChanges).length} Change${Object.keys(pendingChanges).length === 1 ? "" : "s"}`}
      </button>
    {/if}
  </div>

  <!-- Filters -->
  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="flex gap-3 items-end">
      <div class="relative flex-1 max-w-sm">
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="search-users">Search</label>
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            id="search-users"
            type="text"
            placeholder="Search users..."
            oninput={onSearchInput}
            class="w-full pl-9 pr-3.5 py-2 border border-neutral-300 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
                   placeholder:text-neutral-400 transition-shadow"
          />
        </div>
      </div>
      <div class="w-48">
        <label class="block text-xs font-medium text-neutral-500 mb-1.5" for="role-filter">Filter by Role</label>
        <select
          id="role-filter"
          bind:value={roleFilter}
          onchange={() => (currentPage = 1)}
          class="w-full appearance-none px-3.5 py-2 border border-neutral-300 rounded-lg text-sm
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        >
          <option value="">All Roles</option>
          {#each roles as r}
            <option value={r.id}>{r.name}</option>
          {/each}
        </select>
      </div>
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
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
          <svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
          </svg>
        </div>
        <p class="text-sm font-medium text-neutral-900">No users found</p>
        <p class="mt-1 text-xs text-neutral-400">
          {#if searchQuery || roleFilter}
            Try adjusting your search or filters.
          {:else}
            No users in this organization yet.
          {/if}
        </p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">User</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Department</th>
              <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider w-64">Assigned Role</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider w-24"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each users as user}
              {@const isChanged = user.id in pendingChanges}
              <tr class="transition-colors {isChanged ? 'bg-amber-50/50' : 'hover:bg-neutral-50'}">
                <td class="px-5 py-4">
                  <div>
                    <span class="text-sm font-medium text-neutral-900">{user.full_name}</span>
                    <p class="text-xs text-neutral-400 mt-0.5">{user.email}</p>
                  </div>
                </td>
                <td class="px-5 py-4 text-sm text-neutral-600">{user.department_name || "\u2014"}</td>
                <td class="px-5 py-4 text-center">
                  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
                    {user.user_status === 'active' ? 'bg-emerald-50 text-emerald-700' :
                     user.user_status === 'suspended' ? 'bg-red-50 text-red-700' :
                     user.user_status === 'locked' ? 'bg-amber-50 text-amber-700' :
                     'bg-neutral-100 text-neutral-600'}">
                    {user.user_status_display}
                  </span>
                </td>
                <td class="px-5 py-4">
                  <select
                    value={displayRole(user.id, user) ?? ""}
                    onchange={(e) => onRoleSelect(user.id, e)}
                    class="w-full appearance-none px-3 py-1.5 border rounded-lg text-sm transition-shadow
                           {isChanged ? 'border-amber-400 ring-1 ring-amber-200' : 'border-neutral-300'}
                           focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  >
                    <option value="">No role assigned</option>
                    {#each roles as r}
                      <option value={r.id}>{r.name}</option>
                    {/each}
                  </select>
                </td>
                <td class="px-5 py-4 text-right">
                  {#if isChanged}
                    <button
                      onclick={() => saveAssignment(user.id)}
                      disabled={saving !== null}
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-white bg-neutral-900 hover:bg-neutral-800 transition-colors disabled:opacity-60"
                    >
                      {saving === user.id ? "..." : "Save"}
                    </button>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-500">
          Showing {startItem}–{endItem} of {totalCount} {totalCount === 1 ? "user" : "users"}
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
                onclick={() => currentPage--}
                disabled={currentPage <= 1}
                class="p-2 rounded-lg text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
              {#each pageNumbers(currentPage, totalPages) as pg}
                {#if pg === "..."}
                  <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300">...</span>
                {:else}
                  <button
                    onclick={() => (currentPage = pg as number)}
                    class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors
                           {currentPage === pg
                             ? 'bg-neutral-900 text-white'
                             : 'text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700'}"
                  >
                    {pg}
                  </button>
                {/if}
              {/each}
              <button
                type="button"
                aria-label="Next page"
                onclick={() => currentPage++}
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

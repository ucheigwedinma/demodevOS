<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse } from "$lib/types";

  let loading = $state(true);
  let data = $state<RoleListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let typeFilter = $state("");
  let sortValue = $state("name");

  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let deleting = $state<number | null>(null);
  let showDeleteConfirm = $state<number | null>(null);

  let form = $state({
    name: "",
    description: "",
  });

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const ROLE_SAMPLES = [
    { name: "Project Manager", description: "Full access to project dashboards, budgets, timelines, and team assignments. Can approve change orders and sign off on milestones." },
    { name: "Sales Agent", description: "View and manage leads, client interactions, and unit reservations. Can generate SOA and payment schedules but cannot modify pricing." },
    { name: "Finance Controller", description: "Access to all financial modules including journals, chart of accounts, SPVs, and bank reconciliations. Can approve payments up to authority limit." },
  ];
  let roleDevIdx = 0;
  function devFillRole() {
    const s = ROLE_SAMPLES[roleDevIdx % ROLE_SAMPLES.length];
    roleDevIdx++;
    form.name = s.name;
    form.description = s.description;
  }

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

  async function loadRoles() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (typeFilter) params.is_system = typeFilter;
      params.ordering = sortValue;

      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load roles.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void searchQuery;
    void typeFilter;
    void sortValue;
    void currentPage;
    loadRoles();
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

  function openAdd() {
    editingId = null;
    form = { name: "", description: "" };
    showModal = true;
  }

  function openEdit(role: RoleListItem) {
    editingId = role.id;
    form = { name: role.name, description: role.description };
    showModal = true;
  }

  async function handleSave() {
    if (!form.name.trim()) {
      toast.error("Validation", "Role name is required.");
      return;
    }
    saving = true;
    try {
      if (editingId) {
        await api.patch(`/settings/roles/${editingId}/`, form);
        toast.success("Updated", "Role updated successfully.");
      } else {
        await api.post("/settings/roles/", form);
        toast.success("Created", "Role created successfully.");
      }
      showModal = false;
      await loadRoles();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please check the form for errors.");
      }
    } finally {
      saving = false;
    }
  }

  async function handleDelete(id: number) {
    deleting = id;
    try {
      await api.delete(`/settings/roles/${id}/`);
      toast.success("Deleted", "Role removed.");
      showDeleteConfirm = null;
      await loadRoles();
    } catch {
      toast.error("Delete failed", "Could not delete role.");
    } finally {
      deleting = null;
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-xl font-bold text-neutral-800">Roles & Permissions</h2>
      <p class="mt-1 text-sm text-neutral-500">
        Manage roles and configure granular permission access.
        {#if totalCount > 0}
          <span class="ml-1 inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
            {totalCount} {totalCount === 1 ? "role" : "roles"}
          </span>
        {/if}
      </p>
    </div>
    <button
      onclick={openAdd}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
    >
      Add Role
    </button>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input
        type="text"
        placeholder="Search roles..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={typeFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="">All Types</option>
      <option value="true">System</option>
      <option value="false">Custom</option>
    </select>
    <select
      bind:value={sortValue}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="name">Name A–Z</option>
      <option value="-name">Name Z–A</option>
      <option value="-created_at">Newest First</option>
      <option value="created_at">Oldest First</option>
      <option value="-user_count">Most Users</option>
      <option value="user_count">Fewest Users</option>
    </select>
  </div>

  <!-- Table -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading roles...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
          <svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-neutral-800">No roles found</h3>
        <p class="mt-1.5 text-sm text-neutral-500">
          {#if searchQuery || typeFilter}
            Try adjusting your search or filters.
          {:else}
            Create your first role to start managing access control.
          {/if}
        </p>
        {#if !searchQuery && !typeFilter}
          <button onclick={openAdd} class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors">
            Add Role
          </button>
        {/if}
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Role</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Users</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as role}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-800">{role.name}</span>
              </td>
              <td class="px-5 py-4 text-neutral-600 max-w-xs truncate">{role.description || "—"}</td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center justify-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
                  {role.user_count}
                </span>
              </td>
              <td class="px-5 py-4 text-center">
                {#if role.is_system}
                  <span class="inline-flex items-center rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-white">
                    System
                  </span>
                {:else}
                  <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">
                    Custom
                  </span>
                {/if}
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <a
                    href="/iam/roles/{role.id}/permissions"
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-800 bg-neutral-100 hover:bg-neutral-200 transition-colors"
                  >
                    Configure
                  </a>
                  <button
                    onclick={() => openEdit(role)}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
                  >
                    Edit
                  </button>
                  {#if !role.is_system}
                    <button
                      onclick={() => (showDeleteConfirm = role.id)}
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                    >
                      Delete
                    </button>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <!-- Pagination -->
  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">
        Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "role" : "roles"}
      </p>

      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button
            onclick={() => currentPage--}
            disabled={currentPage <= 1}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
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
                         ? 'bg-neutral-800 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100'}"
              >
                {pg}
              </button>
            {/if}
          {/each}

          <button
            onclick={() => currentPage++}
            disabled={currentPage >= totalPages}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
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

<!-- Add/Edit Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6">
        <h2 class="text-lg font-bold text-neutral-800 mb-6">
          {editingId ? "Edit Role" : "Add Role"}
        </h2>

        <div class="space-y-4">
          <div>
            <label for="role-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
            <input
              id="role-name"
              type="text"
              bind:value={form.name}
              placeholder="e.g. Marketing Manager"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
            />
          </div>

          <div>
            <label for="role-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
            <textarea
              id="role-desc"
              rows="3"
              bind:value={form.description}
              placeholder="Brief description of this role's responsibilities..."
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none"
            ></textarea>
          </div>
        </div>

        <div class="mt-7 flex items-center gap-3">
          {#if isDev}
            <button onclick={devFillRole} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
          {/if}
          <button onclick={() => (showModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">
            Cancel
          </button>
          <button onclick={handleSave} disabled={saving} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60">
            {saving ? "Saving..." : editingId ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation -->
{#if showDeleteConfirm !== null}
  {@const roleToDelete = data.find((r) => r.id === showDeleteConfirm)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showDeleteConfirm = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-800">Delete Role</h3>
      <p class="mt-2 text-sm text-neutral-600">
        Are you sure you want to delete <strong>{roleToDelete?.name}</strong>? This will remove all associated permissions. This action cannot be undone.
      </p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (showDeleteConfirm = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
          Cancel
        </button>
        <button
          onclick={() => showDeleteConfirm !== null && handleDelete(showDeleteConfirm)}
          disabled={deleting !== null}
          class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60"
        >
          {deleting !== null ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

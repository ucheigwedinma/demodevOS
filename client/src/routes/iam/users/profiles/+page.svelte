<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { UserDirectoryItem, UserDetailItem, UserListResponse } from "$lib/types";

  let users = $state<UserDirectoryItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 12;

  let search = $state("");
  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  // Detail drawer
  let selectedUser = $state<UserDetailItem | null>(null);
  let showDrawer = $state(false);
  let drawerLoading = $state(false);
  let saving = $state(false);

  let editForm = $state({
    first_name: "",
    last_name: "",
    phone: "",
    job_title: "",
    user_status: "active" as string,
    identity_type: "user" as string,
    partner_type: "" as string,
  });

  async function fetchUsers() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      const res = await api.get<UserListResponse>("/iam/users/", params);
      users = res.results;
      totalCount = res.count;
    } catch {
      users = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function openProfile(userId: number) {
    showDrawer = true;
    drawerLoading = true;
    selectedUser = null;
    try {
      const data = await api.get<UserDetailItem>(`/iam/users/${userId}/`);
      selectedUser = data;
      editForm = {
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone || "",
        job_title: data.job_title || "",
        user_status: data.user_status,
        identity_type: data.identity_type,
        partner_type: data.partner_type || "",
      };
    } catch {
      toast.error("Load failed", "Could not load user profile.");
      showDrawer = false;
    } finally {
      drawerLoading = false;
    }
  }

  async function saveProfile() {
    if (!selectedUser) return;
    saving = true;
    try {
      await api.patch(`/iam/users/${selectedUser.id}/`, editForm);
      toast.success("Saved", "Profile updated.");
      await fetchUsers();
      // Re-fetch detail
      const refreshed = await api.get<UserDetailItem>(`/iam/users/${selectedUser.id}/`);
      selectedUser = refreshed;
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please check the form for errors.");
      }
    } finally {
      saving = false;
    }
  }

  function onSearchInput(e: Event) {
    clearTimeout(debounceTimer);
    const value = (e.target as HTMLInputElement).value;
    debounceTimer = setTimeout(() => {
      search = value;
      currentPage = 1;
    }, 300);
  }

  $effect(() => {
    void search;
    void currentPage;
    fetchUsers();
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">User Profiles</h1>
    <p class="mt-1 text-sm text-neutral-500">Browse rich profile cards. Click any card to view and edit details.</p>
  </div>

  <!-- Search -->
  <div class="relative max-w-sm">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
    <input
      type="text"
      placeholder="Search by name, email, role..."
      oninput={onSearchInput}
      class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent
             placeholder:text-neutral-400"
    />
  </div>

  <!-- Cards grid -->
  {#if loading}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if users.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <h3 class="text-sm font-semibold text-neutral-800">No users</h3>
      <p class="mt-1.5 text-sm text-neutral-500">No users match the current search.</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each users as u}
        <button
          onclick={() => openProfile(u.id)}
          class="text-left rounded-xl border border-neutral-200 bg-white p-5 hover:border-neutral-400 hover:shadow-sm transition-all"
        >
          <div class="flex items-start gap-3">
            <div class="w-12 h-12 rounded-full bg-neutral-100 flex items-center justify-center text-sm font-semibold text-neutral-600">
              {u.full_name.split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()}
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-semibold text-neutral-900 truncate">{u.full_name}</p>
              <p class="text-xs text-neutral-500 truncate">{u.email}</p>
              <div class="mt-2 flex items-center gap-2 flex-wrap">
                <StatusBadge status={u.user_status} label={u.user_status_display} />
                <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                  {u.identity_type_display}
                </span>
              </div>
            </div>
          </div>
          <div class="mt-4 pt-4 border-t border-neutral-100 space-y-1.5 text-xs">
            <div class="flex justify-between">
              <span class="text-neutral-400">Role</span>
              <span class="text-neutral-700">{u.role_name || "—"}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-neutral-400">Department</span>
              <span class="text-neutral-700">{u.department_name || "—"}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-neutral-400">Job title</span>
              <span class="text-neutral-700 truncate ml-2">{u.job_title || "—"}</span>
            </div>
          </div>
        </button>
      {/each}
    </div>
  {/if}

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

<!-- Detail Drawer -->
{#if showDrawer}
  <div class="fixed inset-0 z-50 flex">
    <button class="flex-1 bg-black/40 backdrop-blur-sm" onclick={() => (showDrawer = false)} aria-label="Close"></button>
    <div class="w-full max-w-lg bg-white shadow-2xl border-l border-neutral-200 overflow-y-auto">
      {#if drawerLoading}
        <div class="p-16 text-center">
          <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        </div>
      {:else if selectedUser}
        <div class="p-6 border-b border-neutral-100 flex items-start justify-between">
          <div>
            <h2 class="text-lg font-bold text-neutral-900">{selectedUser.full_name}</h2>
            <p class="text-xs text-neutral-500">{selectedUser.email}</p>
          </div>
          <button onclick={() => (showDrawer = false)} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
        </div>

        <div class="p-6 space-y-5">
          <div class="grid grid-cols-2 gap-3">
            <label class="text-xs font-medium text-neutral-700">
              <span class="block mb-1">First name</span>
              <input bind:value={editForm.first_name} type="text" class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
            </label>
            <label class="text-xs font-medium text-neutral-700">
              <span class="block mb-1">Last name</span>
              <input bind:value={editForm.last_name} type="text" class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
            </label>
          </div>

          <label class="text-xs font-medium text-neutral-700 block">
            <span class="block mb-1">Job title</span>
            <input bind:value={editForm.job_title} type="text" class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </label>

          <label class="text-xs font-medium text-neutral-700 block">
            <span class="block mb-1">Phone</span>
            <input bind:value={editForm.phone} type="text" class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </label>

          <div class="grid grid-cols-2 gap-3">
            <label class="text-xs font-medium text-neutral-700">
              <span class="block mb-1">Status</span>
              <select bind:value={editForm.user_status} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
                <option value="active">Active</option>
                <option value="suspended">Suspended</option>
                <option value="locked">Locked</option>
                <option value="pending">Pending</option>
              </select>
            </label>
            <label class="text-xs font-medium text-neutral-700">
              <span class="block mb-1">Identity</span>
              <select bind:value={editForm.identity_type} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
                <option value="user">User</option>
                <option value="employee">Employee</option>
                <option value="partner">Partner</option>
                <option value="system_account">Service account</option>
              </select>
            </label>
          </div>

          {#if editForm.identity_type === "partner"}
            <label class="text-xs font-medium text-neutral-700 block">
              <span class="block mb-1">Partner type</span>
              <select bind:value={editForm.partner_type} class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
                <option value="">—</option>
                <option value="contractor">Contractor</option>
                <option value="vendor">Vendor</option>
                <option value="client">Client</option>
                <option value="investor">Investor</option>
              </select>
            </label>
          {/if}

          <div class="pt-4 flex items-center justify-end gap-2 border-t border-neutral-100">
            <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
            <button onclick={saveProfile} disabled={saving} class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
              {saving ? "Saving..." : "Save"}
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

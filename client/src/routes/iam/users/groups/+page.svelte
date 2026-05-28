<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { UserDirectoryItem, UserListResponse } from "$lib/types";

  type GroupListItem = {
    id: number;
    name: string;
    description: string;
    member_count: number;
    is_system: boolean;
    created_at: string;
    updated_at: string;
  };
  type GroupMember = { id: number; name: string; email: string; job_title: string; user_status: string };
  type GroupDetail = GroupListItem & { members: GroupMember[] };
  type GroupListResponse = { count: number; results: GroupListItem[] };

  let groups = $state<GroupListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let search = $state("");
  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  // Modal state
  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let showDeleteConfirm = $state<number | null>(null);
  let deleting = $state<number | null>(null);

  // Detail panel state
  let detailGroup = $state<GroupDetail | null>(null);
  let detailLoading = $state(false);

  let form = $state({
    name: "",
    description: "",
    member_ids: [] as number[],
  });

  // Member picker
  let availableUsers = $state<UserDirectoryItem[]>([]);
  let memberPickerSearch = $state("");
  let memberPickerLoading = $state(false);
  let memberPickerTimer: ReturnType<typeof setTimeout>;

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const GROUP_SAMPLES = [
    { name: "Project Approvers", description: "Senior staff with sign-off authority on project budgets and milestones." },
    { name: "Finance Reviewers", description: "Members of finance who review payment runs before they go out the door." },
    { name: "Site Safety Officers", description: "On-site personnel responsible for daily safety inspections and incident response." },
  ];
  let groupDevIdx = 0;
  function devFillGroup() {
    const s = GROUP_SAMPLES[groupDevIdx % GROUP_SAMPLES.length];
    groupDevIdx++;
    form.name = s.name;
    form.description = s.description;
  }

  async function fetchGroups() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (search) params.search = search;
      const res = await api.get<GroupListResponse>("/iam/user-groups/", params);
      groups = res.results;
      totalCount = res.count;
    } catch {
      groups = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function loadAvailableUsers() {
    memberPickerLoading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (memberPickerSearch) params.search = memberPickerSearch;
      const res = await api.get<UserListResponse>("/iam/users/", params);
      availableUsers = res.results;
    } catch {
      availableUsers = [];
    } finally {
      memberPickerLoading = false;
    }
  }

  async function openAdd() {
    editingId = null;
    form = { name: "", description: "", member_ids: [] };
    showModal = true;
    await loadAvailableUsers();
  }

  async function openEdit(g: GroupListItem) {
    editingId = g.id;
    detailLoading = true;
    showModal = true;
    try {
      const detail = await api.get<GroupDetail>(`/iam/user-groups/${g.id}/`);
      form = {
        name: detail.name,
        description: detail.description,
        member_ids: detail.members.map((m) => m.id),
      };
      await loadAvailableUsers();
    } catch {
      toast.error("Load failed", "Could not load group details.");
      showModal = false;
    } finally {
      detailLoading = false;
    }
  }

  async function openDetail(g: GroupListItem) {
    detailLoading = true;
    detailGroup = null;
    try {
      const data = await api.get<GroupDetail>(`/iam/user-groups/${g.id}/`);
      detailGroup = data;
    } catch {
      toast.error("Load failed", "Could not load group.");
    } finally {
      detailLoading = false;
    }
  }

  async function handleSave() {
    if (!form.name.trim()) {
      toast.error("Validation", "Group name is required.");
      return;
    }
    saving = true;
    try {
      if (editingId) {
        await api.patch(`/iam/user-groups/${editingId}/`, form);
        toast.success("Updated", "Group updated.");
      } else {
        await api.post("/iam/user-groups/", form);
        toast.success("Created", "Group created.");
      }
      showModal = false;
      await fetchGroups();
      if (detailGroup && editingId === detailGroup.id) {
        await openDetail(detailGroup);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please check the form.");
      }
    } finally {
      saving = false;
    }
  }

  async function handleDelete(id: number) {
    deleting = id;
    try {
      await api.delete(`/iam/user-groups/${id}/`);
      toast.success("Deleted", "Group removed.");
      showDeleteConfirm = null;
      if (detailGroup && detailGroup.id === id) detailGroup = null;
      await fetchGroups();
    } catch {
      toast.error("Delete failed", "Could not delete group.");
    } finally {
      deleting = null;
    }
  }

  function toggleMember(userId: number) {
    if (form.member_ids.includes(userId)) {
      form.member_ids = form.member_ids.filter((id) => id !== userId);
    } else {
      form.member_ids = [...form.member_ids, userId];
    }
  }

  function onSearchInput(e: Event) {
    clearTimeout(debounceTimer);
    const value = (e.target as HTMLInputElement).value;
    debounceTimer = setTimeout(() => { search = value; currentPage = 1; }, 300);
  }

  function onMemberPickerSearchInput(e: Event) {
    clearTimeout(memberPickerTimer);
    const value = (e.target as HTMLInputElement).value;
    memberPickerTimer = setTimeout(() => {
      memberPickerSearch = value;
      loadAvailableUsers();
    }, 300);
  }

  $effect(() => { void search; void currentPage; fetchGroups(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">User Groups</h1>
      <p class="mt-1 text-sm text-neutral-500">Organise users into named groups for bulk operations and permission grants.</p>
    </div>
    <button onclick={openAdd}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
      Add Group
    </button>
  </div>

  <div class="relative max-w-sm">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
    <input type="text" placeholder="Search groups..." oninput={onSearchInput}
      class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 placeholder:text-neutral-400" />
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if groups.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No groups yet</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Create your first group to start organising users.</p>
        <button onclick={openAdd} class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
          Add Group
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Group</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Members</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each groups as g}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <button onclick={() => openDetail(g)} class="font-medium text-neutral-800 hover:text-neutral-900 underline-offset-2 hover:underline">
                  {g.name}
                </button>
              </td>
              <td class="px-5 py-4 text-neutral-600 max-w-md truncate">{g.description || "—"}</td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center justify-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
                  {g.member_count}
                </span>
              </td>
              <td class="px-5 py-4 text-center">
                {#if g.is_system}
                  <span class="inline-flex items-center rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs font-medium text-white">System</span>
                {:else}
                  <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">Custom</span>
                {/if}
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button onclick={() => openEdit(g)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">Edit</button>
                  {#if !g.is_system}
                    <button onclick={() => (showDeleteConfirm = g.id)} class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">Delete</button>
                  {/if}
                </div>
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

<!-- Detail panel -->
{#if detailGroup}
  <div class="fixed inset-0 z-40 flex">
    <button class="flex-1 bg-black/40 backdrop-blur-sm" onclick={() => (detailGroup = null)} aria-label="Close"></button>
    <div class="w-full max-w-md bg-white shadow-2xl border-l border-neutral-200 overflow-y-auto">
      <div class="p-6 border-b border-neutral-100 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-bold text-neutral-900">{detailGroup.name}</h2>
          <p class="text-xs text-neutral-500 mt-1">{detailGroup.description || "No description"}</p>
        </div>
        <button onclick={() => (detailGroup = null)} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>
      <div class="p-6">
        <p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">
          {detailGroup.members.length} {detailGroup.members.length === 1 ? "member" : "members"}
        </p>
        {#if detailGroup.members.length === 0}
          <p class="text-sm text-neutral-500">No members in this group yet.</p>
        {:else}
          <ul class="space-y-2">
            {#each detailGroup.members as m}
              <li class="flex items-center gap-3 p-3 rounded-lg border border-neutral-100">
                <div class="w-9 h-9 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-semibold text-neutral-600">
                  {m.name.split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()}
                </div>
                <div class="min-w-0">
                  <p class="font-medium text-sm text-neutral-800 truncate">{m.name}</p>
                  <p class="text-xs text-neutral-500 truncate">{m.email}</p>
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Add/Edit Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl rounded-2xl bg-white shadow-2xl border border-neutral-200 max-h-[90vh] flex flex-col">
      <div class="p-6 border-b border-neutral-100 shrink-0">
        <h2 class="text-lg font-bold text-neutral-800">{editingId ? "Edit Group" : "Add Group"}</h2>
      </div>

      <div class="p-6 overflow-y-auto flex-1 min-h-0 space-y-4">
        <div>
          <label for="group-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name *</label>
          <input id="group-name" type="text" bind:value={form.name} placeholder="e.g. Project Approvers"
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>

        <div>
          <label for="group-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <textarea id="group-desc" rows="3" bind:value={form.description} placeholder="What is this group for?"
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
        </div>

        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="block text-sm font-medium text-neutral-700">
              Members
              <span class="text-xs font-normal text-neutral-500 ml-1">({form.member_ids.length} selected)</span>
            </label>
          </div>
          <div class="relative mb-2">
            <input type="text" placeholder="Search users..." oninput={onMemberPickerSearchInput}
              class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div class="rounded-lg border border-neutral-200 max-h-64 overflow-y-auto">
            {#if memberPickerLoading}
              <div class="p-6 text-center text-sm text-neutral-400">Loading…</div>
            {:else if availableUsers.length === 0}
              <div class="p-6 text-center text-sm text-neutral-400">No users.</div>
            {:else}
              {#each availableUsers as u}
                <label class="flex items-center gap-3 p-3 hover:bg-neutral-50 cursor-pointer border-b border-neutral-100 last:border-b-0">
                  <input type="checkbox" checked={form.member_ids.includes(u.id)} onchange={() => toggleMember(u.id)}
                    class="w-4 h-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
                  <div class="min-w-0 flex-1">
                    <p class="text-sm font-medium text-neutral-800 truncate">{u.full_name}</p>
                    <p class="text-xs text-neutral-500 truncate">{u.email}</p>
                  </div>
                </label>
              {/each}
            {/if}
          </div>
        </div>
      </div>

      <div class="p-6 border-t border-neutral-100 flex items-center gap-3 shrink-0">
        {#if isDev}
          <button onclick={devFillGroup} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">
            Dev Fill
          </button>
        {/if}
        <button onclick={() => (showModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">
          Cancel
        </button>
        <button onclick={handleSave} disabled={saving || detailLoading}
          class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors disabled:opacity-60">
          {saving ? "Saving..." : editingId ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete confirmation -->
{#if showDeleteConfirm !== null}
  {@const groupToDelete = groups.find((g) => g.id === showDeleteConfirm)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showDeleteConfirm = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-800">Delete Group</h3>
      <p class="mt-2 text-sm text-neutral-600">
        Are you sure you want to delete <strong>{groupToDelete?.name}</strong>? Members will be unaffected; only the grouping is removed.
      </p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (showDeleteConfirm = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={() => showDeleteConfirm !== null && handleDelete(showDeleteConfirm)} disabled={deleting !== null}
          class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">
          {deleting !== null ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

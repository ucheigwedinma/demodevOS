<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { UserDirectoryItem, UserListResponse } from "$lib/types";

  let users = $state<UserDirectoryItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let search = $state("");
  let identityFilter = $state("partner,system_account");
  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  const IDENTITY_OPTIONS = [
    { value: "partner,system_account", label: "All external" },
    { value: "partner", label: "Partners only" },
    { value: "system_account", label: "Service accounts only" },
  ];

  const PARTNER_TYPE_LABEL: Record<string, string> = {
    contractor: "Contractor",
    vendor: "Vendor",
    client: "Client",
    investor: "Investor",
  };

  async function fetchUsers() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
        identity_type: identityFilter,
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
    void identityFilter;
    void currentPage;
    fetchUsers();
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">External Users</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Partners, contractors, and service accounts — identities that aren't regular org employees.
    </p>
  </div>

  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input type="text" placeholder="Search external users..." oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 placeholder:text-neutral-400" />
    </div>
    <select bind:value={identityFilter} onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800">
      {#each IDENTITY_OPTIONS as opt}<option value={opt.value}>{opt.label}</option>{/each}
    </select>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if users.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No external users</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Partners and service accounts will appear here once added.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Identity</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Sub-type</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each users as u}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4 font-medium text-neutral-800">{u.full_name}</td>
              <td class="px-5 py-4 text-neutral-600">{u.email}</td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
                  {u.identity_type_display}
                </span>
              </td>
              <td class="px-5 py-4 text-neutral-600">
                {u.partner_type ? PARTNER_TYPE_LABEL[u.partner_type] || u.partner_type : "—"}
              </td>
              <td class="px-5 py-4 text-center">
                <StatusBadge status={u.user_status} label={u.user_status_display} />
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

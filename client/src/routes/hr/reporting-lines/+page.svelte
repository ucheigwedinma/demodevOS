<script lang="ts">
  import { api } from "$lib/api";
  import type { ReportingLineUser } from "$lib/types";

  let users = $state<ReportingLineUser[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");

  async function fetchReportingLines() {
    loading = true;
    try {
      users = await api.get<ReportingLineUser[]>("/hr/reporting-lines/");
    } catch {
      users = [];
    } finally {
      loading = false;
    }
  }

  let filteredUsers = $derived(
    searchQuery
      ? users.filter((u) =>
          u.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          u.job_title.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (u.department ?? "").toLowerCase().includes(searchQuery.toLowerCase())
        )
      : users
  );

  // Build a lookup for names
  let userById = $derived(
    Object.fromEntries(users.map((u) => [u.id, u]))
  );

  function managerName(id: number | null): string {
    if (!id) return "\u2014";
    return userById[id]?.full_name ?? "\u2014";
  }

  $effect(() => {
    fetchReportingLines();
  });
</script>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Reporting Lines</h1>
      <p class="mt-1 text-sm text-neutral-500">Manager-to-employee reporting hierarchy</p>
    </div>
  </div>

  <!-- Search -->
  <div class="mb-6">
    <div class="relative max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input
        type="text"
        placeholder="Search by name, title, or department..."
        bind:value={searchQuery}
        class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if filteredUsers.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">{searchQuery ? "No users match your search" : "No reporting data available"}</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Name</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Job Title</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Department</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Reports To</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Direct Reports</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each filteredUsers as user}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5">
                <span class="font-medium text-neutral-900">{user.full_name}</span>
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{user.job_title || "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{user.department ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-neutral-600">{managerName(user.reports_to)}</td>
              <td class="px-5 py-3.5 text-center">
                {#if user.direct_report_count > 0}
                  <span class="inline-flex items-center justify-center min-w-[24px] px-1.5 py-0.5 rounded-full text-xs font-medium bg-neutral-900 text-white">{user.direct_report_count}</span>
                {:else}
                  <span class="text-neutral-300">0</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <p class="mt-3 text-xs text-neutral-400">{filteredUsers.length} of {users.length} user{users.length !== 1 ? 's' : ''}</p>
  {/if}
</div>

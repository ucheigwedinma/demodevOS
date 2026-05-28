<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";

  type LinkedEmployeeItem = {
    user_id: number;
    full_name: string;
    email: string;
    job_title: string;
    department_name: string;
    user_status: string;
    has_employee_record: boolean;
    employee_id: number | null;
    employee_code: string;
    employee_hire_date: string | null;
  };
  type LinkedEmployeeOverview = { total: number; linked: number; unlinked: number };
  type LinkedEmployeeResponse = { count: number; results: LinkedEmployeeItem[]; overview: LinkedEmployeeOverview };

  let items = $state<LinkedEmployeeItem[]>([]);
  let overview = $state<LinkedEmployeeOverview>({ total: 0, linked: 0, unlinked: 0 });
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let search = $state("");
  let linkedFilter = $state("");
  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (search) params.search = search;
      if (linkedFilter) params.linked = linkedFilter;
      const res = await api.get<LinkedEmployeeResponse>("/iam/users/linked-employees/", params);
      items = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      items = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function onSearchInput(e: Event) {
    clearTimeout(debounceTimer);
    const value = (e.target as HTMLInputElement).value;
    debounceTimer = setTimeout(() => { search = value; currentPage = 1; }, 300);
  }

  $effect(() => { void search; void linkedFilter; void currentPage; fetchItems(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Linked Employees</h1>
    <p class="mt-1 text-sm text-neutral-500">Map of platform users to their HR employee records. Highlights users without a corresponding HR record.</p>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">Total users</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.total}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-green-600 uppercase tracking-wider">Linked</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.linked}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-yellow-600 uppercase tracking-wider">Unlinked</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.unlinked}</p>
    </div>
  </div>

  <div class="flex gap-3 items-center flex-wrap">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input type="text" placeholder="Search by name or email..." oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 placeholder:text-neutral-400" />
    </div>
    <select bind:value={linkedFilter} onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800">
      <option value="">All</option>
      <option value="true">Linked only</option>
      <option value="false">Unlinked only</option>
    </select>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if items.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No users to show</h3>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Department</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Employee record</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Hired</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as it}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4 font-medium text-neutral-800">{it.full_name}</td>
              <td class="px-5 py-4 text-neutral-600">{it.email}</td>
              <td class="px-5 py-4 text-neutral-600">{it.department_name || "—"}</td>
              <td class="px-5 py-4">
                {#if it.has_employee_record}
                  <span class="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">
                    <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                    Linked · #{it.employee_code || it.employee_id}
                  </span>
                {:else}
                  <span class="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>
                    Not linked
                  </span>
                {/if}
              </td>
              <td class="px-5 py-4 text-neutral-600">{formatDate(it.employee_hire_date)}</td>
              <td class="px-5 py-4 text-center">
                <StatusBadge status={it.user_status} label={it.user_status} />
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

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { EmploymentHistoryEntry } from "$lib/types";

  // --- Response shape ---
  interface EmploymentHistoryResponse {
    position_history: EmploymentHistoryEntry[];
    employee_record: {
      hire_date: string | null;
      contract_start_date: string | null;
      contract_end_date: string | null;
      contract_type: string | null;
      employment_status: string | null;
      termination_date: string | null;
    } | null;
  }

  // --- State ---
  let userSearch = $state("");
  let loading = $state(false);
  let searched = $state(false);
  let history = $state<EmploymentHistoryEntry[]>([]);
  let employeeRecord = $state<EmploymentHistoryResponse["employee_record"]>(null);

  // --- Helpers ---
  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function contractTypeLabel(ct: string | null): string {
    if (!ct) return "\u2014";
    const map: Record<string, string> = {
      permanent: "Permanent",
      fixed_term: "Fixed Term",
      probation: "Probation",
      contractor: "Contractor",
      intern: "Intern",
      part_time: "Part Time",
    };
    return map[ct] ?? ct;
  }

  function statusLabel(s: string | null): string {
    if (!s) return "\u2014";
    const map: Record<string, string> = {
      active: "Active",
      on_leave: "On Leave",
      suspended: "Suspended",
      terminated: "Terminated",
      resigned: "Resigned",
    };
    return map[s] ?? s;
  }

  // --- Data Fetching ---
  async function fetchHistory() {
    if (!userSearch.trim()) {
      toast.error("User ID required", "Please enter a user ID to search");
      return;
    }

    loading = true;
    searched = true;
    try {
      const res = await api.get<EmploymentHistoryResponse>(
        "/hr/employment-history/",
        { user: userSearch.trim() },
      );
      history = res.position_history;
      employeeRecord = res.employee_record;
    } catch (err) {
      history = [];
      employeeRecord = null;
      if (err instanceof ApiError) {
        toast.error("Error", "Could not fetch employment history");
      } else {
        toast.error("Something went wrong", "Please try again");
      }
    } finally {
      loading = false;
    }
  }

  function handleSearchKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      fetchHistory();
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Employment History</h1>
    <p class="mt-1 text-sm text-neutral-500">Position assignment history for employees</p>
  </div>

  <!-- Search -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="flex items-end gap-4">
      <label class="flex-1 max-w-sm">
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">User ID</span>
        <input
          type="text"
          placeholder="Enter user ID..."
          bind:value={userSearch}
          onkeydown={handleSearchKeydown}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>
      <button
        onclick={fetchHistory}
        disabled={loading}
        class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {#if loading}
          <div class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
        {:else}
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
        {/if}
        Search
      </button>
    </div>
  </div>

  <!-- Employee Record Summary -->
  {#if employeeRecord}
    <div class="bg-white rounded-xl border border-neutral-200 p-5">
      <p class="text-xs font-medium uppercase tracking-wider text-neutral-400 mb-4">Employee Record</p>
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div>
          <p class="text-xs text-neutral-400">Hire Date</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{formatDate(employeeRecord.hire_date)}</p>
        </div>
        <div>
          <p class="text-xs text-neutral-400">Contract Start</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{formatDate(employeeRecord.contract_start_date)}</p>
        </div>
        <div>
          <p class="text-xs text-neutral-400">Contract End</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{formatDate(employeeRecord.contract_end_date)}</p>
        </div>
        <div>
          <p class="text-xs text-neutral-400">Contract Type</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{contractTypeLabel(employeeRecord.contract_type)}</p>
        </div>
        <div>
          <p class="text-xs text-neutral-400">Employment Status</p>
          <p class="mt-1">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {employeeRecord.employment_status === 'active' ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
              {statusLabel(employeeRecord.employment_status)}
            </span>
          </p>
        </div>
        <div>
          <p class="text-xs text-neutral-400">Termination Date</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{formatDate(employeeRecord.termination_date)}</p>
        </div>
      </div>
    </div>
  {/if}

  <!-- Position History Table -->
  {#if searched}
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if history.length === 0}
        <div class="flex flex-col items-center justify-center py-20 text-center">
          <div class="text-neutral-400 mb-2">
            <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </div>
          <p class="text-neutral-500 text-sm">No position history found for this user</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50/50">
              <tr>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Position</th>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Code</th>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Department</th>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Start Date</th>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">End Date</th>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Primary</th>
                <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Active</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each history as entry}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-4 text-sm font-medium text-neutral-900">{entry.position_title}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{entry.position_code || "\u2014"}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{entry.department_name || "\u2014"}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{formatDate(entry.start_date)}</td>
                  <td class="px-5 py-4 text-sm text-neutral-600">{formatDate(entry.end_date)}</td>
                  <td class="px-5 py-4">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {entry.is_primary ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
                      {entry.is_primary ? "Yes" : "No"}
                    </span>
                  </td>
                  <td class="px-5 py-4">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {entry.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
                      {entry.is_active ? "Yes" : "No"}
                    </span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>

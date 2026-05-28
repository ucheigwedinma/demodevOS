<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { LeaveRequestListItem, PaginatedResponse } from "$lib/types";

  let items = $state<LeaveRequestListItem[]>([]);
  let loading = $state(true);
  let filterMonth = $state(new Date().toISOString().slice(0, 7));


  async function fetchItems() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<LeaveRequestListItem>>("/hr/leave-requests/", { page_size: "200", status: "approved" });
      items = res.results;
    } catch { items = []; } finally { loading = false; }
  }

  function daysInMonth(ym: string): number {
    const [y, m] = ym.split("-").map(Number);
    return new Date(y, m, 0).getDate();
  }

  function monthLabel(ym: string): string {
    const [y, m] = ym.split("-").map(Number);
    return new Date(y, m - 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }

  let calendarItems = $derived.by(() => {
    const ym = filterMonth;
    const start = `${ym}-01`;
    const days = daysInMonth(ym);
    const end = `${ym}-${String(days).padStart(2, "0")}`;
    return items.filter((i) => i.start_date <= end && i.end_date >= start);
  });

  function prevMonth() {
    const d = new Date(filterMonth + "-01");
    d.setMonth(d.getMonth() - 1);
    filterMonth = d.toISOString().slice(0, 7);
  }

  function nextMonth() {
    const d = new Date(filterMonth + "-01");
    d.setMonth(d.getMonth() + 1);
    filterMonth = d.toISOString().slice(0, 7);
  }

  $effect(() => { fetchItems(); });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Leave Calendar</h1>
      <p class="mt-1 text-sm text-neutral-500">Approved leave overview by month</p>
    </div>
  </div>

  <div class="flex items-center gap-3 mb-6">
    <button onclick={prevMonth} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white hover:bg-neutral-50 transition-colors">&laquo;</button>
    <span class="text-sm font-medium text-neutral-900 min-w-[160px] text-center">{monthLabel(filterMonth)}</span>
    <button onclick={nextMonth} class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white hover:bg-neutral-50 transition-colors">&raquo;</button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24"><div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div></div>
  {:else if calendarItems.length === 0}
    <div class="text-center py-24"><p class="text-sm text-neutral-500">No approved leave for this month</p></div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Employee</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Leave Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">From</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">To</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Days</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each calendarItems as item}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5 font-medium text-neutral-900">{item.employee_name}</td>
              <td class="px-5 py-3.5 text-neutral-600">{item.leave_type_name}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.start_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-xs">{item.end_date}</td>
              <td class="px-5 py-3.5 text-neutral-600 text-right">{item.total_days}{item.is_half_day ? " (½)" : ""}</td>
              <td class="px-5 py-3.5 text-center">
                <StatusBadge status={item.status} />
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
    <div class="mt-4 text-sm text-neutral-500">{calendarItems.length} leave period{calendarItems.length !== 1 ? "s" : ""} in {monthLabel(filterMonth)}</div>
  {/if}
</div>

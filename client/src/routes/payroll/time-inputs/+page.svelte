<script lang="ts">
  import { onMount } from "svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import type {
    AttendanceLogListItem,
    EmployeeDirectoryItem,
    LeaveRequestListItem,
    OvertimeRequestListItem,
    RemoteWorkLogListItem,
  } from "$lib/types";

  type TabKey = "attendance" | "overtime" | "leave" | "remote";
  type PeriodKey = "this_week" | "this_month" | "last_30_days";

  const MAX_PAGES = 10;

  const TABS: { key: TabKey; label: string; caption: string }[] = [
    { key: "attendance", label: "Attendance", caption: "Daily clock-in / clock-out capture" },
    { key: "overtime", label: "Overtime", caption: "Approved and pending overtime hours" },
    { key: "leave", label: "Leave", caption: "Time off, statutory and personal" },
    { key: "remote", label: "Remote", caption: "Off-site work and field assignments" },
  ];

  const ATTENDANCE_STATUS_CLASSES: Record<string, string> = {
    present: "bg-emerald-50 border-emerald-200 text-emerald-700",
    absent: "bg-orange-50 border-orange-200 text-orange-700",
    late: "bg-amber-50 border-amber-200 text-amber-700",
    half_day: "bg-sky-50 border-sky-200 text-sky-700",
    on_leave: "bg-neutral-100 border-neutral-200 text-neutral-700",
    remote: "bg-sky-50 border-sky-200 text-sky-700",
    holiday: "bg-neutral-100 border-neutral-200 text-neutral-600",
  };

  const OVERTIME_STATUS_CLASSES: Record<string, string> = {
    draft: "bg-neutral-100 border-neutral-200 text-neutral-600",
    pending: "bg-orange-50 border-orange-200 text-orange-700",
    approved: "bg-emerald-50 border-emerald-200 text-emerald-700",
    rejected: "bg-rose-50 border-rose-200 text-rose-700",
    cancelled: "bg-neutral-100 border-neutral-200 text-neutral-500",
  };

  const LEAVE_STATUS_CLASSES: Record<string, string> = {
    draft: "bg-neutral-100 border-neutral-200 text-neutral-600",
    pending: "bg-orange-50 border-orange-200 text-orange-700",
    approved: "bg-emerald-50 border-emerald-200 text-emerald-700",
    rejected: "bg-rose-50 border-rose-200 text-rose-700",
    cancelled: "bg-neutral-100 border-neutral-200 text-neutral-500",
  };

  const REMOTE_STATUS_CLASSES: Record<string, string> = {
    planned: "bg-sky-50 border-sky-200 text-sky-700",
    active: "bg-emerald-50 border-emerald-200 text-emerald-700",
    completed: "bg-neutral-100 border-neutral-200 text-neutral-700",
    cancelled: "bg-neutral-100 border-neutral-200 text-neutral-500",
  };

  const CHIP_BASE =
    "inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider";

  let loading = $state(true);
  let refreshing = $state(false);
  let error = $state<string | null>(null);

  let attendance = $state<AttendanceLogListItem[]>([]);
  let overtime = $state<OvertimeRequestListItem[]>([]);
  let leave = $state<LeaveRequestListItem[]>([]);
  let remote = $state<RemoteWorkLogListItem[]>([]);
  // employees retained for type symmetry / future expansion; intentionally unused otherwise.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  let employees = $state<EmployeeDirectoryItem[]>([]);

  let activeTab = $state<TabKey>("attendance");
  let searchQuery = $state("");
  let statusFilter = $state("all");
  let periodFilter = $state<PeriodKey>("this_month");

  function getSettledValue<T>(result: PromiseSettledResult<T[]>, fallback: T[]): T[] {
    return result.status === "fulfilled" ? result.value : fallback;
  }

  function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function isoDate(date: Date): string {
    return date.toISOString().slice(0, 10);
  }

  function shortDate(value: string | null | undefined): string {
    const date = parseDate(value);
    if (!date) return "—";
    return new Intl.DateTimeFormat("en-NG", { day: "numeric", month: "short", year: "numeric" }).format(date);
  }

  function shortTime(value: string | null | undefined): string {
    if (!value) return "—";
    // Server sometimes returns "HH:MM:SS" strings, sometimes ISO timestamps.
    const trimmed = value.length > 10 ? value : `1970-01-01T${value}`;
    const date = new Date(trimmed);
    if (Number.isNaN(date.getTime())) return value.slice(0, 5) || "—";
    return new Intl.DateTimeFormat("en-NG", { hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
  }

  function formatStatusLabel(value: string): string {
    return value
      .split("_")
      .map((part) => (part.length === 0 ? part : part[0].toUpperCase() + part.slice(1)))
      .join(" ");
  }

  function chipClassFor(map: Record<string, string>, key: string): string {
    return map[key] ?? "bg-neutral-100 border-neutral-200 text-neutral-600";
  }

  function periodBounds(key: PeriodKey): { start: Date; end: Date } {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const end = new Date(today);
    end.setDate(end.getDate() + 1);
    if (key === "this_week") {
      const start = new Date(today);
      const weekday = (start.getDay() + 6) % 7; // Monday=0
      start.setDate(start.getDate() - weekday);
      return { start, end };
    }
    if (key === "this_month") {
      return { start: new Date(today.getFullYear(), today.getMonth(), 1), end };
    }
    // last_30_days
    const start = new Date(today);
    start.setDate(start.getDate() - 30);
    return { start, end };
  }

  function withinPeriod(date: Date | null, bounds: { start: Date; end: Date }): boolean {
    if (!date) return false;
    return date >= bounds.start && date < bounds.end;
  }

  async function loadData(background = false) {
    if (background) refreshing = true;
    else loading = true;
    error = null;

    try {
      const results = await Promise.allSettled([
        fetchAllPages<AttendanceLogListItem>("/hr/attendance-logs/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<OvertimeRequestListItem>("/hr/overtime-requests/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<LeaveRequestListItem>("/hr/leave-requests/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<RemoteWorkLogListItem>("/hr/remote-work-logs/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<EmployeeDirectoryItem>("/hr/employee-records/", { page_size: "200" }, MAX_PAGES),
      ]);

      attendance = getSettledValue(results[0], []);
      overtime = getSettledValue(results[1], []);
      leave = getSettledValue(results[2], []);
      remote = getSettledValue(results[3], []);
      employees = getSettledValue(results[4], []);

      const allFailed = results.every((r) => r.status === "rejected");
      if (allFailed) {
        error = "We couldn't load any time-input data right now.";
      }
    } catch {
      error = "We couldn't load time-input data right now.";
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  onMount(() => {
    void loadData();
  });

  let todayIso = $derived(isoDate(new Date()));

  // KPIs (computed against full datasets, not filters)
  let attendanceDaysCurrentMonth = $derived.by(() => {
    const bounds = periodBounds("this_month");
    return attendance.filter((row) => withinPeriod(parseDate(row.date), bounds)).length;
  });

  let overtimeHoursPending = $derived.by(() =>
    overtime
      .filter((row) => row.status === "pending")
      .reduce((sum, row) => sum + toAmount(row.total_hours), 0)
  );

  let activeLeaveRequests = $derived.by(() =>
    leave.filter((row) => {
      if (row.status !== "approved") return false;
      const end = parseDate(row.end_date);
      if (!end) return false;
      end.setHours(0, 0, 0, 0);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return end.getTime() >= today.getTime();
    }).length
  );

  let remoteWorkToday = $derived.by(() =>
    remote.filter((row) => {
      if (row.date !== todayIso) return false;
      return row.status === "planned" || row.status === "active";
    }).length
  );

  // Tab-aware filter options
  let statusOptionsForTab = $derived.by<{ value: string; label: string }[]>(() => {
    if (activeTab === "attendance") {
      return [
        { value: "all", label: "All statuses" },
        { value: "present", label: "Present" },
        { value: "absent", label: "Absent" },
        { value: "late", label: "Late" },
        { value: "half_day", label: "Half Day" },
        { value: "on_leave", label: "On Leave" },
        { value: "remote", label: "Remote" },
        { value: "holiday", label: "Holiday" },
      ];
    }
    if (activeTab === "overtime") {
      return [
        { value: "all", label: "All statuses" },
        { value: "draft", label: "Draft" },
        { value: "pending", label: "Pending" },
        { value: "approved", label: "Approved" },
        { value: "rejected", label: "Rejected" },
        { value: "cancelled", label: "Cancelled" },
      ];
    }
    if (activeTab === "leave") {
      return [
        { value: "all", label: "All statuses" },
        { value: "draft", label: "Draft" },
        { value: "pending", label: "Pending" },
        { value: "approved", label: "Approved" },
        { value: "rejected", label: "Rejected" },
        { value: "cancelled", label: "Cancelled" },
      ];
    }
    return [
      { value: "all", label: "All statuses" },
      { value: "planned", label: "Planned" },
      { value: "active", label: "Active" },
      { value: "completed", label: "Completed" },
      { value: "cancelled", label: "Cancelled" },
    ];
  });

  function matchesSearch(name: string): boolean {
    if (!searchQuery.trim()) return true;
    return name.toLowerCase().includes(searchQuery.trim().toLowerCase());
  }

  let filteredAttendance = $derived.by(() => {
    const bounds = periodBounds(periodFilter);
    return attendance
      .filter((row) => withinPeriod(parseDate(row.date), bounds))
      .filter((row) => (statusFilter === "all" ? true : row.status === statusFilter))
      .filter((row) => matchesSearch(row.employee_name ?? ""))
      .sort((a, b) => (parseDate(b.date)?.getTime() ?? 0) - (parseDate(a.date)?.getTime() ?? 0));
  });

  let filteredOvertime = $derived.by(() => {
    const bounds = periodBounds(periodFilter);
    return overtime
      .filter((row) => withinPeriod(parseDate(row.date), bounds))
      .filter((row) => (statusFilter === "all" ? true : row.status === statusFilter))
      .filter((row) => matchesSearch(row.employee_name ?? ""))
      .sort((a, b) => (parseDate(b.date)?.getTime() ?? 0) - (parseDate(a.date)?.getTime() ?? 0));
  });

  let filteredLeave = $derived.by(() => {
    const bounds = periodBounds(periodFilter);
    return leave
      .filter((row) => withinPeriod(parseDate(row.start_date), bounds))
      .filter((row) => (statusFilter === "all" ? true : row.status === statusFilter))
      .filter((row) => matchesSearch(row.employee_name ?? ""))
      .sort((a, b) => (parseDate(b.start_date)?.getTime() ?? 0) - (parseDate(a.start_date)?.getTime() ?? 0));
  });

  let filteredRemote = $derived.by(() => {
    const bounds = periodBounds(periodFilter);
    return remote
      .filter((row) => withinPeriod(parseDate(row.date), bounds))
      .filter((row) => (statusFilter === "all" ? true : row.status === statusFilter))
      .filter((row) => matchesSearch(row.employee_name ?? ""))
      .sort((a, b) => (parseDate(b.date)?.getTime() ?? 0) - (parseDate(a.date)?.getTime() ?? 0));
  });

  let activeRowCount = $derived.by(() => {
    if (activeTab === "attendance") return filteredAttendance.length;
    if (activeTab === "overtime") return filteredOvertime.length;
    if (activeTab === "leave") return filteredLeave.length;
    return filteredRemote.length;
  });

  function switchTab(tab: TabKey) {
    activeTab = tab;
    statusFilter = "all";
  }
</script>

<svelte:head>
  <title>Time & Inputs | developerOS</title>
</svelte:head>

{#if loading}
  <div class="flex min-h-[60vh] items-center justify-center">
    <div class="flex items-center gap-3 text-sm text-neutral-500">
      <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
      Loading time and inputs…
    </div>
  </div>
{:else}
  <div class="space-y-4 overflow-x-clip">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
          <a href="/payroll" class="hover:text-indigo-700">Payroll</a>
          <span class="text-neutral-300"> › </span>
          <span class="text-indigo-600">Time & Inputs</span>
        </p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Time & Inputs</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Collect attendance, overtime, leave impacts, and remote work logs that feed into upcoming payroll runs.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950 disabled:opacity-50"
          onclick={() => void loadData(true)}
          disabled={refreshing}
        >
          <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
          </svg>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
        <a
          href="/hr/payroll-processing"
          class="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-800"
        >
          Open Payroll Run
        </a>
      </div>
    </div>

    {#if error}
      <DataStateBanner message={error} onretry={() => loadData(true)} retrying={refreshing} />
    {/if}

    <div class="grid gap-4 xl:grid-cols-4">
      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Attendance Days (this month)</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{attendanceDaysCurrentMonth}</p>
        <p class="mt-2 text-xs text-neutral-500">Total attendance entries logged in the current calendar month.</p>
      </div>

      <div class={`min-w-0 rounded-2xl border p-5 sm:p-6 ${overtimeHoursPending > 0 ? "border-orange-200 bg-orange-50" : "border-neutral-200 bg-white"}`}>
        <p class="text-[10px] font-semibold uppercase tracking-wider {overtimeHoursPending > 0 ? 'text-orange-600' : 'text-neutral-500'}">Overtime Hours Pending</p>
        <p class={`mt-3 text-2xl font-bold tracking-tight tabular-nums ${overtimeHoursPending > 0 ? "text-orange-900" : "text-neutral-900"}`}>
          {overtimeHoursPending.toFixed(1)} hr
        </p>
        <p class={`mt-2 text-xs ${overtimeHoursPending > 0 ? "text-orange-800/90" : "text-neutral-500"}`}>
          Awaiting approval before they roll into payroll release.
        </p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Active Leave Requests</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{activeLeaveRequests}</p>
        <p class="mt-2 text-xs text-neutral-500">Approved leave with an end date today or in the future.</p>
      </div>

      <div class="min-w-0 rounded-2xl border border-sky-200 bg-sky-50 p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-sky-600">Remote Work Today</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-sky-900">{remoteWorkToday}</p>
        <p class="mt-2 text-xs text-sky-800/90">Planned or active remote work assignments dated today.</p>
      </div>
    </div>

    <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex flex-col gap-4">
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Input Streams</p>

        <div class="flex flex-wrap items-center gap-2">
          {#each TABS as tab}
            <button
              type="button"
              class={`inline-flex flex-col items-start gap-0.5 rounded-2xl border px-4 py-2.5 text-left transition ${
                activeTab === tab.key
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-400 hover:text-neutral-950"
              }`}
              onclick={() => switchTab(tab.key)}
            >
              <span class="text-sm font-semibold">{tab.label}</span>
              <span class={`text-[10px] uppercase tracking-wider ${activeTab === tab.key ? "text-neutral-200" : "text-neutral-500"}`}>
                {tab.caption}
              </span>
            </button>
          {/each}
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search employee…"
            bind:value={searchQuery}
            class="min-w-[200px] flex-1 rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          />
          <select
            bind:value={statusFilter}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            {#each statusOptionsForTab as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select
            bind:value={periodFilter}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="this_week">This Week</option>
            <option value="this_month">This Month</option>
            <option value="last_30_days">Last 30 Days</option>
          </select>
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-600">
            {activeRowCount} {activeRowCount === 1 ? "record" : "records"}
          </span>
        </div>
      </div>

      <div class="mt-5 overflow-x-auto">
        {#if activeTab === "attendance"}
          {#if filteredAttendance.length === 0}
            <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-12 text-center text-sm text-neutral-500">
              No attendance entries match the current filters.
            </div>
          {:else}
            <table class="min-w-full text-sm">
              <thead>
                <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
                  <th class="px-4 py-3">Employee</th>
                  <th class="px-4 py-3">Date</th>
                  <th class="px-4 py-3">Status</th>
                  <th class="px-4 py-3">Clock In</th>
                  <th class="px-4 py-3">Clock Out</th>
                  <th class="px-4 py-3 text-right">Total Hours</th>
                </tr>
              </thead>
              <tbody>
                {#each filteredAttendance as row}
                  <tr class="border-t border-neutral-200 hover:bg-neutral-50">
                    <td class="px-4 py-3 font-medium text-neutral-900">{row.employee_name}</td>
                    <td class="px-4 py-3 text-neutral-700">{shortDate(row.date)}</td>
                    <td class="px-4 py-3">
                      <span class={`${CHIP_BASE} ${chipClassFor(ATTENDANCE_STATUS_CLASSES, row.status)}`}>
                        {formatStatusLabel(row.status)}
                      </span>
                    </td>
                    <td class="px-4 py-3 tabular-nums text-neutral-700">{shortTime(row.clock_in)}</td>
                    <td class="px-4 py-3 tabular-nums text-neutral-700">{shortTime(row.clock_out)}</td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {row.total_hours ? toAmount(row.total_hours).toFixed(2) : "—"}
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        {:else if activeTab === "overtime"}
          {#if filteredOvertime.length === 0}
            <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-12 text-center text-sm text-neutral-500">
              No overtime requests match the current filters.
            </div>
          {:else}
            <table class="min-w-full text-sm">
              <thead>
                <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
                  <th class="px-4 py-3">Employee</th>
                  <th class="px-4 py-3">Date</th>
                  <th class="px-4 py-3 text-right">Hours</th>
                  <th class="px-4 py-3">Status</th>
                  <th class="px-4 py-3">Approver</th>
                </tr>
              </thead>
              <tbody>
                {#each filteredOvertime as row}
                  <tr class="border-t border-neutral-200 hover:bg-neutral-50">
                    <td class="px-4 py-3 font-medium text-neutral-900">{row.employee_name}</td>
                    <td class="px-4 py-3 text-neutral-700">{shortDate(row.date)}</td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {toAmount(row.total_hours).toFixed(2)}
                    </td>
                    <td class="px-4 py-3">
                      <span class={`${CHIP_BASE} ${chipClassFor(OVERTIME_STATUS_CLASSES, row.status)}`}>
                        {formatStatusLabel(row.status)}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-neutral-700">{row.approved_by_name ?? "—"}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        {:else if activeTab === "leave"}
          {#if filteredLeave.length === 0}
            <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-12 text-center text-sm text-neutral-500">
              No leave requests match the current filters.
            </div>
          {:else}
            <table class="min-w-full text-sm">
              <thead>
                <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
                  <th class="px-4 py-3">Employee</th>
                  <th class="px-4 py-3">Type</th>
                  <th class="px-4 py-3">Start</th>
                  <th class="px-4 py-3">End</th>
                  <th class="px-4 py-3 text-right">Days</th>
                  <th class="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each filteredLeave as row}
                  <tr class="border-t border-neutral-200 hover:bg-neutral-50">
                    <td class="px-4 py-3 font-medium text-neutral-900">{row.employee_name}</td>
                    <td class="px-4 py-3 text-neutral-700">{row.leave_type_name}</td>
                    <td class="px-4 py-3 text-neutral-700">{shortDate(row.start_date)}</td>
                    <td class="px-4 py-3 text-neutral-700">{shortDate(row.end_date)}</td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {toAmount(row.total_days).toFixed(1)}
                    </td>
                    <td class="px-4 py-3">
                      <span class={`${CHIP_BASE} ${chipClassFor(LEAVE_STATUS_CLASSES, row.status)}`}>
                        {formatStatusLabel(row.status)}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        {:else}
          {#if filteredRemote.length === 0}
            <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-12 text-center text-sm text-neutral-500">
              No remote work logs match the current filters.
            </div>
          {:else}
            <table class="min-w-full text-sm">
              <thead>
                <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
                  <th class="px-4 py-3">Employee</th>
                  <th class="px-4 py-3">Date</th>
                  <th class="px-4 py-3">Location</th>
                  <th class="px-4 py-3 text-right">Hours</th>
                  <th class="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each filteredRemote as row}
                  <tr class="border-t border-neutral-200 hover:bg-neutral-50">
                    <td class="px-4 py-3 font-medium text-neutral-900">{row.employee_name}</td>
                    <td class="px-4 py-3 text-neutral-700">{shortDate(row.date)}</td>
                    <td class="px-4 py-3 text-neutral-700">{row.location || "—"}</td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {row.work_hours ? toAmount(row.work_hours).toFixed(2) : "—"}
                    </td>
                    <td class="px-4 py-3">
                      <span class={`${CHIP_BASE} ${chipClassFor(REMOTE_STATUS_CLASSES, row.status)}`}>
                        {formatStatusLabel(row.status)}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        {/if}
      </div>
    </section>
  </div>
{/if}

<script lang="ts">
  import { onMount } from "svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import { fetchAllPages } from "$lib/contracts";

  type AuditLogEntry = {
    id: number;
    timestamp: string;
    actor_email: string;
    actor_role: string;
    action_display: "Create" | "Update" | "Delete" | "Unknown";
    object_repr: string;
    content_type_name: string;
    ip_address: string;
    changes: Record<string, unknown> | unknown[] | null;
  };

  type PeriodKey = "today" | "this_week" | "this_month" | "all";

  const MAX_PAGES = 10;

  const PAYROLL_CONTENT_TYPES = new Set([
    "PayrollRun",
    "Payslip",
    "Bonus",
    "Deduction",
    "Allowance",
    "TaxRecord",
    "AttendanceLog",
    "OvertimeRequest",
    "RemoteWorkLog",
    "LeaveRequest",
  ]);

  const ACTION_CLASSES: Record<string, string> = {
    Create: "bg-emerald-50 border-emerald-200 text-emerald-700",
    Update: "bg-sky-50 border-sky-200 text-sky-700",
    Delete: "bg-rose-50 border-rose-200 text-rose-700",
    Unknown: "bg-neutral-100 border-neutral-200 text-neutral-600",
  };

  const CHIP_BASE = "inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider";

  let loading = $state(true);
  let refreshing = $state(false);
  let error = $state<string | null>(null);

  let logs = $state<AuditLogEntry[]>([]);

  let searchQuery = $state("");
  let entityFilter = $state("all");
  let actionFilter = $state("all");
  let periodFilter = $state<PeriodKey>("this_week");
  let expandedRows = $state<Set<number>>(new Set());

  function getSettledValue<T>(result: PromiseSettledResult<T[]>, fallback: T[]): T[] {
    return result.status === "fulfilled" ? result.value : fallback;
  }

  function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function relativeTime(date: Date | null): string {
    if (!date) return "—";
    const diffSeconds = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSeconds < 60) return "Just now";
    const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
    if (diffSeconds < 3600) return formatter.format(-Math.floor(diffSeconds / 60), "minute");
    if (diffSeconds < 86400) return formatter.format(-Math.floor(diffSeconds / 3600), "hour");
    if (diffSeconds < 2592000) return formatter.format(-Math.floor(diffSeconds / 86400), "day");
    if (diffSeconds < 31536000) return formatter.format(-Math.floor(diffSeconds / 2592000), "month");
    return formatter.format(-Math.floor(diffSeconds / 31536000), "year");
  }

  function fullTimestamp(value: string): string {
    const date = parseDate(value);
    if (!date) return "—";
    return new Intl.DateTimeFormat("en-NG", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(date);
  }

  function periodBounds(key: PeriodKey): { start: Date | null; end: Date | null } {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const end = new Date(today);
    end.setDate(end.getDate() + 1);
    if (key === "today") return { start: today, end };
    if (key === "this_week") {
      const start = new Date(today);
      const weekday = (start.getDay() + 6) % 7;
      start.setDate(start.getDate() - weekday);
      return { start, end };
    }
    if (key === "this_month") {
      return { start: new Date(today.getFullYear(), today.getMonth(), 1), end };
    }
    return { start: null, end: null };
  }

  function withinBounds(date: Date | null, bounds: { start: Date | null; end: Date | null }): boolean {
    if (!date) return false;
    if (bounds.start === null || bounds.end === null) return true;
    return date >= bounds.start && date < bounds.end;
  }

  async function loadData(background = false) {
    if (background) refreshing = true;
    else loading = true;
    error = null;

    try {
      const results = await Promise.allSettled([
        fetchAllPages<AuditLogEntry>("/settings/audit/logs/", { page_size: "200" }, MAX_PAGES),
      ]);

      const raw = getSettledValue(results[0], []);
      logs = raw.filter((entry) => PAYROLL_CONTENT_TYPES.has(entry.content_type_name));

      const allFailed = results.every((r) => r.status === "rejected");
      if (allFailed) error = "We couldn't reach the audit log service right now.";
    } catch {
      error = "We couldn't reach the audit log service right now.";
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  onMount(() => {
    void loadData();
  });

  // KPIs
  let eventsToday = $derived.by(() => {
    const bounds = periodBounds("today");
    return logs.filter((entry) => withinBounds(parseDate(entry.timestamp), bounds)).length;
  });

  let eventsThisWeek = $derived.by(() => {
    const bounds = periodBounds("this_week");
    return logs.filter((entry) => withinBounds(parseDate(entry.timestamp), bounds)).length;
  });

  let criticalChanges = $derived(logs.filter((entry) => entry.action_display === "Delete").length);

  let distinctActorsThisMonth = $derived.by(() => {
    const bounds = periodBounds("this_month");
    const set = new Set<string>();
    for (const entry of logs) {
      if (!withinBounds(parseDate(entry.timestamp), bounds)) continue;
      if (entry.actor_email) set.add(entry.actor_email);
    }
    return set.size;
  });

  let entityOptions = $derived.by<{ value: string; label: string }[]>(() => {
    const set = new Set<string>();
    for (const entry of logs) set.add(entry.content_type_name);
    return [
      { value: "all", label: "All entities" },
      ...[...set].sort().map((name) => ({ value: name, label: name })),
    ];
  });

  let filteredLogs = $derived.by(() => {
    const bounds = periodBounds(periodFilter);
    const needle = searchQuery.trim().toLowerCase();
    return logs
      .filter((entry) => withinBounds(parseDate(entry.timestamp), bounds))
      .filter((entry) => (entityFilter === "all" ? true : entry.content_type_name === entityFilter))
      .filter((entry) => (actionFilter === "all" ? true : entry.action_display === actionFilter))
      .filter((entry) => {
        if (!needle) return true;
        return (
          (entry.object_repr ?? "").toLowerCase().includes(needle) ||
          (entry.actor_email ?? "").toLowerCase().includes(needle)
        );
      })
      .sort((a, b) => (parseDate(b.timestamp)?.getTime() ?? 0) - (parseDate(a.timestamp)?.getTime() ?? 0))
      .slice(0, 200);
  });

  function toggleRow(id: number) {
    const next = new Set(expandedRows);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    expandedRows = next;
  }

  function changesPretty(changes: AuditLogEntry["changes"]): string {
    if (!changes) return "No structured change diff captured for this event.";
    try {
      return JSON.stringify(changes, null, 2);
    } catch {
      return String(changes);
    }
  }

  function chipClassFor(map: Record<string, string>, key: string): string {
    return map[key] ?? "bg-neutral-100 border-neutral-200 text-neutral-600";
  }
</script>

<svelte:head>
  <title>Payroll Audit Logs | developerOS</title>
</svelte:head>

{#if loading}
  <div class="flex min-h-[60vh] items-center justify-center">
    <div class="flex items-center gap-3 text-sm text-neutral-500">
      <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
      Loading audit logs…
    </div>
  </div>
{:else}
  <div class="space-y-4 overflow-x-clip">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
          <a href="/payroll" class="hover:text-indigo-700">Payroll</a>
          <span class="text-neutral-300"> › </span>
          <span class="text-indigo-600">Audit Logs</span>
        </p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payroll Audit Logs</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Review payroll-related activity — runs, payslips, bonuses, deductions, allowances, tax records, and time inputs — for control and compliance follow-up.
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
      </div>
    </div>

    {#if error}
      <DataStateBanner message={error} onretry={() => loadData(true)} retrying={refreshing} />
    {/if}

    <div class="grid gap-4 xl:grid-cols-4">
      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Events Today</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{eventsToday}</p>
        <p class="mt-2 text-xs text-neutral-500">Payroll-related audit events captured today.</p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Events This Week</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{eventsThisWeek}</p>
        <p class="mt-2 text-xs text-neutral-500">Activity volume since the start of the current week.</p>
      </div>

      <div class={`min-w-0 rounded-2xl border p-5 sm:p-6 ${criticalChanges > 0 ? "border-rose-200 bg-rose-50" : "border-neutral-200 bg-white"}`}>
        <p class={`text-[10px] font-semibold uppercase tracking-wider ${criticalChanges > 0 ? "text-rose-600" : "text-neutral-500"}`}>
          Critical Changes
        </p>
        <p class={`mt-3 text-2xl font-bold tracking-tight tabular-nums ${criticalChanges > 0 ? "text-rose-900" : "text-neutral-900"}`}>
          {criticalChanges}
        </p>
        <p class={`mt-2 text-xs ${criticalChanges > 0 ? "text-rose-800/90" : "text-neutral-500"}`}>
          Deletion events that warrant immediate review.
        </p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Distinct Actors (this month)</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{distinctActorsThisMonth}</p>
        <p class="mt-2 text-xs text-neutral-500">Unique user accounts that touched payroll records this month.</p>
      </div>
    </div>

    <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex flex-col gap-4">
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Activity Timeline</p>

        <div class="flex flex-wrap items-center gap-2">
          <input
            type="search"
            placeholder="Search by object or actor email…"
            bind:value={searchQuery}
            class="min-w-[220px] flex-1 rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          />
          <select
            bind:value={entityFilter}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            {#each entityOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select
            bind:value={actionFilter}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All actions</option>
            <option value="Create">Create</option>
            <option value="Update">Update</option>
            <option value="Delete">Delete</option>
          </select>
          <select
            bind:value={periodFilter}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="today">Today</option>
            <option value="this_week">This Week</option>
            <option value="this_month">This Month</option>
            <option value="all">All</option>
          </select>
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-600">
            {filteredLogs.length} entries
          </span>
        </div>
      </div>

      <div class="mt-5 space-y-2">
        {#if filteredLogs.length === 0}
          <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-12 text-center text-sm text-neutral-500">
            No audit events match the current filters.
          </div>
        {:else}
          {#each filteredLogs as entry (entry.id)}
            {@const isOpen = expandedRows.has(entry.id)}
            <article class="rounded-2xl border border-neutral-200 bg-white p-4 transition hover:border-neutral-300">
              <button
                type="button"
                class="flex w-full flex-col gap-2 text-left"
                onclick={() => toggleRow(entry.id)}
                aria-expanded={isOpen}
              >
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div class="flex flex-wrap items-center gap-2">
                    <span class={`${CHIP_BASE} ${chipClassFor(ACTION_CLASSES, entry.action_display)}`}>
                      {entry.action_display}
                    </span>
                    <span class="rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-neutral-700">
                      {entry.content_type_name}
                    </span>
                    <span class="text-sm font-medium text-neutral-900">{entry.object_repr || "—"}</span>
                  </div>
                  <div class="flex items-center gap-3 text-xs text-neutral-500">
                    <span title={fullTimestamp(entry.timestamp)}>{relativeTime(parseDate(entry.timestamp))}</span>
                    <svg
                      class={`h-3.5 w-3.5 transition-transform ${isOpen ? "rotate-180" : ""}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      stroke-width="2"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </div>
                </div>
                <div class="flex flex-wrap items-center gap-3 text-xs text-neutral-500">
                  <span class="font-medium text-neutral-700">{entry.actor_email || "system"}</span>
                  {#if entry.actor_role}
                    <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-600">
                      {entry.actor_role}
                    </span>
                  {/if}
                  {#if entry.ip_address}
                    <span class="tabular-nums">{entry.ip_address}</span>
                  {/if}
                  <span class="tabular-nums">{fullTimestamp(entry.timestamp)}</span>
                </div>
              </button>

              {#if isOpen}
                <div class="mt-3 border-t border-neutral-200 pt-3">
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Change Payload</p>
                  <pre class="mt-2 overflow-x-auto rounded-xl bg-neutral-900 px-4 py-3 text-xs leading-relaxed text-neutral-100">{changesPretty(entry.changes)}</pre>
                </div>
              {/if}
            </article>
          {/each}
        {/if}
      </div>
    </section>
  </div>
{/if}

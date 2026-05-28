<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";
  import type {
    RiskAlertAck,
    RiskAlertAckStatus,
    RiskAlertItem,
    RiskAlertModuleFeed,
    RiskAlertsPayload,
    RiskAlertSeverity,
  } from "$lib/types";

  type FeedKey = keyof RiskAlertsPayload["feeds"];

  const feedOrder: FeedKey[] = [
    "projects",
    "workflows",
    "finance",
    "procurement",
    "facilities",
    "crm",
  ];

  const severityTone: Record<RiskAlertSeverity, { label: string; color: string; chip: string }> = {
    critical: {
      label: "Critical",
      color: "#e11d48",
      chip: "bg-rose-100 text-rose-700 border-rose-200",
    },
    high: {
      label: "High",
      color: "#d97706",
      chip: "bg-amber-100 text-amber-700 border-amber-200",
    },
    medium: {
      label: "Medium",
      color: "#2563eb",
      chip: "bg-sky-100 text-sky-700 border-sky-200",
    },
    low: {
      label: "Low",
      color: "#16a34a",
      chip: "bg-emerald-100 text-emerald-700 border-emerald-200",
    },
  };

  const moduleColor: Record<FeedKey, string> = {
    projects: "#0ea5e9",
    workflows: "#4f46e5",
    finance: "#f97316",
    procurement: "#0f766e",
    facilities: "#7c3aed",
    crm: "#e11d48",
  };

  let loading = $state(true);
  let refreshing = $state(false);
  let data = $state<RiskAlertsPayload | null>(null);
  let selectedModule = $state<FeedKey | "all">("all");
  let requestSeq = 0;

  const PAGE_SIZE_OPTIONS = [25, 50, 100] as const;
  let pageSize = $state<(typeof PAGE_SIZE_OPTIONS)[number]>(25);
  let page = $state(1);

  let openMenuId = $state<string | null>(null);
  let pendingAlertId = $state<string | null>(null);

  const ackToneClass: Record<RiskAlertAckStatus, string> = {
    open: "bg-neutral-100 text-neutral-600 border-neutral-200",
    acknowledged: "bg-sky-100 text-sky-700 border-sky-200",
    resolved: "bg-emerald-100 text-emerald-700 border-emerald-200",
  };

  const ackLabel: Record<RiskAlertAckStatus, string> = {
    open: "Open",
    acknowledged: "Acknowledged",
    resolved: "Resolved",
  };

  function setSelectedModule(next: FeedKey | "all") {
    selectedModule = next;
    page = 1;
  }

  function toggleMenu(alertId: string) {
    openMenuId = openMenuId === alertId ? null : alertId;
  }

  function closeMenu() {
    openMenuId = null;
  }

  function applyAckLocally(alertId: string, ack: RiskAlertAck | null) {
    if (!data) return;
    const next = { ...data };
    next.recent_alerts = next.recent_alerts.map((row) =>
      row.id === alertId ? { ...row, acknowledgement: ack } : row,
    );
    next.feeds = { ...next.feeds };
    for (const key of feedOrder) {
      const feed = next.feeds[key];
      next.feeds[key] = {
        ...feed,
        items: feed.items.map((row) =>
          row.id === alertId ? { ...row, acknowledgement: ack } : row,
        ),
      };
    }
    data = next;
  }

  async function setAck(item: RiskAlertItem, status: RiskAlertAckStatus, opts: { assignToMe?: boolean } = {}) {
    closeMenu();
    pendingAlertId = item.id;
    const previous = item.acknowledgement;
    try {
      const body: Record<string, string | number> = { status };
      if (opts.assignToMe) body.assigned_to = "me";
      const ack = await api.post<RiskAlertAck>(
        `/analytics/risk-alerts/${encodeURIComponent(item.id)}/ack/`,
        body,
      );
      applyAckLocally(item.id, ack);
      toast.success(
        status === "resolved" ? "Resolved" : status === "acknowledged" ? "Acknowledged" : "Reopened",
        item.title,
      );
    } catch {
      applyAckLocally(item.id, previous);
      toast.error("Update failed", "Could not update the alert.");
    } finally {
      pendingAlertId = null;
    }
  }

  async function clearAck(item: RiskAlertItem) {
    closeMenu();
    pendingAlertId = item.id;
    const previous = item.acknowledgement;
    try {
      await api.delete(`/analytics/risk-alerts/${encodeURIComponent(item.id)}/ack/`);
      applyAckLocally(item.id, null);
      toast.success("Reopened", item.title);
    } catch {
      applyAckLocally(item.id, previous);
      toast.error("Update failed", "Could not reopen the alert.");
    } finally {
      pendingAlertId = null;
    }
  }

  function formatNumber(value: number): string {
    return Number(value || 0).toLocaleString("en-US");
  }

  function formatDate(value: string | null): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function formatAmount(value: string | null): string {
    if (!value) return "--";
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) return value;
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(parsed);
  }

  function severityClass(severity: RiskAlertSeverity): string {
    return severityTone[severity]?.chip ?? "bg-neutral-100 text-neutral-700 border-neutral-200";
  }

  function titleCase(input: string): string {
    return input
      .replaceAll("_", " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function summaryPairs(feed: RiskAlertModuleFeed): Array<[string, string | number | null]> {
    return Object.entries(feed.summary).slice(0, 4);
  }

  async function loadRiskAlerts(manual = false) {
    const seq = ++requestSeq;
    loading = data === null && !manual;
    refreshing = manual;

    try {
      const payload = await api.get<RiskAlertsPayload>("/analytics/risk-alerts/");
      if (seq !== requestSeq) return;
      data = payload;
      page = 1;
    } catch {
      if (seq !== requestSeq) return;
      data = null;
      toast.error("Load failed", "Could not load risk alerts.");
    } finally {
      if (seq !== requestSeq) return;
      loading = false;
      refreshing = false;
    }
  }

  onMount(() => {
    void loadRiskAlerts(false);
  });

  const severityRows = $derived.by(() => {
    const payload = data;
    if (!payload) return [];
    const total = Math.max(
      payload.severity_distribution.critical
        + payload.severity_distribution.high
        + payload.severity_distribution.medium
        + payload.severity_distribution.low,
      1,
    );
    return (Object.keys(severityTone) as RiskAlertSeverity[]).map((severity) => ({
      severity,
      label: severityTone[severity].label,
      count: payload.severity_distribution[severity] ?? 0,
      width: ((payload.severity_distribution[severity] ?? 0) / total) * 100,
      color: severityTone[severity].color,
    }));
  });

  const moduleRows = $derived.by(() => {
    const payload = data;
    if (!payload) return [];
    return payload.module_totals.map((row) => ({
      ...row,
      ratio:
        payload.overview.total_open_alerts > 0
          ? (row.open_alerts / payload.overview.total_open_alerts) * 100
          : 0,
    }));
  });

  const queueRows = $derived.by(() => {
    if (!data) return [];
    if (selectedModule === "all") return data.recent_alerts;
    return data.recent_alerts.filter((row) => row.module === selectedModule);
  });

  const totalRows = $derived(queueRows.length);
  const pageCount = $derived(Math.max(1, Math.ceil(totalRows / pageSize)));
  const safePage = $derived(Math.min(Math.max(1, page), pageCount));
  const pageStart = $derived(totalRows === 0 ? 0 : (safePage - 1) * pageSize + 1);
  const pageEnd = $derived(Math.min(totalRows, safePage * pageSize));
  const pagedQueueRows = $derived(queueRows.slice((safePage - 1) * pageSize, safePage * pageSize));

  $effect(() => {
    if (page > pageCount) page = pageCount;
  });

  function changePageSize(next: number) {
    pageSize = next as (typeof PAGE_SIZE_OPTIONS)[number];
    page = 1;
  }

  const criticalQueue = $derived.by(() => {
    if (!data) return [];
    const critical = data.recent_alerts.filter((row) => row.severity === "critical");
    if (critical.length > 0) return critical.slice(0, 8);
    return data.recent_alerts.filter((row) => row.severity === "high").slice(0, 8);
  });

  const feedList = $derived.by(() => {
    const payload = data;
    if (!payload) return [];
    return feedOrder.map((key) => ({ key, feed: payload.feeds[key] }));
  });

  const selectedFeed = $derived.by(() => {
    if (!data || selectedModule === "all") return null;
    return data.feeds[selectedModule];
  });
</script>

<svelte:window
  onclick={(event) => {
    if (openMenuId === null) return;
    const target = event.target as HTMLElement | null;
    if (target && target.closest("[data-row-actions]")) return;
    closeMenu();
  }}
/>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !data}
  <div class="rounded-xl border border-neutral-200 bg-white px-6 py-10 text-center">
    <p class="text-sm text-neutral-600">Risk alert feed is unavailable right now.</p>
    <button
      type="button"
      onclick={() => loadRiskAlerts(true)}
      class="mt-3 rounded-lg border border-neutral-300 bg-white px-4 py-2 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Risk Alert Center</h1>
        <p class="mt-1 text-sm text-neutral-500">Consolidated signal from every board domain feed.</p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
          Last generated: {formatDateTime(data.generated_at)}
        </span>
        <button
          type="button"
          onclick={() => loadRiskAlerts(true)}
          class="rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>
    </div>

    <section class="relative overflow-hidden rounded-xl border border-neutral-200 bg-white p-4 sm:p-5">
      <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.12),transparent_45%),radial-gradient(circle_at_bottom_right,rgba(34,197,94,0.14),transparent_50%)]"></div>
      <div class="relative grid gap-4 xl:grid-cols-[1.15fr_1fr_1fr]">
        <div class="rounded-xl border border-neutral-200 bg-white/90 p-4">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Global Risk Snapshot</h2>
            <p class="mt-1 text-[11px] text-neutral-500">
              Open exposure, critical pressure, and seven-day resolution throughput.
            </p>
          </div>
          <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-neutral-500">Open Alerts</p>
              <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{formatNumber(data.overview.total_open_alerts)}</p>
            </div>
            <div class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-rose-600">Critical</p>
              <p class="mt-1 text-lg font-bold text-rose-700 tabular-nums">{formatNumber(data.overview.critical_alerts)}</p>
            </div>
            <div class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-amber-600">Watch</p>
              <p class="mt-1 text-lg font-bold text-amber-700 tabular-nums">{formatNumber(data.overview.watch_alerts)}</p>
            </div>
            <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wider text-emerald-600">Resolved 7d</p>
              <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{formatNumber(data.overview.resolved_last_7_days)}</p>
            </div>
          </div>

          <div class="mt-4 h-3 overflow-hidden rounded-full bg-neutral-200">
            <div class="flex h-full w-full">
              {#each severityRows as row}
                <div style="width: {row.width}%; background: {row.color};"></div>
              {/each}
            </div>
          </div>
          <div class="mt-2 flex flex-wrap gap-2">
            {#each severityRows as row}
              <span class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold {severityClass(row.severity)}">
                <span class="h-1.5 w-1.5 rounded-full" style="background: {row.color};"></span>
                {row.label}: {formatNumber(row.count)}
              </span>
            {/each}
          </div>
        </div>

        <div class="rounded-xl border border-neutral-200 bg-white/90 p-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-600">Module Pressure Map</h2>
          <div class="mt-3 space-y-2">
            {#each moduleRows as module}
              <div class="grid grid-cols-[84px_1fr_auto] items-center gap-2 text-[11px]">
                <span class="font-medium text-neutral-700">{module.label}</span>
                <div class="h-2 overflow-hidden rounded-full bg-neutral-200">
                  <div class="h-full rounded-full" style="width: {module.ratio}%; background: {moduleColor[module.module]};"></div>
                </div>
                <span class="tabular-nums font-semibold text-neutral-700">{module.open_alerts}</span>
              </div>
            {/each}
          </div>
          <div class="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-[11px] text-neutral-600">
            {formatNumber(data.overview.modules_affected)} of {moduleRows.length} modules currently have active risk pressure.
          </div>
        </div>

        <div class="rounded-xl border border-neutral-200 bg-white/90 p-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-600">Immediate Response Queue</h2>
          <div class="mt-3 space-y-2">
            {#if criticalQueue.length === 0}
              <div class="rounded-lg border border-dashed border-neutral-200 px-3 py-4 text-center text-xs text-neutral-500">
                No critical or high alerts in queue.
              </div>
            {:else}
              {#each criticalQueue as item}
                <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
                  <div class="flex items-center justify-between gap-2">
                    <p class="truncate text-xs font-semibold text-neutral-900">{item.title}</p>
                    <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {severityClass(item.severity)}">
                      {titleCase(item.severity)}
                    </span>
                  </div>
                  <p class="mt-1 truncate text-[11px] text-neutral-600">{item.module_label} · {item.note}</p>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </section>

    <section class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Unified Alert Stream</h2>
          <div class="flex items-center gap-2">
            <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-600">
              {totalRows === 0 ? "0 rows" : `${formatNumber(pageStart)}–${formatNumber(pageEnd)} of ${formatNumber(totalRows)}`}
            </span>
            <label class="inline-flex items-center gap-1 text-[10px] text-neutral-500">
              Rows
              <select
                value={pageSize}
                onchange={(e) => changePageSize(Number((e.currentTarget as HTMLSelectElement).value))}
                class="rounded-md border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] font-semibold text-neutral-700 focus:border-neutral-400 focus:outline-none"
              >
                {#each PAGE_SIZE_OPTIONS as opt}
                  <option value={opt}>{opt}</option>
                {/each}
              </select>
            </label>
          </div>
        </div>
        <div class="overflow-x-auto rounded-xl border border-neutral-200">
          <table class="min-w-full text-xs">
            <thead class="bg-neutral-50 text-neutral-500">
              <tr>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Severity</th>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Module</th>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Alert</th>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Owner</th>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Due</th>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Amount</th>
                <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Status</th>
                <th class="px-3 py-2 text-right font-semibold uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#if totalRows === 0}
                <tr>
                  <td colspan="8" class="px-3 py-6 text-center text-neutral-500">No alerts for this filter.</td>
                </tr>
              {:else}
                {#each pagedQueueRows as item}
                  {@const ack = item.acknowledgement}
                  {@const ackStatus = (ack?.status ?? "open") as RiskAlertAckStatus}
                  {@const isPending = pendingAlertId === item.id}
                  <tr class="border-t border-neutral-100 text-neutral-700 hover:bg-neutral-50 {ackStatus === 'resolved' ? 'opacity-60' : ''}">
                    <td class="px-3 py-2.5">
                      <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {severityClass(item.severity)}">
                        {titleCase(item.severity)}
                      </span>
                    </td>
                    <td class="px-3 py-2.5">{item.module_label}</td>
                    <td class="px-3 py-2.5">
                      <p class="max-w-[220px] truncate font-semibold text-neutral-900">{item.title}</p>
                      <p class="max-w-[220px] truncate text-[10px] text-neutral-500">{item.subject}</p>
                      {#if ack?.assigned_to_name}
                        <p class="text-[10px] text-sky-700">Assigned: {ack.assigned_to_name}</p>
                      {/if}
                    </td>
                    <td class="px-3 py-2.5">{item.owner || "--"}</td>
                    <td class="px-3 py-2.5">{formatDate(item.due_date)}</td>
                    <td class="px-3 py-2.5 tabular-nums">{formatAmount(item.amount)}</td>
                    <td class="px-3 py-2.5">
                      <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {ackToneClass[ackStatus]}">
                        {ackLabel[ackStatus]}
                      </span>
                    </td>
                    <td class="px-3 py-2.5 text-right">
                      <div class="relative inline-block" data-row-actions>
                        <button
                          type="button"
                          onclick={(event) => { event.stopPropagation(); toggleMenu(item.id); }}
                          disabled={isPending}
                          aria-label="Alert actions"
                          aria-expanded={openMenuId === item.id}
                          class="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-neutral-200 bg-white text-neutral-500 hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {#if isPending}
                            <span class="inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-neutral-300 border-t-neutral-700"></span>
                          {:else}
                            ⋯
                          {/if}
                        </button>
                        {#if openMenuId === item.id}
                          <div
                            role="menu"
                            class="absolute right-0 top-full z-20 mt-1 w-48 overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-lg"
                          >
                            {#if ackStatus !== "acknowledged"}
                              <button
                                type="button"
                                role="menuitem"
                                onclick={() => setAck(item, "acknowledged")}
                                class="block w-full px-3 py-2 text-left text-[11px] text-neutral-700 hover:bg-neutral-50"
                              >
                                Acknowledge
                              </button>
                            {/if}
                            {#if ackStatus !== "resolved"}
                              <button
                                type="button"
                                role="menuitem"
                                onclick={() => setAck(item, "resolved")}
                                class="block w-full px-3 py-2 text-left text-[11px] text-neutral-700 hover:bg-neutral-50"
                              >
                                Resolve
                              </button>
                            {/if}
                            <button
                              type="button"
                              role="menuitem"
                              onclick={() => setAck(item, ackStatus === "resolved" ? "resolved" : "acknowledged", { assignToMe: true })}
                              class="block w-full px-3 py-2 text-left text-[11px] text-neutral-700 hover:bg-neutral-50"
                            >
                              Assign to me
                            </button>
                            {#if ack !== null}
                              <button
                                type="button"
                                role="menuitem"
                                onclick={() => clearAck(item)}
                                class="block w-full border-t border-neutral-100 px-3 py-2 text-left text-[11px] text-neutral-700 hover:bg-neutral-50"
                              >
                                Reopen
                              </button>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>

        {#if totalRows > 0 && pageCount > 1}
          <div class="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-neutral-600">
            <span>Page <span class="font-semibold text-neutral-900 tabular-nums">{safePage}</span> of <span class="tabular-nums">{pageCount}</span></span>
            <div class="flex items-center gap-1">
              <button
                type="button"
                onclick={() => (page = 1)}
                disabled={safePage === 1}
                class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                First
              </button>
              <button
                type="button"
                onclick={() => (page = safePage - 1)}
                disabled={safePage === 1}
                class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Prev
              </button>
              <button
                type="button"
                onclick={() => (page = safePage + 1)}
                disabled={safePage === pageCount}
                class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
              <button
                type="button"
                onclick={() => (page = pageCount)}
                disabled={safePage === pageCount}
                class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Last
              </button>
            </div>
          </div>
        {/if}
      </div>

      <aside class="space-y-3">
        <section class="rounded-xl border border-neutral-200 bg-white p-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-600">Feed Filter</h2>
          <div class="mt-3 grid grid-cols-2 gap-2">
            <button
              type="button"
              onclick={() => setSelectedModule("all")}
              class="rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors
                {selectedModule === 'all'
                  ? 'border-neutral-900 bg-neutral-900 text-white'
                  : 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300'}"
            >
              All Feeds
            </button>
            {#each feedOrder as key}
              <button
                type="button"
                onclick={() => setSelectedModule(key)}
                class="rounded-lg border px-2 py-1.5 text-[11px] font-semibold transition-colors
                  {selectedModule === key
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300'}"
              >
                {data.feeds[key].label}
              </button>
            {/each}
          </div>
        </section>

        <section class="rounded-xl border border-neutral-200 bg-white p-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-600">
            {selectedModule === "all" ? "Module Ranking" : `${selectedFeed?.label ?? "Feed"} Summary`}
          </h2>
          {#if selectedModule === "all"}
            <div class="mt-3 space-y-2">
              {#each moduleRows.slice().sort((a, b) => b.open_alerts - a.open_alerts) as module}
                <div class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-[11px]">
                  <span class="font-medium text-neutral-700">{module.label}</span>
                  <span class="tabular-nums font-semibold text-neutral-900">{module.open_alerts}</span>
                </div>
              {/each}
            </div>
          {:else if selectedFeed}
            <div class="mt-3 space-y-2">
              {#each summaryPairs(selectedFeed) as [key, value]}
                <div class="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-[11px]">
                  <span class="text-neutral-600">{titleCase(key)}</span>
                  <span class="tabular-nums font-semibold text-neutral-900">
                    {typeof value === "number" ? formatNumber(value) : value ?? "--"}
                  </span>
                </div>
              {/each}
            </div>
          {/if}
        </section>
      </aside>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">All Domain Feeds</h2>
      <p class="mt-1 text-xs text-neutral-500">Every risk feed remains visible here with its own records and summary context.</p>
      <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {#each feedList as { key, feed }}
          <article class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-3">
            <div class="flex items-center justify-between gap-2">
              <div class="inline-flex items-center gap-2">
                <span class="h-2.5 w-2.5 rounded-full" style="background: {moduleColor[key]};"></span>
                <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-800">{feed.label}</h3>
              </div>
              <span class="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-neutral-700">
                {feed.open_alerts} open
              </span>
            </div>

            <div class="mt-2 h-2 overflow-hidden rounded-full bg-neutral-200">
              <div class="flex h-full w-full">
                <div style="width: {(feed.critical_alerts / Math.max(feed.open_alerts, 1)) * 100}%; background: {severityTone.critical.color};"></div>
                <div style="width: {(feed.high_alerts / Math.max(feed.open_alerts, 1)) * 100}%; background: {severityTone.high.color};"></div>
                <div style="width: {(feed.medium_alerts / Math.max(feed.open_alerts, 1)) * 100}%; background: {severityTone.medium.color};"></div>
                <div style="width: {(feed.low_alerts / Math.max(feed.open_alerts, 1)) * 100}%; background: {severityTone.low.color};"></div>
              </div>
            </div>

            <div class="mt-3 space-y-1.5">
              {#if feed.items.length === 0}
                <div class="rounded-lg border border-dashed border-neutral-200 bg-white px-3 py-3 text-center text-[11px] text-neutral-500">
                  No active alerts in this feed.
                </div>
              {:else}
                {#each feed.items.slice(0, 3) as item}
                  <div class="rounded-lg border border-neutral-200 bg-white px-2.5 py-2">
                    <div class="flex items-center justify-between gap-2">
                      <p class="truncate text-[11px] font-semibold text-neutral-900">{item.title}</p>
                      <span class="rounded-full border px-1.5 py-0.5 text-[10px] font-semibold {severityClass(item.severity)}">
                        {titleCase(item.severity)}
                      </span>
                    </div>
                    <p class="mt-1 truncate text-[10px] text-neutral-500">{item.note}</p>
                  </div>
                {/each}
              {/if}
            </div>
          </article>
        {/each}
      </div>
    </section>
  </div>
{/if}

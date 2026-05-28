<script lang="ts">
  import { api } from "$lib/api";

  type AuditEvent = {
    id: number;
    event_type: string;
    event_type_display: string;
    status: "success" | "failed" | "info";
    status_display: string;
    severity: "low" | "medium" | "high" | "critical";
    severity_display: string;
    actor_id: number | null;
    actor_email: string;
    actor_name: string;
    principal: string;
    provider: string;
    ip_address: string | null;
    user_agent: string;
    device_label: string;
    target_type: string;
    target_id: string;
    detail: string;
    metadata: Record<string, unknown>;
    occurred_at: string;
  };

  type AuditOverview = {
    total: number;
    recent_24h: number;
    by_severity: Record<string, number>;
  };

  type AuditEventsResponse = {
    count: number;
    results: AuditEvent[];
    overview: AuditOverview;
  };

  type Props = {
    eventTypes?: string[];
    severities?: string[];
    status?: string;
    emptyText?: string;
    showSeverity?: boolean;
    showStatus?: boolean;
  };

  let {
    eventTypes = [],
    severities = [],
    status: statusFilter = "",
    emptyText = "No matching audit events.",
    showSeverity = true,
    showStatus = true,
  }: Props = $props();

  let events = $state<AuditEvent[]>([]);
  let overview = $state<AuditOverview>({ total: 0, recent_24h: 0, by_severity: {} });
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  const pageSize = 50;
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let search = $state("");
  let debounceTimer: ReturnType<typeof setTimeout>;

  let expandedId = $state<number | null>(null);

  function formatDate(d: string): string {
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit", second: "2-digit",
    });
  }

  function relativeTime(d: string): string {
    const diff = Date.now() - new Date(d).getTime();
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return `${sec}s ago`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    const day = Math.floor(hr / 24);
    if (day < 7) return `${day}d ago`;
    return formatDate(d);
  }

  function severityClasses(s: string): string {
    return ({
      low: "bg-neutral-100 text-neutral-600",
      medium: "bg-yellow-50 text-yellow-700",
      high: "bg-orange-50 text-orange-700",
      critical: "bg-red-50 text-red-700",
    } as Record<string, string>)[s] ?? "bg-neutral-100 text-neutral-600";
  }

  function statusClasses(s: string): string {
    return ({
      success: "bg-green-50 text-green-700",
      failed: "bg-red-50 text-red-700",
      info: "bg-blue-50 text-blue-700",
    } as Record<string, string>)[s] ?? "bg-neutral-100 text-neutral-600";
  }

  async function fetchEvents() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (eventTypes.length) params.event_type = eventTypes.join(",");
      if (severities.length) params.severity = severities.join(",");
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      const res = await api.get<AuditEventsResponse>("/iam/audit/events/", params);
      events = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      events = [];
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
    void currentPage;
    fetchEvents();
  });
</script>

<div class="space-y-5">
  <!-- Stat cards -->
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">Matching events</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.total}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-blue-600 uppercase tracking-wider">In the last 24h</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.recent_24h}</p>
    </div>
    {#if showSeverity}
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">By severity</p>
        <div class="mt-2 flex items-baseline gap-3 text-sm">
          <span class="font-semibold text-neutral-900">L {overview.by_severity.low ?? 0}</span>
          <span class="font-semibold text-yellow-700">M {overview.by_severity.medium ?? 0}</span>
          <span class="font-semibold text-orange-700">H {overview.by_severity.high ?? 0}</span>
          <span class="font-semibold text-red-700">C {overview.by_severity.critical ?? 0}</span>
        </div>
      </div>
    {/if}
  </div>

  <!-- Search -->
  <div class="relative max-w-sm">
    <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
    </svg>
    <input type="text" placeholder="Search by detail, IP, email…" oninput={onSearchInput}
      class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 placeholder:text-neutral-400" />
  </div>

  <!-- Events table -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if events.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">{emptyText}</h3>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">When</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Event</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Actor</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">IP</th>
            {#if showStatus}
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            {/if}
            {#if showSeverity}
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Severity</th>
            {/if}
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each events as ev}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer"
              onclick={() => (expandedId = expandedId === ev.id ? null : ev.id)}>
              <td class="px-5 py-3 text-neutral-600 whitespace-nowrap">
                <p>{relativeTime(ev.occurred_at)}</p>
                <p class="text-[10px] text-neutral-400">{formatDate(ev.occurred_at)}</p>
              </td>
              <td class="px-5 py-3">
                <p class="font-medium text-neutral-800">{ev.event_type_display}</p>
                {#if ev.detail}
                  <p class="mt-0.5 text-xs text-neutral-500 max-w-md truncate">{ev.detail}</p>
                {/if}
              </td>
              <td class="px-5 py-3">
                <p class="text-neutral-700 truncate max-w-[14rem]">{ev.actor_name}</p>
                {#if ev.actor_email && ev.actor_email !== ev.actor_name}
                  <p class="text-[11px] text-neutral-500 truncate">{ev.actor_email}</p>
                {/if}
              </td>
              <td class="px-5 py-3 text-neutral-600 font-mono text-xs">{ev.ip_address || "—"}</td>
              {#if showStatus}
                <td class="px-5 py-3 text-center">
                  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {statusClasses(ev.status)}">
                    {ev.status_display}
                  </span>
                </td>
              {/if}
              {#if showSeverity}
                <td class="px-5 py-3 text-center">
                  <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {severityClasses(ev.severity)}">
                    {ev.severity_display}
                  </span>
                </td>
              {/if}
            </tr>
            {#if expandedId === ev.id}
              <tr class="bg-neutral-50">
                <td colspan={2 + (showStatus ? 1 : 0) + (showSeverity ? 1 : 0) + 3} class="px-5 py-4 text-xs">
                  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p class="font-semibold text-neutral-700 mb-1.5">Context</p>
                      <dl class="space-y-1 text-neutral-600">
                        <div class="flex gap-2"><dt class="text-neutral-400 w-24 shrink-0">Target</dt><dd>{ev.target_type ? `${ev.target_type} #${ev.target_id || "—"}` : "—"}</dd></div>
                        <div class="flex gap-2"><dt class="text-neutral-400 w-24 shrink-0">Provider</dt><dd>{ev.provider || "—"}</dd></div>
                        <div class="flex gap-2"><dt class="text-neutral-400 w-24 shrink-0">Device</dt><dd class="break-all">{ev.device_label || ev.user_agent || "—"}</dd></div>
                      </dl>
                    </div>
                    <div>
                      <p class="font-semibold text-neutral-700 mb-1.5">Metadata</p>
                      {#if Object.keys(ev.metadata).length === 0}
                        <p class="text-neutral-500 italic">none</p>
                      {:else}
                        <pre class="bg-white border border-neutral-200 rounded p-2 text-[11px] text-neutral-700 max-h-40 overflow-auto">{JSON.stringify(ev.metadata, null, 2)}</pre>
                      {/if}
                    </div>
                  </div>
                </td>
              </tr>
            {/if}
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

<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    SupportDeskAgentWorkloadItem,
    SupportDeskBreakdownItem,
    SupportDeskOverview,
    SupportTicketListItem,
  } from "$lib/types";

  type MetricTone = "neutral" | "alert" | "positive";

  type SummaryMetric = {
    label: string;
    value: string;
    helper: string;
    tone: MetricTone;
    icon: string;
  };

  type BreakdownRow = {
    label: string;
    value: string;
    share: number;
    note: string;
    barClass: string;
  };

  type SecondaryMetric = {
    label: string;
    value: string;
    helper: string;
  };

  const priorityBarClasses: Record<string, string> = {
    critical: "bg-red-500",
    high: "bg-orange-500",
    medium: "bg-amber-400",
    low: "bg-emerald-500",
  };

  const statusBarClasses: Record<string, string> = {
    open: "bg-sky-500",
    in_progress: "bg-neutral-800",
    pending_requester: "bg-violet-500",
    escalated: "bg-rose-500",
    resolved: "bg-emerald-500",
    closed: "bg-neutral-400",
  };

  const summaryIcons = {
    openTickets: "M4.5 7.5A2.25 2.25 0 0 1 6.75 5.25h10.5A2.25 2.25 0 0 1 19.5 7.5v2.25a1.5 1.5 0 0 0 0 3V15a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 15v-2.25a1.5 1.5 0 0 0 0-3V7.5Z",
    slaBreaches: "M12 9v3.75m0 3.75h.008v.008H12v-.008Zm9-3.758a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    resolution: "M12 6v6l3.75 2.25m5.25-2.25a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    workload: "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
    csat: "M9.813 15.904 9 18.75l-2.063-1.547A9 9 0 1 1 21 12c0 1.128-.207 2.209-.585 3.206a9.023 9.023 0 0 1-3.226 4.12c-.457.298-.836.674-1.11 1.11L15 21l-1.813-3.172a2.25 2.25 0 0 0-1.45-1.077l-1.924-.481Z",
    requests: "M7.5 3.75h9A2.25 2.25 0 0 1 18.75 6v12A2.25 2.25 0 0 1 16.5 20.25h-9A2.25 2.25 0 0 1 5.25 18V6A2.25 2.25 0 0 1 7.5 3.75Zm2.25 4.5h4.5m-4.5 3.75h4.5m-4.5 3.75h3",
  };

  let loading = $state(true);
  let errorMessage = $state("");
  let overview = $state<SupportDeskOverview | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function metricCardClasses(tone: MetricTone): string {
    if (tone === "alert") return "border-red-200 bg-[linear-gradient(180deg,#ffffff,#fef2f2)]";
    if (tone === "positive") return "border-emerald-200 bg-[linear-gradient(180deg,#ffffff,#f0fdf4)]";
    return "border-neutral-200 bg-white";
  }

  function metricIconClasses(tone: MetricTone): string {
    if (tone === "alert") return "bg-red-100 text-red-700";
    if (tone === "positive") return "bg-emerald-100 text-emerald-700";
    return "bg-neutral-100 text-neutral-700";
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatCompact(value: number | null): string {
    if (value === null) return "--";
    return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
  }

  function totalCount(rows: SupportDeskBreakdownItem[]): number {
    return rows.reduce((sum, row) => sum + row.count, 0);
  }

  function buildBreakdownRows(
    rows: SupportDeskBreakdownItem[],
    barClasses: Record<string, string>,
    emptyMessage: string,
  ): BreakdownRow[] {
    const total = totalCount(rows);
    return rows.map((row) => ({
      label: row.label,
      value: String(row.count),
      share: total > 0 ? Math.max(6, Math.round((row.count / total) * 100)) : 0,
      note: total > 0 ? `${row.count} of ${total} tickets in this bucket.` : emptyMessage,
      barClass: barClasses[row.key] ?? "bg-neutral-400",
    }));
  }

  function buildSummaryMetrics(data: SupportDeskOverview): SummaryMetric[] {
    return [
      {
        label: "Open Tickets",
        value: String(data.open_tickets),
        helper: data.open_tickets > 0 ? "Active queue items currently awaiting support handling." : "No open tickets in the queue.",
        tone: "neutral",
        icon: summaryIcons.openTickets,
      },
      {
        label: "SLA Breaches",
        value: String(data.sla_breaches),
        helper: data.sla_breaches > 0 ? "Tickets have crossed their SLA deadline and need intervention." : "No active SLA breaches right now.",
        tone: data.sla_breaches > 0 ? "alert" : "positive",
        icon: summaryIcons.slaBreaches,
      },
      {
        label: "Avg. Resolution Time",
        value: data.average_resolution_time_display,
        helper: data.average_resolution_time_hours !== null ? "Calculated from tickets that have already been resolved." : "No resolved ticket history yet.",
        tone: data.average_resolution_time_hours !== null ? "positive" : "neutral",
        icon: summaryIcons.resolution,
      },
      {
        label: "Agent Workload",
        value: `${data.agent_workload.length}`,
        helper: data.agent_workload.length > 0 ? "Agents with active work are listed in the workload panel." : "No active agent workload is recorded yet.",
        tone: "neutral",
        icon: summaryIcons.workload,
      },
      {
        label: "Customer Satisfaction",
        value: data.customer_satisfaction_display,
        helper: data.customer_satisfaction_score !== null ? "Average CSAT from tickets with submitted feedback." : "Feedback data has not been captured yet.",
        tone: data.customer_satisfaction_score !== null ? "positive" : "neutral",
        icon: summaryIcons.csat,
      },
      {
        label: "Recent Requests",
        value: String(data.recent_requests.length),
        helper: data.recent_requests.length > 0 ? "Latest requests are listed below for fast intake review." : "No recent request activity yet.",
        tone: "neutral",
        icon: summaryIcons.requests,
      },
    ];
  }

  function buildSecondaryMetrics(data: SupportDeskOverview): SecondaryMetric[] {
    return [
      {
        label: "First Response Time",
        value: data.first_response_time_display,
        helper: data.first_response_time_hours !== null ? "Average time taken before the first requester-facing reply." : "No first-response telemetry yet.",
      },
      {
        label: "Ticket Backlog",
        value: String(data.ticket_backlog),
        helper: data.ticket_backlog > 0 ? "Open and pending queue depth across the current organization." : "Backlog is currently clear.",
      },
      {
        label: "Escalated Tickets",
        value: String(data.escalated_tickets),
        helper: data.escalated_tickets > 0 ? "Tickets currently sitting in an escalated state." : "No escalations are currently active.",
      },
      {
        label: "Customer Satisfaction Score",
        value: data.customer_satisfaction_display,
        helper: data.customer_satisfaction_score !== null ? "Average score out of five from ticket feedback." : "Waiting for ticket feedback submissions.",
      },
    ];
  }

  async function loadOverview() {
    loading = true;
    errorMessage = "";
    try {
      overview = await api.get<SupportDeskOverview>("/support-desk/overview/");
    } catch (error) {
      overview = null;
      errorMessage = parseError(error, "Could not load the Support Desk overview.");
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    void loadOverview();
  });

  const live = useLiveKpis(
    ["Ticket"],
    loadOverview,
    { debounceMs: 3000 },
  );

  let summaryMetrics = $derived(overview ? buildSummaryMetrics(overview) : []);
  let priorityBreakdown = $derived(
    overview
      ? buildBreakdownRows(overview.tickets_by_priority, priorityBarClasses, "No priority distribution is available yet.")
      : [],
  );
  let statusBreakdown = $derived(
    overview
      ? buildBreakdownRows(overview.tickets_by_status, statusBarClasses, "No status distribution is available yet.")
      : [],
  );
  let secondaryMetrics = $derived(overview ? buildSecondaryMetrics(overview) : []);
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
  </div>
{:else if errorMessage}
  <div class="rounded-3xl border border-red-200 bg-red-50 p-6 text-red-800">
    <h1 class="text-lg font-semibold">Support dashboard unavailable</h1>
    <p class="mt-2 text-sm">{errorMessage}</p>
    <button
      type="button"
      onclick={() => loadOverview()}
      class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else if overview}
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div class="flex items-center gap-2">
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-teal-600">Support Desk</p>
          <LiveBadge refreshing={live.refreshing} />
        </div>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Support Desk Control Center</h1>
        <p class="mt-1 text-sm text-neutral-500">Live queue, SLA, workload, and satisfaction data for your organization.</p>
      </div>
      <a
        href="/support-desk/tickets"
        class="shrink-0 rounded-lg bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        Open Tickets Workspace
      </a>
    </div>

    <!-- KPI Cards -->
    <div class="grid gap-2 md:grid-cols-2 xl:grid-cols-6">
      {#each summaryMetrics as metric}
        <div class="rounded-xl border border-neutral-200 bg-emerald-50 px-4 py-2.5 text-center">
          <p class="text-lg font-bold text-neutral-800 tabular-nums">{metric.value}</p>
          <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">{metric.label}</p>
        </div>
      {/each}
    </div>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,1.05fr)_minmax(320px,0.9fr)]">
      <section class="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-neutral-800">Tickets by Priority</h2>
            <p class="mt-1 text-sm text-neutral-500">Priority distribution across the current support queue.</p>
          </div>
          <div class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
            {totalCount(overview.tickets_by_priority)} total
          </div>
        </div>

        <div class="mt-6 space-y-5">
          {#each priorityBreakdown as row}
            <div class="space-y-2">
              <div class="flex items-center justify-between gap-4">
                <div class="flex items-center gap-3">
                  <div class={`h-2.5 w-2.5 rounded-full ${row.barClass}`}></div>
                  <p class="text-sm font-medium text-neutral-800">{row.label}</p>
                </div>
                <p class="text-sm font-semibold text-neutral-500">{row.value}</p>
              </div>
              <div class="h-2 rounded-full bg-neutral-100">
                <div class={`h-2 rounded-full ${row.barClass}`} style={`width: ${row.share}%`}></div>
              </div>
              <p class="text-xs text-neutral-500">{row.note}</p>
            </div>
          {/each}
        </div>
      </section>

      <section class="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-neutral-800">Tickets by Status</h2>
            <p class="mt-1 text-sm text-neutral-500">Queue state coverage from intake through closure.</p>
          </div>
          <div class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">
            {totalCount(overview.tickets_by_status)} total
          </div>
        </div>

        <div class="mt-6 space-y-5">
          {#each statusBreakdown as row}
            <div class="space-y-2">
              <div class="flex items-center justify-between gap-4">
                <div class="flex items-center gap-3">
                  <div class={`h-2.5 w-2.5 rounded-full ${row.barClass}`}></div>
                  <p class="text-sm font-medium text-neutral-800">{row.label}</p>
                </div>
                <p class="text-sm font-semibold text-neutral-500">{row.value}</p>
              </div>
              <div class="h-2 rounded-full bg-neutral-100">
                <div class={`h-2 rounded-full ${row.barClass}`} style={`width: ${row.share}%`}></div>
              </div>
              <p class="text-xs text-neutral-500">{row.note}</p>
            </div>
          {/each}
        </div>
      </section>

      <section class="space-y-6">
        <article class="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-neutral-800">Agent Workload</h2>
              <p class="mt-1 text-sm text-neutral-500">Distribution of active work across the busiest support agents.</p>
            </div>
            <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-neutral-100 text-neutral-700">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
                <path stroke-linecap="round" stroke-linejoin="round" d={summaryIcons.workload} />
              </svg>
            </div>
          </div>

          <div class="mt-6 space-y-3">
            {#if overview.agent_workload.length === 0}
              <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-5 py-6">
                <p class="text-sm font-medium text-neutral-800">No active workload yet</p>
                <p class="mt-2 text-sm leading-6 text-neutral-500">Agent assignment data will populate here once tickets are owned.</p>
              </div>
            {:else}
              {#each overview.agent_workload as agent}
                <div class="rounded-2xl border border-neutral-200 px-4 py-4">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-sm font-semibold text-neutral-800">{agent.agent_name}</p>
                      <p class="mt-1 text-xs text-neutral-500">{agent.active_tickets} active tickets</p>
                    </div>
                    <span class={`rounded-full px-2.5 py-1 text-xs font-semibold ${agent.sla_breaches > 0 ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'}`}>
                      {agent.sla_breaches > 0 ? `${agent.sla_breaches} breaches` : "On SLA"}
                    </span>
                  </div>
                </div>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-3xl border border-neutral-200 bg-white p-7 shadow-sm">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-neutral-800">Recent Requests</h2>
              <p class="mt-1 text-sm text-neutral-500">Newest ticket intake across the current support queue.</p>
            </div>
            <a href="/support-desk/tickets" class="text-xs font-semibold text-neutral-800 hover:text-neutral-700">
              View all
            </a>
          </div>

          <div class="mt-6 space-y-3">
            {#if overview.recent_requests.length === 0}
              <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-5 py-6">
                <p class="text-sm font-medium text-neutral-800">No requests recorded yet</p>
                <p class="mt-2 text-sm leading-6 text-neutral-500">The recent request feed will populate as tickets are created.</p>
              </div>
            {:else}
              {#each overview.recent_requests as ticket}
                <a href="/support-desk/tickets" class="block rounded-2xl border border-neutral-200 px-4 py-4 hover:border-neutral-300 hover:bg-neutral-50">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-sm font-semibold text-neutral-800">{ticket.ticket_id} • {ticket.subject}</p>
                      <p class="mt-1 text-sm text-neutral-500">{ticket.requester_name || "Unknown requester"} • {ticket.department_name || "No department"}</p>
                    </div>
                    <span class="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold text-neutral-700">
                      {ticket.status_display}
                    </span>
                  </div>
                  <p class="mt-3 text-xs text-neutral-500">Created {formatDateTime(ticket.created_at)}</p>
                </a>
              {/each}
            {/if}
          </div>
        </article>
      </section>
    </div>

    <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {#each secondaryMetrics as metric}
        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <p class="text-[11px] font-bold uppercase tracking-[0.16em] text-neutral-400">{metric.label}</p>
          <p class="mt-3 text-xl font-bold tracking-tight text-neutral-800">{metric.value}</p>
          <p class="mt-3 text-sm leading-6 text-neutral-500">{metric.helper}</p>
        </article>
      {/each}
    </section>
  </div>
{/if}

<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    BrokerPerformanceOverview,
    CommunicationOverview,
    FollowUpTaskListItem,
    LeadListItem,
    PaginatedResponse,
    PipelineOverview,
    PipelineStage,
    ReservationOverview,
  } from "$lib/types";

  type PeriodWindow = "1" | "3" | "6" | "12";
  type OwnerScope = "all" | "assigned" | "unassigned";
  type PaginatedBucket<T> = { rows: T[]; total: number };

  const stageOrder: PipelineStage[] = [
    "inquiry",
    "qualified",
    "site_visit",
    "offer_made",
    "reservation",
    "spa_issued",
    "closed",
  ];

  const stageWeights: Record<PipelineStage, number> = {
    inquiry: 0.1,
    qualified: 0.25,
    site_visit: 0.4,
    offer_made: 0.6,
    reservation: 0.75,
    spa_issued: 0.9,
    closed: 1,
  };

  const stageFillClasses = [
    "bg-violet-300",
    "bg-violet-400",
    "bg-violet-500",
    "bg-violet-600",
    "bg-violet-700",
    "bg-violet-800",
    "bg-violet-900",
  ];

  const stageDotColors = [
    "#c4b5fd",
    "#a78bfa",
    "#8b5cf6",
    "#7c3aed",
    "#6d28d9",
    "#5b21b6",
    "#4c1d95",
  ];

  const brokerFillClasses = [
    "bg-violet-900",
    "bg-violet-800",
    "bg-violet-700",
    "bg-violet-600",
    "bg-violet-500",
  ];

  const sourceFillClasses = [
    "bg-violet-700",
    "bg-violet-600",
    "bg-violet-500",
    "bg-violet-400",
    "bg-violet-300",
    "bg-violet-200",
  ];

  let loading = $state(true);
  let refreshing = $state(false);

  let periodWindow = $state<PeriodWindow>("3");
  let ownerScope = $state<OwnerScope>("all");
  let regionScope = $state("global");

  let pipelineOverview = $state<PipelineOverview | null>(null);
  let brokerOverview = $state<BrokerPerformanceOverview | null>(null);
  let communicationOverview = $state<CommunicationOverview | null>(null);
  let reservationOverview = $state<ReservationOverview | null>(null);
  let activeLeads = $state<LeadListItem[]>([]);
  let activeLeadsTotal = $state(0);
  let followUpTasks = $state<FollowUpTaskListItem[]>([]);
  let followUpTasksTotal = $state(0);

  const DATA_PAGE_SIZE = "200";
  const MAX_DATA_PAGES = 6;

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function dealValue(lead: LeadListItem): number {
    const max = toNumber(lead.budget_max);
    if (max > 0) return max;
    return toNumber(lead.budget_min);
  }

  function fmtDateTime(value: string | null): string {
    if (!value) return "--";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "--";
    return dt.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function fmtShortDate(value: string): string {
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "--";
    return dt.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function stageLabel(stage: PipelineStage): string {
    const found = pipelineOverview?.pipeline_stages.find((row) => row.stage === stage);
    return found?.label ?? stage.replaceAll("_", " ");
  }

  function ownerScoped<T extends { assigned_to: number | null }>(rows: T[]): T[] {
    if (ownerScope === "assigned") {
      return rows.filter((row) => row.assigned_to !== null);
    }
    if (ownerScope === "unassigned") {
      return rows.filter((row) => row.assigned_to === null);
    }
    return rows;
  }

  async function fetchPaginatedBucket<T>(
    endpoint: string,
    params: Record<string, string>,
  ): Promise<PaginatedBucket<T>> {
    const rows: T[] = [];
    let total = 0;

    for (let page = 1; page <= MAX_DATA_PAGES; page += 1) {
      const res = await api.get<PaginatedResponse<T>>(endpoint, {
        ...params,
        page: String(page),
        page_size: DATA_PAGE_SIZE,
      });
      if (page === 1) total = res.count;
      rows.push(...res.results);
      if (!res.next || rows.length >= total || res.results.length === 0) break;
    }

    return { rows, total };
  }

  async function fetchDashboard() {
    if (!loading) refreshing = true;

    try {
      const [
        pipelineRes,
        brokerRes,
        communicationRes,
        reservationRes,
        leadsBucket,
        tasksBucket,
      ] = await Promise.all([
        api.get<PipelineOverview>("/crm/pipeline/overview/"),
        api.get<BrokerPerformanceOverview>("/crm/brokers/performance/", { months: periodWindow }),
        api.get<CommunicationOverview>("/crm/communications/overview/", { months: periodWindow }),
        api.get<ReservationOverview>("/crm/reservations/overview/"),
        fetchPaginatedBucket<LeadListItem>("/crm/leads/", {
          status: "active",
          ordering: "-updated_at",
        }),
        fetchPaginatedBucket<FollowUpTaskListItem>("/crm/follow-up-tasks/", {
          ordering: "due_at",
        }),
      ]);

      pipelineOverview = pipelineRes;
      brokerOverview = brokerRes;
      communicationOverview = communicationRes;
      reservationOverview = reservationRes;
      activeLeads = leadsBucket.rows;
      activeLeadsTotal = leadsBucket.total;
      followUpTasks = tasksBucket.rows;
      followUpTasksTotal = tasksBucket.total;
    } catch (err) {
      console.error("[crm]", err);
      pipelineOverview = null;
      brokerOverview = null;
      communicationOverview = null;
      reservationOverview = null;
      activeLeads = [];
      activeLeadsTotal = 0;
      followUpTasks = [];
      followUpTasksTotal = 0;
      toast.error("CRM dashboard unavailable", "Could not load CRM dashboard metrics.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  let mounted = $state(false);

  onMount(() => {
    mounted = true;
    void fetchDashboard();
  });

  // Re-fetch when the period window changes; mounted guard prevents the
  // double-fetch on initial mount.
  $effect(() => {
    periodWindow;
    if (mounted) void fetchDashboard();
  });

  const live = useLiveKpis(
    ["Lead", "Reservation"],
    fetchDashboard,
    { debounceMs: 3000 },
  );

  const scopedLeads = $derived.by(() => ownerScoped(activeLeads));
  const activeLeadsSampled = $derived(activeLeadsTotal > activeLeads.length);

  const scopedTasks = $derived.by(() => {
    const scoped = ownerScoped(followUpTasks);
    return scoped.filter((task) => task.status !== "completed" && task.status !== "cancelled");
  });
  const followUpTasksSampled = $derived(followUpTasksTotal > followUpTasks.length);

  const upcomingTasks = $derived.by(() =>
    [...scopedTasks]
      .sort((a, b) => new Date(a.due_at).getTime() - new Date(b.due_at).getTime())
      .slice(0, 6),
  );

  const overdueTaskCount = $derived(scopedTasks.filter((task) => task.is_overdue).length);

  const dueSoonTaskCount = $derived.by(() => {
    const now = Date.now();
    const soon = now + 24 * 60 * 60 * 1000;
    return scopedTasks.filter((task) => {
      const due = new Date(task.due_at).getTime();
      return Number.isFinite(due) && due >= now && due <= soon;
    }).length;
  });

  const pipelineValue = $derived.by(() =>
    scopedLeads.reduce((sum, lead) => sum + dealValue(lead), 0),
  );

  const scopedStageCounts = $derived.by(() => {
    const counts: Record<PipelineStage, number> = {
      inquiry: 0,
      qualified: 0,
      site_visit: 0,
      offer_made: 0,
      reservation: 0,
      spa_issued: 0,
      closed: 0,
    };
    for (const lead of scopedLeads) {
      counts[lead.pipeline_stage] += 1;
    }
    return counts;
  });

  const stageFinancials = $derived.by(() => {
    const grossByStage: Record<PipelineStage, number> = {
      inquiry: 0,
      qualified: 0,
      site_visit: 0,
      offer_made: 0,
      reservation: 0,
      spa_issued: 0,
      closed: 0,
    };

    for (const lead of scopedLeads) {
      grossByStage[lead.pipeline_stage] += dealValue(lead);
    }

    return stageOrder.map((stage) => {
      const gross = grossByStage[stage];
      const weighted = gross * stageWeights[stage];
      return {
        stage,
        label: stageLabel(stage),
        count: scopedStageCounts[stage],
        gross,
        weighted,
      };
    });
  });

  const maxStageCount = $derived(
    Math.max(...stageFinancials.map((row) => row.count), 1),
  );

  const weightedForecastTotal = $derived.by(() =>
    stageFinancials.reduce((sum, row) => sum + row.weighted, 0),
  );

  const sparklinePoints = $derived.by(() => {
    const rows = stageFinancials;
    if (rows.length === 0) return "";

    const maxValue = Math.max(...rows.map((row) => row.weighted), 1);
    const xMin = 12;
    const xMax = 308;
    const yMin = 18;
    const yMax = 108;

    return rows
      .map((row, index) => {
        const x = xMin + (index / Math.max(rows.length - 1, 1)) * (xMax - xMin);
        const y = yMax - (row.weighted / maxValue) * (yMax - yMin);
        return `${x},${y}`;
      })
      .join(" ");
  });

  const conversionRate = $derived(pipelineOverview?.conversion_rate ?? 0);

  const activityScore = $derived.by(() => {
    const base = 48;
    const conversionWeight = conversionRate * 0.45;
    const followUpWeight = Math.min((communicationOverview?.follow_up_pending ?? 0) / 4, 20);
    const overduePenalty = Math.min(overdueTaskCount * 4, 35);
    const valueWeight = Math.min(pipelineValue / 5_000_000, 18);
    const computed = Math.round(base + conversionWeight + followUpWeight + valueWeight - overduePenalty);
    return Math.max(0, Math.min(100, computed));
  });

  const activityRing = $derived.by(
    () =>
      `conic-gradient(#6d28d9 ${activityScore}%, #ede9fe ${activityScore}% 100%)`,
  );

  const channelMap = $derived.by(() => {
    const map: Record<string, number> = {};
    for (const row of communicationOverview?.channel_breakdown ?? []) {
      map[row.channel] = row.count;
    }
    return map;
  });

  const sourceRows = $derived.by(() => {
    const rows = pipelineOverview?.by_source ?? [];
    return rows.slice(0, 6);
  });

  const sourcePeak = $derived(Math.max(...sourceRows.map((row) => row.count), 1));

  const topDeals = $derived.by(() =>
    [...scopedLeads]
      .sort((a, b) => dealValue(b) - dealValue(a))
      .slice(0, 6),
  );

  const brokerRows = $derived.by(() => (brokerOverview?.top_by_deals ?? []).slice(0, 5));
  const brokerPeak = $derived(Math.max(...brokerRows.map((row) => row.deals), 1));

  function dueStateLabel(task: FollowUpTaskListItem): string {
    if (task.is_overdue) return "Overdue";
    const due = new Date(task.due_at).getTime();
    if (!Number.isFinite(due)) return "Scheduled";
    const hours = Math.round((due - Date.now()) / (1000 * 60 * 60));
    if (hours <= 24) return "Due <24h";
    return `Due in ${Math.max(1, Math.round(hours / 24))}d`;
  }

  function scopeLabel(value: OwnerScope): string {
    if (value === "assigned") return "Assigned";
    if (value === "unassigned") return "Unassigned";
    return "All reps";
  }
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <div class="flex items-center gap-2">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">CRM</p>
        <LiveBadge refreshing={live.refreshing} />
      </div>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Dashboard</h1>
      <p class="mt-1 text-sm text-neutral-500">Pipeline health, follow-ups, conversion momentum, and team activity in one command view.</p>
    </div>

    <div class="flex flex-wrap items-end gap-3">
      <label class="text-xs font-medium text-neutral-600">
        Time Window
        <select
          bind:value={periodWindow}
          class="mt-1 block rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800"
        >
          <option value="1">Last 30 days</option>
          <option value="3">Last 90 days</option>
          <option value="6">Last 6 months</option>
          <option value="12">Last 12 months</option>
        </select>
      </label>

      <label class="text-xs font-medium text-neutral-600">
        Owner
        <select
          bind:value={ownerScope}
          class="mt-1 block rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800"
        >
          <option value="all">All reps</option>
          <option value="assigned">Assigned only</option>
          <option value="unassigned">Unassigned queue</option>
        </select>
      </label>

      <label class="text-xs font-medium text-neutral-600">
        Region
        <select
          bind:value={regionScope}
          class="mt-1 block rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800"
        >
          <option value="global">Global</option>
          <option value="org">Organization Scope</option>
        </select>
      </label>

      <button
        onclick={fetchDashboard}
        class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        {refreshing ? "Refreshing..." : "Refresh"}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center rounded-2xl border border-neutral-200 bg-white py-24">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
    </div>
  {:else}
    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
      <div class="rounded-xl border border-violet-200 bg-violet-50 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-violet-700">Active Deals</p>
        <p class="mt-2 text-3xl font-semibold text-violet-950 tabular-nums">{scopedLeads.length}</p>
        <p class="mt-1 text-xs text-violet-700">Scope: {scopeLabel(ownerScope)}</p>
        {#if activeLeadsSampled}
          <p class="mt-1 text-[11px] text-amber-700">
            Showing {activeLeads.length.toLocaleString()} of {activeLeadsTotal.toLocaleString()} active deals.
          </p>
        {/if}
      </div>

      <div class="rounded-xl border border-purple-200 bg-purple-50 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-purple-700">Pipeline Value</p>
        <p class="mt-2 text-3xl font-semibold text-purple-950 tabular-nums">{currency.formatAbbreviated(pipelineValue)}</p>
        <p class="mt-1 text-xs text-purple-700">Weighted: {currency.formatAbbreviated(weightedForecastTotal)}</p>
      </div>

      <div class="rounded-xl border border-fuchsia-200 bg-fuchsia-50 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-fuchsia-700">Tasks Due</p>
        <p class="mt-2 text-3xl font-semibold text-fuchsia-950 tabular-nums">{dueSoonTaskCount + overdueTaskCount}</p>
        <p class="mt-1 text-xs text-rose-700">{overdueTaskCount} overdue</p>
      </div>

      <div class="rounded-xl border border-violet-300 bg-violet-100 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-violet-800">Conversion</p>
        <p class="mt-2 text-3xl font-semibold text-violet-950 tabular-nums">{conversionRate.toFixed(1)}%</p>
        <p class="mt-1 text-xs text-violet-800">Org-wide: {pipelineOverview?.won_leads ?? 0} won / {pipelineOverview?.total_leads ?? 0} total</p>
      </div>

      <div class="rounded-xl border border-purple-300 bg-purple-100 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-purple-800">Communications</p>
        <p class="mt-2 text-3xl font-semibold text-purple-950 tabular-nums">{(communicationOverview?.total_communications ?? 0).toLocaleString()}</p>
        <p class="mt-1 text-xs text-purple-800">Period: {communicationOverview?.period_months ?? Number(periodWindow)} months</p>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-12">
      <section class="rounded-2xl border border-neutral-200 bg-white p-6 xl:col-span-8">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-800">Pipeline Pulse</h2>
            <p class="text-sm text-neutral-500">Stage load, expected close value, and forecast direction.</p>
          </div>
          <button onclick={() => goto("/crm/leads")} class="text-sm font-medium text-neutral-700 hover:text-neutral-800">View Leads</button>
        </div>

        <div class="grid grid-cols-1 gap-6 md:grid-cols-5">
          <div class="space-y-3 md:col-span-3">
            {#each stageFinancials as row, rowIndex}
              <button
                class="w-full rounded-lg border border-violet-100 px-3 py-2 text-left hover:border-violet-300"
                onclick={() => goto("/crm/leads")}
              >
                <div class="mb-2 flex items-center justify-between text-xs text-violet-700">
                  <span>{row.label}</span>
                  <span class="tabular-nums">{row.count} deals</span>
                </div>
                <div class="h-2 overflow-hidden rounded-full bg-violet-100">
                  <div
                    class={`h-full rounded-full transition-[width] duration-300 ${stageFillClasses[rowIndex % stageFillClasses.length]}`}
                    style={`width: ${Math.max(4, (row.count / maxStageCount) * 100)}%`}
                  ></div>
                </div>
                <div class="mt-2 flex items-center justify-between text-xs text-violet-700">
                  <span>{currency.formatAbbreviated(row.gross)}</span>
                  <span class="font-medium text-violet-900">Forecast {currency.formatAbbreviated(row.weighted)}</span>
                </div>
              </button>
            {/each}
          </div>

          <div class="rounded-xl border border-violet-100 bg-violet-50 p-4 md:col-span-2">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-neutral-800">Revenue Forecast</h3>
              <span class="text-xs text-violet-700">{currency.formatAbbreviated(weightedForecastTotal)}</span>
            </div>

            <svg viewBox="0 0 320 120" class="mt-4 h-36 w-full">
              <polyline fill="none" stroke="#6d28d9" stroke-width="2.5" points={sparklinePoints} />
              {#each stageFinancials as row, index}
                {@const x = 12 + (index / Math.max(stageFinancials.length - 1, 1)) * (308 - 12)}
                {@const y = 108 - (row.weighted / Math.max(...stageFinancials.map((item) => item.weighted), 1)) * (108 - 18)}
                <circle cx={x} cy={y} r="3" fill={stageDotColors[index % stageDotColors.length]} />
              {/each}
            </svg>

            <div class="mt-3 grid grid-cols-3 gap-2 text-xs text-violet-700">
              {#each stageFinancials.slice(-3) as row}
                <div class="min-w-0 rounded-md border border-violet-200 bg-white px-2 py-2 text-center">
                  <p class="min-h-6 whitespace-normal wrap-break-word text-[10px] font-medium uppercase leading-tight tracking-[0.08em] text-violet-600">
                    {row.label}
                  </p>
                  <p
                    class="mt-1 truncate text-sm font-semibold tabular-nums text-violet-900"
                    title={currency.formatCompact(row.weighted)}
                  >
                    {currency.formatAbbreviated(row.weighted)}
                  </p>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </section>

      <div class="space-y-6 xl:col-span-4">
        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-neutral-800">Activity Summary</h2>
            <span class="text-xs text-neutral-500">Live</span>
          </div>

          <div class="grid grid-cols-3 gap-3 text-center">
            <div>
              <p class="text-2xl font-semibold text-violet-800 tabular-nums">{(channelMap.email ?? 0).toLocaleString()}</p>
              <p class="text-xs text-neutral-500">Emails</p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-violet-700 tabular-nums">{(channelMap.phone ?? 0).toLocaleString()}</p>
              <p class="text-xs text-neutral-500">Calls</p>
            </div>
            <div>
              <p class="text-2xl font-semibold text-fuchsia-700 tabular-nums">{(communicationOverview?.follow_up_pending ?? 0).toLocaleString()}</p>
              <p class="text-xs text-neutral-500">Follow-Ups</p>
            </div>
          </div>

          <div class="mt-6 flex items-center justify-center">
            <div class="grid h-32 w-32 place-items-center rounded-full" style={`background: ${activityRing}`}>
              <div class="grid h-24 w-24 place-items-center rounded-full bg-white text-center">
                <p class="text-3xl font-semibold text-neutral-800 tabular-nums">{activityScore}</p>
                <p class="text-[11px] uppercase tracking-wider text-violet-600">Health</p>
              </div>
            </div>
          </div>

          <div class="mt-4 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-700">
            Overdue follow-ups are reducing score by {Math.min(overdueTaskCount * 4, 35)} points.
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-lg font-semibold text-neutral-800">Upcoming Follow-Ups</h2>
            <button onclick={() => goto("/crm/communications")} class="text-sm font-medium text-neutral-700 hover:text-neutral-800">View All</button>
          </div>

          {#if upcomingTasks.length === 0}
            <p class="py-10 text-center text-sm text-neutral-500">No pending follow-up tasks.</p>
          {:else}
            <div class="space-y-3">
              {#each upcomingTasks as task}
                <button onclick={() => goto("/crm/communications")} class="w-full rounded-lg border border-violet-100 px-3 py-2 text-left hover:border-violet-300">
                  <div class="flex items-center justify-between gap-3">
                    <p class="truncate text-sm font-medium text-neutral-800">{task.lead_name}</p>
                    <span class="rounded-full px-2 py-0.5 text-[11px] font-medium {task.is_overdue ? 'bg-rose-100 text-rose-700' : 'bg-violet-100 text-violet-700'}">{dueStateLabel(task)}</span>
                  </div>
                  <p class="mt-1 text-xs text-neutral-500">{task.rule_name}</p>
                  <p class="mt-1 text-xs text-neutral-400">{fmtDateTime(task.due_at)}</p>
                </button>
              {/each}
            </div>
            {#if followUpTasksSampled}
              <p class="mt-3 text-[11px] text-amber-700">
                Showing first {followUpTasks.length.toLocaleString()} of {followUpTasksTotal.toLocaleString()} tasks.
              </p>
            {/if}
          {/if}
        </section>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-12">
      <section class="rounded-2xl border border-neutral-200 bg-white p-6 xl:col-span-7">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-800">Recent Deals</h2>
            <p class="text-sm text-neutral-500">Highest-value active opportunities in scope.</p>
          </div>
          <button onclick={() => goto("/crm/leads")} class="text-sm font-medium text-neutral-700 hover:text-neutral-800">Open Pipeline</button>
        </div>

        {#if topDeals.length === 0}
          <p class="py-12 text-center text-sm text-neutral-500">No active leads found for this scope.</p>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="border-b border-neutral-200 text-left text-xs uppercase tracking-wider text-neutral-500">
                <tr>
                  <th class="pb-3">Lead</th>
                  <th class="pb-3">Stage</th>
                  <th class="pb-3">Score</th>
                  <th class="pb-3 text-right">Potential Value</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each topDeals as lead}
                  <tr class="cursor-pointer hover:bg-violet-50/60" onclick={() => goto(`/crm/leads/${lead.id}`)}>
                    <td class="py-3 text-sm font-medium text-neutral-800">{lead.full_name}</td>
                    <td class="py-3 text-sm text-neutral-600">{lead.pipeline_stage_display}</td>
                    <td class="py-3 text-sm text-neutral-600">{lead.score}</td>
                    <td class="py-3 text-right text-sm font-medium text-neutral-800 tabular-nums">{currency.formatAbbreviated(dealValue(lead))}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </section>

      <div class="space-y-6 xl:col-span-5">
        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <h2 class="text-lg font-semibold text-neutral-800">Reservation Snapshot</h2>
          <div class="mt-4 grid grid-cols-2 gap-3">
            <div class="rounded-lg border border-violet-100 bg-violet-50 px-3 py-2">
              <p class="text-xs uppercase tracking-wider text-neutral-500">Active Holds</p>
              <p class="mt-1 text-xl font-semibold text-neutral-800">{reservationOverview?.active_holds ?? 0}</p>
            </div>
            <div class="rounded-lg border border-violet-100 bg-violet-50 px-3 py-2">
              <p class="text-xs uppercase tracking-wider text-neutral-500">Pending Payment</p>
              <p class="mt-1 text-xl font-semibold text-neutral-800">{reservationOverview?.pending_payments ?? 0}</p>
            </div>
            <div class="rounded-lg border border-violet-100 bg-violet-50 px-3 py-2">
              <p class="text-xs uppercase tracking-wider text-neutral-500">Converted</p>
              <p class="mt-1 text-xl font-semibold text-neutral-800">{reservationOverview?.converted ?? 0}</p>
            </div>
            <div class="rounded-lg border border-violet-100 bg-violet-50 px-3 py-2">
              <p class="text-xs uppercase tracking-wider text-neutral-500">Converted Value</p>
              <p class="mt-1 text-xl font-semibold text-neutral-800 tabular-nums">{currency.formatAbbreviated(toNumber(reservationOverview?.total_converted_value ?? 0))}</p>
            </div>
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <h2 class="text-lg font-semibold text-neutral-800">Broker Momentum</h2>
          {#if brokerRows.length === 0}
            <p class="mt-4 text-sm text-neutral-500">No broker performance data yet.</p>
          {:else}
            <div class="mt-4 space-y-3">
              {#each brokerRows as row, index}
                <div>
                  <div class="mb-1 flex items-center justify-between text-sm">
                    <span class="truncate text-neutral-700">{row.broker_name}</span>
                    <span class="font-medium text-neutral-800 tabular-nums">{row.deals}</span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-violet-100">
                    <div class={`h-full rounded-full ${brokerFillClasses[index % brokerFillClasses.length]}`} style={`width: ${(row.deals / brokerPeak) * 100}%`}></div>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <h2 class="text-lg font-semibold text-neutral-800">Lead Source Mix</h2>
          {#if sourceRows.length === 0}
            <p class="mt-4 text-sm text-neutral-500">No source distribution available.</p>
          {:else}
            <div class="mt-4 space-y-3">
              {#each sourceRows as source, index}
                <div>
                  <div class="mb-1 flex items-center justify-between text-sm">
                    <span class="truncate text-neutral-700">{source.source || "Unspecified"}</span>
                    <span class="font-medium text-neutral-800 tabular-nums">{source.count}</span>
                  </div>
                  <div class="h-2 overflow-hidden rounded-full bg-violet-100">
                    <div class={`h-full rounded-full ${sourceFillClasses[index % sourceFillClasses.length]}`} style={`width: ${(source.count / sourcePeak) * 100}%`}></div>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </section>
      </div>
    </div>
  {/if}
</div>

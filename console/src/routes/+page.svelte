<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import StatCard from "$lib/components/ui/StatCard.svelte";

  // --- State ---
  let loading = $state(true);

  // User stats
  let userStats = $state<{
    total: number;
    active: number;
    suspended: number;
    locked: number;
  }>({ total: 0, active: 0, suspended: 0, locked: 0 });

  // Lifecycle
  let lifecycle = $state<{
    stages: Record<string, number>;
    timeline: { date: string; invitations_sent: number; users_joined: number }[];
  }>({ stages: {}, timeline: [] });

  // Core telemetry metrics
  interface TelemetryMetrics {
    active_tenants: number;
    total_users: number;
    realtime_users: number;
    daily_users: number;
    p95_latency_ms: number;
    error_rate_pct: number;
    celery_status: string;
    pending_tasks: number;
    storage_bytes: number;
    storage_formatted: string;
    file_count: number;
  }
  let telemetry = $state<TelemetryMetrics | null>(null);

  async function loadTelemetry() {
    try {
      telemetry = await api.get<TelemetryMetrics>("/telemetry/metrics/");
    } catch { telemetry = null; }
  }

  // System health
  let apiHealthy = $state<boolean | null>(null);
  let analyticsHealth = $state<{
    portfolio: { status: string; last_computed: string | null; age_hours: number | null; is_stale: boolean };
    board_kpis: { status: string; last_computed: string | null; age_hours: number | null; is_stale: boolean };
  } | null>(null);

  // Activity feed
  interface ActivityItem {
    id: number;
    timestamp: string;
    module: string;
    app_label: string;
    model: string;
    action: string;
    object_repr: string;
    description: string;
    severity: string;
    actor: string | null;
    tenant: string | null;
  }
  let activityItems = $state<ActivityItem[]>([]);
  let activityLoading = $state(true);
  let activityModule = $state("");
  let activityOrg = $state("");
  let orgList = $state<{ id: number; name: string }[]>([]);

  async function loadActivityFeed() {
    activityLoading = true;
    try {
      const params: Record<string, string> = { limit: "20" };
      if (activityModule) params.module = activityModule;
      if (activityOrg) params.organization = activityOrg;
      const res = await api.get<{ items: ActivityItem[] }>("/telemetry/activity-feed/", params);
      activityItems = res.items;
    } catch { activityItems = []; }
    activityLoading = false;
  }

  async function loadOrgList() {
    try {
      const res = await api.get<{ results: { id: number; name: string }[] }>("/iam/organizations/");
      orgList = res.results ?? res as any;
    } catch { orgList = []; }
  }

  function formatTimeAgo(iso: string): string {
    const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  // Workflow monitor
  interface WorkflowStep { sequence: number; name: string; decision: string; sla_breached: boolean; }
  interface WorkflowInstance {
    id: number; template_name: string; state: string;
    content_type: string; object_id: number | null;
    submitted_by: string | null; submitted_at: string | null;
    created_at: string; steps: WorkflowStep[];
  }
  interface CeleryTask { name: string; task: string; last_run: string | null; enabled: boolean; }
  interface WorkflowMonitorData {
    total_today: number; completed_today: number; failed_today: number;
    delayed_jobs: number; active_workflows: number;
    top_triggers: { app_label: string; model: string; label: string; count: number }[];
    recent_instances: WorkflowInstance[];
    celery_tasks: CeleryTask[];
    celery_task_count: number;
  }
  let wfMonitor = $state<WorkflowMonitorData | null>(null);
  let wfExpanded = $state<number | null>(null);

  async function loadWorkflowMonitor() {
    try { wfMonitor = await api.get<WorkflowMonitorData>("/telemetry/workflow-monitor/"); }
    catch { wfMonitor = null; }
  }

  // Alerts & Risk Center
  interface AlertItem {
    category: string;
    severity: string;
    title: string;
    detail: string;
    metric: string | null;
    timestamp: string;
  }
  interface AlertSummary {
    total: number;
    critical: number;
    warning: number;
    info: number;
    by_category: Record<string, number>;
  }
  let alertItems = $state<AlertItem[]>([]);
  let alertSummary = $state<AlertSummary | null>(null);
  let alertsLoading = $state(true);
  let alertCategoryFilter = $state("");

  async function loadAlerts() {
    alertsLoading = true;
    try {
      const res = await api.get<{ alerts: AlertItem[]; summary: AlertSummary }>("/telemetry/alerts/");
      alertItems = res.alerts;
      alertSummary = res.summary;
    } catch { alertItems = []; alertSummary = null; }
    alertsLoading = false;
  }

  const filteredAlerts = $derived(() => {
    if (!alertCategoryFilter) return alertItems;
    return alertItems.filter(a => a.category === alertCategoryFilter);
  });

  const categoryLabels: Record<string, string> = {
    system: "System",
    revenue: "Revenue",
    tenant_health: "Tenant Health",
    security: "Security",
    usage: "Usage & Cost",
  };

  // Heroicon paths
  const icons = {
    users: "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
    active: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    suspended: "M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636",
    invite: "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75",
  };

  const lifecycleLabels: Record<string, string> = {
    pending_invitations: "Pending Invitations",
    pending_onboarding: "Pending Onboarding",
    active: "Active",
    suspended: "Suspended",
    locked: "Locked",
    never_logged_in: "Never Logged In",
  };

  const quickActions = [
    { label: "Manage Users", href: "/accounts/users", icon: "M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" },
    { label: "Invite User", href: "/accounts/invitations/new", icon: "M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" },
    { label: "System Preferences", href: "/settings/system-preferences", icon: "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" },
    { label: "Feature Flags", href: "/settings/feature-flags", icon: "M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l.108.054a9 9 0 0 0 6.086.71l3.114-.732a48.524 48.524 0 0 1-.005-10.499l-3.11.732a9 9 0 0 1-6.085-.711l-.108-.054a9 9 0 0 0-6.208-.682L3 4.5M3 15V4.5" },
    { label: "Audit Log", href: "/settings/audit-compliance", icon: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z" },
    { label: "Operations", href: "/platform/operations", icon: "M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Zm-3 6h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" },
  ];

  async function loadAll() {
    loading = true;
    await Promise.allSettled([
      loadTelemetry(),
      loadUserStats(),
      loadLifecycle(),
      loadApiHealth(),
      loadAnalyticsHealth(),
      loadActivityFeed(),
      loadOrgList(),
      loadWorkflowMonitor(),
      loadAlerts(),
    ]);
    loading = false;
  }

  async function loadUserStats() {
    try {
      const res = await api.get<{ overview: { total: number; active: number; suspended: number; locked: number } }>("/iam/users/", { page: "1", page_size: "1" });
      if (res.overview) {
        userStats = res.overview;
      }
    } catch {
      // Dashboard should be resilient to partial failures
    }
  }

  async function loadLifecycle() {
    try {
      const res = await api.get<{
        stages: Record<string, number>;
        timeline: { date: string; invitations_sent: number; users_joined: number }[];
      }>("/iam/users/lifecycle/");
      lifecycle = res;
    } catch {
      // silently fail
    }
  }

  async function loadApiHealth() {
    try {
      await api.get("/health/");
      apiHealthy = true;
    } catch {
      apiHealthy = false;
    }
  }

  async function loadAnalyticsHealth() {
    try {
      const res = await api.get<{
        portfolio: { status: string; last_computed: string | null; age_hours: number | null; is_stale: boolean };
        board_kpis: { status: string; last_computed: string | null; age_hours: number | null; is_stale: boolean };
      }>("/analytics/health/");
      analyticsHealth = res;
    } catch {
      analyticsHealth = null;
    }
  }

  function formatAge(hours: number | null): string {
    if (hours == null) return "Never";
    if (hours < 1) return `${Math.round(hours * 60)}m ago`;
    if (hours < 24) return `${Math.round(hours)}h ago`;
    return `${Math.round(hours / 24)}d ago`;
  }

  function statusDot(status: string): string {
    switch (status) {
      case "fresh": return "bg-emerald-500";
      case "stale": return "bg-amber-500";
      case "missing": return "bg-red-500";
      default: return "bg-neutral-400";
    }
  }

  onMount(loadAll);
</script>

<div class="space-y-8">
  <!-- Page header -->
  <div>
    <h1 class="text-xl font-semibold text-neutral-900">Control Center</h1>
    <p class="text-sm text-neutral-500 mt-1">Platform overview and quick actions</p>
  </div>

  <!-- Status Indicator -->
  {#if telemetry && apiHealthy !== null}
    {@const hasIncident = apiHealthy === false || telemetry.celery_status !== "healthy" || telemetry.error_rate_pct >= 5}
    {@const isDegraded = !hasIncident && (telemetry.p95_latency_ms >= 500 || telemetry.error_rate_pct >= 1 || (analyticsHealth && (analyticsHealth.portfolio.is_stale || analyticsHealth.board_kpis.is_stale)))}
    <div class="rounded-xl border px-5 py-3 flex items-center gap-3" style="background: {hasIncident ? '#fef2f2' : isDegraded ? '#fffbeb' : '#f0fdf4'}; border-color: {hasIncident ? '#fecaca' : isDegraded ? '#fde68a' : '#bbf7d0'};">
      <span class="w-3 h-3 rounded-full shrink-0" style="background: {hasIncident ? '#ef4444' : isDegraded ? '#eab308' : '#22c55e'}; box-shadow: 0 0 0 3px {hasIncident ? 'rgba(239,68,68,0.2)' : isDegraded ? 'rgba(234,179,8,0.2)' : 'rgba(34,197,94,0.2)'};"></span>
      <div>
        <p class="text-sm font-semibold" style="color: {hasIncident ? '#991b1b' : isDegraded ? '#92400e' : '#166534'};">
          {hasIncident ? "Incident in progress" : isDegraded ? "Degraded performance" : "All systems operational"}
        </p>
        <p class="text-xs mt-0.5" style="color: {hasIncident ? '#dc2626' : isDegraded ? '#ca8a04' : '#16a34a'};">
          {#if hasIncident}
            {apiHealthy === false ? "API server unreachable" : ""}{telemetry.celery_status !== "healthy" ? (apiHealthy === false ? " · " : "") + "Job queue down" : ""}{telemetry.error_rate_pct >= 5 ? ((apiHealthy === false || telemetry.celery_status !== "healthy") ? " · " : "") + `Error rate ${telemetry.error_rate_pct}%` : ""}
          {:else if isDegraded}
            {telemetry.p95_latency_ms >= 500 ? `High latency (${telemetry.p95_latency_ms}ms)` : ""}{telemetry.error_rate_pct >= 1 ? (telemetry.p95_latency_ms >= 500 ? " · " : "") + `Elevated errors (${telemetry.error_rate_pct}%)` : ""}{analyticsHealth?.portfolio.is_stale ? " · Stale analytics" : ""}
          {:else}
            API {telemetry.p95_latency_ms}ms · {telemetry.error_rate_pct}% errors · {telemetry.realtime_users} online
          {/if}
        </p>
      </div>
    </div>
  {/if}

  <!-- Alerts & Risk Center -->
  {#if alertSummary && alertSummary.total > 0}
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-3">
          <h2 class="text-sm font-semibold text-neutral-900">Alerts & Risk Center</h2>
          <!-- Severity badges -->
          {#if alertSummary.critical > 0}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold" style="background: #fee2e2; color: #991b1b;">
              <span class="w-1.5 h-1.5 rounded-full" style="background: #ef4444;"></span>
              {alertSummary.critical} critical
            </span>
          {/if}
          {#if alertSummary.warning > 0}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold" style="background: #fef3c7; color: #92400e;">
              <span class="w-1.5 h-1.5 rounded-full" style="background: #f59e0b;"></span>
              {alertSummary.warning} warning
            </span>
          {/if}
          {#if alertSummary.info > 0}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-neutral-100 text-neutral-500">
              {alertSummary.info} info
            </span>
          {/if}
        </div>
        <div class="flex items-center gap-2">
          <select bind:value={alertCategoryFilter} class="px-2.5 py-1.5 border border-neutral-200 rounded-lg text-xs bg-white text-neutral-600 focus:outline-none focus:ring-1 focus:ring-neutral-900">
            <option value="">All Categories</option>
            <option value="system">System</option>
            <option value="revenue">Revenue</option>
            <option value="tenant_health">Tenant Health</option>
            <option value="security">Security</option>
            <option value="usage">Usage & Cost</option>
          </select>
          <button type="button" onclick={loadAlerts} class="p-1.5 border border-neutral-200 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-50 transition-colors" aria-label="Refresh">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M2.985 14.652V19.644" /></svg>
          </button>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        {#if alertsLoading}
          <div class="p-8 text-center"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
        {:else}
          <div class="max-h-72 overflow-y-auto divide-y divide-neutral-100">
            {#each filteredAlerts() as alert}
              <div class="px-4 py-3 flex items-start gap-3 hover:bg-neutral-50 transition-colors">
                <!-- Severity icon -->
                <div class="mt-0.5 shrink-0">
                  {#if alert.severity === "critical"}
                    <div class="w-6 h-6 rounded-full flex items-center justify-center" style="background: #fee2e2;">
                      <svg class="w-3.5 h-3.5" style="color: #dc2626;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
                    </div>
                  {:else if alert.severity === "warning"}
                    <div class="w-6 h-6 rounded-full flex items-center justify-center" style="background: #fef3c7;">
                      <svg class="w-3.5 h-3.5" style="color: #d97706;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0 3.75h.008v.008H12v-.008ZM21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                    </div>
                  {:else}
                    <div class="w-6 h-6 rounded-full flex items-center justify-center bg-neutral-100">
                      <svg class="w-3.5 h-3.5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" /></svg>
                    </div>
                  {/if}
                </div>

                <!-- Content -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <p class="text-xs font-semibold text-neutral-900">{alert.title}</p>
                    <span class="text-[9px] font-medium uppercase tracking-wider px-1.5 py-0.5 rounded" style="background: {alert.category === 'system' ? '#ede9fe' : alert.category === 'revenue' ? '#fdf2f8' : alert.category === 'security' ? '#fee2e2' : alert.category === 'tenant_health' ? '#fff7ed' : '#f0fdf4'}; color: {alert.category === 'system' ? '#6d28d9' : alert.category === 'revenue' ? '#9d174d' : alert.category === 'security' ? '#991b1b' : alert.category === 'tenant_health' ? '#c2410c' : '#166534'};">
                      {categoryLabels[alert.category] || alert.category}
                    </span>
                  </div>
                  <p class="text-[11px] text-neutral-500 mt-0.5">{alert.detail}</p>
                </div>

                <!-- Metric -->
                {#if alert.metric}
                  <span class="text-xs font-bold tabular-nums shrink-0 mt-0.5" style="color: {alert.severity === 'critical' ? '#dc2626' : alert.severity === 'warning' ? '#d97706' : '#525252'};">
                    {alert.metric}
                  </span>
                {/if}
              </div>
            {/each}
          </div>

          {#if filteredAlerts().length === 0}
            <div class="p-6 text-center"><p class="text-xs text-neutral-400">No alerts in this category.</p></div>
          {/if}
        {/if}
      </div>
    </div>
  {:else if !alertsLoading && alertSummary && alertSummary.total === 0}
    <!-- Clean state — no alerts -->
    <div class="rounded-xl border px-5 py-3 flex items-center gap-3" style="background: #f0fdf4; border-color: #bbf7d0;">
      <span class="w-3 h-3 rounded-full shrink-0" style="background: #22c55e; box-shadow: 0 0 0 3px rgba(34,197,94,0.2);"></span>
      <div>
        <p class="text-sm font-semibold" style="color: #166534;">No active alerts</p>
        <p class="text-xs" style="color: #16a34a;">All systems, tenants, and security checks are clear.</p>
      </div>
    </div>
  {/if}

  <!-- Core Metrics (Telemetry) -->
  {#if telemetry}
    <div>
      <h2 class="text-sm font-semibold text-neutral-900 mb-3">Core Metrics</h2>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <!-- Active Tenants -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center">
              <svg class="w-4 h-4 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Tenants</p>
          </div>
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{telemetry.active_tenants}</p>
          <p class="text-[10px] text-neutral-400 mt-0.5">active organisations</p>
        </div>

        <!-- Active Users -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center">
              <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Users</p>
          </div>
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{telemetry.realtime_users} <span class="text-sm font-normal text-neutral-400">/ {telemetry.daily_users}</span></p>
          <p class="text-[10px] text-neutral-400 mt-0.5">real-time / daily active</p>
        </div>

        <!-- API Latency -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background: {telemetry.p95_latency_ms < 200 ? '#dcfce7' : telemetry.p95_latency_ms < 500 ? '#fef9c3' : '#fee2e2'};">
              <svg class="w-4 h-4" style="color: {telemetry.p95_latency_ms < 200 ? '#16a34a' : telemetry.p95_latency_ms < 500 ? '#ca8a04' : '#dc2626'};" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">P95 Latency</p>
          </div>
          <p class="text-2xl font-bold tabular-nums" style="color: {telemetry.p95_latency_ms < 200 ? '#16a34a' : telemetry.p95_latency_ms < 500 ? '#ca8a04' : '#dc2626'};">{telemetry.p95_latency_ms}<span class="text-sm font-normal text-neutral-400">ms</span></p>
          <p class="text-[10px] text-neutral-400 mt-0.5">API response time</p>
        </div>

        <!-- Error Rate -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background: {telemetry.error_rate_pct < 1 ? '#dcfce7' : telemetry.error_rate_pct < 5 ? '#fef9c3' : '#fee2e2'};">
              <svg class="w-4 h-4" style="color: {telemetry.error_rate_pct < 1 ? '#16a34a' : telemetry.error_rate_pct < 5 ? '#ca8a04' : '#dc2626'};" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Error Rate</p>
          </div>
          <p class="text-2xl font-bold tabular-nums" style="color: {telemetry.error_rate_pct < 1 ? '#16a34a' : telemetry.error_rate_pct < 5 ? '#ca8a04' : '#dc2626'};">{telemetry.error_rate_pct}<span class="text-sm font-normal text-neutral-400">%</span></p>
          <p class="text-[10px] text-neutral-400 mt-0.5">failed requests</p>
        </div>

        <!-- Background Jobs -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg flex items-center justify-center" style="background: {telemetry.celery_status === 'healthy' ? '#dcfce7' : '#fee2e2'};">
              <svg class="w-4 h-4" style="color: {telemetry.celery_status === 'healthy' ? '#16a34a' : '#dc2626'};" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 14.25h13.5m-13.5 0a3 3 0 0 1-3-3m3 3a3 3 0 1 0 0 6h13.5a3 3 0 1 0 0-6m-16.5-3a3 3 0 0 1 3-3h13.5a3 3 0 0 1 3 3m-19.5 0a4.5 4.5 0 0 1 .9-2.7L5.737 5.1a3.375 3.375 0 0 1 2.7-1.35h7.126c1.062 0 2.062.5 2.7 1.35l2.587 3.45a4.5 4.5 0 0 1 .9 2.7m0 0a3 3 0 0 1-3 3m0 3h.008v.008h-.008v-.008Zm0-6h.008v.008h-.008v-.008Z" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Job Queue</p>
          </div>
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{telemetry.pending_tasks}</p>
          <p class="text-[10px] mt-0.5" style="color: {telemetry.celery_status === 'healthy' ? '#16a34a' : '#dc2626'};">{telemetry.celery_status === "healthy" ? "Healthy" : "Unavailable"}</p>
        </div>

        <!-- Storage -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center">
              <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Storage</p>
          </div>
          <p class="text-2xl font-bold text-neutral-900">{telemetry.storage_formatted}</p>
          <p class="text-[10px] text-neutral-400 mt-0.5">{telemetry.file_count.toLocaleString()} files</p>
        </div>

        <!-- Active Accounts (status-based) -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center">
              <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Account Status</p>
          </div>
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{userStats.active} <span class="text-sm font-normal text-neutral-400">/ {userStats.suspended}</span></p>
          <p class="text-[10px] text-neutral-400 mt-0.5">active / suspended accounts</p>
        </div>

        <!-- Pending Invitations -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <div class="flex items-center gap-2 mb-2">
            <div class="w-7 h-7 rounded-lg bg-amber-100 flex items-center justify-center">
              <svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" /></svg>
            </div>
            <p class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Invitations</p>
          </div>
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{lifecycle.stages.pending_invitations ?? 0}</p>
          <p class="text-[10px] text-neutral-400 mt-0.5">pending invitations</p>
        </div>
      </div>
    </div>
  {:else if loading}
    <div>
      <h2 class="text-sm font-semibold text-neutral-900 mb-3">Core Metrics</h2>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {#each { length: 8 } as _}
          <div class="bg-white rounded-xl border border-neutral-200 p-4 animate-pulse">
            <div class="flex items-center gap-2 mb-2">
              <div class="w-7 h-7 rounded-lg bg-neutral-100"></div>
              <div class="h-2 bg-neutral-100 rounded w-12"></div>
            </div>
            <div class="h-7 bg-neutral-200 rounded w-14 mb-1"></div>
            <div class="h-2 bg-neutral-100 rounded w-20"></div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  <!-- System status -->
  <div>
    <h2 class="text-sm font-semibold text-neutral-900 mb-3">System Status</h2>
    <div class="grid grid-cols-3 gap-4">
      <!-- API Server -->
      <div class="bg-white rounded-xl border border-neutral-200 p-4 flex items-center gap-3">
        <div class="w-2.5 h-2.5 rounded-full shrink-0 {apiHealthy === true ? 'bg-emerald-500' : apiHealthy === false ? 'bg-red-500' : 'bg-neutral-300 animate-pulse'}"></div>
        <div>
          <p class="text-sm font-medium text-neutral-900">API Server</p>
          <p class="text-xs text-neutral-500">{apiHealthy === true ? 'Operational' : apiHealthy === false ? 'Unreachable' : 'Checking...'}</p>
        </div>
      </div>

      <!-- Portfolio Snapshots -->
      <div class="bg-white rounded-xl border border-neutral-200 p-4 flex items-center gap-3">
        <div class="w-2.5 h-2.5 rounded-full shrink-0 {analyticsHealth ? statusDot(analyticsHealth.portfolio.status) : 'bg-neutral-300 animate-pulse'}"></div>
        <div>
          <p class="text-sm font-medium text-neutral-900">Portfolio Snapshots</p>
          <p class="text-xs text-neutral-500">
            {#if analyticsHealth}
              {analyticsHealth.portfolio.status === "fresh" ? "Fresh" : analyticsHealth.portfolio.status === "stale" ? "Stale" : "Missing"} · {formatAge(analyticsHealth.portfolio.age_hours)}
            {:else}
              Checking...
            {/if}
          </p>
        </div>
      </div>

      <!-- Board KPIs -->
      <div class="bg-white rounded-xl border border-neutral-200 p-4 flex items-center gap-3">
        <div class="w-2.5 h-2.5 rounded-full shrink-0 {analyticsHealth ? statusDot(analyticsHealth.board_kpis.status) : 'bg-neutral-300 animate-pulse'}"></div>
        <div>
          <p class="text-sm font-medium text-neutral-900">Board KPIs</p>
          <p class="text-xs text-neutral-500">
            {#if analyticsHealth}
              {analyticsHealth.board_kpis.status === "fresh" ? "Fresh" : analyticsHealth.board_kpis.status === "stale" ? "Stale" : "Missing"} · {formatAge(analyticsHealth.board_kpis.age_hours)}
            {:else}
              Checking...
            {/if}
          </p>
        </div>
      </div>
    </div>
  </div>

  <!-- Cross-Module Activity Feed -->
  <div>
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-sm font-semibold text-neutral-900">Activity Feed</h2>
      <div class="flex items-center gap-2">
        <select bind:value={activityOrg} onchange={() => loadActivityFeed()} class="px-2.5 py-1.5 border border-neutral-200 rounded-lg text-xs bg-white text-neutral-600 focus:outline-none focus:ring-1 focus:ring-neutral-900">
          <option value="">All Tenants</option>
          {#each orgList as org}
            <option value={String(org.id)}>{org.name}</option>
          {/each}
        </select>
        <select bind:value={activityModule} onchange={() => loadActivityFeed()} class="px-2.5 py-1.5 border border-neutral-200 rounded-lg text-xs bg-white text-neutral-600 focus:outline-none focus:ring-1 focus:ring-neutral-900">
          <option value="">All Modules</option>
          <option value="crm">CRM</option>
          <option value="finance">Finance</option>
          <option value="hr">HR</option>
          <option value="projects">Projects</option>
          <option value="properties">Properties</option>
          <option value="procurement">Procurement</option>
          <option value="accounts">Accounts</option>
          <option value="documents">Documents</option>
          <option value="support">Support</option>
          <option value="partners">Partners</option>
        </select>
        <button type="button" onclick={loadActivityFeed} class="p-1.5 border border-neutral-200 rounded-lg text-neutral-400 hover:text-neutral-700 hover:bg-neutral-50 transition-colors" aria-label="Refresh feed">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M2.985 14.652V19.644" /></svg>
        </button>
      </div>
    </div>
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if activityLoading}
        <div class="p-8 text-center"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div></div>
      {:else if activityItems.length === 0}
        <div class="p-8 text-center"><p class="text-xs text-neutral-400">No activity recorded yet.</p></div>
      {:else}
        <div class="max-h-80 overflow-y-auto divide-y divide-neutral-100">
          {#each activityItems as item}
            <div class="px-4 py-3 flex items-start gap-3 hover:bg-neutral-50 transition-colors">
              <!-- Severity dot -->
              <div class="mt-1.5 shrink-0">
                <span class="block w-2 h-2 rounded-full" style="background: {item.severity === 'critical' ? '#ef4444' : item.severity === 'warning' ? '#eab308' : '#a3a3a3'};"></span>
              </div>

              <!-- Content -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded" style="background: {item.action === 'created' ? '#dcfce7' : item.action === 'deleted' ? '#fee2e2' : '#f3f4f6'}; color: {item.action === 'created' ? '#166534' : item.action === 'deleted' ? '#991b1b' : '#525252'};">
                    {item.action}
                  </span>
                  <span class="text-[10px] font-medium text-neutral-400 uppercase tracking-wider">{item.module}</span>
                  {#if item.tenant}
                    <span class="text-[10px] font-medium px-1.5 py-0.5 rounded" style="background: #ede9fe; color: #6d28d9;">{item.tenant}</span>
                  {:else}
                    <span class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-neutral-100 text-neutral-400">System</span>
                  {/if}
                </div>
                <p class="text-xs text-neutral-900 mt-1 truncate">{item.object_repr}</p>
                {#if item.actor}
                  <p class="text-[10px] text-neutral-400 mt-0.5">by {item.actor}</p>
                {/if}
              </div>

              <!-- Timestamp -->
              <span class="text-[10px] text-neutral-400 shrink-0 mt-1">{formatTimeAgo(item.timestamp)}</span>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <!-- Automation & Workflow Monitor -->
  {#if wfMonitor}
    <div>
      <h2 class="text-sm font-semibold text-neutral-900 mb-3">Automation & Workflow Engine</h2>

      <!-- Metric cards (pastel) -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
        <div class="rounded-xl border p-4" style="background: #f5f3ff; border-color: #ddd6fe;">
          <p class="text-[10px] font-medium uppercase tracking-wider mb-1" style="color: #8b5cf6;">Executed Today</p>
          <p class="text-2xl font-bold tabular-nums" style="color: #5b21b6;">{wfMonitor.total_today}</p>
        </div>
        <div class="rounded-xl border p-4" style="background: #ecfdf5; border-color: #a7f3d0;">
          <p class="text-[10px] font-medium uppercase tracking-wider mb-1" style="color: #34d399;">Completed</p>
          <p class="text-2xl font-bold tabular-nums" style="color: #047857;">{wfMonitor.completed_today}</p>
        </div>
        <div class="rounded-xl border p-4" style="background: {wfMonitor.failed_today > 0 ? '#fef2f2' : '#ecfdf5'}; border-color: {wfMonitor.failed_today > 0 ? '#fecaca' : '#a7f3d0'};">
          <p class="text-[10px] font-medium uppercase tracking-wider mb-1" style="color: {wfMonitor.failed_today > 0 ? '#f87171' : '#34d399'};">Failed</p>
          <p class="text-2xl font-bold tabular-nums" style="color: {wfMonitor.failed_today > 0 ? '#dc2626' : '#047857'};">{wfMonitor.failed_today}</p>
        </div>
        <div class="rounded-xl border p-4" style="background: {wfMonitor.delayed_jobs > 0 ? '#fffbeb' : '#ecfdf5'}; border-color: {wfMonitor.delayed_jobs > 0 ? '#fde68a' : '#a7f3d0'};">
          <p class="text-[10px] font-medium uppercase tracking-wider mb-1" style="color: {wfMonitor.delayed_jobs > 0 ? '#fbbf24' : '#34d399'};">Delayed Jobs</p>
          <p class="text-2xl font-bold tabular-nums" style="color: {wfMonitor.delayed_jobs > 0 ? '#d97706' : '#047857'};">{wfMonitor.delayed_jobs}</p>
          <p class="text-[10px] mt-0.5" style="color: {wfMonitor.delayed_jobs > 0 ? '#f59e0b' : '#6ee7b7'};">SLA breached</p>
        </div>
        <div class="rounded-xl border p-4" style="background: #eff6ff; border-color: #bfdbfe;">
          <p class="text-[10px] font-medium uppercase tracking-wider mb-1" style="color: #60a5fa;">Active</p>
          <p class="text-2xl font-bold tabular-nums" style="color: #1d4ed8;">{wfMonitor.active_workflows}</p>
          <p class="text-[10px] mt-0.5" style="color: #93c5fd;">in progress</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- Top Triggering Events -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <p class="text-xs font-semibold text-neutral-700 mb-3">Top Triggering Events</p>
          {#if wfMonitor.top_triggers.length === 0}
            <p class="text-xs text-neutral-400">No workflows triggered yet.</p>
          {:else}
            <div class="space-y-2">
              {#each wfMonitor.top_triggers as trigger}
                {@const maxCount = wfMonitor.top_triggers[0]?.count || 1}
                <div class="flex items-center gap-3">
                  <span class="text-xs text-neutral-700 w-28 truncate capitalize">{trigger.label}</span>
                  <div class="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
                    <div class="h-full bg-neutral-900 rounded-full" style="width: {Math.max((trigger.count / maxCount) * 100, 4)}%;"></div>
                  </div>
                  <span class="text-xs font-semibold text-neutral-900 tabular-nums w-8 text-right">{trigger.count}</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Recent Workflows with Drill-down -->
        <div class="bg-white rounded-xl border border-neutral-200 p-4">
          <p class="text-xs font-semibold text-neutral-700 mb-3">Recent Workflows</p>
          {#if wfMonitor.recent_instances.length === 0}
            <p class="text-xs text-neutral-400">No workflow instances.</p>
          {:else}
            <div class="max-h-56 overflow-y-auto space-y-1">
              {#each wfMonitor.recent_instances as inst}
                <button
                  type="button"
                  class="w-full text-left px-3 py-2 rounded-lg transition-colors"
                  style="background: {wfExpanded === inst.id ? '#f5f5f5' : 'white'};"
                  onclick={() => (wfExpanded = wfExpanded === inst.id ? null : inst.id)}
                >
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2 min-w-0">
                      <span class="w-2 h-2 rounded-full shrink-0" style="background: {inst.state === 'approved' ? '#22c55e' : inst.state === 'rejected' || inst.state === 'cancelled' ? '#ef4444' : inst.state === 'escalated' ? '#f59e0b' : '#a3a3a3'};"></span>
                      <span class="text-xs font-medium text-neutral-900 truncate">{inst.template_name}</span>
                    </div>
                    <span class="text-[10px] text-neutral-400 shrink-0 ml-2">{formatTimeAgo(inst.created_at)}</span>
                  </div>

                  <!-- Workflow Graph (drill-down) -->
                  {#if wfExpanded === inst.id && inst.steps.length > 0}
                    <div class="mt-2 flex items-center gap-1 flex-wrap">
                      {#each inst.steps as step, i}
                        <div class="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium" style="background: {step.decision === 'approved' ? '#dcfce7' : step.decision === 'rejected' ? '#fee2e2' : step.decision === 'escalated' ? '#fef3c7' : '#f3f4f6'}; color: {step.decision === 'approved' ? '#166534' : step.decision === 'rejected' ? '#991b1b' : step.decision === 'escalated' ? '#92400e' : '#525252'};">
                          {#if step.sla_breached}
                            <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                          {/if}
                          {step.name}
                        </div>
                        {#if i < inst.steps.length - 1}
                          <svg class="w-3 h-3 text-neutral-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
                        {/if}
                      {/each}
                    </div>
                  {:else if wfExpanded === inst.id}
                    <p class="mt-2 text-[10px] text-neutral-400">No steps recorded for this workflow.</p>
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  {/if}

  <!-- User Lifecycle -->
  {#if Object.keys(lifecycle.stages).length > 0}
    <div>
      <h2 class="text-sm font-semibold text-neutral-900 mb-3">User Lifecycle</h2>
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="divide-y divide-neutral-100">
          {#each Object.entries(lifecycle.stages) as [stage, count]}
            {@const totalUsers = Object.values(lifecycle.stages).reduce((a, b) => a + b, 0)}
            {@const pct = totalUsers > 0 ? (count / totalUsers) * 100 : 0}
            <div class="flex items-center gap-4 px-5 py-3">
              <span class="text-sm text-neutral-600 w-40">{lifecycleLabels[stage] ?? stage}</span>
              <div class="flex-1 h-2 bg-neutral-100 rounded-full overflow-hidden">
                <div
                  class="h-full bg-neutral-900 rounded-full transition-all"
                  style="width: {Math.max(pct, 1)}%"
                ></div>
              </div>
              <span class="text-sm font-medium text-neutral-900 tabular-nums w-12 text-right">{count}</span>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <!-- Quick Actions -->
  <div>
    <h2 class="text-sm font-semibold text-neutral-900 mb-3">Quick Actions</h2>
    <div class="grid grid-cols-3 gap-3">
      {#each quickActions as action}
        <a
          href={action.href}
          class="flex items-center gap-3 bg-white rounded-xl border border-neutral-200 px-4 py-3 hover:border-neutral-300 hover:shadow-sm transition-all group"
        >
          <div class="w-8 h-8 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 group-hover:bg-neutral-200 transition-colors">
            <svg class="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d={action.icon} />
            </svg>
          </div>
          <span class="text-sm font-medium text-neutral-700 group-hover:text-neutral-900 transition-colors">{action.label}</span>
        </a>
      {/each}
    </div>
  </div>
</div>

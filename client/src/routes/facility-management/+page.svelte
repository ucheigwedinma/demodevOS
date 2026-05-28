<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";

  interface PreventiveMaintenanceItem {
    id: number;
    title: string;
    next_due_date: string;
    property_name: string;
    asset_component_name: string;
    assigned_to: string;
    category: string;
  }

  interface FacilityDashboardOverview {
    generated_at: string;
    facility_health_score: number;
    active_maintenance_requests: {
      work_orders: number;
      service_requests: number;
      total: number;
    };
    sla_compliance_rate: {
      value: number;
      measured_count: number;
      on_time_count: number;
    };
    asset_uptime_downtime: {
      tracked_assets: number;
      degraded_assets: number;
      uptime_pct: number;
      downtime_pct: number;
    };
    energy_utility_consumption: {
      window_days: number;
      electricity_kwh: number;
      water_m3: number;
      diesel_liters: number;
      gas_m3: number;
      energy_index: number;
      energy_change_vs_previous_pct: number | null;
    };
    incident_alerts: {
      total_alerts: number;
      open_incidents: number;
      critical_incidents: number;
      high_incidents: number;
      post_incident_inspections: number;
      high_risk_inspections: number;
    };
    upcoming_preventive_maintenance: {
      upcoming_count: number;
      overdue_count: number;
      items: PreventiveMaintenanceItem[];
    };
  }

  let loading = $state(true);
  let refreshing = $state(false);
  let overview = $state<FacilityDashboardOverview | null>(null);

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtInt(value: unknown): string {
    return toNumber(value).toLocaleString("en-US");
  }

  function fmtPct(value: number | null | undefined): string {
    if (value === null || value === undefined) return "--";
    return `${value.toFixed(1)}%`;
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function fmtLabel(value: string): string {
    return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  async function fetchOverview() {
    if (!loading) refreshing = true;
    try {
      overview = await api.get<FacilityDashboardOverview>("/facility-management/dashboard/overview/");
    } catch {
      overview = null;
      toast.error("Load failed", "Could not load facility management dashboard.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  $effect(() => {
    fetchOverview();
  });

  const live = useLiveKpis(
    ["Document"],
    fetchOverview,
    { debounceMs: 5000 },
  );
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <div class="flex items-center gap-2">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-500">Facility Management</p>
        <LiveBadge refreshing={live.refreshing} />
      </div>
      <h1 class="mt-2 text-2xl font-bold text-neutral-800 tracking-wide">Dashboard</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Operational control for built assets, maintenance workload, incidents, and utility performance.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">
          Last refreshed: {fmtDateTime(overview.generated_at)}
        </p>
      {/if}
    </div>
    <button
      onclick={fetchOverview}
      disabled={refreshing}
      class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
      aria-label={refreshing ? "Refreshing facility management dashboard" : "Refresh facility management dashboard"}
      title={refreshing ? "Refreshing facility management dashboard" : "Refresh facility management dashboard"}
    >
      <svg
        class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        stroke-width="1.8"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003"
        />
      </svg>
    </button>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-10 text-center text-sm text-neutral-500">
      Loading facility dashboard...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Facility dashboard is unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 lg:grid-cols-12">
      <section class="rounded-2xl border border-teal-200 bg-teal-50 p-5 lg:col-span-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-teal-700">Facility Health Score</p>
        <p class="mt-3 text-2xl font-semibold text-teal-900">{fmtPct(overview.facility_health_score)}</p>
        <div class="mt-4 h-2 w-full overflow-hidden rounded-full bg-teal-100">
          <div
            class="h-full rounded-full bg-teal-500 transition-all"
            style={`width: ${Math.max(0, Math.min(overview.facility_health_score, 100))}%`}
          ></div>
        </div>
      </section>

      <section class="rounded-2xl border border-blue-200 bg-blue-50 p-5 lg:col-span-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-blue-700">Active Maintenance Requests</p>
        <p class="mt-3 text-2xl font-semibold text-blue-900">
          {fmtInt(overview.active_maintenance_requests.total)}
        </p>
        <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-blue-800">
          <p>Work Orders: {fmtInt(overview.active_maintenance_requests.work_orders)}</p>
          <p>Service Requests: {fmtInt(overview.active_maintenance_requests.service_requests)}</p>
        </div>
      </section>

      <section class="rounded-2xl border border-amber-200 bg-amber-50 p-5 lg:col-span-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">SLA Compliance Rate</p>
        <p class="mt-3 text-2xl font-semibold text-amber-900">{fmtPct(overview.sla_compliance_rate.value)}</p>
        <p class="mt-3 text-xs text-amber-800">
          {fmtInt(overview.sla_compliance_rate.on_time_count)} on-time out of
          {` ${fmtInt(overview.sla_compliance_rate.measured_count)} `}
          completed work orders with due dates.
        </p>
      </section>
    </div>

    <div class="grid gap-4 lg:grid-cols-12">
      <section class="rounded-2xl border border-violet-200 bg-violet-50 p-5 lg:col-span-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-violet-700">Asset Uptime / Downtime</p>
        <div class="mt-3 flex items-end justify-between gap-3">
          <p class="text-2xl font-semibold text-violet-900">{fmtPct(overview.asset_uptime_downtime.uptime_pct)}</p>
          <p class="text-sm text-violet-700">Downtime {fmtPct(overview.asset_uptime_downtime.downtime_pct)}</p>
        </div>
        <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-violet-800">
          <p>Tracked: {fmtInt(overview.asset_uptime_downtime.tracked_assets)}</p>
          <p>Degraded: {fmtInt(overview.asset_uptime_downtime.degraded_assets)}</p>
        </div>
      </section>

      <section class="rounded-2xl border border-orange-200 bg-orange-50 p-5 lg:col-span-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-orange-700">Incident Alerts</p>
        <p class="mt-3 text-2xl font-semibold text-orange-900">{fmtInt(overview.incident_alerts.total_alerts)}</p>
        <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-orange-800">
          <p>Open: {fmtInt(overview.incident_alerts.open_incidents)}</p>
          <p>Critical: {fmtInt(overview.incident_alerts.critical_incidents)}</p>
          <p>High: {fmtInt(overview.incident_alerts.high_incidents)}</p>
          <p>Post-Incident Checks: {fmtInt(overview.incident_alerts.post_incident_inspections)}</p>
        </div>
      </section>

      <section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-5 lg:col-span-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Upcoming Preventive Maintenance</p>
        <p class="mt-3 text-2xl font-semibold text-emerald-900">
          {fmtInt(overview.upcoming_preventive_maintenance.upcoming_count)}
        </p>
        <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-emerald-800">
          <p>Upcoming (30d): {fmtInt(overview.upcoming_preventive_maintenance.upcoming_count)}</p>
          <p>Overdue: {fmtInt(overview.upcoming_preventive_maintenance.overdue_count)}</p>
        </div>
      </section>
    </div>

    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Energy & Utility Consumption</h2>
          <p class="text-xs text-neutral-500">Last {overview.energy_utility_consumption.window_days} days</p>
        </div>
        <p class="text-xs text-neutral-500">
          Energy index change:
          <span
            class={`ml-1 rounded-full px-2 py-1 font-semibold ${
              (overview.energy_utility_consumption.energy_change_vs_previous_pct ?? 0) > 0
                ? "bg-red-50 text-red-700"
                : "bg-emerald-50 text-emerald-700"
            }`}
          >
            {fmtPct(overview.energy_utility_consumption.energy_change_vs_previous_pct)}
          </span>
        </p>
      </div>
      <div class="mt-4 grid gap-3 md:grid-cols-5">
        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-[11px] uppercase text-neutral-500">Electricity</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtInt(overview.energy_utility_consumption.electricity_kwh)}</p>
          <p class="text-xs text-neutral-500">kWh</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-[11px] uppercase text-neutral-500">Water</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtInt(overview.energy_utility_consumption.water_m3)}</p>
          <p class="text-xs text-neutral-500">m3</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-[11px] uppercase text-neutral-500">Diesel</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtInt(overview.energy_utility_consumption.diesel_liters)}</p>
          <p class="text-xs text-neutral-500">L</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-[11px] uppercase text-neutral-500">Gas</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtInt(overview.energy_utility_consumption.gas_m3)}</p>
          <p class="text-xs text-neutral-500">m3</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-[11px] uppercase text-neutral-500">Energy Index</p>
          <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtInt(overview.energy_utility_consumption.energy_index)}</p>
          <p class="text-xs text-neutral-500">total</p>
        </div>
      </div>
    </section>

    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <div class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Upcoming Preventive Maintenance</h2>
        <p class="text-xs text-neutral-500">
          Showing {fmtInt(overview.upcoming_preventive_maintenance.items.length)} of
          {` ${fmtInt(overview.upcoming_preventive_maintenance.upcoming_count)} `}
          due schedules.
        </p>
      </div>

      <div class="mt-4 overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="px-3 py-2">Schedule</th>
              <th class="px-3 py-2">Property</th>
              <th class="px-3 py-2">Asset</th>
              <th class="px-3 py-2">Category</th>
              <th class="px-3 py-2">Assigned</th>
              <th class="px-3 py-2">Due Date</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white text-neutral-700">
            {#if overview.upcoming_preventive_maintenance.items.length === 0}
              <tr>
                <td colspan="6" class="px-3 py-6 text-center text-sm text-neutral-500">
                  No preventive schedules due in the next 30 days.
                </td>
              </tr>
            {:else}
              {#each overview.upcoming_preventive_maintenance.items as item (item.id)}
                <tr>
                  <td class="px-3 py-3 font-medium text-neutral-900">{item.title}</td>
                  <td class="px-3 py-3">{item.property_name || "--"}</td>
                  <td class="px-3 py-3">{item.asset_component_name || "--"}</td>
                  <td class="px-3 py-3">{fmtLabel(item.category)}</td>
                  <td class="px-3 py-3">{item.assigned_to || "--"}</td>
                  <td class="px-3 py-3">{fmtDate(item.next_due_date)}</td>
                </tr>
              {/each}
            {/if}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

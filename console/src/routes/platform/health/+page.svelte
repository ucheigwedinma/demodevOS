<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { api } from "$lib/api";

  interface ServiceCheck {
    name: string;
    status: "ok" | "error" | "checking";
    detail: string;
    lastChecked: Date | null;
  }

  interface SnapshotHealth {
    status: string;
    last_computed: string | null;
    age_hours: number | null;
    is_stale: boolean;
  }

  let services = $state<ServiceCheck[]>([
    { name: "API Server", status: "checking", detail: "Checking...", lastChecked: null },
    { name: "Portfolio Snapshots", status: "checking", detail: "Checking...", lastChecked: null },
    { name: "Board KPI Engine", status: "checking", detail: "Checking...", lastChecked: null },
  ]);

  let refreshing = $state(false);
  let refreshInterval: ReturnType<typeof setInterval>;

  function formatAge(hours: number | null): string {
    if (hours == null) return "Never computed";
    if (hours < 1) return `${Math.round(hours * 60)} minutes ago`;
    if (hours < 24) return `${Math.round(hours)} hours ago`;
    return `${Math.round(hours / 24)} days ago`;
  }

  function formatTime(date: Date): string {
    return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function snapshotToService(name: string, snapshot: SnapshotHealth): ServiceCheck {
    let status: ServiceCheck["status"];
    let detail: string;

    switch (snapshot.status) {
      case "fresh":
        status = "ok";
        detail = `Fresh · Last computed ${formatAge(snapshot.age_hours)}`;
        break;
      case "stale":
        status = "error";
        detail = `Stale · Last computed ${formatAge(snapshot.age_hours)}`;
        break;
      default:
        status = "error";
        detail = "No data available";
    }

    return { name, status, detail, lastChecked: new Date() };
  }

  async function checkAll() {
    refreshing = true;

    // API health
    try {
      await api.get("/health/");
      services[0] = { name: "API Server", status: "ok", detail: "Operational", lastChecked: new Date() };
    } catch {
      services[0] = { name: "API Server", status: "error", detail: "Unreachable", lastChecked: new Date() };
    }

    // Analytics health
    try {
      const res = await api.get<{
        portfolio: SnapshotHealth;
        board_kpis: SnapshotHealth;
      }>("/analytics/health/");
      services[1] = snapshotToService("Portfolio Snapshots", res.portfolio);
      services[2] = snapshotToService("Board KPI Engine", res.board_kpis);
    } catch {
      services[1] = { name: "Portfolio Snapshots", status: "error", detail: "Could not check", lastChecked: new Date() };
      services[2] = { name: "Board KPI Engine", status: "error", detail: "Could not check", lastChecked: new Date() };
    }

    refreshing = false;
  }

  onMount(() => {
    checkAll();
    refreshInterval = setInterval(checkAll, 60000);
  });

  onDestroy(() => {
    clearInterval(refreshInterval);
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-xl font-semibold text-neutral-900">System Health</h1>
      <p class="text-sm text-neutral-500 mt-1">Service connectivity and data freshness</p>
    </div>
    <button
      onclick={checkAll}
      disabled={refreshing}
      class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-neutral-200 text-neutral-700 hover:bg-neutral-50 hover:border-neutral-300 transition-colors disabled:opacity-50"
    >
      <svg class="w-4 h-4 {refreshing ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
      </svg>
      {refreshing ? "Checking..." : "Refresh"}
    </button>
  </div>

  <!-- Auto-refresh notice -->
  <p class="text-xs text-neutral-400">Auto-refreshes every 60 seconds</p>

  <!-- Service cards -->
  <div class="space-y-3">
    {#each services as service}
      <div class="bg-white rounded-xl border border-neutral-200 p-5 flex items-center gap-4">
        <!-- Status indicator -->
        <div class="relative">
          {#if service.status === "checking"}
            <div class="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center">
              <div class="w-4 h-4 border-2 border-neutral-300 border-t-neutral-600 rounded-full animate-spin"></div>
            </div>
          {:else if service.status === "ok"}
            <div class="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
              </svg>
            </div>
          {:else}
            <div class="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
            </div>
          {/if}
        </div>

        <!-- Service info -->
        <div class="flex-1">
          <p class="text-sm font-medium text-neutral-900">{service.name}</p>
          <p class="text-xs text-neutral-500 mt-0.5">{service.detail}</p>
        </div>

        <!-- Last checked -->
        {#if service.lastChecked}
          <span class="text-xs text-neutral-400">
            Checked at {formatTime(service.lastChecked)}
          </span>
        {/if}

        <!-- Status badge -->
        <span class="text-xs font-medium px-2.5 py-1 rounded-full
                     {service.status === 'ok'
                       ? 'bg-emerald-50 text-emerald-700'
                       : service.status === 'error'
                         ? 'bg-red-50 text-red-700'
                         : 'bg-neutral-100 text-neutral-500'}">
          {service.status === "ok" ? "Healthy" : service.status === "error" ? "Issue" : "Checking"}
        </span>
      </div>
    {/each}
  </div>
</div>

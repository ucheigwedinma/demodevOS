<script lang="ts">
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { Equipment } from "$lib/types";

  let {
    open = false,
    equipmentId = null,
    onclose,
  }: {
    open?: boolean;
    equipmentId?: number | null;
    onclose?: () => void;
  } = $props();

  let loading = $state(true);
  let eq = $state<Equipment | null>(null);
  let activeTab = $state<"specs" | "maintenance" | "deployment">("specs");
  let loadedId: number | null = null;

  $effect(() => {
    if (open && equipmentId && equipmentId !== loadedId) {
      loadedId = equipmentId;
      loadData(equipmentId);
    }
    if (!open) {
      loadedId = null;
      activeTab = "specs";
    }
  });

  async function loadData(id: number) {
    loading = true;
    eq = null;
    try {
      eq = await api.get<Equipment>(`/projects/equipment/${id}/`);
    } catch {
      eq = null;
    }
    loading = false;
  }

  function close() {
    onclose?.();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") close();
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "--";
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function fmtCurrency(value: string | null | undefined): string {
    if (!value) return "--";
    return currency.formatCompact(value);
  }

  const statusGlow: Record<string, string> = {
    operational: "border-emerald-300 bg-emerald-50/40",
    in_repair: "border-orange-300 bg-orange-50/40",
    idle: "border-neutral-200 bg-neutral-50/40",
    decommissioned: "border-red-200 bg-red-50/40",
    in_transit: "border-blue-200 bg-blue-50/40",
  };

  const tabs = [
    { key: "specs" as const, label: "Technical Specs" },
    { key: "maintenance" as const, label: "Maintenance" },
    { key: "deployment" as const, label: "Deployment" },
  ];
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/30 z-998 transition-opacity"
    onclick={close}
    role="presentation"
  ></div>

  <!-- Drawer -->
  <div
    class="fixed inset-y-0 right-0 z-999 w-full max-w-[600px] bg-white shadow-2xl
           flex flex-col overflow-hidden animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="Equipment details"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-5 bg-linear-to-br from-neutral-900 to-neutral-800">
      <div class="min-w-0 flex-1">
        {#if loading}
          <div class="h-5 w-48 bg-white/10 rounded animate-pulse"></div>
          <div class="h-3.5 w-32 bg-white/5 rounded animate-pulse mt-1.5"></div>
        {:else if eq}
          <h2 class="text-base font-semibold text-white truncate">{eq.name}</h2>
          <p class="text-xs text-neutral-400 mt-0.5 flex items-center gap-2">
            {eq.asset_id}
            <StatusBadge status={eq.status} />
          </p>
        {:else}
          <h2 class="text-base font-semibold text-neutral-500">Equipment not found</h2>
        {/if}
      </div>
      <button
        onclick={close}
        class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-white transition-colors ml-4 shrink-0"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto">
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
          <span class="ml-3 text-sm text-neutral-400">Loading equipment...</span>
        </div>
      {:else if !eq}
        <div class="text-center py-20">
          <p class="text-sm text-neutral-400">Could not load equipment details.</p>
        </div>
      {:else}
        <!-- Live Status Card -->
        <div class="m-6 rounded-xl border {statusGlow[eq.status] ?? 'border-neutral-200 bg-neutral-50/40'} p-4 backdrop-blur-sm">
          <div class="grid grid-cols-3 gap-4 text-center">
            <div>
              <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</p>
              <p class="mt-1 text-sm font-bold text-neutral-900">{eq.status_display}</p>
            </div>
            <div>
              <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Location</p>
              <p class="mt-1 text-sm font-semibold text-neutral-900 truncate">{eq.current_location || "--"}</p>
            </div>
            <div>
              <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Operator</p>
              <p class="mt-1 text-sm font-semibold text-neutral-900 truncate">{eq.current_operator || "--"}</p>
            </div>
          </div>
        </div>

        <!-- Tabs -->
        <div class="border-b border-neutral-200 px-6">
          <nav class="flex gap-6">
            {#each tabs as tab}
              <button
                onclick={() => (activeTab = tab.key)}
                class="pb-2.5 text-sm font-medium border-b-2 transition-colors {activeTab === tab.key
                  ? 'border-neutral-900 text-neutral-900'
                  : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
              >
                {tab.label}
              </button>
            {/each}
          </nav>
        </div>

        <div class="p-6 space-y-5">
          {#if activeTab === "specs"}
            <!-- Technical Specifications -->
            <section class="space-y-3">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Identity</h3>
              <div class="grid grid-cols-2 gap-3">
                <div><p class="text-[10px] text-neutral-400">Make</p><p class="text-sm font-medium text-neutral-900">{eq.make || "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Model</p><p class="text-sm font-medium text-neutral-900">{eq.model_name || "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Type</p><p class="text-sm font-medium text-neutral-900">{eq.equipment_type_display}</p></div>
                <div><p class="text-[10px] text-neutral-400">Year</p><p class="text-sm font-medium text-neutral-900">{eq.year_of_manufacture ?? "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Serial Number</p><p class="text-sm font-medium text-neutral-900">{eq.serial_number || "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Engine Number</p><p class="text-sm font-medium text-neutral-900">{eq.engine_number || "--"}</p></div>
              </div>
            </section>

            <hr class="border-neutral-100" />

            <section class="space-y-3">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Performance</h3>
              <div class="grid grid-cols-2 gap-3">
                <div><p class="text-[10px] text-neutral-400">Fuel Type</p><p class="text-sm font-medium text-neutral-900">{eq.fuel_type_display}</p></div>
                <div><p class="text-[10px] text-neutral-400">Fuel Consumption</p><p class="text-sm font-medium text-neutral-900">{eq.fuel_consumption_rate ? `${eq.fuel_consumption_rate} L/hr` : "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Capacity</p><p class="text-sm font-medium text-neutral-900">{eq.capacity || "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Weight</p><p class="text-sm font-medium text-neutral-900">{eq.weight_kg ? `${Number(eq.weight_kg).toLocaleString()} kg` : "--"}</p></div>
              </div>
            </section>

            <hr class="border-neutral-100" />

            <section class="space-y-3">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Cost Recovery</h3>
              <div class="grid grid-cols-2 gap-3">
                <div><p class="text-[10px] text-neutral-400">Ownership</p><p class="text-sm font-medium text-neutral-900">{eq.ownership_display}</p></div>
                <div><p class="text-[10px] text-neutral-400">Purchase Price</p><p class="text-sm font-medium text-neutral-900">{fmtCurrency(eq.purchase_price)}</p></div>
                <div><p class="text-[10px] text-neutral-400">Book Value</p><p class="text-sm font-medium text-neutral-900">{fmtCurrency(eq.current_book_value)}</p></div>
                <div><p class="text-[10px] text-neutral-400">Daily Rate</p><p class="text-sm font-medium text-neutral-900">{fmtCurrency(eq.internal_daily_rate)}</p></div>
                <div><p class="text-[10px] text-neutral-400">Hourly Rate</p><p class="text-sm font-medium text-neutral-900">{fmtCurrency(eq.internal_hourly_rate)}</p></div>
                <div><p class="text-[10px] text-neutral-400">Mobilization Cost</p><p class="text-sm font-medium text-neutral-900">{fmtCurrency(eq.mobilization_cost)}</p></div>
              </div>
            </section>

            <hr class="border-neutral-100" />

            <section class="space-y-3">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Insurance</h3>
              <div class="grid grid-cols-2 gap-3">
                <div><p class="text-[10px] text-neutral-400">Policy Number</p><p class="text-sm font-medium text-neutral-900">{eq.insurance_policy_number || "--"}</p></div>
                <div><p class="text-[10px] text-neutral-400">Expiry</p><p class="text-sm font-medium text-neutral-900">{fmtDate(eq.insurance_expiry)}</p></div>
              </div>
            </section>

            {#if eq.notes}
              <hr class="border-neutral-100" />
              <section>
                <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">Notes</h3>
                <p class="text-sm text-neutral-700 whitespace-pre-wrap">{eq.notes}</p>
              </section>
            {/if}

          {:else if activeTab === "maintenance"}
            <!-- Maintenance & Telematics -->
            <section class="space-y-3">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Readings</h3>
              <div class="grid grid-cols-3 gap-3">
                <div><p class="text-[10px] text-neutral-400">Hour Meter</p><p class="text-sm font-bold tabular-nums text-neutral-900">{Number(eq.hour_meter_reading).toLocaleString()} hrs</p></div>
                <div><p class="text-[10px] text-neutral-400">Odometer</p><p class="text-sm font-bold tabular-nums text-neutral-900">{Number(eq.odometer_reading).toLocaleString()} km</p></div>
                <div><p class="text-[10px] text-neutral-400">Service Interval</p><p class="text-sm font-bold tabular-nums text-neutral-900">{eq.service_interval_hours ? `${eq.service_interval_hours} hrs` : "--"}</p></div>
              </div>
            </section>

            <section class="space-y-3">
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Service Schedule</h3>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <p class="text-[10px] text-neutral-400">Last Service</p>
                  <p class="text-sm font-medium text-neutral-900">{fmtDate(eq.last_service_date)}</p>
                </div>
                <div>
                  <p class="text-[10px] text-neutral-400">Next Service Due</p>
                  <p class="text-sm font-medium {eq.maintenance_due ? 'text-orange-600' : 'text-neutral-900'}">
                    {fmtDate(eq.next_service_due)}
                    {#if eq.maintenance_due}
                      <span class="ml-1 inline-block px-1.5 py-0.5 text-[10px] font-semibold bg-orange-100 text-orange-700 rounded">OVERDUE</span>
                    {/if}
                  </p>
                </div>
              </div>
            </section>

            <hr class="border-neutral-100" />

            <section>
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Fault & Service Logs</h3>
              {#if eq.maintenance_logs.length === 0}
                <p class="text-sm text-neutral-400 py-4 text-center">No maintenance records yet.</p>
              {:else}
                <div class="space-y-2.5">
                  {#each eq.maintenance_logs as log}
                    <div class="rounded-lg border border-neutral-100 p-3">
                      <div class="flex items-start justify-between gap-2">
                        <div>
                          <p class="text-sm font-medium text-neutral-900">{log.description}</p>
                          {#if log.parts_replaced}
                            <p class="mt-0.5 text-xs text-neutral-500">Parts: {log.parts_replaced}</p>
                          {/if}
                        </div>
                        <StatusBadge status={log.log_type} />
                      </div>
                      <div class="mt-2 flex items-center gap-4 text-[11px] text-neutral-400">
                        <span>{fmtDate(log.date)}</span>
                        {#if log.performed_by}<span>By: {log.performed_by}</span>{/if}
                        {#if Number(log.cost) > 0}<span>Cost: {fmtCurrency(log.cost)}</span>{/if}
                        {#if Number(log.downtime_hours) > 0}<span>Downtime: {log.downtime_hours}h</span>{/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </section>

          {:else if activeTab === "deployment"}
            <!-- Deployment History -->
            <section>
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">
                Operator Certification
              </h3>
              <div class="flex items-center gap-2 rounded-lg border border-neutral-100 p-3">
                {#if eq.operator_license_verified}
                  <span class="h-5 w-5 flex items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                  </span>
                  <span class="text-sm text-emerald-700 font-medium">Operator license verified</span>
                {:else}
                  <span class="h-5 w-5 flex items-center justify-center rounded-full bg-amber-100 text-amber-600">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126Z" /></svg>
                  </span>
                  <span class="text-sm text-amber-700 font-medium">License not verified</span>
                {/if}
              </div>
            </section>

            <hr class="border-neutral-100" />

            <section>
              <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Site Log</h3>
              {#if eq.deployment_logs.length === 0}
                <p class="text-sm text-neutral-400 py-4 text-center">No deployment records yet.</p>
              {:else}
                <div class="space-y-2.5">
                  {#each eq.deployment_logs as dep}
                    <div class="rounded-lg border border-neutral-100 p-3">
                      <div class="flex items-start justify-between gap-2">
                        <div>
                          <p class="text-sm font-semibold text-neutral-900">{dep.project_name}</p>
                          {#if dep.site_name}
                            <p class="text-xs text-neutral-500">{dep.site_name}</p>
                          {/if}
                        </div>
                        {#if dep.returned_date}
                          <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-neutral-100 text-neutral-500">Returned</span>
                        {:else}
                          <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-100 text-emerald-700">Active</span>
                        {/if}
                      </div>
                      <div class="mt-2 flex items-center gap-4 text-[11px] text-neutral-400">
                        <span>{fmtDate(dep.deployed_date)}{dep.returned_date ? ` → ${fmtDate(dep.returned_date)}` : ""}</span>
                        {#if dep.operator}<span>Operator: {dep.operator}</span>{/if}
                        {#if Number(dep.hours_used) > 0}<span>{dep.hours_used} hrs</span>{/if}
                      </div>
                      {#if dep.notes}
                        <p class="mt-1.5 text-xs text-neutral-500">{dep.notes}</p>
                      {/if}
                    </div>
                  {/each}
                </div>
              {/if}
            </section>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }
  .animate-slide-in {
    animation: slideIn 0.2s ease-out;
  }
</style>

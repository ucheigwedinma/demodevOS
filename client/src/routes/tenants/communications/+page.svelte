<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      messages_30_days: number;
      queued_broadcasts: number;
      failed_messages: number;
      reminders_30_days: number;
    };
    recent_logs: CommunicationLog[];
    broadcasts: BroadcastRecord[];
  }

  interface CommunicationLog {
    id: number | string;
    subject: string;
    message: string;
    channel_display: string;
    status_display: string;
    happened_at: string;
    author_name: string;
  }

  interface BroadcastRecord {
    id: number;
    audience_type_display: string;
    status_display: string;
    subject: string;
    recipient_count: number;
    delivered_count: number;
    sent_at: string | null;
  }

  interface LookupItem {
    id: number;
    label: string;
  }

  let loading = $state(true);
  let refreshing = $state(false);
  let syncing = $state(false);
  let saving = $state(false);
  let showDrawer = $state(false);

  let overview = $state<Overview | null>(null);
  let logs = $state<CommunicationLog[]>([]);
  let broadcasts = $state<BroadcastRecord[]>([]);
  let propertyLookup = $state<LookupItem[]>([]);
  let facilityLookup = $state<LookupItem[]>([]);

  let form = $state({
    audience_type: "all_tenants",
    property: "",
    facility: "",
    tenant_type_filter: "",
    status: "queued",
    subject: "",
    message: "",
    send_email: true,
    send_whatsapp: false,
    send_in_app: true,
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  function devFillBroadcast() {
    const subjects = ["Scheduled Maintenance Notice — Water Supply", "Community Event: End-of-Year Social", "Updated Parking Regulations Effective Immediately", "Fire Drill Scheduled for Next Friday", "Rent Payment Reminder — Q2 2026", "New Waste Disposal Guidelines"];
    const messages = [
      "Dear Tenants,\n\nPlease be advised that water supply will be temporarily interrupted on Saturday, March 22, from 08:00 to 14:00 for scheduled maintenance. We recommend storing water in advance.\n\nThank you for your understanding.\n\nFacilities Management",
      "Dear Residents,\n\nYou are cordially invited to our end-of-year community social event. Light refreshments will be provided. Please RSVP by replying to this message.\n\nBest regards,\nManagement",
      "Dear Tenants,\n\nEffective immediately, all vehicles must display valid parking permits. Unauthorized vehicles will be subject to towing. Contact the front desk for permit applications.\n\nThank you.",
    ];
    const idx = Math.floor(Math.random() * subjects.length);
    form.subject = subjects[idx];
    form.message = messages[idx % messages.length];
    form.audience_type = ["all_tenants", "by_property", "by_facility"][Math.floor(Math.random() * 3)];
    form.send_email = true;
    form.send_in_app = true;
    form.send_whatsapp = Math.random() > 0.5;
    form.notes = "Broadcast queued for immediate delivery.";
  }

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function parseApiMessage(error: unknown, fallback: string) {
    if (error instanceof ApiError) {
      if (typeof error.body?.detail === "string" && error.body.detail.trim()) return error.body.detail;
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ").trim();
      if (fieldMessage) return fieldMessage;
    }
    if (error instanceof Error && error.message.trim()) return error.message;
    return fallback;
  }

  async function loadData(showSpinner = true) {
    if (showSpinner) loading = true;
    try {
      const [overviewRes, logsRes, broadcastRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/communications/overview/"),
        api.get<CommunicationLog[]>("/tenants/communications/logs/"),
        api.get<BroadcastRecord[]>("/tenants/communications/broadcasts/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      logs = logsRes;
      broadcasts = broadcastRes;
      propertyLookup = (lookupsRes.properties ?? []).map((item: any) => ({ id: item.id, label: item.name }));
      facilityLookup = lookupsRes.facilities ?? [];
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load tenant communications."));
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function refreshAll() {
    refreshing = true;
    await loadData(false);
  }

  async function runWorkflows() {
    syncing = true;
    try {
      const result = await api.post<Record<string, number>>("/tenants/communications/sync/", {});
      toast.success(
        "Communication sync completed",
        `Reminders ${result.rent_reminders_sent ?? 0}, broadcasts ${result.broadcasts_processed ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run communication workflows."));
    } finally {
      syncing = false;
    }
  }

  function openDrawer() {
    form = {
      audience_type: "all_tenants",
      property: "",
      facility: "",
      tenant_type_filter: "",
      status: "queued",
      subject: "",
      message: "",
      send_email: true,
      send_whatsapp: false,
      send_in_app: true,
      notes: "",
    };
    showDrawer = true;
  }

  async function saveBroadcast() {
    saving = true;
    try {
      await api.post("/tenants/communications/broadcasts/", {
        ...form,
        property: form.property ? Number(form.property) : null,
        facility: form.facility ? Number(form.facility) : null,
      });
      toast.success("Broadcast saved", "The audience campaign is queued for workflow delivery.");
      showDrawer = false;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the broadcast."));
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    void loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Communication & Engagement</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Rent reminders, announcements, email/WhatsApp outreach, and broadcast targeting by property, facility, or tenant segment.
      </p>
      {#if overview?.generated_at}<p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>{/if}
    </div>
    <div class="flex items-center gap-2 self-start">
      <button aria-label="Refresh data" onclick={refreshAll} disabled={refreshing || loading} class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50">
        <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" /></svg>
      </button>
      <button onclick={runWorkflows} disabled={syncing || loading} class="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{syncing ? "Running..." : "Run Workflows"}</button>
    </div>
  </div>

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <section class="rounded-2xl border border-violet-200/70 bg-linear-to-br from-violet-50 via-white to-fuchsia-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">30d Messages</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.messages_30_days ?? 0}</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Queued Broadcasts</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.queued_broadcasts ?? 0}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Failed</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.failed_messages ?? 0}</p></section>
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Reminders</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.reminders_30_days ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading communication engine...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Communication Log</p>
              <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Email, WhatsApp, and in-app history</h2>
            </div>
            <button onclick={openDrawer} class="rounded-xl bg-violet-500 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-600">New Broadcast</button>
          </div>
          <div class="space-y-3">
            {#each logs.slice(0, 12) as log}
              <article class="rounded-2xl border border-neutral-200 bg-white p-4">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{log.subject}</p>
                    <p class="mt-1 text-xs text-neutral-500">{log.channel_display} • {fmtDateTime(log.happened_at)}</p>
                  </div>
                  <span class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold text-neutral-700">{log.status_display}</span>
                </div>
                <p class="mt-2 text-sm text-neutral-600 line-clamp-2">{log.message}</p>
              </article>
            {/each}
          </div>
        </div>

        <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Broadcast Queue</p>
          <div class="mt-4 space-y-3">
            {#each broadcasts.slice(0, 8) as broadcast}
              <article class="rounded-2xl border border-white/80 bg-white p-3 shadow-sm">
                <p class="text-sm font-semibold text-neutral-900">{broadcast.subject}</p>
                <p class="mt-1 text-xs text-neutral-500">{broadcast.audience_type_display}</p>
                <p class="mt-2 text-sm text-neutral-600">{broadcast.delivered_count} / {broadcast.recipient_count} delivered</p>
                <p class="mt-1 text-xs text-neutral-400">{broadcast.status_display} • {fmtDateTime(broadcast.sent_at)}</p>
              </article>
            {/each}
          </div>
        </div>
      </div>
    </section>
  {/if}
</div>

{#if showDrawer}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={() => (showDrawer = false)} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Audience Campaign</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-wider text-neutral-900">New Broadcast</h2>
      </div>
      <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      <label class="space-y-2 text-sm text-neutral-600"><span>Audience</span><select bind:value={form.audience_type} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="all_tenants">All tenants</option><option value="property">Specific property</option><option value="facility">Specific facility</option><option value="tenant_type">Tenant type</option><option value="delinquent">Delinquent tenants</option><option value="lease_expiry">Expiring leases</option></select></label>
      {#if form.audience_type === "property"}
        <label class="space-y-2 text-sm text-neutral-600"><span>Property</span><select bind:value={form.property} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select property</option>{#each propertyLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      {/if}
      {#if form.audience_type === "facility"}
        <label class="space-y-2 text-sm text-neutral-600"><span>Facility</span><select bind:value={form.facility} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select facility</option>{#each facilityLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      {/if}
      {#if form.audience_type === "tenant_type"}
        <label class="space-y-2 text-sm text-neutral-600"><span>Tenant type</span><select bind:value={form.tenant_type_filter} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select tenant type</option><option value="individual">Individual</option><option value="corporate">Corporate</option></select></label>
      {/if}
      <label class="space-y-2 text-sm text-neutral-600"><span>Subject</span><input bind:value={form.subject} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Message</span><textarea rows="6" bind:value={form.message} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5"></textarea></label>
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}<button type="button" onclick={devFillBroadcast} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>{/if}
      <button onclick={() => (showDrawer = false)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveBroadcast} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Save Broadcast"}</button>
    </div>
  </aside>
{/if}

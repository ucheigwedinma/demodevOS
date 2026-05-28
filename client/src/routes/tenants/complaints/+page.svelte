<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      open_complaints: number;
      escalated: number;
      resolved_30_days: number;
      linked_service_requests: number;
    };
    watchlist: ComplaintRecord[];
  }

  interface ComplaintRecord {
    id: number;
    tenant_name: string;
    subject: string;
    category_display: string;
    priority_display: string;
    status_display: string;
    sla_due_at: string | null;
    service_request_title: string;
    feedback_rating: number | null;
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
  let complaints = $state<ComplaintRecord[]>([]);
  let tenantLookup = $state<LookupItem[]>([]);

  let form = $state({
    tenant_profile: "",
    category: "maintenance",
    priority: "medium",
    subject: "",
    description: "",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  function devFillComplaint() {
    const subjects = ["Noise disturbance from adjacent unit", "Water pressure issue in bathroom", "Parking space blocked by unauthorized vehicle", "Broken security gate latch — Block C", "Pest sighting in common area kitchen", "Elevator frequently out of service"];
    const cats = ["maintenance", "noise", "parking", "security", "pest_control", "facility"];
    const idx = Math.floor(Math.random() * subjects.length);
    form.subject = subjects[idx];
    form.description = `${subjects[idx]}. Tenant reports recurring issue affecting daily operations. Requesting prompt investigation and resolution.`;
    form.category = cats[idx % cats.length];
    form.priority = ["low", "medium", "high"][Math.floor(Math.random() * 3)];
    form.notes = "Logged via tenant portal. Follow-up within 24 hours required.";
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
      const [overviewRes, complaintRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/complaints/overview/"),
        api.get<ComplaintRecord[]>("/tenants/complaints/records/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      complaints = complaintRes;
      tenantLookup = lookupsRes.tenants ?? [];
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load complaints and escalations."));
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
      const result = await api.post<Record<string, number>>("/tenants/complaints/sync/", {});
      toast.success(
        "Complaint sync completed",
        `Escalated ${result.complaints_escalated ?? 0}, service requests created ${result.service_requests_created ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run complaint workflows."));
    } finally {
      syncing = false;
    }
  }

  function openDrawer() {
    form = {
      tenant_profile: "",
      category: "maintenance",
      priority: "medium",
      subject: "",
      description: "",
      notes: "",
    };
    showDrawer = true;
  }

  async function saveComplaint() {
    saving = true;
    try {
      await api.post("/tenants/complaints/records/", {
        ...form,
        tenant_profile: Number(form.tenant_profile),
      });
      toast.success("Complaint logged", "Escalation SLA and facility linkage are now being tracked.");
      showDrawer = false;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the complaint."));
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
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-rose-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Complaints & Escalations</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Complaint logging, escalation workflow, SLA enforcement, and resolution tracking across billing, maintenance, and tenant conduct issues.
      </p>
      {#if overview?.generated_at}<p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>{/if}
    </div>
    <div class="flex items-center gap-2 self-start">
      <!-- svelte-ignore a11y_consider_explicit_label -->
      <button onclick={refreshAll} disabled={refreshing || loading} class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50">
        <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" /></svg>
      </button>
      <button onclick={runWorkflows} disabled={syncing || loading} class="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{syncing ? "Running..." : "Run Workflows"}</button>
    </div>
  </div>

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Open</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.open_complaints ?? 0}</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Escalated</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.escalated ?? 0}</p></section>
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Resolved 30d</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.resolved_30_days ?? 0}</p></section>
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Linked Requests</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.linked_service_requests ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading complaints...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Complaint Register</p>
          <h2 class="mt-1 text-sm font-bold uppercase tracking-wider text-neutral-800">Logged issues and escalation status</h2>
        </div>
        <button onclick={openDrawer} class="rounded-xl bg-rose-500 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-600">Log Complaint</button>
      </div>
      <div class="overflow-x-auto rounded-2xl border border-neutral-200">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
            <tr>
              <th class="px-4 py-3 text-left">Complaint</th>
              <th class="px-4 py-3 text-left">Tenant</th>
              <th class="px-4 py-3 text-left">Priority</th>
              <th class="px-4 py-3 text-left">Status</th>
              <th class="px-4 py-3 text-left">SLA Due</th>
              <th class="px-4 py-3 text-left">Linked Request</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white">
            {#each complaints.slice(0, 14) as complaint}
              <tr class="transition hover:bg-neutral-50/80">
                <td class="px-4 py-3"><p class="font-semibold text-neutral-900">{complaint.subject}</p><p class="text-xs text-neutral-500">{complaint.category_display}</p></td>
                <td class="px-4 py-3 text-neutral-600">{complaint.tenant_name}</td>
                <td class="px-4 py-3 text-neutral-600">{complaint.priority_display}</td>
                <td class="px-4 py-3"><span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-700">{complaint.status_display}</span></td>
                <td class="px-4 py-3 text-neutral-600">{fmtDateTime(complaint.sla_due_at)}</td>
                <td class="px-4 py-3 text-neutral-600">{complaint.service_request_title || "--"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

{#if showDrawer}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={() => (showDrawer = false)} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Complaint Workflow</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-wider text-neutral-900">Log Complaint</h2>
      </div>
      <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      <label class="space-y-2 text-sm text-neutral-600"><span>Tenant</span><select bind:value={form.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select tenant</option>{#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Category</span><select bind:value={form.category} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="maintenance">Maintenance</option><option value="billing">Billing</option><option value="security">Security</option><option value="noise">Noise</option><option value="cleanliness">Cleanliness</option><option value="communication">Communication</option><option value="legal">Legal</option><option value="other">Other</option></select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Priority</span><select bind:value={form.priority} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></select></label>
      </div>
      <label class="space-y-2 text-sm text-neutral-600"><span>Subject</span><input bind:value={form.subject} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Description</span><textarea rows="6" bind:value={form.description} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5"></textarea></label>
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}<button type="button" onclick={devFillComplaint} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>{/if}
      <button onclick={() => (showDrawer = false)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveComplaint} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Save Complaint"}</button>
    </div>
  </aside>
{/if}

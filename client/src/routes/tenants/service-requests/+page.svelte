<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      open_requests: number;
      escalated_requests: number;
      sla_at_risk: number;
      resolved_requests: number;
      avg_feedback: number | null;
    };
    watchlist: ServiceRequestRecord[];
  }

  interface ServiceRequestRecord {
    id: number;
    title: string;
    description: string;
    property_name: string;
    facility_code: string;
    category_display: string;
    priority_display: string;
    status: string;
    status_display: string;
    requested_date: string;
    sla_due_at: string | null;
    feedback_rating: number | null;
    unit_number: string;
    location_label: string;
  }

  type DrawerMode = "request" | "feedback" | null;

  let loading = $state(true);
  let refreshing = $state(false);
  let syncing = $state(false);
  let saving = $state(false);
  let drawerMode = $state<DrawerMode>(null);

  let overview = $state<Overview | null>(null);
  let requests = $state<ServiceRequestRecord[]>([]);
  let spaceLookup = $state<Array<{ id: number; label: string }>>([]);

  let form = $state({
    facility_space: "",
    title: "",
    description: "",
    category: "general",
    priority: "medium",
    source_channel: "web",
  });

  let feedbackForm = $state({
    requestId: 0,
    feedback_rating: "5",
    feedback_comment: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillRequest() {
    const titles = ["AC not cooling in unit 3A", "Water leak from ceiling — Block B corridor", "Power outage in parking level 2", "Broken window latch — Office 204", "Elevator stuck on floor 7", "Pest control needed — kitchen area", "Internet connectivity drop in conference room"];
    const categories = ["general", "maintenance", "plumbing", "electrical", "hvac", "pest_control", "security"];
    const priorities = ["low", "medium", "high", "critical"];
    const channels = ["web", "phone", "email", "walk_in"];
    const idx = Math.floor(Math.random() * titles.length);
    form.title = titles[idx];
    form.description = `${titles[idx]}. Reported by tenant during working hours. Requires immediate assessment and resolution within SLA.`;
    form.category = categories[idx % categories.length];
    form.priority = priorities[Math.floor(Math.random() * priorities.length)];
    form.source_channel = channels[Math.floor(Math.random() * channels.length)];
  }

  function fmtDate(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
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
      const [overviewRes, requestRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/service-requests/overview/"),
        api.get<ServiceRequestRecord[]>("/tenants/service-requests/requests/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      requests = requestRes;
      spaceLookup = lookupsRes.spaces ?? [];
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load tenant service requests."));
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
      const result = await api.post<Record<string, number>>("/tenants/service-requests/sync/", {});
      toast.success(
        "Workflow completed",
        `Requests synced ${result.service_requests_synced ?? 0}, escalated ${result.service_requests_escalated ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run service request workflows."));
    } finally {
      syncing = false;
    }
  }

  function openRequestDrawer() {
    form = { facility_space: "", title: "", description: "", category: "general", priority: "medium", source_channel: "web" };
    drawerMode = "request";
  }

  function openFeedbackDrawer(requestItem: ServiceRequestRecord) {
    feedbackForm = { requestId: requestItem.id, feedback_rating: String(requestItem.feedback_rating || 5), feedback_comment: "" };
    drawerMode = "feedback";
  }

  async function saveDrawer() {
    saving = true;
    try {
      if (drawerMode === "request") {
        await api.post("/tenants/service-requests/requests/", {
          ...form,
          facility_space: form.facility_space ? Number(form.facility_space) : null,
        });
        toast.success("Request logged", "Facility integration, SLA tracking, and work-order automation are active.");
      } else if (drawerMode === "feedback") {
        await api.post(`/tenants/service-requests/requests/${feedbackForm.requestId}/feedback/`, {
          feedback_rating: Number(feedbackForm.feedback_rating),
          feedback_comment: feedbackForm.feedback_comment,
        });
        toast.success("Feedback saved", "Tenant rating and comments were recorded.");
      }
      drawerMode = null;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the service-request action."));
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
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-sky-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Service Requests</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Tenant maintenance issue logging, status visibility, SLA tracking, and feedback flow integrated with the facility team.
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

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Open</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.open_requests ?? 0}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Escalated</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.escalated_requests ?? 0}</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">SLA At Risk</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.sla_at_risk ?? 0}</p></section>
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Resolved</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.resolved_requests ?? 0}</p></section>
    <section class="rounded-2xl border border-neutral-200 bg-linear-to-br from-neutral-50 via-white to-slate-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-600">Avg Feedback</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.avg_feedback ?? "--"}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading tenant requests...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Request Register</p>
          <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Maintenance issues and tenant-facing SLA queue</h2>
        </div>
        <button onclick={openRequestDrawer} class="rounded-xl bg-sky-500 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-600">Log Request</button>
      </div>
      <div class="overflow-x-auto rounded-2xl border border-neutral-200">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
            <tr>
              <th class="px-4 py-3 text-left">Request</th>
              <th class="px-4 py-3 text-left">Location</th>
              <th class="px-4 py-3 text-left">Priority</th>
              <th class="px-4 py-3 text-left">Status</th>
              <th class="px-4 py-3 text-left">SLA Due</th>
              <th class="px-4 py-3 text-left">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white">
            {#each requests.slice(0, 14) as item}
              <tr class="transition hover:bg-neutral-50/80">
                <td class="px-4 py-3"><p class="font-semibold text-neutral-900">{item.title}</p><p class="text-xs text-neutral-500">{item.category_display}</p></td>
                <td class="px-4 py-3 text-neutral-600">{item.property_name} {item.location_label ? `• ${item.location_label}` : ""}</td>
                <td class="px-4 py-3 text-neutral-600">{item.priority_display}</td>
                <td class="px-4 py-3"><span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-700">{item.status_display}</span></td>
                <td class="px-4 py-3 text-neutral-600">{fmtDateTime(item.sla_due_at)}</td>
                <td class="px-4 py-3">
                  {#if item.status === "resolved" || item.status === "closed"}
                    <button onclick={() => openFeedbackDrawer(item)} class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Feedback</button>
                  {:else}
                    <span class="text-xs text-neutral-400">Live</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

{#if drawerMode}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={() => (drawerMode = null)} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Tenant Requests</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">{drawerMode === "request" ? "Log Service Request" : "Save Feedback"}</h2>
      </div>
      <button onclick={() => (drawerMode = null)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      {#if drawerMode === "request"}
        <label class="space-y-2 text-sm text-neutral-600">
          <span>Mapped room / space</span>
          <select bind:value={form.facility_space} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
            <option value="">Select room / space</option>
            {#each spaceLookup as item}<option value={item.id}>{item.label}</option>{/each}
          </select>
        </label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Title</span><input bind:value={form.title} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Description</span><textarea rows="5" bind:value={form.description} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5"></textarea></label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="space-y-2 text-sm text-neutral-600"><span>Category</span><select bind:value={form.category} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="general">General</option><option value="electrical">Electrical</option><option value="plumbing">Plumbing</option><option value="hvac">HVAC</option><option value="cleaning">Cleaning</option></select></label>
          <label class="space-y-2 text-sm text-neutral-600"><span>Priority</span><select bind:value={form.priority} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
        </div>
      {:else}
        <label class="space-y-2 text-sm text-neutral-600"><span>Rating</span><select bind:value={feedbackForm.feedback_rating} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="5">5</option><option value="4">4</option><option value="3">3</option><option value="2">2</option><option value="1">1</option></select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Comment</span><textarea rows="5" bind:value={feedbackForm.feedback_comment} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5"></textarea></label>
      {/if}
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev && drawerMode === "request"}
        <button type="button" onclick={devFillRequest} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button onclick={() => (drawerMode = null)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveDrawer} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Save"}</button>
    </div>
  </aside>
{/if}

<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      scheduled: number;
      completed_30_days: number;
      move_out_pending: number;
      deposit_deductions: string;
      settlement_queue: number;
    };
    watchlist: InspectionRecord[];
    settlement_watchlist: DepositSettlementRecord[];
  }

  interface InspectionRecord {
    id: number;
    tenant_name: string;
    title: string;
    inspection_type_display: string;
    status_display: string;
    scheduled_date: string;
    completed_date: string | null;
    checklist_summary: string;
    security_deposit_deduction: string;
  }

  interface DepositSettlementRecord {
    id: number;
    tenant_name: string;
    lease_code: string;
    status: string;
    status_display: string;
    move_out_date: string | null;
    deposit_amount: string;
    assessed_deductions: string;
    refundable_amount: string;
    additional_amount_due: string;
    collection_invoice_number: string;
    notes: string;
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
  let inspections = $state<InspectionRecord[]>([]);
  let tenantLookup = $state<LookupItem[]>([]);
  let leaseLookup = $state<LookupItem[]>([]);

  let form = $state({
    tenant_profile: "",
    lease_agreement: "",
    inspection_type: "move_in",
    status: "scheduled",
    title: "",
    scheduled_date: "",
    checklist_summary: "",
    security_deposit_deduction: "",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  function devFillInspection() {
    const today = new Date().toISOString().slice(0, 10);
    const titles = ["Move-in condition assessment", "Annual safety compliance check", "Pre-lease renewal inspection", "Move-out damage assessment", "Quarterly facility walkthrough"];
    const types = ["move_in", "move_out", "routine", "safety", "pre_renewal"];
    const idx = Math.floor(Math.random() * titles.length);
    form.title = titles[idx];
    form.inspection_type = types[idx % types.length];
    form.status = "scheduled";
    form.scheduled_date = today;
    form.checklist_summary = "Walls, floors, fixtures, plumbing, electrical, windows, doors, appliances — all to be inspected and rated.";
    form.security_deposit_deduction = form.inspection_type === "move_out" ? String(Math.floor(Math.random() * 200000) + 10000) : "";
    form.notes = "Inspector to photograph all findings. Report due within 48 hours.";
  }

  function fmtDate(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function fmtMoney(value?: string | number | null) {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: "NGN", maximumFractionDigits: 2 }).format(Number(value ?? 0));
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
      const [overviewRes, inspectionRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/inspections/overview/"),
        api.get<InspectionRecord[]>("/tenants/inspections/records/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      inspections = inspectionRes;
      tenantLookup = lookupsRes.tenants ?? [];
      leaseLookup = (lookupsRes.leases ?? []).map((item: any) => ({ id: item.id, label: item.label }));
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load tenant inspections."));
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
      const result = await api.post<Record<string, number>>("/tenants/inspections/sync/", {});
      toast.success(
        "Inspection sync completed",
        `Inspections created ${result.inspections_created ?? 0}, facility alerts ${result.facility_inspection_alerts_sent ?? 0}, settlements ready ${result.deposit_settlements_ready ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run inspection workflows."));
    } finally {
      syncing = false;
    }
  }

  function openDrawer() {
    form = {
      tenant_profile: "",
      lease_agreement: "",
      inspection_type: "move_in",
      status: "scheduled",
      title: "",
      scheduled_date: "",
      checklist_summary: "",
      security_deposit_deduction: "",
      notes: "",
    };
    showDrawer = true;
  }

  async function saveInspection() {
    saving = true;
    try {
      await api.post("/tenants/inspections/records/", {
        ...form,
        tenant_profile: Number(form.tenant_profile),
        lease_agreement: form.lease_agreement ? Number(form.lease_agreement) : null,
        security_deposit_deduction: Number(form.security_deposit_deduction || 0),
      });
      toast.success("Inspection saved", "Move-in / move-out management record created.");
      showDrawer = false;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the inspection."));
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
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Inspections & Move-In/Out</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Move-in and move-out checklist control, damage assessment, and security-deposit deduction tracking.
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
    <section class="rounded-2xl border border-slate-200/70 bg-linear-to-br from-slate-50 via-white to-zinc-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-700">Scheduled</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.scheduled ?? 0}</p></section>
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Completed 30d</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.completed_30_days ?? 0}</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Move-Out Pending</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.move_out_pending ?? 0}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Deposit Deductions</p><p class="mt-3 text-xl font-semibold text-neutral-900">{fmtMoney(overview?.kpis.deposit_deductions)}</p></section>
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Settlement Queue</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.settlement_queue ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading inspections...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Inspection Register</p>
          <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Move-in, move-out, and periodic checks</h2>
        </div>
        <button onclick={openDrawer} class="rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800">Schedule Inspection</button>
      </div>
      <div class="overflow-x-auto rounded-2xl border border-neutral-200">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
            <tr>
              <th class="px-4 py-3 text-left">Inspection</th>
              <th class="px-4 py-3 text-left">Tenant</th>
              <th class="px-4 py-3 text-left">Type</th>
              <th class="px-4 py-3 text-left">Scheduled</th>
              <th class="px-4 py-3 text-left">Status</th>
              <th class="px-4 py-3 text-left">Deposit Deduction</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100 bg-white">
            {#each inspections.slice(0, 14) as inspection}
              <tr class="transition hover:bg-neutral-50/80">
                <td class="px-4 py-3 font-semibold text-neutral-900">{inspection.title}</td>
                <td class="px-4 py-3 text-neutral-600">{inspection.tenant_name}</td>
                <td class="px-4 py-3 text-neutral-600">{inspection.inspection_type_display}</td>
                <td class="px-4 py-3 text-neutral-600">{fmtDate(inspection.scheduled_date)}</td>
                <td class="px-4 py-3"><span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-700">{inspection.status_display}</span></td>
                <td class="px-4 py-3 text-neutral-900">{fmtMoney(inspection.security_deposit_deduction)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Deposit Settlement</p>
          <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Refund and collection follow-up</h2>
        </div>
      </div>
      <div class="grid gap-4 lg:grid-cols-2">
        {#each overview?.settlement_watchlist ?? [] as settlement}
          <article class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-neutral-900">{settlement.tenant_name}</p>
                <p class="mt-1 text-xs text-neutral-500">{settlement.lease_code} • move-out {fmtDate(settlement.move_out_date)}</p>
              </div>
              <span class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold text-neutral-700">{settlement.status_display}</span>
            </div>
            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              <div class="rounded-xl border border-white/80 bg-white p-3">
                <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-500">Deposit</p>
                <p class="mt-2 text-sm font-semibold text-neutral-900">{fmtMoney(settlement.deposit_amount)}</p>
              </div>
              <div class="rounded-xl border border-white/80 bg-white p-3">
                <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-500">Deductions</p>
                <p class="mt-2 text-sm font-semibold text-neutral-900">{fmtMoney(settlement.assessed_deductions)}</p>
              </div>
              <div class="rounded-xl border border-white/80 bg-white p-3">
                <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-500">Refund Due</p>
                <p class="mt-2 text-sm font-semibold text-emerald-700">{fmtMoney(settlement.refundable_amount)}</p>
              </div>
              <div class="rounded-xl border border-white/80 bg-white p-3">
                <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-500">Collection Due</p>
                <p class="mt-2 text-sm font-semibold text-rose-700">{fmtMoney(settlement.additional_amount_due)}</p>
              </div>
            </div>
            <p class="mt-3 text-sm text-neutral-600">{settlement.notes || "Deposit settlement is being prepared."}</p>
            {#if settlement.collection_invoice_number}
              <p class="mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">Collection invoice {settlement.collection_invoice_number}</p>
            {/if}
          </article>
        {/each}
        {#if !(overview?.settlement_watchlist?.length)}
          <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-4 py-8 text-sm text-neutral-500 lg:col-span-2">
            No active deposit settlements right now.
          </div>
        {/if}
      </div>
    </section>
  {/if}
</div>

{#if showDrawer}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={() => (showDrawer = false)} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Tenant Inspection</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Schedule Inspection</h2>
      </div>
      <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      <label class="space-y-2 text-sm text-neutral-600"><span>Tenant</span><select bind:value={form.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select tenant</option>{#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Lease</span><select bind:value={form.lease_agreement} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select lease</option>{#each leaseLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Type</span><select bind:value={form.inspection_type} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="move_in">Move-in</option><option value="move_out">Move-out</option><option value="periodic">Periodic</option></select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Scheduled date</span><input type="date" bind:value={form.scheduled_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      </div>
      <label class="space-y-2 text-sm text-neutral-600"><span>Title</span><input bind:value={form.title} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}<button type="button" onclick={devFillInspection} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>{/if}
      <button onclick={() => (showDrawer = false)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveInspection} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Save Inspection"}</button>
    </div>
  </aside>
{/if}

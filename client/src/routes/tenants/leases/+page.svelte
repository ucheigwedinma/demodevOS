<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      active_leases: number;
      expiring_soon: number;
      pending_renewals: number;
      termination_queue: number;
      notice_given: number;
      vacancy_risks_open: number;
    };
    lease_watchlist: LeaseRecord[];
    vacancy_risk_watchlist: VacancyRiskRecord[];
  }

  interface LeaseRecord {
    id: number;
    tenant_name: string;
    lease_code: string;
    property_name: string;
    unit_label: string;
    facility_code: string;
    space_label: string;
    status: string;
    status_display: string;
    start_date: string;
    end_date: string;
    rent_amount: string;
    service_charge_amount: string;
    currency?: string;
    payment_frequency_display: string;
  }

  interface RenewalRecord {
    id: number;
    tenant_name: string;
    lease_code: string;
    status: string;
    status_display: string;
    proposed_start_date: string;
    proposed_end_date: string;
    proposed_rent_amount: string;
  }

  interface TerminationRecord {
    id: number;
    tenant_name: string;
    lease_code: string;
    status: string;
    status_display: string;
    requested_move_out_date: string;
    effective_date: string | null;
    reason: string;
  }

  interface VacancyRiskRecord {
    id: number;
    tenant_name: string;
    lease_code: string;
    property_name: string;
    unit_label: string;
    status: string;
    status_display: string;
    risk_level: string;
    risk_level_display: string;
    risk_score: number;
    forecasted_vacancy_date: string | null;
    days_to_vacancy: number;
    notes: string;
  }

  interface LookupItem {
    id: number;
    label: string;
  }

  type DrawerMode = "lease" | "renewal" | "termination" | null;

  let loading = $state(true);
  let refreshing = $state(false);
  let syncing = $state(false);
  let saving = $state(false);

  let overview = $state<Overview | null>(null);
  let leases = $state<LeaseRecord[]>([]);
  let renewals = $state<RenewalRecord[]>([]);
  let terminations = $state<TerminationRecord[]>([]);

  let tenantLookup = $state<LookupItem[]>([]);
  let leaseLookup = $state<LookupItem[]>([]);
  let propertyLookup = $state<LookupItem[]>([]);
  let unitLookup = $state<LookupItem[]>([]);
  let facilityLookup = $state<LookupItem[]>([]);
  let spaceLookup = $state<LookupItem[]>([]);

  let drawerMode = $state<DrawerMode>(null);

  let leaseForm = $state({
    tenant_profile: "",
    property: "",
    unit: "",
    facility: "",
    facility_space: "",
    title: "",
    start_date: "",
    end_date: "",
    rent_amount: "",
    service_charge_amount: "",
    security_deposit: "",
    payment_frequency: "monthly",
    escalation_rule: "none",
    escalation_value: "",
    notice_period_days: "30",
    auto_generate_billing: true,
    renewal_option: true,
    notes: "",
  });

  let renewalForm = $state({
    tenant_profile: "",
    lease_agreement: "",
    proposed_start_date: "",
    proposed_end_date: "",
    proposed_rent_amount: "",
    proposed_service_charge_amount: "",
    notes: "",
  });

  let terminationForm = $state({
    tenant_profile: "",
    lease_agreement: "",
    requested_move_out_date: "",
    effective_date: "",
    notice_period_days: "30",
    reason: "",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillLease() {
    const today = new Date().toISOString().slice(0, 10);
    const nextYear = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const titles = ["Standard Commercial Lease", "Residential Tenancy Agreement", "Short-Term Office Lease", "Warehouse Storage Lease", "Retail Space Lease"];
    leaseForm.title = titles[Math.floor(Math.random() * titles.length)];
    leaseForm.start_date = today;
    leaseForm.end_date = nextYear;
    leaseForm.rent_amount = String(Math.floor(Math.random() * 5000000) + 500000);
    leaseForm.service_charge_amount = String(Math.floor(Math.random() * 500000) + 50000);
    leaseForm.security_deposit = String(Math.floor(Math.random() * 2000000) + 200000);
    leaseForm.payment_frequency = ["monthly", "quarterly", "annually"][Math.floor(Math.random() * 3)];
    leaseForm.escalation_rule = ["none", "fixed_percent", "cpi"][Math.floor(Math.random() * 3)];
    leaseForm.escalation_value = leaseForm.escalation_rule !== "none" ? String(Math.floor(Math.random() * 10) + 3) : "";
    leaseForm.notice_period_days = ["30", "60", "90"][Math.floor(Math.random() * 3)];
    leaseForm.auto_generate_billing = true;
    leaseForm.renewal_option = Math.random() > 0.3;
    leaseForm.notes = "Standard lease terms apply. Annual rent review clause included.";
    if (tenantLookup.length > 0 && !leaseForm.tenant_profile) leaseForm.tenant_profile = String(tenantLookup[0].id);
    if (propertyLookup.length > 0 && !leaseForm.property) leaseForm.property = String(propertyLookup[0].id);
    if (unitLookup.length > 0 && !leaseForm.unit) leaseForm.unit = String(unitLookup[0].id);
  }

  function devFillRenewal() {
    const nextMonth = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const nextYearPlus = new Date(Date.now() + 395 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    renewalForm.proposed_start_date = nextMonth;
    renewalForm.proposed_end_date = nextYearPlus;
    renewalForm.proposed_rent_amount = String(Math.floor(Math.random() * 5500000) + 600000);
    renewalForm.proposed_service_charge_amount = String(Math.floor(Math.random() * 550000) + 60000);
    renewalForm.notes = "Renewal with 10% rent escalation as per lease agreement clause 7.2.";
    if (tenantLookup.length > 0 && !renewalForm.tenant_profile) renewalForm.tenant_profile = String(tenantLookup[0].id);
    if (leaseLookup.length > 0 && !renewalForm.lease_agreement) renewalForm.lease_agreement = String(leaseLookup[0].id);
  }

  function devFillTermination() {
    const nextMonth = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const twoMonths = new Date(Date.now() + 60 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    terminationForm.requested_move_out_date = twoMonths;
    terminationForm.effective_date = twoMonths;
    terminationForm.notice_period_days = "60";
    terminationForm.reason = "Tenant relocating operations to a larger facility. All obligations to be settled before move-out date.";
    terminationForm.notes = "Exit inspection to be scheduled 7 days before move-out.";
    if (tenantLookup.length > 0 && !terminationForm.tenant_profile) terminationForm.tenant_profile = String(tenantLookup[0].id);
    if (leaseLookup.length > 0 && !terminationForm.lease_agreement) terminationForm.lease_agreement = String(leaseLookup[0].id);
  }

  function fmtDate(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function fmtMoney(value?: string | number | null, currency = "NGN") {
    const amount = Number(value ?? 0);
    return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 2 }).format(amount);
  }

  function parseApiMessage(error: unknown, fallback: string) {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string" && error.data.detail.trim()) return error.data.detail;
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ").trim();
      if (fieldMessage) return fieldMessage;
    }
    if (error instanceof Error && error.message.trim()) return error.message;
    return fallback;
  }

  function riskTone(level?: string) {
    if (level === "critical") return "bg-rose-100 text-rose-700";
    if (level === "high") return "bg-orange-100 text-orange-700";
    if (level === "medium") return "bg-amber-100 text-amber-700";
    return "bg-sky-100 text-sky-700";
  }

  async function loadData(showSpinner = true) {
    if (showSpinner) loading = true;
    try {
      const [overviewRes, lookupsRes, leaseRes, renewalRes, terminationRes] = await Promise.all([
        api.get<Overview>("/tenants/lease-occupancy/overview/"),
        api.get<any>("/tenants/operations/lookups/"),
        api.get<LeaseRecord[]>("/tenants/lease-occupancy/leases/"),
        api.get<RenewalRecord[]>("/tenants/lease-occupancy/renewals/"),
        api.get<TerminationRecord[]>("/tenants/lease-occupancy/terminations/"),
      ]);
      overview = overviewRes;
      leases = leaseRes;
      renewals = renewalRes;
      terminations = terminationRes;
      tenantLookup = lookupsRes.tenants ?? [];
      leaseLookup = (lookupsRes.leases ?? []).map((item: any) => ({ id: item.id, label: item.label }));
      propertyLookup = (lookupsRes.properties ?? []).map((item: any) => ({ id: item.id, label: item.name }));
      unitLookup = lookupsRes.units ?? [];
      facilityLookup = lookupsRes.facilities ?? [];
      spaceLookup = lookupsRes.spaces ?? [];
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load lease management."));
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
      const result = await api.post<Record<string, number>>("/tenants/lease-occupancy/sync/", {});
      toast.success(
        "Workflows completed",
        `Leases synced ${result.leases_synced ?? 0}, renewals ${result.renewals_created ?? 0}, vacancy alerts ${result.vacancy_risks_open ?? 0}, admin alerts ${result.admin_expiry_alerts_sent ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run lease workflows."));
    } finally {
      syncing = false;
    }
  }

  function resetForms() {
    leaseForm = {
      tenant_profile: "",
      property: "",
      unit: "",
      facility: "",
      facility_space: "",
      title: "",
      start_date: "",
      end_date: "",
      rent_amount: "",
      service_charge_amount: "",
      security_deposit: "",
      payment_frequency: "monthly",
      escalation_rule: "none",
      escalation_value: "",
      notice_period_days: "30",
      auto_generate_billing: true,
      renewal_option: true,
      notes: "",
    };
    renewalForm = {
      tenant_profile: "",
      lease_agreement: "",
      proposed_start_date: "",
      proposed_end_date: "",
      proposed_rent_amount: "",
      proposed_service_charge_amount: "",
      notes: "",
    };
    terminationForm = {
      tenant_profile: "",
      lease_agreement: "",
      requested_move_out_date: "",
      effective_date: "",
      notice_period_days: "30",
      reason: "",
      notes: "",
    };
  }

  function openDrawer(mode: DrawerMode) {
    resetForms();
    drawerMode = mode;
  }

  function closeDrawer() {
    drawerMode = null;
  }

  async function saveDrawer() {
    saving = true;
    try {
      if (drawerMode === "lease") {
        await api.post("/tenants/lease-occupancy/leases/", {
          ...leaseForm,
          tenant_profile: Number(leaseForm.tenant_profile),
          property: leaseForm.property ? Number(leaseForm.property) : null,
          unit: leaseForm.unit ? Number(leaseForm.unit) : null,
          facility: leaseForm.facility ? Number(leaseForm.facility) : null,
          facility_space: leaseForm.facility_space ? Number(leaseForm.facility_space) : null,
          rent_amount: Number(leaseForm.rent_amount || 0),
          service_charge_amount: Number(leaseForm.service_charge_amount || 0),
          security_deposit: Number(leaseForm.security_deposit || 0),
          escalation_value: Number(leaseForm.escalation_value || 0),
          notice_period_days: Number(leaseForm.notice_period_days || 30),
        });
        toast.success("Lease created", "The lease contract and billing posture were saved.");
      } else if (drawerMode === "renewal") {
        await api.post("/tenants/lease-occupancy/renewals/", {
          ...renewalForm,
          tenant_profile: Number(renewalForm.tenant_profile),
          lease_agreement: Number(renewalForm.lease_agreement),
          proposed_rent_amount: Number(renewalForm.proposed_rent_amount || 0),
          proposed_service_charge_amount: Number(renewalForm.proposed_service_charge_amount || 0),
        });
        toast.success("Renewal request created", "Renewal workflow is now queued for approval.");
      } else if (drawerMode === "termination") {
        await api.post("/tenants/lease-occupancy/terminations/", {
          ...terminationForm,
          tenant_profile: Number(terminationForm.tenant_profile),
          lease_agreement: Number(terminationForm.lease_agreement),
          notice_period_days: Number(terminationForm.notice_period_days || 30),
          effective_date: terminationForm.effective_date || null,
        });
        toast.success("Termination request created", "Termination approval tracking has started.");
      }
      closeDrawer();
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the lease workflow record."));
    } finally {
      saving = false;
    }
  }

  async function approveRenewal(id: number) {
    try {
      await api.post(`/tenants/lease-occupancy/renewals/${id}/approve/`, {});
      toast.success("Renewal approved", "The renewal record is now approved.");
      await loadData(false);
    } catch (error) {
      toast.error("Approve failed", parseApiMessage(error, "Could not approve the renewal."));
    }
  }

  async function approveTermination(id: number) {
    try {
      await api.post(`/tenants/lease-occupancy/terminations/${id}/approve/`, {});
      toast.success("Termination approved", "Lease termination and inspection workflow were updated.");
      await loadData(false);
    } catch (error) {
      toast.error("Approve failed", parseApiMessage(error, "Could not approve the termination."));
    }
  }

  onMount(() => {
    void loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Lease Management</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Core engine for lease contracts, renewals, terminations, notice tracking, billing posture, and vacancy risk.
      </p>
      <p class="mt-1 max-w-3xl text-xs text-neutral-400">
        Occupancy allocation, tenant mapping, space configuration, and bookings remain in Facility Management &gt; Space & Occupancy Management.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>
    <div class="flex items-center gap-2 self-start">
      <button
        onclick={refreshAll}
        disabled={refreshing || loading}
        class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50"
        aria-label="Refresh lease management"
        title="Refresh lease management"
      >
        <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
        </svg>
      </button>
      <button
        onclick={runWorkflows}
        disabled={syncing || loading}
        class="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
      >
        {syncing ? "Running..." : "Run Workflows"}
      </button>
    </div>
  </div>

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Active Leases</p>
      <p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.active_leases ?? 0}</p>
    </section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-orange-50 p-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Expiring Soon</p>
      <p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.expiring_soon ?? 0}</p>
    </section>
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Renewals</p>
      <p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.pending_renewals ?? 0}</p>
    </section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Termination Queue</p>
      <p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.termination_queue ?? 0}</p>
    </section>
    <section class="rounded-2xl border border-fuchsia-200/70 bg-linear-to-br from-fuchsia-50 via-white to-pink-50 p-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-fuchsia-700">Notice Given</p>
      <p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.notice_given ?? 0}</p>
    </section>
    <section class="rounded-2xl border border-violet-200/70 bg-linear-to-br from-violet-50 via-white to-indigo-50 p-4">
      <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-violet-700">Vacancy Risk</p>
      <p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.vacancy_risks_open ?? 0}</p>
    </section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading lease engine...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Lease Register</p>
              <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Active, expiring, and billed contracts</h2>
            </div>
            <button onclick={() => openDrawer("lease")} class="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600">New Lease</button>
          </div>
          <div class="overflow-x-auto rounded-2xl border border-neutral-200">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
                <tr>
                  <th class="px-4 py-3 text-left">Lease</th>
                  <th class="px-4 py-3 text-left">Location</th>
                  <th class="px-4 py-3 text-left">Term</th>
                  <th class="px-4 py-3 text-left">Rent</th>
                  <th class="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 bg-white">
                {#each leases.slice(0, 12) as lease}
                  <tr class="transition hover:bg-neutral-50/80">
                    <td class="px-4 py-3">
                      <p class="font-semibold text-neutral-900">{lease.lease_code}</p>
                      <p class="text-xs text-neutral-500">{lease.tenant_name}</p>
                    </td>
                    <td class="px-4 py-3 text-neutral-600">{lease.property_name} {lease.unit_label ? `• ${lease.unit_label}` : ""}</td>
                    <td class="px-4 py-3 text-neutral-600">{fmtDate(lease.start_date)} - {fmtDate(lease.end_date)}</td>
                    <td class="px-4 py-3 text-neutral-900">{fmtMoney(lease.rent_amount, lease.currency || "NGN")}</td>
                    <td class="px-4 py-3"><span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-semibold text-neutral-700">{lease.status_display}</span></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>

        <div class="space-y-4">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Renewals</p>
                <h3 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Pending approval queue</h3>
              </div>
              <button onclick={() => openDrawer("renewal")} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">New</button>
            </div>
            <div class="mt-4 space-y-3">
              {#each renewals.slice(0, 4) as renewal}
                <article class="rounded-2xl border border-white/80 bg-white p-3 shadow-sm">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-neutral-900">{renewal.tenant_name}</p>
                      <p class="text-xs text-neutral-500">{renewal.lease_code} • {fmtDate(renewal.proposed_start_date)} - {fmtDate(renewal.proposed_end_date)}</p>
                    </div>
                    {#if renewal.status === "pending"}
                      <button onclick={() => approveRenewal(renewal.id)} class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800">Approve</button>
                    {:else}
                      <span class="rounded-full bg-emerald-100 px-3 py-1 text-[11px] font-semibold text-emerald-700">{renewal.status_display}</span>
                    {/if}
                  </div>
                  <p class="mt-2 text-sm text-neutral-600">Proposed rent {fmtMoney(renewal.proposed_rent_amount)}</p>
                </article>
              {/each}
            </div>
          </div>

          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Terminations</p>
                <h3 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Notice and exit approvals</h3>
              </div>
              <button onclick={() => openDrawer("termination")} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">New</button>
            </div>
            <div class="mt-4 space-y-3">
              {#each terminations.slice(0, 4) as termination}
                <article class="rounded-2xl border border-white/80 bg-white p-3 shadow-sm">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-neutral-900">{termination.tenant_name}</p>
                      <p class="text-xs text-neutral-500">{termination.lease_code} • move-out {fmtDate(termination.requested_move_out_date)}</p>
                    </div>
                    {#if termination.status === "requested" || termination.status === "pending_approval"}
                      <button onclick={() => approveTermination(termination.id)} class="rounded-lg bg-rose-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-600">Approve</button>
                    {:else}
                      <span class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold text-neutral-700">{termination.status_display}</span>
                    {/if}
                  </div>
                  <p class="mt-2 text-sm text-neutral-600">{termination.reason || "No reason logged yet."}</p>
                </article>
              {/each}
            </div>
          </div>

          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Vacancy Risk</p>
                <h3 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Leases likely to turn vacant</h3>
              </div>
              <span class="rounded-full bg-violet-100 px-3 py-1 text-[11px] font-semibold text-violet-700">
                {overview?.kpis.vacancy_risks_open ?? 0} active
              </span>
            </div>
            <div class="mt-4 space-y-3">
              {#each overview?.vacancy_risk_watchlist ?? [] as risk}
                <article class="rounded-2xl border border-white/80 bg-white p-3 shadow-sm">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-neutral-900">{risk.tenant_name}</p>
                      <p class="text-xs text-neutral-500">
                        {risk.lease_code} • {risk.property_name}{risk.unit_label ? ` • ${risk.unit_label}` : ""}
                      </p>
                    </div>
                    <span class={`rounded-full px-3 py-1 text-[11px] font-semibold ${riskTone(risk.risk_level)}`}>
                      {risk.risk_level_display}
                    </span>
                  </div>
                  <div class="mt-3 flex items-center justify-between text-xs text-neutral-500">
                    <span>{risk.forecasted_vacancy_date ? `Forecast ${fmtDate(risk.forecasted_vacancy_date)}` : "Forecast pending"}</span>
                    <span>Score {risk.risk_score}</span>
                  </div>
                  <p class="mt-2 text-sm text-neutral-600">{risk.notes || "Lease requires renewal or exit planning."}</p>
                </article>
              {/each}
              {#if !(overview?.vacancy_risk_watchlist?.length)}
                <div class="rounded-2xl border border-dashed border-neutral-200 bg-white px-4 py-5 text-sm text-neutral-500">
                  No active vacancy-risk alerts right now.
                </div>
              {/if}
            </div>
          </div>
        </div>
      </div>
    </section>
  {/if}
</div>

{#if drawerMode}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={closeDrawer} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Tenant Workflow</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">
          {drawerMode === "lease" ? "Create Lease" : drawerMode === "renewal" ? "Create Renewal" : "Create Termination"}
        </h2>
      </div>
      <button onclick={closeDrawer} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>

    <div class="space-y-4 px-6 py-5">
      {#if drawerMode === "lease"}
        <label class="space-y-2 text-sm text-neutral-600">
          <span>Tenant</span>
          <select bind:value={leaseForm.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
            <option value="">Select tenant</option>
            {#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}
          </select>
        </label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Title</span><input bind:value={leaseForm.title} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="space-y-2 text-sm text-neutral-600"><span>Start date</span><input type="date" bind:value={leaseForm.start_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
          <label class="space-y-2 text-sm text-neutral-600"><span>End date</span><input type="date" bind:value={leaseForm.end_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="space-y-2 text-sm text-neutral-600"><span>Rent amount</span><input type="number" bind:value={leaseForm.rent_amount} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
          <label class="space-y-2 text-sm text-neutral-600"><span>Service charge</span><input type="number" bind:value={leaseForm.service_charge_amount} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="space-y-2 text-sm text-neutral-600">
            <span>Unit</span>
            <select bind:value={leaseForm.unit} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
              <option value="">Select unit</option>
              {#each unitLookup as item}<option value={item.id}>{item.label}</option>{/each}
            </select>
          </label>
          <label class="space-y-2 text-sm text-neutral-600">
            <span>Facility space</span>
            <select bind:value={leaseForm.facility_space} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
              <option value="">Select space</option>
              {#each spaceLookup as item}<option value={item.id}>{item.label}</option>{/each}
            </select>
          </label>
        </div>
      {:else if drawerMode === "renewal"}
        <label class="space-y-2 text-sm text-neutral-600">
          <span>Tenant</span>
          <select bind:value={renewalForm.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
            <option value="">Select tenant</option>
            {#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}
          </select>
        </label>
        <label class="space-y-2 text-sm text-neutral-600">
          <span>Lease</span>
          <select bind:value={renewalForm.lease_agreement} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
            <option value="">Select lease</option>
            {#each leaseLookup as item}<option value={item.id}>{item.label}</option>{/each}
          </select>
        </label>
        <div class="grid gap-4 sm:grid-cols-2">
          <label class="space-y-2 text-sm text-neutral-600"><span>Proposed start</span><input type="date" bind:value={renewalForm.proposed_start_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
          <label class="space-y-2 text-sm text-neutral-600"><span>Proposed end</span><input type="date" bind:value={renewalForm.proposed_end_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        </div>
        <label class="space-y-2 text-sm text-neutral-600"><span>Proposed rent</span><input type="number" bind:value={renewalForm.proposed_rent_amount} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      {:else}
        <label class="space-y-2 text-sm text-neutral-600">
          <span>Tenant</span>
          <select bind:value={terminationForm.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
            <option value="">Select tenant</option>
            {#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}
          </select>
        </label>
        <label class="space-y-2 text-sm text-neutral-600">
          <span>Lease</span>
          <select bind:value={terminationForm.lease_agreement} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">
            <option value="">Select lease</option>
            {#each leaseLookup as item}<option value={item.id}>{item.label}</option>{/each}
          </select>
        </label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Requested move-out date</span><input type="date" bind:value={terminationForm.requested_move_out_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Reason</span><textarea rows="4" bind:value={terminationForm.reason} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5"></textarea></label>
      {/if}
    </div>

    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}
        <button
          type="button"
          onclick={() => {
            if (drawerMode === "lease") devFillLease();
            else if (drawerMode === "renewal") devFillRenewal();
            else if (drawerMode === "termination") devFillTermination();
          }}
          class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600"
        >Dev Fill</button>
      {/if}
      <button onclick={closeDrawer} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveDrawer} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
        {saving ? "Saving..." : "Save"}
      </button>
    </div>
  </aside>
{/if}

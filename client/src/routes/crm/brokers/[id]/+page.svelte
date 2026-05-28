<script lang="ts">
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import LeadReadOnlyModal from "$lib/components/crm/LeadReadOnlyModal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    BrokerDetail,
    BrokerTier,
    BrokerPerformance,
    BrokerForecast,
    CommissionEarning,
    CommissionStructure,
    BrokerStatus,
    PipelineStage,
  } from "$lib/types";

  let {
    brokerId: brokerIdProp = null,
    embedded = false,
  }: {
    brokerId?: number | string | null;
    embedded?: boolean;
  } = $props();

  const brokerId = $derived(String(brokerIdProp ?? $page.params.id ?? ""));

  // --- Core state ---
  let broker = $state<BrokerDetail | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let editing = $state(false);

  // --- Tab state ---
  let activeTab = $state<"profile" | "performance" | "commissions" | "forecast">("profile");

  // --- Edit form ---
  let editForm = $state({
    name: "",
    company: "",
    license_number: "",
    email: "",
    phone: "",
    commission_rate: "",
    tier: "" as string,
    status: "active" as BrokerStatus,
    notes: "",
  });

  // --- Tiers ---
  let tiers = $state<BrokerTier[]>([]);

  // --- Performance ---
  let performance = $state<BrokerPerformance | null>(null);
  let perfLoading = $state(false);
  let perfMonths = $state(12);

  // --- Commissions ---
  let earnings = $state<CommissionEarning[]>([]);
  let earningsLoading = $state(false);

  // --- Forecast ---
  let forecast = $state<BrokerForecast | null>(null);
  let forecastLoading = $state(false);

  // --- Commission actions ---
  let approvingId = $state<number | null>(null);
  let markPaidId = $state<number | null>(null);
  let paymentRef = $state("");
  let showPaymentModal = $state(false);
  let paymentEarningId = $state<number | null>(null);
  let showLeadModal = $state(false);
  let selectedLeadId = $state<number | null>(null);

  // --- Helpers ---
  function fmtDate(value: string | null | undefined): string {
    if (!value) return "\u2014";
    const d = new Date(value);
    if (isNaN(d.getTime())) return "\u2014";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "\u2014";
    const d = new Date(value);
    if (isNaN(d.getTime())) return "\u2014";
    return d.toLocaleDateString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  function fmtPct(value: number | string | null | undefined): string {
    if (value == null) return "\u2014";
    const n = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(n)) return "\u2014";
    return n.toFixed(1) + "%";
  }

  function fmtNum(value: number | string | null | undefined): string {
    if (value == null) return "\u2014";
    const n = typeof value === "string" ? parseFloat(value) : value;
    if (isNaN(n)) return "\u2014";
    return n.toLocaleString();
  }

  const earningStatusBadge: Record<string, string> = {
    pending: "bg-neutral-100 text-neutral-600",
    approved: "bg-neutral-200 text-neutral-800",
    processing: "bg-neutral-300 text-neutral-800",
    paid: "bg-neutral-900 text-white",
    cancelled: "bg-neutral-100 text-neutral-400 line-through",
  };

  const pipelineStageLabels: Record<PipelineStage, string> = {
    inquiry: "Inquiry",
    qualified: "Qualified",
    site_visit: "Site Visit",
    offer_made: "Offer Made",
    reservation: "Reservation",
    spa_issued: "SPA Issued",
    closed: "Closed",
  };

  const stageProbabilities: Record<PipelineStage, number> = {
    inquiry: 10,
    qualified: 25,
    site_visit: 40,
    offer_made: 60,
    reservation: 75,
    spa_issued: 90,
    closed: 100,
  };

  const tabs = [
    { key: "profile" as const, label: "Profile" },
    { key: "performance" as const, label: "Performance" },
    { key: "commissions" as const, label: "Commissions" },
    { key: "forecast" as const, label: "Forecast" },
  ];

  // --- Populate edit form ---
  function populateEditForm(b: BrokerDetail) {
    editForm = {
      name: b.name,
      company: b.company,
      license_number: b.license_number,
      email: b.email,
      phone: b.phone,
      commission_rate: b.commission_rate ?? "",
      tier: b.tier != null ? String(b.tier) : "",
      status: b.status,
      notes: b.notes,
    };
  }

  // --- Load broker ---
  $effect(() => {
    void brokerId;
    loadBroker();
    loadTiers();
  });

  async function loadBroker() {
    loading = true;
    try {
      const res = await api.get<BrokerDetail>(`/crm/brokers/${brokerId}/`);
      broker = res;
      populateEditForm(res);
    } catch {
      broker = null;
    }
    loading = false;
  }

  async function loadTiers() {
    try {
      const res = await api.get<{ results: BrokerTier[] }>("/crm/tiers/");
      tiers = res.results;
    } catch {
      tiers = [];
    }
  }

  // --- Save broker ---
  async function saveBroker() {
    if (!broker) return;
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        name: editForm.name,
        company: editForm.company,
        license_number: editForm.license_number,
        email: editForm.email,
        phone: editForm.phone,
        commission_rate: editForm.commission_rate || null,
        tier: editForm.tier ? Number(editForm.tier) : null,
        status: editForm.status,
        notes: editForm.notes,
      };
      const res = await api.patch<BrokerDetail>(`/crm/brokers/${brokerId}/`, payload);
      broker = res;
      populateEditForm(res);
      editing = false;
      toast.success("Broker updated", "Changes have been saved");
    } catch (err) {
      if (err instanceof ApiError) {
        const msgs = Object.values(err.fieldErrors).flat();
        toast.error("Failed to save", msgs.join(". ") || "Please check the form and try again");
      } else {
        toast.error("Failed to save", "Please try again later");
      }
    }
    saving = false;
  }

  // --- Load performance ---
  $effect(() => {
    if (activeTab === "performance") {
      void perfMonths;
      loadPerformance();
    }
  });

  async function loadPerformance() {
    perfLoading = true;
    try {
      const params: Record<string, string> = {};
      if (perfMonths > 0) params.months = String(perfMonths);
      const res = await api.get<BrokerPerformance>(`/crm/brokers/${brokerId}/performance/`, params);
      performance = res;
    } catch {
      performance = null;
    }
    perfLoading = false;
  }

  // --- Load commissions ---
  $effect(() => {
    if (activeTab === "commissions") {
      loadEarnings();
    }
  });

  async function loadEarnings() {
    earningsLoading = true;
    try {
      const res = await api.get<{ results: CommissionEarning[] }>("/crm/commission-earnings/", { broker: brokerId });
      earnings = res.results;
    } catch {
      earnings = [];
    }
    earningsLoading = false;
  }

  // --- Load forecast ---
  $effect(() => {
    if (activeTab === "forecast") {
      loadForecast();
    }
  });

  async function loadForecast() {
    forecastLoading = true;
    try {
      const res = await api.get<BrokerForecast>(`/crm/brokers/${brokerId}/forecast/`);
      forecast = res;
    } catch {
      forecast = null;
    }
    forecastLoading = false;
  }

  // --- Approve earning ---
  async function approveEarning(earningId: number) {
    if (!confirm("Approve this commission earning?")) return;
    approvingId = earningId;
    try {
      await api.post(`/crm/commission-earnings/${earningId}/approve/`, {});
      toast.success("Earning approved", "Commission earning has been approved");
      await loadEarnings();
    } catch {
      toast.error("Approval failed", "Please try again later");
    }
    approvingId = null;
  }

  // --- Mark paid ---
  function openPaymentModal(earningId: number) {
    paymentEarningId = earningId;
    paymentRef = "";
    showPaymentModal = true;
  }

  async function confirmMarkPaid() {
    if (!paymentEarningId) return;
    markPaidId = paymentEarningId;
    try {
      await api.post(`/crm/commission-earnings/${paymentEarningId}/mark_paid/`, {
        payment_reference: paymentRef,
      });
      toast.success("Marked as paid", "Commission earning has been marked as paid");
      showPaymentModal = false;
      paymentEarningId = null;
      paymentRef = "";
      await loadEarnings();
    } catch {
      toast.error("Failed to mark paid", "Please try again later");
    }
    markPaidId = null;
  }

  function openLeadModal(leadId: number) {
    selectedLeadId = leadId;
    showLeadModal = true;
  }

  function closeLeadModal() {
    showLeadModal = false;
    selectedLeadId = null;
  }

  // --- Derived computations ---
  const earningsSummary = $derived(() => {
    let totalDeal = 0;
    let totalComm = 0;
    const byStatus: Record<string, number> = {};
    for (const e of earnings) {
      totalDeal += parseFloat(e.deal_value) || 0;
      totalComm += parseFloat(e.total_commission) || 0;
      const s = e.status;
      byStatus[s] = (byStatus[s] || 0) + (parseFloat(e.total_commission) || 0);
    }
    return { totalDeal, totalComm, byStatus };
  });

  const monthlyMax = $derived(() => {
    if (!performance?.monthly_deals?.length) return 0;
    return Math.max(...performance.monthly_deals.map((d) => d.count), 1);
  });

  const forecastRatio = $derived(() => {
    if (!forecast || !forecast.best_case_commission) return 0;
    return Math.min(forecast.weighted_forecast / forecast.best_case_commission, 1);
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !broker}
  <div class="py-24 text-center">
    <p class="text-neutral-400 text-sm">Broker not found</p>
    <a href="/crm/brokers" class="inline-block mt-3 text-sm font-medium text-neutral-900 hover:underline">Back to brokers</a>
  </div>
{:else}
  <div class="space-y-6">

    <!-- Header -->
    <div>
      {#if !embedded}
        <Breadcrumb items={[
          { label: "CRM", href: "/crm" },
          { label: "Brokers & Partners", href: "/crm/brokers" },
          { label: broker.name },
        ]} />
      {/if}

      <div class="mt-4 flex items-start justify-between">
        <div class="min-w-0">
          <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">{broker.name}</h1>
          {#if broker.company}
            <p class="text-sm text-neutral-400 mt-0.5">{broker.company}</p>
          {/if}
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <!-- Status badge -->
          <StatusBadge status={broker.status} size="md" />

          <!-- Tier badge -->
          {#if broker.tier_name}
            <span
              class="inline-flex items-center px-2.5 py-1 rounded text-xs font-medium"
              style="background-color: {broker.tier_color || '#e5e5e5'}; color: {broker.tier_color ? '#fff' : '#525252'};"
            >
              {broker.tier_name}
            </span>
          {/if}

          <!-- Edit Profile button -->
          <button
            onclick={() => {
              if (editing) {
                populateEditForm(broker!);
              }
              editing = !editing;
            }}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium transition-colors
                   {editing ? 'bg-neutral-900 text-white hover:bg-neutral-800 border-neutral-900' : 'text-neutral-600 hover:bg-neutral-50'}"
          >
            {editing ? "Cancel" : "Edit Profile"}
          </button>

          {#if editing}
            <button
              onclick={saveBroker}
              disabled={saving}
              class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {#if saving}
                <div class="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-1.5"></div>
              {/if}
              Save
            </button>
          {/if}
        </div>
      </div>
    </div>

    <!-- KPI Strip -->
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-4">
      <div class="bg-white rounded-xl border border-neutral-200 p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Leads</p>
        <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtNum(broker.lead_count)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Deals Closed</p>
        <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtNum(broker.deals_closed)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Conversion Rate</p>
        <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtPct(broker.conversion_rate)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Earned</p>
        <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{currency.format(broker.total_earnings)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Pending</p>
        <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{currency.format(broker.pending_earnings)}</p>
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-neutral-200">
      <nav class="flex gap-6">
        {#each tabs as tab}
          <button
            onclick={() => (activeTab = tab.key)}
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors
                   {activeTab === tab.key
                     ? 'border-neutral-900 text-neutral-900'
                     : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
          >
            {tab.label}
          </button>
        {/each}
      </nav>
    </div>

    <!-- ============================================ -->
    <!-- TAB: Profile                                  -->
    <!-- ============================================ -->
    {#if activeTab === "profile"}
      <div class="grid md:grid-cols-2 gap-6">

        <!-- Left: Contact / Identity -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Broker Details</h3>
          <div class="space-y-3 text-sm">
            {#if editing}
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Name</span>
                <input bind:value={editForm.name} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400" />
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Company</span>
                <input bind:value={editForm.company} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400" />
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">License Number</span>
                <input bind:value={editForm.license_number} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400" />
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Email</span>
                <input bind:value={editForm.email} type="email" class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400" />
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Phone</span>
                <input bind:value={editForm.phone} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400" />
              </label>
            {:else}
              <div class="flex justify-between"><span class="text-neutral-400">Name</span><span class="text-neutral-900">{broker.name}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Company</span><span class="text-neutral-900">{broker.company || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">License Number</span><span class="text-neutral-900">{broker.license_number || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Email</span><span class="text-neutral-900">{broker.email || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Phone</span><span class="text-neutral-900">{broker.phone || "\u2014"}</span></div>
              <div class="flex justify-between border-t border-neutral-100 pt-3"><span class="text-neutral-400">Joined</span><span class="text-neutral-900">{fmtDate(broker.created_at)}</span></div>
            {/if}
          </div>
        </div>

        <!-- Right: Commission / Settings -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Commission Settings</h3>
          <div class="space-y-3 text-sm">
            {#if editing}
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Commission Rate (%)</span>
                <input bind:value={editForm.commission_rate} type="number" step="0.01" min="0" max="100" class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm tabular-nums focus:outline-none focus:border-neutral-400" placeholder="e.g. 3.00" />
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Tier</span>
                <select bind:value={editForm.tier} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400">
                  <option value="">No tier assigned</option>
                  {#each tiers as t}
                    <option value={String(t.id)}>{t.name}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Status</span>
                <select bind:value={editForm.status} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400">
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                  <option value="suspended">Suspended</option>
                </select>
              </label>
              <label class="block">
                <span class="text-sm font-medium text-neutral-700">Notes</span>
                <textarea bind:value={editForm.notes} rows={4} class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400 resize-none" placeholder="Internal notes about this broker..."></textarea>
              </label>
            {:else}
              <div class="flex justify-between"><span class="text-neutral-400">Commission Rate</span><span class="text-neutral-900 tabular-nums">{broker.commission_rate ? broker.commission_rate + "%" : "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Tier</span><span class="text-neutral-900">{broker.tier_name || "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Multiplier</span><span class="text-neutral-900 tabular-nums">{broker.commission_multiplier ? broker.commission_multiplier + "x" : "\u2014"}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Status</span><span class="text-neutral-900 capitalize">{broker.status}</span></div>
              <div class="flex justify-between"><span class="text-neutral-400">Active Leads</span><span class="text-neutral-900 tabular-nums">{broker.active_leads}</span></div>
            {/if}
          </div>
        </div>

        <!-- Notes (view mode only, spans full width) -->
        {#if !editing && broker.notes}
          <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2 space-y-3">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Notes</h3>
            <p class="text-sm text-neutral-600 leading-relaxed whitespace-pre-line">{broker.notes}</p>
          </div>
        {/if}

        <!-- Tier Info Card -->
        {#if broker.tier_data}
          <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2 space-y-4">
            <div class="flex items-center gap-3">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Tier Details</h3>
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold"
                style="background-color: {broker.tier_data.color || '#e5e5e5'}; color: #fff;"
              >
                {broker.tier_data.name}
              </span>
            </div>
            <div class="grid sm:grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <p class="text-neutral-400 text-xs">Commission Multiplier</p>
                <p class="text-neutral-900 font-semibold tabular-nums mt-0.5">{broker.tier_data.commission_multiplier}x</p>
              </div>
              <div>
                <p class="text-neutral-400 text-xs">Bonus</p>
                <p class="text-neutral-900 font-semibold tabular-nums mt-0.5">{broker.tier_data.bonus_pct}%</p>
              </div>
              <div>
                <p class="text-neutral-400 text-xs">Min Deals Required</p>
                <p class="text-neutral-900 font-semibold tabular-nums mt-0.5">{broker.tier_data.min_deals}</p>
              </div>
              <div>
                <p class="text-neutral-400 text-xs">Min Revenue Required</p>
                <p class="text-neutral-900 font-semibold tabular-nums mt-0.5">{currency.format(broker.tier_data.min_revenue)}</p>
              </div>
            </div>
            {#if broker.tier_data.benefits}
              <div>
                <p class="text-neutral-400 text-xs mb-1">Benefits</p>
                <p class="text-sm text-neutral-700 leading-relaxed whitespace-pre-line">{broker.tier_data.benefits}</p>
              </div>
            {/if}
            <div class="text-xs text-neutral-400">
              Evaluation period: {broker.tier_data.evaluation_period_months} months
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- ============================================ -->
    <!-- TAB: Performance                              -->
    <!-- ============================================ -->
    {#if activeTab === "performance"}
      <!-- Period selector -->
      <div class="flex items-center gap-2">
        {#each [{ label: "3 months", value: 3 }, { label: "6 months", value: 6 }, { label: "12 months", value: 12 }, { label: "All time", value: 0 }] as period}
          <button
            onclick={() => (perfMonths = period.value)}
            class="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors
                   {perfMonths === period.value ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}"
          >
            {period.label}
          </button>
        {/each}
      </div>

      {#if perfLoading}
        <div class="flex items-center justify-center py-16">
          <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if !performance}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">Performance data unavailable</p>
        </div>
      {:else}
        <!-- Stats grid -->
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Leads</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtNum(performance.total_leads)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Won</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtNum(performance.won_leads)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Lost</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtNum(performance.lost_leads)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Active</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtNum(performance.active_leads)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Conversion Rate</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtPct(performance.conversion_rate)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Avg Days to Close</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{performance.avg_days_to_close != null ? performance.avg_days_to_close : "\u2014"}</p>
          </div>
        </div>

        <!-- Deal value and commission breakdown -->
        <div class="grid md:grid-cols-2 gap-4">
          <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-3">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Deal Value</h3>
            <p class="text-2xl font-bold text-neutral-900 tabular-nums">{currency.format(performance.total_deal_value)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-3">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Commission Breakdown</h3>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span class="text-neutral-400">Total Commission</span>
                <span class="text-neutral-900 font-semibold tabular-nums">{currency.format(performance.total_commission)}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-neutral-400">Paid</span>
                <span class="text-neutral-900 tabular-nums">{currency.format(performance.paid_commission)}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-neutral-400">Pending</span>
                <span class="text-neutral-900 tabular-nums">{currency.format(performance.pending_commission)}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Monthly deals chart -->
        {#if performance.monthly_deals && performance.monthly_deals.length > 0}
          <div class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-6">Monthly Deals</h3>
            <div class="flex items-end gap-2" style="height: 180px;">
              {#each performance.monthly_deals as month}
                {@const barHeight = monthlyMax() > 0 ? (month.count / monthlyMax()) * 100 : 0}
                <div class="flex-1 flex flex-col items-center justify-end h-full group">
                  <span class="text-xs font-medium text-neutral-900 tabular-nums mb-1 opacity-0 group-hover:opacity-100 transition-opacity">{month.count}</span>
                  <div
                    class="w-full bg-neutral-800 rounded-t hover:bg-neutral-600 transition-colors"
                    style="height: {Math.max(barHeight, 2)}%;"
                  ></div>
                  <span class="text-xs text-neutral-400 mt-2 truncate w-full text-center">{month.month}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      {/if}
    {/if}

    <!-- ============================================ -->
    <!-- TAB: Commissions                              -->
    <!-- ============================================ -->
    {#if activeTab === "commissions"}
      {#if earningsLoading}
        <div class="flex items-center justify-center py-16">
          <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if earnings.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">No commission earnings recorded for this broker.</p>
        </div>
      {:else}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-neutral-200">
                  <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Lead Name</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Project</th>
                  <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Deal Value</th>
                  <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Rate</th>
                  <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Total Commission</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Trigger</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Status</th>
                  <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Date</th>
                  <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                    {#each earnings as earning}
                      <tr class="hover:bg-neutral-50 transition-colors">
                        <td class="px-4 py-3 text-sm text-neutral-900 font-medium">
                          <button
                            type="button"
                            class="text-left hover:underline"
                            onclick={() => openLeadModal(earning.lead)}
                          >
                            {earning.lead_name}
                          </button>
                        </td>
                    <td class="px-4 py-3 text-sm text-neutral-600">{earning.project_name || "\u2014"}</td>
                    <td class="px-4 py-3 text-sm text-neutral-900 tabular-nums text-right">{currency.format(earning.deal_value)}</td>
                    <td class="px-4 py-3 text-sm text-neutral-600 tabular-nums text-right">{earning.commission_rate}%</td>
                    <td class="px-4 py-3 text-sm text-neutral-900 font-semibold tabular-nums text-right">{currency.format(earning.total_commission)}</td>
                    <td class="px-4 py-3 text-sm text-neutral-600">{earning.trigger_stage_display}</td>
                    <td class="px-4 py-3">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {earningStatusBadge[earning.status] || 'bg-neutral-100 text-neutral-600'}">
                        {earning.status_display}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-xs text-neutral-400">{fmtDate(earning.triggered_at)}</td>
                    <td class="px-4 py-3 text-right">
                      <div class="flex items-center justify-end gap-2">
                        {#if earning.status === "pending"}
                          <button
                            onclick={() => approveEarning(earning.id)}
                            disabled={approvingId === earning.id}
                            class="px-2.5 py-1 bg-neutral-900 text-white rounded text-xs font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                          >
                            {approvingId === earning.id ? "..." : "Approve"}
                          </button>
                        {/if}
                        {#if earning.status === "approved"}
                          <button
                            onclick={() => openPaymentModal(earning.id)}
                            class="px-2.5 py-1 border border-neutral-900 text-neutral-900 rounded text-xs font-medium hover:bg-neutral-900 hover:text-white transition-colors"
                          >
                            Mark Paid
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
              <tfoot>
                <tr class="border-t-2 border-neutral-200 bg-neutral-50">
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900" colspan={2}>
                    Summary ({earnings.length} earning{earnings.length !== 1 ? "s" : ""})
                  </td>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900 tabular-nums text-right">{currency.format(earningsSummary().totalDeal)}</td>
                  <td class="px-4 py-3"></td>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900 tabular-nums text-right">{currency.format(earningsSummary().totalComm)}</td>
                  <td class="px-4 py-3" colspan={4}>
                    <div class="flex items-center gap-3 text-xs">
                      {#each Object.entries(earningsSummary().byStatus) as [status, amount]}
                        <span class="text-neutral-500">
                          <span class="capitalize">{status}:</span>
                          <span class="font-medium text-neutral-700 tabular-nums">{currency.format(amount)}</span>
                        </span>
                      {/each}
                    </div>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      {/if}
    {/if}

    <!-- ============================================ -->
    <!-- TAB: Forecast                                 -->
    <!-- ============================================ -->
    {#if activeTab === "forecast"}
      {#if forecastLoading}
        <div class="flex items-center justify-center py-16">
          <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if !forecast}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">Forecast data unavailable</p>
        </div>
      {:else}
        <!-- Summary cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Active Pipeline</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{forecast.active_pipeline_count}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Pipeline Value</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{currency.format(forecast.total_pipeline_value)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Best Case Commission</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{currency.format(forecast.best_case_commission)}</p>
          </div>
          <div class="bg-white rounded-xl border border-neutral-200 p-4">
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Weighted Forecast</p>
            <p class="text-xl font-bold text-neutral-900 mt-1 tabular-nums">{currency.format(forecast.weighted_forecast)}</p>
          </div>
        </div>

        <!-- Confidence gauge -->
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Forecast Confidence</h3>
          <div class="flex items-center gap-6">
            <svg viewBox="0 0 120 70" class="w-40 h-24 shrink-0">
              <!-- Background arc -->
              <path d="M 10 60 A 50 50 0 0 1 110 60" fill="none" stroke="#e5e5e5" stroke-width="8" stroke-linecap="round" />
              <!-- Foreground arc -->
              {#if forecastRatio() > 0}
                <path
                  d="M 10 60 A 50 50 0 0 1 110 60"
                  fill="none"
                  stroke="#171717"
                  stroke-width="8"
                  stroke-linecap="round"
                  stroke-dasharray="{forecastRatio() * 157} 157"
                />
              {/if}
              <!-- Center text -->
              <text x="60" y="55" text-anchor="middle" class="text-sm font-bold" fill="#171717" font-size="16">
                {Math.round(forecastRatio() * 100)}%
              </text>
              <text x="60" y="68" text-anchor="middle" fill="#a3a3a3" font-size="8">
                weighted / best case
              </text>
            </svg>
            <div class="text-sm space-y-2">
              <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full bg-neutral-800 shrink-0"></span>
                <span class="text-neutral-600">Weighted Forecast: <span class="font-semibold text-neutral-900 tabular-nums">{currency.format(forecast.weighted_forecast)}</span></span>
              </div>
              <div class="flex items-center gap-3">
                <span class="w-3 h-3 rounded-full bg-neutral-200 shrink-0"></span>
                <span class="text-neutral-600">Best Case: <span class="font-semibold text-neutral-900 tabular-nums">{currency.format(forecast.best_case_commission)}</span></span>
              </div>
              <div class="text-xs text-neutral-400 mt-1">
                Rate: {forecast.commission_rate}% | Tier multiplier: {forecast.tier_multiplier}x
              </div>
            </div>
          </div>
        </div>

        <!-- Pipeline deals table -->
        {#if forecast.pipeline_deals.length === 0}
          <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
            <p class="text-neutral-400 text-sm">No active pipeline deals</p>
          </div>
        {:else}
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full">
                <thead>
                  <tr class="border-b border-neutral-200">
                    <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Lead Name</th>
                    <th class="text-left px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Pipeline Stage</th>
                    <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Deal Value</th>
                    <th class="text-center px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Probability</th>
                    <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Est. Commission</th>
                    <th class="text-right px-4 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Weighted</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each forecast.pipeline_deals as deal}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-4 py-3 text-sm text-neutral-900 font-medium">
                        <button
                          type="button"
                          class="text-left hover:underline"
                          onclick={() => openLeadModal(deal.lead_id)}
                        >
                          {deal.lead_name}
                        </button>
                      </td>
                      <td class="px-4 py-3">
                        <span class="text-xs font-medium text-neutral-600">{pipelineStageLabels[deal.pipeline_stage] || deal.pipeline_stage}</span>
                        <!-- Stage probability bar -->
                        <div class="mt-1 w-full h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                          <div
                            class="h-full bg-neutral-800 rounded-full transition-all"
                            style="width: {deal.probability}%;"
                          ></div>
                        </div>
                      </td>
                      <td class="px-4 py-3 text-sm text-neutral-900 tabular-nums text-right">{currency.format(deal.deal_value)}</td>
                      <td class="px-4 py-3 text-sm text-neutral-600 tabular-nums text-center">{deal.probability}%</td>
                      <td class="px-4 py-3 text-sm text-neutral-900 tabular-nums text-right">{currency.format(deal.estimated_commission)}</td>
                      <td class="px-4 py-3 text-sm text-neutral-900 font-semibold tabular-nums text-right">{currency.format(deal.weighted_commission)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          </div>
        {/if}
      {/if}
    {/if}
  </div>

  <LeadReadOnlyModal
    open={showLeadModal}
    leadId={selectedLeadId}
    onClose={closeLeadModal}
    backdropZ={embedded ? 1300 : 70}
    panelZ={embedded ? 1310 : 80}
  />

  <!-- ============================================ -->
  <!-- MODAL: Mark as Paid                           -->
  <!-- ============================================ -->
  {#if showPaymentModal}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="fixed inset-0 flex items-center justify-center bg-black/40"
      style={`z-index: ${embedded ? 1320 : 50};`}
      onkeydown={(e) => {
        if (e.key === "Escape") showPaymentModal = false;
      }}
    >
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <div class="absolute inset-0" onclick={() => (showPaymentModal = false)}></div>
      <div class="relative bg-white rounded-xl border border-neutral-200 shadow-xl w-full max-w-md p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-1">Mark as Paid</h2>
        <p class="text-sm text-neutral-500 mb-4">Enter a payment reference to confirm this commission has been paid.</p>
        <label class="block">
          <span class="text-sm font-medium text-neutral-700">Payment Reference</span>
          <input
            bind:value={paymentRef}
            class="mt-1 w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-neutral-400"
            placeholder="e.g. TXN-20240301-001"
          />
        </label>
        <div class="flex gap-3 justify-end mt-6">
          <button
            onclick={() => (showPaymentModal = false)}
            class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={confirmMarkPaid}
            disabled={markPaidId != null}
            class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {markPaidId != null ? "Processing..." : "Confirm Payment"}
          </button>
        </div>
      </div>
    </div>
  {/if}
{/if}

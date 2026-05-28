<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import BrokerDetailPage from "./[id]/+page.svelte";
  import type {
    BrokerListItem,
    BrokerTier,
    BrokerStatus,
    BrokerPerformanceOverview,
    CommissionStructure,
    CommissionType,
    CommissionTriggerStage,
    CommissionPaymentSplit,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";

  // ── Tab state ──
  type Tab = "brokers" | "commissions" | "tiers";
  let activeTab = $state<Tab>("brokers");

  // ── Brokers state ──
  let brokers = $state<BrokerListItem[]>([]);
  let brokersCount = $state(0);
  let brokersLoading = $state(true);
  let brokersError = $state<string | null>(null);
  let brokersPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let tierFilter = $state("");

  // ── Performance state ──
  let performance = $state<BrokerPerformanceOverview | null>(null);
  let perfLoading = $state(true);

  // ── Tiers state ──
  let tiers = $state<BrokerTier[]>([]);
  let tiersLoading = $state(true);

  // ── Commission Structures state ──
  let commissions = $state<CommissionStructure[]>([]);
  let commissionsLoading = $state(true);

  // ── Slide-over state ──
  let showBrokerPanel = $state(false);
  let showCommissionPanel = $state(false);
  let showTierPanel = $state(false);
  let showBrokerDetailModal = $state(false);
  let selectedBrokerId = $state<number | null>(null);
  let panelSaving = $state(false);

  // ── Broker form ──
  let brokerForm = $state<{
    name: string;
    company: string;
    license_number: string;
    email: string;
    phone: string;
    commission_rate: string;
    tier: string;
    status: BrokerStatus;
    notes: string;
  }>({
    name: "",
    company: "",
    license_number: "",
    email: "",
    phone: "",
    commission_rate: "",
    tier: "",
    status: "active",
    notes: "",
  });
  let brokerFormErrors = $state<Record<string, string[]>>({});

  // ── Commission form ──
  let commissionForm = $state<{
    name: string;
    description: string;
    commission_type: CommissionType;
    base_rate: string;
    fixed_amount: string;
    trigger_stage: CommissionTriggerStage;
    payment_split: CommissionPaymentSplit;
    broker: string;
    project: string;
    is_default: boolean;
    effective_from: string;
    effective_to: string;
  }>({
    name: "",
    description: "",
    commission_type: "percentage",
    base_rate: "",
    fixed_amount: "",
    trigger_stage: "closed",
    payment_split: "upfront",
    broker: "",
    project: "",
    is_default: false,
    effective_from: "",
    effective_to: "",
  });
  let commissionFormErrors = $state<Record<string, string[]>>({});

  // ── Tier form ──
  let tierForm = $state<{
    name: string;
    code: string;
    min_deals: string;
    min_revenue: string;
    commission_multiplier: string;
    bonus_pct: string;
    evaluation_period_months: string;
    benefits: string;
    color: string;
    sort_order: string;
  }>({
    name: "",
    code: "",
    min_deals: "0",
    min_revenue: "0",
    commission_multiplier: "1.00",
    bonus_pct: "0",
    evaluation_period_months: "12",
    benefits: "",
    color: "#6b7280",
    sort_order: "0",
  });
  let tierFormErrors = $state<Record<string, string[]>>({});

  // ── Dev fill ──
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  let devIdx = $state(0);

  function devFillBroker() {
    const samples = [
      { name: "Adebola Fashola", company: "Premier Realty Partners", license_number: "BRK-LAG-2024-0891", email: "adebola@premierrealty.ng", phone: "+234 801 444 5566", commission_rate: "3.5", notes: "Top performer Q4 2025. Specializes in Lekki corridor." },
      { name: "Chisom Eze", company: "Sapphire Properties", license_number: "BRK-ABJ-2024-1204", email: "chisom@sapphireprop.com", phone: "+234 802 333 7788", commission_rate: "2.5", notes: "Abuja-based. Strong corporate client network." },
    ];
    const s = samples[devIdx % samples.length]; devIdx++;
    brokerForm.name = s.name; brokerForm.company = s.company; brokerForm.license_number = s.license_number;
    brokerForm.email = s.email; brokerForm.phone = s.phone; brokerForm.commission_rate = s.commission_rate;
    brokerForm.notes = s.notes; brokerForm.status = "active";
  }

  function devFillCommission() {
    const samples: Array<{
      name: string;
      description: string;
      commission_type: CommissionType;
      base_rate: string;
      trigger_stage: CommissionTriggerStage;
      is_default: boolean;
    }> = [
      { name: "Standard Sales Commission", description: "Default commission for completed unit sales", commission_type: "percentage", base_rate: "3.0", trigger_stage: "closed", is_default: true },
      { name: "Premium Referral Bonus", description: "Enhanced rate for HNI client referrals", commission_type: "percentage", base_rate: "4.5", trigger_stage: "reservation", is_default: false },
    ];
    const s = samples[devIdx % samples.length]; devIdx++;
    commissionForm.name = s.name; commissionForm.description = s.description;
    commissionForm.commission_type = s.commission_type; commissionForm.base_rate = s.base_rate;
    commissionForm.trigger_stage = s.trigger_stage; commissionForm.is_default = s.is_default;
  }

  function devFillTier() {
    const samples = [
      { name: "Gold", code: "GOLD", min_deals: "10", min_revenue: "50000000", commission_multiplier: "1.25", bonus_pct: "5", evaluation_period_months: "6", benefits: "Priority lead assignment, quarterly bonus", color: "#F59E0B", sort_order: "2" },
      { name: "Platinum", code: "PLAT", min_deals: "25", min_revenue: "150000000", commission_multiplier: "1.5", bonus_pct: "10", evaluation_period_months: "12", benefits: "Exclusive listings, annual retreat, dedicated support", color: "#8B5CF6", sort_order: "3" },
    ];
    const s = samples[devIdx % samples.length]; devIdx++;
    tierForm.name = s.name; tierForm.code = s.code; tierForm.min_deals = s.min_deals;
    tierForm.min_revenue = s.min_revenue; tierForm.commission_multiplier = s.commission_multiplier;
    tierForm.bonus_pct = s.bonus_pct; tierForm.evaluation_period_months = s.evaluation_period_months;
    tierForm.benefits = s.benefits; tierForm.color = s.color; tierForm.sort_order = s.sort_order;
  }

  // ── Delete confirmation ──
  let deleteId = $state<number | null>(null);
  let deleteType = $state<"broker" | "commission" | "tier">("broker");
  let deleting = $state(false);

  // ── Pagination ──
  const PAGE_SIZE = 20;
  let totalPages = $derived(Math.max(1, Math.ceil(brokersCount / PAGE_SIZE)));

  // ── Data fetching ──
  async function fetchBrokers() {
    brokersLoading = true;
    brokersError = null;
    try {
      const params: Record<string, string> = { page: String(brokersPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (tierFilter) params.tier = tierFilter;
      const data = await api.get<{ results: BrokerListItem[]; count: number }>("/crm/brokers/", params);
      brokers = data.results;
      brokersCount = data.count;
    } catch (err) {
      console.error("[crm/brokers]", err);
      toast.error("Failed to load brokers");
      brokers = [];
      brokersCount = 0;
      brokersError = err instanceof Error ? err.message : "Could not load brokers.";
    }
    brokersLoading = false;
  }

  async function fetchPerformance() {
    perfLoading = true;
    try {
      performance = await api.get<BrokerPerformanceOverview>("/crm/brokers/performance/", { months: "12" });
    } catch (err) {
      console.error("[crm/brokers]", err);
      performance = null;
    }
    perfLoading = false;
  }

  async function fetchTiers() {
    tiersLoading = true;
    try {
      const data = await api.get<{ results: BrokerTier[] }>("/crm/tiers/");
      tiers = data.results;
    } catch (err) {
      console.error("[crm/brokers]", err);
      toast.error("Failed to load tiers");
      tiers = [];
    }
    tiersLoading = false;
  }

  async function fetchCommissions() {
    commissionsLoading = true;
    try {
      const data = await api.get<{ results: CommissionStructure[] }>("/crm/commission-structures/");
      commissions = data.results;
    } catch (err) {
      console.error("[crm/brokers]", err);
      toast.error("Failed to load commission structures");
      commissions = [];
    }
    commissionsLoading = false;
  }

  // Load tiers + performance on mount
  onMount(() => {
    void fetchTiers();
    void fetchPerformance();
  });

  // Fetch brokers on filter/page change
  $effect(() => {
    // Touch reactive deps
    searchQuery;
    statusFilter;
    tierFilter;
    brokersPage;
    fetchBrokers();
  });

  // Fetch commissions when tab switches
  $effect(() => {
    if (activeTab === "commissions") {
      fetchCommissions();
    }
  });

  $effect(() => {
    const openParam = $page.url.searchParams.get("open");
    if (!openParam) return;
    const id = Number(openParam);
    if (!Number.isInteger(id) || id <= 0) return;
    if (showBrokerDetailModal && selectedBrokerId === id) return;
    openBrokerDetail(id, false);
  });

  // ── Search debounce ──
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  function onSearchInput(e: Event) {
    const val = (e.target as HTMLInputElement).value;
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = val;
      brokersPage = 1;
    }, 300);
  }

  function openBrokerDetail(brokerId: number, syncUrl = true) {
    selectedBrokerId = brokerId;
    showBrokerDetailModal = true;
    if (!syncUrl) return;
    const params = new URLSearchParams($page.url.searchParams);
    params.set("open", String(brokerId));
    goto(`/crm/brokers?${params.toString()}`, {
      replaceState: true,
      noScroll: true,
      keepFocus: true,
    });
  }

  function closeBrokerDetail() {
    showBrokerDetailModal = false;
    selectedBrokerId = null;
    void Promise.all([fetchBrokers(), fetchPerformance()]);
    if (!$page.url.searchParams.has("open")) return;
    const params = new URLSearchParams($page.url.searchParams);
    params.delete("open");
    const query = params.toString();
    goto(query ? `/crm/brokers?${query}` : "/crm/brokers", {
      replaceState: true,
      noScroll: true,
      keepFocus: true,
    });
  }

  // ── CRUD: Broker ──
  function openNewBroker() {
    brokerForm = {
      name: "",
      company: "",
      license_number: "",
      email: "",
      phone: "",
      commission_rate: "",
      tier: "",
      status: "active",
      notes: "",
    };
    brokerFormErrors = {};
    showBrokerPanel = true;
  }

  async function saveBroker() {
    panelSaving = true;
    brokerFormErrors = {};
    try {
      const payload: Record<string, unknown> = {
        name: brokerForm.name,
        company: brokerForm.company,
        license_number: brokerForm.license_number,
        email: brokerForm.email,
        phone: brokerForm.phone,
        commission_rate: brokerForm.commission_rate || null,
        tier: brokerForm.tier ? Number(brokerForm.tier) : null,
        status: brokerForm.status,
        notes: brokerForm.notes,
      };
      await api.post("/crm/brokers/", payload);
      toast.success("Broker created successfully");
      showBrokerPanel = false;
      fetchBrokers();
      fetchPerformance();
    } catch (err) {
      console.error("[crm/brokers]", err);
      if (err instanceof ApiError && err.fieldErrors) {
        brokerFormErrors = err.fieldErrors;
      }
      toast.error("Failed to create broker");
    }
    panelSaving = false;
  }

  // ── CRUD: Commission Structure ──
  function openNewCommission() {
    commissionForm = {
      name: "",
      description: "",
      commission_type: "percentage",
      base_rate: "",
      fixed_amount: "",
      trigger_stage: "closed",
      payment_split: "upfront",
      broker: "",
      project: "",
      is_default: false,
      effective_from: "",
      effective_to: "",
    };
    commissionFormErrors = {};
    showCommissionPanel = true;
  }

  async function saveCommission() {
    panelSaving = true;
    commissionFormErrors = {};
    try {
      const payload: Record<string, unknown> = {
        name: commissionForm.name,
        description: commissionForm.description,
        commission_type: commissionForm.commission_type,
        base_rate: commissionForm.base_rate || "0",
        fixed_amount: commissionForm.fixed_amount || null,
        trigger_stage: commissionForm.trigger_stage,
        payment_split: commissionForm.payment_split,
        broker: commissionForm.broker ? Number(commissionForm.broker) : null,
        project: commissionForm.project ? Number(commissionForm.project) : null,
        is_default: commissionForm.is_default,
        effective_from: commissionForm.effective_from || null,
        effective_to: commissionForm.effective_to || null,
      };
      await api.post("/crm/commission-structures/", payload);
      toast.success("Commission structure created");
      showCommissionPanel = false;
      fetchCommissions();
    } catch (err) {
      console.error("[crm/brokers]", err);
      if (err instanceof ApiError && err.fieldErrors) {
        commissionFormErrors = err.fieldErrors;
      }
      toast.error("Failed to create commission structure");
    }
    panelSaving = false;
  }

  // ── CRUD: Tier ──
  function openNewTier() {
    tierForm = {
      name: "",
      code: "",
      min_deals: "0",
      min_revenue: "0",
      commission_multiplier: "1.00",
      bonus_pct: "0",
      evaluation_period_months: "12",
      benefits: "",
      color: "#6b7280",
      sort_order: "0",
    };
    tierFormErrors = {};
    showTierPanel = true;
  }

  async function saveTier() {
    panelSaving = true;
    tierFormErrors = {};
    try {
      const payload: Record<string, unknown> = {
        name: tierForm.name,
        code: tierForm.code,
        min_deals: Number(tierForm.min_deals),
        min_revenue: tierForm.min_revenue,
        commission_multiplier: tierForm.commission_multiplier,
        bonus_pct: tierForm.bonus_pct,
        evaluation_period_months: Number(tierForm.evaluation_period_months),
        benefits: tierForm.benefits,
        color: tierForm.color,
        sort_order: Number(tierForm.sort_order),
      };
      await api.post("/crm/tiers/", payload);
      toast.success("Tier created successfully");
      showTierPanel = false;
      fetchTiers();
    } catch (err) {
      console.error("[crm/brokers]", err);
      if (err instanceof ApiError && err.fieldErrors) {
        tierFormErrors = err.fieldErrors;
      }
      toast.error("Failed to create tier");
    }
    panelSaving = false;
  }

  // ── Delete ──
  function confirmDelete(id: number, type: "broker" | "commission" | "tier") {
    deleteId = id;
    deleteType = type;
  }

  async function executeDelete() {
    if (deleteId === null) return;
    deleting = true;
    try {
      const endpoints: Record<string, string> = {
        broker: `/crm/brokers/${deleteId}/`,
        commission: `/crm/commission-structures/${deleteId}/`,
        tier: `/crm/tiers/${deleteId}/`,
      };
      await api.delete(endpoints[deleteType]);
      toast.success(`${deleteType.charAt(0).toUpperCase() + deleteType.slice(1)} deleted`);
      deleteId = null;
      if (deleteType === "broker") {
        fetchBrokers();
        fetchPerformance();
      } else if (deleteType === "commission") {
        fetchCommissions();
      } else {
        fetchTiers();
      }
    } catch (err) {
      console.error("[crm/brokers]", err);
      toast.error(`Failed to delete ${deleteType}`);
    }
    deleting = false;
  }

  // ── Helpers ──
  const statusClasses: Record<BrokerStatus, string> = {
    active: "bg-neutral-900 text-white",
    inactive: "bg-neutral-200 text-neutral-600",
    suspended: "bg-neutral-100 text-neutral-500",
  };

  const statusLabels: Record<BrokerStatus, string> = {
    active: "Active",
    inactive: "Inactive",
    suspended: "Suspended",
  };

  function fmtDate(dateStr: string): string {
    if (!dateStr) return "--";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fmtPct(val: string | number | null): string {
    if (val === null || val === undefined) return "--";
    const n = typeof val === "string" ? parseFloat(val) : val;
    if (isNaN(n)) return "--";
    return `${n}%`;
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <div class="flex items-center justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">CRM</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Brokers & Channel Partners</h1>
        <p class="text-sm text-neutral-400 mt-1">Manage broker relationships, commissions, and tier structures</p>
      </div>
      {#if activeTab === "brokers"}
        <button onclick={openNewBroker} class="bg-neutral-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-800 transition-colors">
          + New Broker
        </button>
      {:else if activeTab === "commissions"}
        <button onclick={openNewCommission} class="bg-neutral-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-800 transition-colors">
          + New Structure
        </button>
      {:else if activeTab === "tiers"}
        <button onclick={openNewTier} class="bg-neutral-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-800 transition-colors">
          + New Tier
        </button>
      {/if}
    </div>
  </div>

  <!-- Tabs -->
  <div class="border-b border-neutral-200">
    <nav class="flex gap-0 -mb-px">
      <button
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab === 'brokers' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
        onclick={() => (activeTab = "brokers")}
      >
        Brokers
      </button>
      <button
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab === 'commissions' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
        onclick={() => (activeTab = "commissions")}
      >
        Commission Structures
      </button>
      <button
        class="px-4 py-2 text-sm font-medium border-b-2 transition-colors {activeTab === 'tiers' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
        onclick={() => (activeTab = "tiers")}
      >
        Tiers
      </button>
    </nav>
  </div>

  <!-- ═══════════════════════════════════════ TAB 1: BROKERS ═══════════════════════════════════════ -->
  {#if activeTab === "brokers"}
    <!-- KPI Strip -->
    {#if perfLoading}
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {#each Array(4) as _}
          <div class="rounded-xl border border-violet-200 bg-violet-50 p-5 animate-pulse">
            <div class="h-3 w-24 rounded bg-violet-200"></div>
            <div class="mt-3 h-7 w-16 rounded bg-violet-200"></div>
          </div>
        {/each}
      </div>
    {:else if performance}
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="rounded-xl border border-violet-200 bg-violet-50 p-5">
          <p class="text-xs font-medium uppercase tracking-wider text-violet-700">Total Active Brokers</p>
          <p class="mt-2 text-2xl font-bold tabular-nums text-violet-950">{performance.total_active_brokers}</p>
        </div>
        <div class="rounded-xl border border-violet-200 bg-violet-50 p-5">
          <p class="text-xs font-medium uppercase tracking-wider text-violet-700">Deals Closed</p>
          <p class="mt-2 text-2xl font-bold tabular-nums text-violet-950">{performance.won_broker_leads}</p>
        </div>
        <div class="rounded-xl border border-violet-200 bg-violet-50 p-5">
          <p class="text-xs font-medium uppercase tracking-wider text-violet-700">Total Commission</p>
          <p class="mt-2 text-2xl font-bold tabular-nums text-violet-950">{currency.format(performance.total_commission)}</p>
        </div>
        <div class="rounded-xl border border-violet-200 bg-violet-50 p-5">
          <p class="text-xs font-medium uppercase tracking-wider text-violet-700">Conversion Rate</p>
          <p class="mt-2 text-2xl font-bold tabular-nums text-violet-950">{performance.conversion_rate.toFixed(1)}%</p>
        </div>
      </div>
    {/if}

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-3">
      <div class="flex-1 min-w-[200px] max-w-sm">
        <input
          type="text"
          placeholder="Search brokers..."
          oninput={onSearchInput}
          class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300 transition-colors"
        />
      </div>
      <select
        bind:value={statusFilter}
        onchange={() => (brokersPage = 1)}
        class="bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-1 focus:ring-neutral-300"
      >
        <option value="">All Statuses</option>
        <option value="active">Active</option>
        <option value="inactive">Inactive</option>
        <option value="suspended">Suspended</option>
      </select>
      <select
        bind:value={tierFilter}
        onchange={() => (brokersPage = 1)}
        class="bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-1 focus:ring-neutral-300"
      >
        <option value="">All Tiers</option>
        {#each tiers as t}
          <option value={String(t.id)}>{t.name}</option>
        {/each}
      </select>
    </div>

    <!-- Brokers Table -->
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if brokersLoading}
        <div class="flex items-center justify-center py-16">
          <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if brokersError}
        <div class="p-6">
          <DataStateBanner
            title="Couldn't load brokers"
            message={brokersError}
            onretry={fetchBrokers}
          />
        </div>
      {:else if brokers.length === 0}
        <div class="py-16 text-center">
          <svg class="mx-auto w-10 h-10 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
          </svg>
          <p class="mt-3 text-sm text-neutral-500">No brokers found</p>
          <button onclick={openNewBroker} class="mt-3 text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
            + Add your first broker
          </button>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider">Name</th>
                <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider">Company</th>
                <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider">License #</th>
                <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider">Tier</th>
                <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-400 uppercase tracking-wider">Comm. Rate</th>
                <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-400 uppercase tracking-wider">Deals</th>
                <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-400 uppercase tracking-wider">Total Earned</th>
                <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-3 text-right text-xs font-semibold text-neutral-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {#each brokers as broker}
                <tr class="border-t border-neutral-100 hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-3">
                    <p class="text-sm font-medium text-neutral-900">{broker.name}</p>
                    <p class="text-xs text-neutral-400">{broker.email}</p>
                  </td>
                  <td class="px-5 py-3 text-sm text-neutral-600">{broker.company || "--"}</td>
                  <td class="px-5 py-3 text-sm text-neutral-600 font-mono wrap-break-word">{broker.license_number || "--"}</td>
                  <td class="px-5 py-3">
                    {#if broker.tier_name}
                      <span
                        class="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-full bg-neutral-100 text-neutral-700"
                      >
                        {#if broker.tier_color}
                          <span class="w-2 h-2 rounded-full shrink-0" style="background-color: {broker.tier_color}"></span>
                        {/if}
                        {broker.tier_name}
                      </span>
                    {:else}
                      <span class="text-xs text-neutral-300">--</span>
                    {/if}
                  </td>
                  <td class="px-5 py-3 text-sm text-neutral-600 text-right tabular-nums">
                    {broker.commission_rate ? `${broker.commission_rate}%` : "--"}
                  </td>
                  <td class="px-5 py-3 text-sm text-neutral-600 text-right tabular-nums">{broker.deals_closed}</td>
                  <td class="px-5 py-3 text-sm text-neutral-600 text-right tabular-nums">
                    {currency.format(broker.total_earnings)}
                  </td>
                  <td class="px-5 py-3">
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full {statusClasses[broker.status]}">
                      {statusLabels[broker.status]}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-right">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        onclick={() => openBrokerDetail(broker.id)}
                        class="text-xs font-medium text-neutral-500 hover:text-neutral-900 transition-colors"
                      >
                        View
                      </button>
                      <button
                        onclick={() => confirmDelete(broker.id, "broker")}
                        class="text-xs font-medium text-neutral-400 hover:text-neutral-700 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        {#if totalPages > 1}
          <div class="px-5 py-3 border-t border-neutral-100 flex items-center justify-between">
            <p class="text-xs text-neutral-400">
              Showing {(brokersPage - 1) * PAGE_SIZE + 1}--{Math.min(brokersPage * PAGE_SIZE, brokersCount)} of {brokersCount}
            </p>
            <div class="flex items-center gap-1">
              <button
                disabled={brokersPage <= 1}
                onclick={() => (brokersPage = brokersPage - 1)}
                class="px-3 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-700 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              {#each Array(totalPages) as _, i}
                {#if totalPages <= 7 || i === 0 || i === totalPages - 1 || (i >= brokersPage - 2 && i <= brokersPage)}
                  <button
                    onclick={() => (brokersPage = i + 1)}
                    class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors {brokersPage === i + 1 ? 'bg-neutral-900 text-white' : 'border border-neutral-200 text-neutral-700 hover:bg-neutral-50'}"
                  >
                    {i + 1}
                  </button>
                {:else if i === 1 || i === totalPages - 2}
                  <span class="px-1 text-neutral-300 text-xs">...</span>
                {/if}
              {/each}
              <button
                disabled={brokersPage >= totalPages}
                onclick={() => (brokersPage = brokersPage + 1)}
                class="px-3 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-700 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        {/if}
      {/if}
    </div>

  <!-- ═══════════════════════════════════ TAB 2: COMMISSION STRUCTURES ═══════════════════════════════════ -->
  {:else if activeTab === "commissions"}
    {#if commissionsLoading}
      <div class="flex items-center justify-center py-16">
        <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if commissions.length === 0}
      <div class="py-16 text-center">
        <svg class="mx-auto w-10 h-10 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
        </svg>
        <p class="mt-3 text-sm text-neutral-500">No commission structures defined</p>
        <button onclick={openNewCommission} class="mt-3 text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
          + Create your first structure
        </button>
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {#each commissions as cs}
          <div class="bg-white rounded-xl border border-neutral-200 p-6 hover:border-neutral-300 transition-colors group">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-sm font-semibold text-neutral-900">{cs.name}</h3>
                {#if cs.description}
                  <p class="mt-1 text-xs text-neutral-400 line-clamp-2">{cs.description}</p>
                {/if}
              </div>
              <button
                onclick={() => confirmDelete(cs.id, "commission")}
                aria-label="Delete commission structure"
                class="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-neutral-700 transition-all"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                </svg>
              </button>
            </div>
            <div class="mt-4 space-y-2">
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-400">Type</span>
                <span class="text-xs font-medium text-neutral-700">{cs.commission_type_display}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-400">Rate / Amount</span>
                <span class="text-xs font-medium text-neutral-700 tabular-nums">
                  {#if cs.commission_type === "fixed"}
                    {currency.format(cs.fixed_amount ?? 0)}
                  {:else}
                    {cs.base_rate}%
                  {/if}
                </span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-400">Trigger</span>
                <span class="text-xs font-medium text-neutral-700">{cs.trigger_stage_display}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-400">Payment Split</span>
                <span class="text-xs font-medium text-neutral-700">{cs.payment_split_display}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-xs text-neutral-400">Scope</span>
                <span class="text-xs font-medium text-neutral-700">
                  {#if cs.is_default}
                    Default
                  {:else if cs.broker_name}
                    {cs.broker_name}
                  {:else if cs.project_name}
                    {cs.project_name}
                  {:else}
                    --
                  {/if}
                </span>
              </div>
            </div>
            {#if cs.effective_from || cs.effective_to}
              <div class="mt-3 pt-3 border-t border-neutral-100 text-xs text-neutral-400">
                {#if cs.effective_from}From {fmtDate(cs.effective_from)}{/if}
                {#if cs.effective_from && cs.effective_to} &mdash; {/if}
                {#if cs.effective_to}Until {fmtDate(cs.effective_to)}{/if}
              </div>
            {/if}
            <div class="mt-3 pt-3 border-t border-neutral-100 flex items-center justify-between">
              <span class="text-xs text-neutral-400">{cs.earning_count} earning{cs.earning_count !== 1 ? "s" : ""}</span>
              <span class="px-2 py-0.5 text-xs font-medium rounded-full {cs.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-600'}">
                {cs.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          </div>
        {/each}
      </div>
    {/if}

  <!-- ═══════════════════════════════════════ TAB 3: TIERS ═══════════════════════════════════════ -->
  {:else if activeTab === "tiers"}
    {#if tiersLoading}
      <div class="flex items-center justify-center py-16">
        <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if tiers.length === 0}
      <div class="py-16 text-center">
        <svg class="mx-auto w-10 h-10 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 7.5 7.5 3m0 0L12 7.5M7.5 3v13.5m13.5-6L16.5 16.5m0 0L12 10.5m4.5 6V3" />
        </svg>
        <p class="mt-3 text-sm text-neutral-500">No tiers configured</p>
        <button onclick={openNewTier} class="mt-3 text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
          + Create your first tier
        </button>
      </div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {#each tiers as tier}
          <div
            class="bg-white rounded-xl border border-neutral-200 overflow-hidden hover:border-neutral-300 transition-colors group"
          >
            <div class="flex">
              <!-- Colored left border -->
              <div class="w-1.5 shrink-0" style="background-color: {tier.color || '#6b7280'}"></div>
              <div class="flex-1 p-6">
                <div class="flex items-start justify-between">
                  <div>
                    <h3 class="text-sm font-semibold text-neutral-900">{tier.name}</h3>
                    <p class="text-xs text-neutral-400 font-mono">{tier.code}</p>
                  </div>
                  <button
                    onclick={() => confirmDelete(tier.id, "tier")}
                    aria-label="Delete tier"
                    class="opacity-0 group-hover:opacity-100 text-neutral-400 hover:text-neutral-700 transition-all"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" aria-hidden="true">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                    </svg>
                  </button>
                </div>
                <div class="mt-4 space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-neutral-400">Min Deals</span>
                    <span class="text-xs font-medium text-neutral-700 tabular-nums">{tier.min_deals}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-neutral-400">Min Revenue</span>
                    <span class="text-xs font-medium text-neutral-700 tabular-nums">{currency.format(tier.min_revenue)}</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-neutral-400">Commission Multiplier</span>
                    <span class="text-xs font-medium text-neutral-700 tabular-nums">{tier.commission_multiplier}x</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-neutral-400">Bonus</span>
                    <span class="text-xs font-medium text-neutral-700 tabular-nums">{tier.bonus_pct}%</span>
                  </div>
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-neutral-400">Eval Period</span>
                    <span class="text-xs font-medium text-neutral-700">{tier.evaluation_period_months} months</span>
                  </div>
                </div>
                <div class="mt-4 pt-3 border-t border-neutral-100 flex items-center justify-between">
                  <span class="text-xs text-neutral-400">{tier.broker_count} broker{tier.broker_count !== 1 ? "s" : ""}</span>
                  <span class="px-2 py-0.5 text-xs font-medium rounded-full {tier.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-600'}">
                    {tier.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

{#if showBrokerDetailModal && selectedBrokerId !== null}
  <button
    type="button"
    class="fixed inset-0 z-70 bg-black/50 backdrop-blur-sm"
    onclick={closeBrokerDetail}
    aria-label="Close broker details"
  ></button>

  <div class="fixed inset-0 z-80 flex items-center justify-center p-4 sm:p-6">
    <div class="h-[92vh] w-full max-w-7xl overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl">
      <div class="flex h-full flex-col">
        <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-500">Broker Detail</h2>
          <button
            type="button"
            class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
            onclick={closeBrokerDetail}
          >
            Close
          </button>
        </div>
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <BrokerDetailPage brokerId={selectedBrokerId} embedded={true} />
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- ════════════════════════════════════════ SLIDE-OVER: NEW BROKER ════════════════════════════════════════ -->
{#if showBrokerPanel}
  <div class="fixed inset-0 z-50 flex justify-end">
    <!-- Backdrop -->
    <button class="absolute inset-0 bg-neutral-900/30" onclick={() => (showBrokerPanel = false)} aria-label="Close panel"></button>
    <!-- Panel -->
    <div class="relative max-w-lg w-full bg-white shadow-xl flex flex-col h-full">
      <div class="px-6 py-5 border-b border-neutral-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-neutral-900">New Broker</h2>
        <button onclick={() => (showBrokerPanel = false)} aria-label="Close panel" class="text-neutral-400 hover:text-neutral-700 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto p-6 space-y-5">
        <!-- Name -->
        <div>
          <label for="broker-name" class="block text-xs font-medium text-neutral-700 mb-1">Name <span class="text-neutral-400">*</span></label>
          <input id="broker-name" type="text" bind:value={brokerForm.name} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="Full name" />
          {#if brokerFormErrors.name}
            <p class="mt-1 text-xs text-neutral-500">{brokerFormErrors.name[0]}</p>
          {/if}
        </div>
        <!-- Company -->
        <div>
          <label for="broker-company" class="block text-xs font-medium text-neutral-700 mb-1">Company</label>
          <input id="broker-company" type="text" bind:value={brokerForm.company} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="Company name" />
          {#if brokerFormErrors.company}
            <p class="mt-1 text-xs text-neutral-500">{brokerFormErrors.company[0]}</p>
          {/if}
        </div>
        <!-- License Number -->
        <div>
          <label for="broker-license" class="block text-xs font-medium text-neutral-700 mb-1">License Number</label>
          <input id="broker-license" type="text" bind:value={brokerForm.license_number} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="e.g. BRN-00123" />
          {#if brokerFormErrors.license_number}
            <p class="mt-1 text-xs text-neutral-500">{brokerFormErrors.license_number[0]}</p>
          {/if}
        </div>
        <!-- Email -->
        <div>
          <label for="broker-email" class="block text-xs font-medium text-neutral-700 mb-1">Email</label>
          <input id="broker-email" type="email" bind:value={brokerForm.email} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="broker@example.com" />
          {#if brokerFormErrors.email}
            <p class="mt-1 text-xs text-neutral-500">{brokerFormErrors.email[0]}</p>
          {/if}
        </div>
        <!-- Phone -->
        <div>
          <label for="broker-phone" class="block text-xs font-medium text-neutral-700 mb-1">Phone</label>
          <input id="broker-phone" type="text" bind:value={brokerForm.phone} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="+1 234 567 8900" />
          {#if brokerFormErrors.phone}
            <p class="mt-1 text-xs text-neutral-500">{brokerFormErrors.phone[0]}</p>
          {/if}
        </div>
        <!-- Commission Rate -->
        <div>
          <label for="broker-rate" class="block text-xs font-medium text-neutral-700 mb-1">Commission Rate (%)</label>
          <input id="broker-rate" type="text" bind:value={brokerForm.commission_rate} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="e.g. 5.00" />
          {#if brokerFormErrors.commission_rate}
            <p class="mt-1 text-xs text-neutral-500">{brokerFormErrors.commission_rate[0]}</p>
          {/if}
        </div>
        <!-- Tier -->
        <div>
          <label for="broker-tier" class="block text-xs font-medium text-neutral-700 mb-1">Tier</label>
          <select id="broker-tier" bind:value={brokerForm.tier} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300">
            <option value="">No tier</option>
            {#each tiers as t}
              <option value={String(t.id)}>{t.name}</option>
            {/each}
          </select>
        </div>
        <!-- Status -->
        <div>
          <label for="broker-status" class="block text-xs font-medium text-neutral-700 mb-1">Status</label>
          <select id="broker-status" bind:value={brokerForm.status} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300">
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
        <!-- Notes -->
        <div>
          <label for="broker-notes" class="block text-xs font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="broker-notes" bind:value={brokerForm.notes} rows="3" class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300 resize-none" placeholder="Additional notes..."></textarea>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillBroker} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>{/if}
        <button onclick={() => (showBrokerPanel = false)} class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors">
          Cancel
        </button>
        <button onclick={saveBroker} disabled={panelSaving} class="px-4 py-2 text-sm font-medium bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {panelSaving ? "Saving..." : "Create Broker"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ════════════════════════════════════ SLIDE-OVER: NEW COMMISSION ════════════════════════════════════ -->
{#if showCommissionPanel}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-neutral-900/30" onclick={() => (showCommissionPanel = false)} aria-label="Close panel"></button>
    <div class="relative max-w-lg w-full bg-white shadow-xl flex flex-col h-full">
      <div class="px-6 py-5 border-b border-neutral-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-neutral-900">New Commission Structure</h2>
        <button onclick={() => (showCommissionPanel = false)} aria-label="Close panel" class="text-neutral-400 hover:text-neutral-700 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto p-6 space-y-5">
        <!-- Name -->
        <div>
          <label for="cs-name" class="block text-xs font-medium text-neutral-700 mb-1">Name <span class="text-neutral-400">*</span></label>
          <input id="cs-name" type="text" bind:value={commissionForm.name} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="Structure name" />
          {#if commissionFormErrors.name}
            <p class="mt-1 text-xs text-neutral-500">{commissionFormErrors.name[0]}</p>
          {/if}
        </div>
        <!-- Description -->
        <div>
          <label for="cs-desc" class="block text-xs font-medium text-neutral-700 mb-1">Description</label>
          <textarea id="cs-desc" bind:value={commissionForm.description} rows="2" class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300 resize-none" placeholder="Description..."></textarea>
        </div>
        <!-- Commission Type -->
        <div>
          <label for="cs-type" class="block text-xs font-medium text-neutral-700 mb-1">Commission Type</label>
          <select id="cs-type" bind:value={commissionForm.commission_type} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300">
            <option value="percentage">Percentage</option>
            <option value="fixed">Fixed</option>
            <option value="tiered">Tiered</option>
          </select>
        </div>
        <!-- Base Rate -->
        {#if commissionForm.commission_type !== "fixed"}
          <div>
            <label for="cs-rate" class="block text-xs font-medium text-neutral-700 mb-1">Base Rate (%)</label>
            <input id="cs-rate" type="text" bind:value={commissionForm.base_rate} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="e.g. 3.50" />
            {#if commissionFormErrors.base_rate}
              <p class="mt-1 text-xs text-neutral-500">{commissionFormErrors.base_rate[0]}</p>
            {/if}
          </div>
        {/if}
        <!-- Fixed Amount -->
        {#if commissionForm.commission_type === "fixed"}
          <div>
            <label for="cs-fixed" class="block text-xs font-medium text-neutral-700 mb-1">Fixed Amount</label>
            <input id="cs-fixed" type="text" bind:value={commissionForm.fixed_amount} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="e.g. 5000.00" />
            {#if commissionFormErrors.fixed_amount}
              <p class="mt-1 text-xs text-neutral-500">{commissionFormErrors.fixed_amount[0]}</p>
            {/if}
          </div>
        {/if}
        <!-- Trigger Stage -->
        <div>
          <label for="cs-trigger" class="block text-xs font-medium text-neutral-700 mb-1">Trigger Stage</label>
          <select id="cs-trigger" bind:value={commissionForm.trigger_stage} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300">
            <option value="reservation">Reservation</option>
            <option value="spa_issued">SPA Issued</option>
            <option value="closed">Closed</option>
            <option value="milestone">Milestone</option>
          </select>
        </div>
        <!-- Payment Split -->
        <div>
          <label for="cs-split" class="block text-xs font-medium text-neutral-700 mb-1">Payment Split</label>
          <select id="cs-split" bind:value={commissionForm.payment_split} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300">
            <option value="upfront">Upfront</option>
            <option value="split_50_50">50/50 Split</option>
            <option value="split_30_70">30/70 Split</option>
            <option value="milestone">Milestone-based</option>
          </select>
        </div>
        <!-- Broker (optional scope) -->
        <div>
          <label for="cs-broker" class="block text-xs font-medium text-neutral-700 mb-1">Broker (optional)</label>
          <select id="cs-broker" bind:value={commissionForm.broker} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300">
            <option value="">None</option>
            {#each brokers as b}
              <option value={String(b.id)}>{b.name}</option>
            {/each}
          </select>
        </div>
        <!-- Is Default -->
        <div class="flex items-center gap-2">
          <input id="cs-default" type="checkbox" bind:checked={commissionForm.is_default} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-300" />
          <label for="cs-default" class="text-xs font-medium text-neutral-700">Set as default structure</label>
        </div>
        <!-- Effective From/To -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="cs-from" class="block text-xs font-medium text-neutral-700 mb-1">Effective From</label>
            <DateInput id="cs-from" bind:value={commissionForm.effective_from} />
          </div>
          <div>
            <label for="cs-to" class="block text-xs font-medium text-neutral-700 mb-1">Effective To</label>
            <DateInput id="cs-to" bind:value={commissionForm.effective_to} />
          </div>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillCommission} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>{/if}
        <button onclick={() => (showCommissionPanel = false)} class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors">
          Cancel
        </button>
        <button onclick={saveCommission} disabled={panelSaving} class="px-4 py-2 text-sm font-medium bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {panelSaving ? "Saving..." : "Create Structure"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ══════════════════════════════════════ SLIDE-OVER: NEW TIER ══════════════════════════════════════ -->
{#if showTierPanel}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-neutral-900/30" onclick={() => (showTierPanel = false)} aria-label="Close panel"></button>
    <div class="relative max-w-lg w-full bg-white shadow-xl flex flex-col h-full">
      <div class="px-6 py-5 border-b border-neutral-200 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-neutral-900">New Tier</h2>
        <button onclick={() => (showTierPanel = false)} aria-label="Close panel" class="text-neutral-400 hover:text-neutral-700 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto p-6 space-y-5">
        <!-- Name -->
        <div>
          <label for="tier-name" class="block text-xs font-medium text-neutral-700 mb-1">Name <span class="text-neutral-400">*</span></label>
          <input id="tier-name" type="text" bind:value={tierForm.name} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="e.g. Gold" />
          {#if tierFormErrors.name}
            <p class="mt-1 text-xs text-neutral-500">{tierFormErrors.name[0]}</p>
          {/if}
        </div>
        <!-- Code -->
        <div>
          <label for="tier-code" class="block text-xs font-medium text-neutral-700 mb-1">Code <span class="text-neutral-400">*</span></label>
          <input id="tier-code" type="text" bind:value={tierForm.code} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="e.g. GOLD" />
          {#if tierFormErrors.code}
            <p class="mt-1 text-xs text-neutral-500">{tierFormErrors.code[0]}</p>
          {/if}
        </div>
        <!-- Min Deals + Min Revenue -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tier-deals" class="block text-xs font-medium text-neutral-700 mb-1">Min Deals</label>
            <input id="tier-deals" type="number" bind:value={tierForm.min_deals} min="0" class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" />
          </div>
          <div>
            <label for="tier-revenue" class="block text-xs font-medium text-neutral-700 mb-1">Min Revenue</label>
            <input id="tier-revenue" type="text" bind:value={tierForm.min_revenue} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="0.00" />
          </div>
        </div>
        <!-- Commission Multiplier + Bonus -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tier-mult" class="block text-xs font-medium text-neutral-700 mb-1">Commission Multiplier</label>
            <input id="tier-mult" type="text" bind:value={tierForm.commission_multiplier} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="1.00" />
          </div>
          <div>
            <label for="tier-bonus" class="block text-xs font-medium text-neutral-700 mb-1">Bonus (%)</label>
            <input id="tier-bonus" type="text" bind:value={tierForm.bonus_pct} class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" placeholder="0" />
          </div>
        </div>
        <!-- Evaluation Period -->
        <div>
          <label for="tier-eval" class="block text-xs font-medium text-neutral-700 mb-1">Evaluation Period (months)</label>
          <input id="tier-eval" type="number" bind:value={tierForm.evaluation_period_months} min="1" class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" />
        </div>
        <!-- Benefits -->
        <div>
          <label for="tier-benefits" class="block text-xs font-medium text-neutral-700 mb-1">Benefits</label>
          <textarea id="tier-benefits" bind:value={tierForm.benefits} rows="3" class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300 resize-none" placeholder="Describe tier benefits..."></textarea>
        </div>
        <!-- Color + Sort Order -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="tier-color" class="block text-xs font-medium text-neutral-700 mb-1">Color</label>
            <div class="flex items-center gap-2">
              <input id="tier-color" type="color" bind:value={tierForm.color} class="w-8 h-8 rounded border border-neutral-200 cursor-pointer" />
              <input type="text" bind:value={tierForm.color} class="flex-1 bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" />
            </div>
          </div>
          <div>
            <label for="tier-sort" class="block text-xs font-medium text-neutral-700 mb-1">Sort Order</label>
            <input id="tier-sort" type="number" bind:value={tierForm.sort_order} min="0" class="w-full bg-white border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-neutral-300 focus:border-neutral-300" />
          </div>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillTier} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>{/if}
        <button onclick={() => (showTierPanel = false)} class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors">
          Cancel
        </button>
        <button onclick={saveTier} disabled={panelSaving} class="px-4 py-2 text-sm font-medium bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {panelSaving ? "Saving..." : "Create Tier"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- ══════════════════════════════════ DELETE CONFIRMATION MODAL ══════════════════════════════════ -->
{#if deleteId !== null}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <button class="absolute inset-0 bg-neutral-900/30" onclick={() => (deleteId = null)} aria-label="Close modal"></button>
    <div class="relative bg-white rounded-xl shadow-xl max-w-sm w-full mx-4 p-6">
      <h3 class="text-lg font-semibold text-neutral-900">Confirm Deletion</h3>
      <p class="mt-2 text-sm text-neutral-500">
        Are you sure you want to delete this {deleteType}? This action cannot be undone.
      </p>
      <div class="mt-5 flex items-center justify-end gap-3">
        <button onclick={() => (deleteId = null)} class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors">
          Cancel
        </button>
        <button onclick={executeDelete} disabled={deleting} class="px-4 py-2 text-sm font-medium bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

<svelte:window
  onkeydown={(event) => {
    if (event.key !== "Escape") return;
    if (showBrokerDetailModal) {
      closeBrokerDetail();
      return;
    }
    if (deleteId !== null) {
      deleteId = null;
      return;
    }
    if (showTierPanel) {
      showTierPanel = false;
      return;
    }
    if (showCommissionPanel) {
      showCommissionPanel = false;
      return;
    }
    if (showBrokerPanel) {
      showBrokerPanel = false;
    }
  }}
/>

<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type { PaginatedResponse } from "$lib/types";

  type DealStatus = "active" | "won" | "lost" | "on_hold";

  type OpportunityDeal = {
    id: number;
    contact: number;
    contact_name: string;
    lead: number | null;
    lead_name: string | null;
    broker_name: string | null;
    reservation: number | null;
    reservation_number: string | null;
    reservation_status: string | null;
    unit_number: string | null;
    property_name: string | null;
    deal_name: string;
    stage: string;
    status: DealStatus;
    status_display: string;
    deal_value: string | null;
    close_probability: number;
    weighted_value: string;
    expected_commission: string;
    notes: string;
    linked_at: string;
  };

  type StageBreakdown = {
    stage: string;
    count: number;
    deal_value: string;
    weighted_value: string;
  };

  type OpportunityOverview = {
    total_deals: number;
    active_deals: number;
    pipeline_value: string;
    weighted_forecast: string;
    closed_won_value: string;
    expected_commission: string;
    commission_paid: string;
    commission_pending: string;
    stage_breakdown: StageBreakdown[];
  };

  type ContactOption = {
    id: number;
    display_name: string;
  };

  type LeadOption = {
    id: number;
    first_name: string;
    last_name: string;
    status: string;
  };

  type ReservationOption = {
    id: number;
    reservation_number: string;
    lead_id: number;
    lead_name: string;
    unit_number: string;
    property_name: string;
    total_price: string;
    status: string;
  };

  type CommissionItem = {
    id: number;
    broker_name: string;
    lead_name: string;
    deal_value: string;
    total_commission: string;
    status: string;
    status_display: string;
    triggered_at: string;
  };

  const defaultStageOrder = [
    "Prospecting",
    "Qualified",
    "Proposal",
    "Negotiation",
    "Closed Won",
    "Closed Lost",
  ];

  const statusOptions: { value: DealStatus; label: string }[] = [
    { value: "active", label: "Active" },
    { value: "on_hold", label: "On Hold" },
    { value: "won", label: "Closed Won" },
    { value: "lost", label: "Closed Lost" },
  ];

  let overview = $state<OpportunityOverview | null>(null);
  let overviewLoading = $state(true);

  let deals = $state<OpportunityDeal[]>([]);
  let dealsLoading = $state(true);
  let dealsError = $state<string | null>(null);
  let totalCount = $state(0);
  let currentPage = $state(1);
  const pageSize = 200;

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  const pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i += 1) pages.push(i);
    return pages;
  });

  const pageStart = $derived(totalCount === 0 ? 0 : ((currentPage - 1) * pageSize) + 1);
  const pageEnd = $derived(totalCount === 0 ? 0 : Math.min(currentPage * pageSize, totalCount));

  let search = $state("");
  let statusFilter = $state("");
  let stageFilter = $state("");

  let commissions = $state<CommissionItem[]>([]);
  let commissionsLoading = $state(true);
  let commissionsTotalCount = $state(0);
  let commissionsCurrentPage = $state(1);
  const commissionsPageSize = 10;

  const commissionsTotalPages = $derived(
    Math.max(1, Math.ceil(commissionsTotalCount / commissionsPageSize)),
  );

  const commissionsPageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, commissionsCurrentPage - Math.floor(maxVisible / 2));
    let end = Math.min(commissionsTotalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i += 1) pages.push(i);
    return pages;
  });

  const commissionsPageStart = $derived(
    commissionsTotalCount === 0 ? 0 : ((commissionsCurrentPage - 1) * commissionsPageSize) + 1,
  );
  const commissionsPageEnd = $derived(
    commissionsTotalCount === 0 ? 0 : Math.min(commissionsCurrentPage * commissionsPageSize, commissionsTotalCount),
  );

  let contacts = $state<ContactOption[]>([]);
  let leads = $state<LeadOption[]>([]);
  let reservations = $state<ReservationOption[]>([]);

  let showSlideOver = $state(false);
  let savingOpportunity = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    contact: "",
    lead: "",
    reservation: "",
    deal_name: "",
    stage: "Prospecting",
    status: "active" as DealStatus,
    deal_value: "",
    close_probability: "60",
    notes: "",
  });

  let stageSelection = $state<Record<number, string>>({});
  let statusSelection = $state<Record<number, DealStatus>>({});
  let probabilitySelection = $state<Record<number, number>>({});

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const OPPORTUNITY_SAMPLES = [
    { deal_name: "Lekki Phase 3 — Block A Penthouse", stage: "Negotiation", deal_value: "85000000", close_probability: "75", notes: "Client interested in 4-bed penthouse. Site visit completed." },
    { deal_name: "Abuja CBD — Office Space Lease", stage: "Prospecting", deal_value: "12500000", close_probability: "40", notes: "Corporate tenant, 3-year lease term under discussion." },
    { deal_name: "Ikoyi Waterfront Villa — Plot 7", stage: "Proposal", deal_value: "250000000", close_probability: "55", notes: "HNI buyer. Awaiting bank pre-approval letter." },
    { deal_name: "Victoria Island — Retail Unit 2B", stage: "Qualification", deal_value: "45000000", close_probability: "30", notes: "Franchise operator evaluating foot traffic data." },
  ];

  let devIdx = $state(0);

  function devFillOpportunity() {
    const sample = OPPORTUNITY_SAMPLES[devIdx % OPPORTUNITY_SAMPLES.length];
    devIdx++;
    createForm.deal_name = sample.deal_name;
    createForm.stage = sample.stage;
    createForm.deal_value = sample.deal_value;
    createForm.close_probability = sample.close_probability;
    createForm.notes = sample.notes;
    createForm.status = "active";
    if (contacts.length > 0) createForm.contact = String(contacts[devIdx % contacts.length].id);
    if (leads.length > 0) createForm.lead = String(leads[devIdx % leads.length].id);
  }

  let debounceTimer: ReturnType<typeof setTimeout>;

  function normalizeStage(value: string | null | undefined): string {
    if (!value) return "Unstaged";
    const normalized = value.replaceAll("_", " ").trim();
    return normalized || "Unstaged";
  }

  function stageSortRank(stage: string): number {
    const idx = defaultStageOrder.findIndex(
      (item) => item.toLowerCase() === stage.toLowerCase(),
    );
    return idx >= 0 ? idx : 999;
  }

  function toNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined || value === "") return 0;
    const parsed = typeof value === "number" ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatMoney(value: string | number | null | undefined): string {
    return currency.format(toNumber(value));
  }

  function formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return "\u2014";
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      contact: "",
      lead: "",
      reservation: "",
      deal_name: "",
      stage: "Prospecting",
      status: "active",
      deal_value: "",
      close_probability: "60",
      notes: "",
    };
    createErrors = {};
  }

  const stageOptions = $derived.by(() => {
    const seen = new Set<string>();
    const options: string[] = [];

    for (const stage of defaultStageOrder) {
      const label = normalizeStage(stage);
      const key = label.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      options.push(label);
    }

    for (const stageBucket of overview?.stage_breakdown ?? []) {
      const label = normalizeStage(stageBucket.stage);
      const key = label.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      options.push(label);
    }

    for (const deal of deals) {
      const label = normalizeStage(deal.stage);
      const key = label.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      options.push(label);
    }

    return options.sort((a, b) => {
      const rankDiff = stageSortRank(a) - stageSortRank(b);
      if (rankDiff !== 0) return rankDiff;
      return a.localeCompare(b);
    });
  });

  const pipelineColumns = $derived.by(() => {
    const byStage = new Map<string, OpportunityDeal[]>();
    for (const deal of deals) {
      const label = normalizeStage(deal.stage);
      const list = byStage.get(label) ?? [];
      list.push(deal);
      byStage.set(label, list);
    }

    return stageOptions.map((stage) => {
      const stageDeals = byStage.get(stage) ?? [];
      const totalValue = stageDeals.reduce((sum, deal) => sum + toNumber(deal.deal_value), 0);
      return {
        stage,
        deals: stageDeals,
        count: stageDeals.length,
        totalValue,
      };
    });
  });

  async function fetchOverview() {
    overviewLoading = true;
    try {
      overview = await api.get<OpportunityOverview>("/crm/opportunities/overview/");
    } catch (err) {
      console.error("[crm/opportunities]", err);
      overview = null;
    } finally {
      overviewLoading = false;
    }
  }

  async function fetchDeals() {
    dealsLoading = true;
    dealsError = null;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      if (stageFilter) params.stage = stageFilter;

      const res = await api.get<PaginatedResponse<OpportunityDeal>>("/crm/opportunities/", params);
      deals = res.results;
      totalCount = res.count;

      const nextStageSelection: Record<number, string> = {};
      const nextStatusSelection: Record<number, DealStatus> = {};
      const nextProbabilitySelection: Record<number, number> = {};
      for (const deal of deals) {
        nextStageSelection[deal.id] = normalizeStage(deal.stage);
        nextStatusSelection[deal.id] = deal.status;
        nextProbabilitySelection[deal.id] = Math.max(0, Math.min(100, Number(deal.close_probability ?? 0)));
      }
      stageSelection = nextStageSelection;
      statusSelection = nextStatusSelection;
      probabilitySelection = nextProbabilitySelection;
    } catch (err) {
      console.error("[crm/opportunities]", err);
      deals = [];
      totalCount = 0;
      stageSelection = {};
      statusSelection = {};
      probabilitySelection = {};
      dealsError = err instanceof Error ? err.message : "Could not load opportunities.";
    } finally {
      dealsLoading = false;
    }
  }

  async function fetchCommissions() {
    commissionsLoading = true;
    try {
      const res = await api.get<PaginatedResponse<CommissionItem>>("/crm/commission-earnings/", {
        page: String(commissionsCurrentPage),
        page_size: String(commissionsPageSize),
      });
      commissionsTotalCount = res.count;
      const latestTotalPages = Math.max(1, Math.ceil(res.count / commissionsPageSize));
      if (commissionsCurrentPage > latestTotalPages) {
        commissionsCurrentPage = latestTotalPages;
        await fetchCommissions();
        return;
      }
      commissions = res.results;
    } catch (err) {
      console.error("[crm/opportunities]", err);
      commissions = [];
      commissionsTotalCount = 0;
    } finally {
      commissionsLoading = false;
    }
  }

  async function fetchContacts() {
    try {
      const res = await api.get<PaginatedResponse<ContactOption>>("/crm/contacts/", {
        page_size: "200",
      });
      contacts = res.results;
    } catch (err) {
      console.error("[crm/opportunities]", err);
      contacts = [];
    }
  }

  async function fetchLeads() {
    try {
      const res = await api.get<PaginatedResponse<LeadOption>>("/crm/leads/", {
        status: "active",
        page_size: "200",
      });
      leads = res.results;
    } catch (err) {
      console.error("[crm/opportunities]", err);
      leads = [];
    }
  }

  async function fetchReservations() {
    try {
      const res = await api.get<PaginatedResponse<ReservationOption>>("/crm/reservations/", {
        page_size: "200",
      });
      reservations = res.results.filter((item) => !["cancelled", "converted", "expired"].includes(item.status));
    } catch (err) {
      console.error("[crm/opportunities]", err);
      reservations = [];
    }
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchDeals();
    }, 300);
  }

  function handleStatusFilter(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchDeals();
  }

  function handleStageFilter(value: string) {
    stageFilter = value;
    currentPage = 1;
    fetchDeals();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    fetchDeals();
  }

  function goToCommissionsPage(page: number) {
    if (page < 1 || page > commissionsTotalPages || page === commissionsCurrentPage) return;
    commissionsCurrentPage = page;
    fetchCommissions();
  }

  async function saveDealUpdates(deal: OpportunityDeal) {
    const stage = stageSelection[deal.id] ?? normalizeStage(deal.stage);
    const status = statusSelection[deal.id] ?? deal.status;
    const probability = Math.max(0, Math.min(100, Number(probabilitySelection[deal.id] ?? deal.close_probability ?? 0)));

    try {
      await api.patch(`/crm/opportunities/${deal.id}/`, {
        stage,
        status,
        close_probability: probability,
      });
      toast.success("Opportunity updated", "Pipeline stage and forecast were saved");
      await Promise.all([fetchDeals(), fetchOverview(), fetchCommissions()]);
    } catch (err) {
      console.error("[crm/opportunities]", err);
      if (err instanceof ApiError) {
        toast.error("Validation error", err.message || "Please review the update values");
      } else {
        toast.error("Update failed", "Could not save opportunity changes");
      }
    }
  }

  async function createOpportunity(event: Event) {
    event.preventDefault();
    createErrors = {};
    savingOpportunity = true;

    try {
      const closeProbability = Math.max(
        0,
        Math.min(100, Number(createForm.close_probability || "0")),
      );

      const payload: Record<string, unknown> = {
        contact: Number(createForm.contact),
        lead: createForm.lead ? Number(createForm.lead) : null,
        reservation: createForm.reservation ? Number(createForm.reservation) : null,
        deal_name: createForm.deal_name.trim(),
        stage: normalizeStage(createForm.stage),
        status: createForm.status,
        deal_value: createForm.deal_value ? createForm.deal_value : null,
        close_probability: closeProbability,
        notes: createForm.notes?.trim() || "",
      };

      await api.post<OpportunityDeal>("/crm/opportunities/", payload);
      toast.success("Opportunity created", "Deal has been added to your CRM pipeline");
      showSlideOver = false;
      resetCreateForm();
      await Promise.all([fetchDeals(), fetchOverview(), fetchCommissions()]);
    } catch (err) {
      console.error("[crm/opportunities]", err);
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Creation failed", "Could not create opportunity");
      }
    }

    savingOpportunity = false;
  }

  function openCreatePanel() {
    resetCreateForm();
    showSlideOver = true;
    fetchContacts();
    fetchLeads();
    fetchReservations();
  }

  function closeCreatePanel() {
    showSlideOver = false;
    resetCreateForm();
  }

  onMount(() => {
    void fetchOverview();
    void fetchDeals();
    void fetchCommissions();
  });

  $effect(() => {
    if (!createForm.reservation) return;
    const selected = reservations.find((item) => String(item.id) === createForm.reservation);
    if (!selected) return;
    if (!createForm.lead) createForm.lead = String(selected.lead_id);
    if (!createForm.deal_name) createForm.deal_name = `${selected.property_name} ${selected.unit_number}`;
    if (!createForm.deal_value) createForm.deal_value = selected.total_price;
  });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-orange-400">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Opportunity/Deal Management</h1>
      <p class="mt-1 text-sm text-neutral-500">Manage revenue pipeline, weighted forecasts, linked units, and broker commissions.</p>
    </div>
    <button
      onclick={openCreatePanel}
      class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Opportunity
    </button>
  </div>

  {#if overviewLoading}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-6">
      {#each Array(6) as _}
        <div class="animate-pulse rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
          <div class="mb-3 h-3 w-24 rounded bg-neutral-200"></div>
          <div class="h-6 w-16 rounded bg-neutral-200"></div>
        </div>
      {/each}
    </div>
  {:else if overview}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-6">
      <div class="rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Active Deals</p>
        <p class="mt-2 text-2xl font-semibold tabular-nums text-neutral-900">{overview.active_deals.toLocaleString()}</p>
      </div>
      <div class="rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Pipeline Value</p>
        <p class="mt-2 text-lg font-semibold tabular-nums text-neutral-900">{formatMoney(overview.pipeline_value)}</p>
      </div>
      <div class="rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Weighted Forecast</p>
        <p class="mt-2 text-lg font-semibold tabular-nums text-neutral-900">{formatMoney(overview.weighted_forecast)}</p>
      </div>
      <div class="rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Closed Won</p>
        <p class="mt-2 text-lg font-semibold tabular-nums text-neutral-900">{formatMoney(overview.closed_won_value)}</p>
      </div>
      <div class="rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Expected Commission</p>
        <p class="mt-2 text-lg font-semibold tabular-nums text-neutral-900">{formatMoney(overview.expected_commission)}</p>
      </div>
      <div class="rounded-xl border border-[#f2d4c4] bg-[#fff1e8] p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Paid Commission</p>
        <p class="mt-2 text-lg font-semibold tabular-nums text-neutral-900">{formatMoney(overview.commission_paid)}</p>
      </div>
    </div>
  {/if}

  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Search</span>
        <div class="relative">
          <svg class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="text"
            value={search}
            oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
            placeholder="Deal name, contact, reservation..."
            class="w-full rounded-lg border border-neutral-300 py-2 pl-9 pr-3 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
          />
        </div>
      </label>

      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusFilter((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
        >
          <option value="">All statuses</option>
          {#each statusOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>

      <label>
        <span class="mb-1.5 block text-sm font-medium text-neutral-700">Stage</span>
        <select
          value={stageFilter}
          onchange={(e) => handleStageFilter((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
        >
          <option value="">All stages</option>
          {#each stageOptions as stage}
            <option value={stage}>{stage}</option>
          {/each}
        </select>
      </label>
    </div>
  </div>

  {#if dealsError && !dealsLoading}
    <DataStateBanner
      title="Couldn't load opportunities"
      message={dealsError}
      onretry={fetchDeals}
    />
  {/if}

  <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
    {#if dealsLoading}
      {#each Array(3) as _}
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <div class="mb-3 h-4 w-32 animate-pulse rounded bg-neutral-200"></div>
          {#each Array(3) as __}
            <div class="mb-3 rounded-lg border border-neutral-100 p-3">
              <div class="mb-2 h-3 w-24 animate-pulse rounded bg-neutral-200"></div>
              <div class="h-3 w-40 animate-pulse rounded bg-neutral-200"></div>
            </div>
          {/each}
        </div>
      {/each}
    {:else if dealsError}
      <!-- error banner above already conveys the failure; suppress kanban -->
    {:else}
      {#each pipelineColumns as column}
        <section class="rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-4 py-3">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">{column.stage}</h2>
              <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-semibold text-neutral-700">{column.count}</span>
            </div>
            <p class="mt-1 text-xs text-neutral-500">{formatMoney(column.totalValue)}</p>
          </div>

          <div class="max-h-136 space-y-3 overflow-y-auto p-4">
            {#if column.deals.length === 0}
              <p class="rounded-lg border border-dashed border-neutral-200 px-3 py-4 text-center text-xs text-neutral-400">No opportunities in this stage.</p>
            {:else}
              {#each column.deals as deal}
                <article class="space-y-3 rounded-lg border border-neutral-200 p-3">
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <h3 class="text-sm font-semibold text-neutral-900">{deal.deal_name || deal.contact_name}</h3>
                      <p class="mt-0.5 text-xs text-neutral-500">{deal.contact_name}</p>
                    </div>
                    <StatusBadge status={deal.status} label={deal.status_display} />
                  </div>

                  <div class="space-y-1 text-xs text-neutral-600">
                    <p><span class="font-medium text-neutral-700">Lead:</span> {deal.lead_name || "\u2014"}</p>
                    <p><span class="font-medium text-neutral-700">Property / Unit:</span> {deal.property_name ? `${deal.property_name} / ${deal.unit_number || "\u2014"}` : "\u2014"}</p>
                    <p><span class="font-medium text-neutral-700">Reservation:</span> {deal.reservation_number || "\u2014"}</p>
                    <p><span class="font-medium text-neutral-700">Broker:</span> {deal.broker_name || "\u2014"}</p>
                    <p><span class="font-medium text-neutral-700">Deal Value:</span> {formatMoney(deal.deal_value)}</p>
                    <p><span class="font-medium text-neutral-700">Weighted:</span> {formatMoney(deal.weighted_value)} ({probabilitySelection[deal.id] ?? deal.close_probability}%)</p>
                    <p><span class="font-medium text-neutral-700">Expected Commission:</span> {formatMoney(deal.expected_commission)}</p>
                  </div>

                  <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <label class="text-xs text-neutral-600">
                      <span class="mb-1 block font-medium">Stage</span>
                      <input
                        type="text"
                        value={stageSelection[deal.id] ?? normalizeStage(deal.stage)}
                        oninput={(e) => {
                          stageSelection = {
                            ...stageSelection,
                            [deal.id]: (e.target as HTMLInputElement).value,
                          };
                        }}
                        list="opportunity-stage-options"
                        class="w-full rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
                      />
                    </label>

                    <label class="text-xs text-neutral-600">
                      <span class="mb-1 block font-medium">Status</span>
                      <select
                        value={statusSelection[deal.id] ?? deal.status}
                        onchange={(e) => {
                          statusSelection = {
                            ...statusSelection,
                            [deal.id]: (e.target as HTMLSelectElement).value as DealStatus,
                          };
                        }}
                        class="w-full rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
                      >
                        {#each statusOptions as option}
                          <option value={option.value}>{option.label}</option>
                        {/each}
                      </select>
                    </label>

                    <label class="text-xs text-neutral-600 sm:col-span-2">
                      <span class="mb-1 block font-medium">Close Probability (%)</span>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={probabilitySelection[deal.id] ?? deal.close_probability}
                        oninput={(e) => {
                          const raw = Number((e.target as HTMLInputElement).value || "0");
                          probabilitySelection = {
                            ...probabilitySelection,
                            [deal.id]: Math.max(0, Math.min(100, raw)),
                          };
                        }}
                        class="w-full rounded-md border border-neutral-300 px-2.5 py-1.5 text-xs focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
                      />
                    </label>
                  </div>

                  <button
                    onclick={() => saveDealUpdates(deal)}
                    class="w-full rounded-md border border-neutral-300 px-3 py-2 text-xs font-medium text-neutral-700 transition-colors hover:border-neutral-400 hover:bg-neutral-50"
                  >
                    Update Opportunity
                  </button>
                </article>
              {/each}
            {/if}
          </div>
        </section>
      {/each}
    {/if}
  </div>

  {#if !dealsLoading && totalCount > 0}
    <div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-sm text-neutral-500">
        Showing {pageStart.toLocaleString()}&#8211;{pageEnd.toLocaleString()} of {totalCount.toLocaleString()} opportunities
      </p>
      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button
            type="button"
            onclick={() => goToPage(currentPage - 1)}
            disabled={currentPage <= 1}
            aria-label="Previous page"
            class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>
          {#each pageNumbers as page}
            <button
              type="button"
              onclick={() => goToPage(page)}
              class="rounded-lg border px-3 py-1.5 text-sm transition-colors {page === currentPage
                ? 'border-neutral-900 bg-neutral-900 text-white'
                : 'border-neutral-200 hover:bg-neutral-50'}"
            >
              {page}
            </button>
          {/each}
          <button
            type="button"
            onclick={() => goToPage(currentPage + 1)}
            disabled={currentPage >= totalPages}
            aria-label="Next page"
            class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}

  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-100 px-5 py-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-800">Commission Tracking (Agents / Brokers)</h2>
      <p class="mt-1 text-xs text-neutral-500">Linked commission records from CRM broker earnings.</p>
    </div>

    {#if commissionsLoading}
      <div class="space-y-3 p-5">
        {#each Array(4) as _}
          <div class="h-10 animate-pulse rounded bg-neutral-100"></div>
        {/each}
      </div>
    {:else if commissions.length === 0}
      <div class="px-5 py-10 text-center text-sm text-neutral-500">No commission records yet.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Broker</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Lead</th>
              <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Deal Value</th>
              <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Commission</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Triggered</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each commissions as item}
              <tr>
                <td class="px-5 py-3 text-sm text-neutral-900">{item.broker_name || "\u2014"}</td>
                <td class="px-5 py-3 text-sm text-neutral-700">{item.lead_name || "\u2014"}</td>
                <td class="px-5 py-3 text-right text-sm tabular-nums text-neutral-800">{formatMoney(item.deal_value)}</td>
                <td class="px-5 py-3 text-right text-sm tabular-nums text-neutral-900">{formatMoney(item.total_commission)}</td>
                <td class="px-5 py-3"><StatusBadge status={item.status} label={item.status_display} /></td>
                <td class="px-5 py-3 text-sm text-neutral-500">{formatDate(item.triggered_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if commissionsTotalCount > 0}
        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-neutral-200 px-5 py-4">
          <p class="text-sm text-neutral-500">
            Showing {commissionsPageStart.toLocaleString()}&#8211;{commissionsPageEnd.toLocaleString()} of {commissionsTotalCount.toLocaleString()} broker records
          </p>
          {#if commissionsTotalPages > 1}
            <div class="flex items-center gap-1">
              <button
                type="button"
                onclick={() => goToCommissionsPage(commissionsCurrentPage - 1)}
                disabled={commissionsCurrentPage <= 1}
                aria-label="Previous commission page"
                class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
              {#each commissionsPageNumbers as page}
                <button
                  type="button"
                  onclick={() => goToCommissionsPage(page)}
                  class="rounded-lg border px-3 py-1.5 text-sm transition-colors {page === commissionsCurrentPage
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-200 hover:bg-neutral-50'}"
                >
                  {page}
                </button>
              {/each}
              <button
                type="button"
                onclick={() => goToCommissionsPage(commissionsCurrentPage + 1)}
                disabled={commissionsCurrentPage >= commissionsTotalPages}
                aria-label="Next commission page"
                class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </div>
          {/if}
        </div>
      {/if}
    {/if}
  </div>

  <datalist id="opportunity-stage-options">
    {#each stageOptions as stage}
      <option value={stage}></option>
    {/each}
  </datalist>
</div>

{#if showSlideOver}
  <button
    class="fixed inset-0 z-40 cursor-default bg-black/40 backdrop-blur-sm"
    onclick={closeCreatePanel}
    aria-label="Close panel"
    tabindex="-1"
  ></button>

  <div class="slide-over-enter fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-2xl">
    <div class="shrink-0 border-b border-neutral-100 px-6 py-4">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold text-neutral-900">New Opportunity</h2>
        <button
          onclick={closeCreatePanel}
          class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
          aria-label="Close"
        >
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="opportunity-create-form" onsubmit={createOpportunity} class="space-y-5">
        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Contact <span class="text-neutral-400">*</span></span>
          <select
            bind:value={createForm.contact}
            required
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
          >
            <option value="">Select contact</option>
            {#each contacts as contact}
              <option value={String(contact.id)}>{contact.display_name}</option>
            {/each}
          </select>
          {#if formError("contact")}
            <p class="mt-1 text-xs text-red-600">{formError("contact")}</p>
          {/if}
        </label>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Lead</span>
            <select
              bind:value={createForm.lead}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            >
              <option value="">Optional lead</option>
              {#each leads as lead}
                <option value={String(lead.id)}>{lead.first_name} {lead.last_name}</option>
              {/each}
            </select>
            {#if formError("lead")}
              <p class="mt-1 text-xs text-red-600">{formError("lead")}</p>
            {/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Reservation</span>
            <select
              bind:value={createForm.reservation}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            >
              <option value="">Optional reservation</option>
              {#each reservations as reservation}
                <option value={String(reservation.id)}>
                  {reservation.reservation_number} · {reservation.property_name} {reservation.unit_number}
                </option>
              {/each}
            </select>
            {#if formError("reservation")}
              <p class="mt-1 text-xs text-red-600">{formError("reservation")}</p>
            {/if}
          </label>
        </div>

        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Deal Name</span>
          <input
            bind:value={createForm.deal_name}
            type="text"
            placeholder="e.g. Waterfront Penthouse - Phase 1"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
          />
          {#if formError("deal_name")}
            <p class="mt-1 text-xs text-red-600">{formError("deal_name")}</p>
          {/if}
        </label>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Stage</span>
            <input
              bind:value={createForm.stage}
              type="text"
              list="opportunity-stage-options"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            />
            {#if formError("stage")}
              <p class="mt-1 text-xs text-red-600">{formError("stage")}</p>
            {/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Status</span>
            <select
              bind:value={createForm.status}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            >
              {#each statusOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
            {#if formError("status")}
              <p class="mt-1 text-xs text-red-600">{formError("status")}</p>
            {/if}
          </label>
        </div>

        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Deal Value</span>
            <input
              bind:value={createForm.deal_value}
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            />
            {#if formError("deal_value")}
              <p class="mt-1 text-xs text-red-600">{formError("deal_value")}</p>
            {/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Close Probability (%)</span>
            <input
              bind:value={createForm.close_probability}
              type="number"
              min="0"
              max="100"
              step="1"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            />
            {#if formError("close_probability")}
              <p class="mt-1 text-xs text-red-600">{formError("close_probability")}</p>
            {/if}
          </label>
        </div>

        <label>
          <span class="mb-1.5 block text-sm font-medium text-neutral-700">Notes</span>
          <textarea
            bind:value={createForm.notes}
            rows="4"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            placeholder="Additional opportunity context"
          ></textarea>
        </label>
      </form>
    </div>

    <div class="shrink-0 border-t border-neutral-100 px-6 py-4">
      <div class="flex items-center justify-end gap-3">
        {#if isDev}
          <button type="button" onclick={devFillOpportunity} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
        {/if}
        <button
          type="button"
          onclick={closeCreatePanel}
          class="rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          form="opportunity-create-form"
          disabled={savingOpportunity}
          class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {#if savingOpportunity}
            <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-20"></circle>
              <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" stroke-width="4" class="opacity-80"></path>
            </svg>
          {/if}
          Create Opportunity
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .slide-over-enter {
    animation: slide-over-enter 0.22s ease-out;
  }

  @keyframes slide-over-enter {
    from {
      transform: translateX(20px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
</style>

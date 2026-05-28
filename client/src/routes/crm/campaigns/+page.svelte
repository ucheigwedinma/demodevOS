<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    CampaignListItem,
    CampaignStatus,
    CampaignType,
    CommunicationChannel,
    PaginatedResponse,
  } from "$lib/types";

  // ── State ────────────────────────────────────────────────────────────
  const pageSize = 25;

  let campaigns = $state<CampaignListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let refreshing = $state(false);
  let currentPage = $state(1);

  // Filters
  let search = $state("");
  let statusFilter = $state<"" | CampaignStatus>("");
  let typeFilter = $state<"" | CampaignType>("");
  let channelFilter = $state<"" | CommunicationChannel>("");

  let debounceTimer: ReturnType<typeof setTimeout>;

  // ── Reference data ──────────────────────────────────────────────────
  const STATUS_LABELS: Record<CampaignStatus, string> = {
    draft: "Draft",
    scheduled: "Scheduled",
    running: "Running",
    paused: "Paused",
    completed: "Completed",
    cancelled: "Cancelled",
  };

  const TYPE_LABELS: Record<CampaignType, string> = {
    email_blast: "Email Blast",
    whatsapp_campaign: "WhatsApp",
    sms_blast: "SMS Blast",
    digital_ads: "Digital Ads",
    drip: "Drip",
    follow_up: "Follow-Up",
  };

  const CHANNEL_LABELS: Record<CommunicationChannel, string> = {
    email: "Email",
    whatsapp: "WhatsApp",
    sms: "SMS",
    phone: "Phone",
    video_call: "Video Call",
    in_person: "In Person",
    other: "Other",
  };

  // Static class map (Tailwind 4 scanner-safe)
  const STATUS_BADGE: Record<CampaignStatus, string> = {
    draft: "border-neutral-200 bg-neutral-50 text-neutral-600",
    scheduled: "border-neutral-300 bg-neutral-100 text-neutral-700",
    running: "border-neutral-900 bg-neutral-900 text-white",
    paused: "border-neutral-300 bg-neutral-50 text-neutral-500",
    completed: "border-neutral-400 bg-white text-neutral-700",
    cancelled: "border-neutral-200 bg-white text-neutral-400",
  };

  // ── Derived ─────────────────────────────────────────────────────────
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  const pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    const end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) start = Math.max(1, end - maxVisible + 1);
    for (let i = start; i <= end; i += 1) pages.push(i);
    return pages;
  });

  const pageStart = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const pageEnd = $derived(Math.min(currentPage * pageSize, totalCount));

  // KPI strip — derived from the loaded page (cheap rough indicator).
  const liveCount = $derived(campaigns.filter((c) => c.status === "running").length);
  const totalRecipients = $derived(campaigns.reduce((sum, c) => sum + (c.total_recipients ?? 0), 0));
  const totalSent = $derived(campaigns.reduce((sum, c) => sum + (c.sent_count ?? 0), 0));
  const totalOpened = $derived(campaigns.reduce((sum, c) => sum + (c.opened_count ?? 0), 0));

  // ── Helpers ──────────────────────────────────────────────────────────
  function fmtNumber(n: number | null | undefined): string {
    return Number(n ?? 0).toLocaleString("en-US");
  }

  function fmtCurrency(value: string | null | undefined): string {
    if (!value) return "—";
    return currency.format(parseFloat(value));
  }

  function fmtDateTime(value: string | null): string {
    if (!value) return "—";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function openRate(item: CampaignListItem): string {
    if (!item.delivered_count) return "—";
    return `${((item.opened_count / item.delivered_count) * 100).toFixed(1)}%`;
  }

  function clickRate(item: CampaignListItem): string {
    if (!item.delivered_count) return "—";
    return `${((item.clicked_count / item.delivered_count) * 100).toFixed(1)}%`;
  }

  // ── Data fetch ───────────────────────────────────────────────────────
  async function fetchCampaigns(manual = false) {
    if (manual) refreshing = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
        ordering: "-created_at",
      };
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.campaign_type = typeFilter;
      if (channelFilter) params.channel = channelFilter;

      const res = await api.get<PaginatedResponse<CampaignListItem>>("/crm/campaigns/", params);
      campaigns = res.results;
      totalCount = res.count;
    } catch (err) {
      console.error("[crm/campaigns]", err);
      campaigns = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load campaigns.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  // Filters change → debounce + reset to page 1
  function onFilterChange() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      void fetchCampaigns();
    }, 200);
  }

  function gotoPage(p: number) {
    if (p < 1 || p > totalPages || p === currentPage) return;
    currentPage = p;
    void fetchCampaigns();
  }

  function openCampaign(id: number) {
    void goto(`/crm/campaigns/${id}`);
  }

  function newCampaign() {
    // Campaign creation form lives in the Communications page's Campaigns tab.
    // Route there so the user gets the full create flow without duplicating UI.
    void goto("/crm/communications?tab=campaigns");
  }

  onMount(() => {
    void fetchCampaigns();
  });
</script>

<div class="space-y-6">
  <!-- ── Header ─────────────────────────────────────────────────────── -->
  <section class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-neutral-400">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Campaigns</h1>
      <p class="mt-1 text-sm text-neutral-500">
        All marketing &amp; outreach campaigns — broadcast performance, recipient counts, and conversion impact.
      </p>
    </div>
    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onclick={() => fetchCampaigns(true)}
        class="rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
      >
        {refreshing ? "Refreshing…" : "Refresh"}
      </button>
      <button
        type="button"
        onclick={newCampaign}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        New Campaign
      </button>
    </div>
  </section>

  <!-- ── KPI strip ──────────────────────────────────────────────────── -->
  <section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    <article class="rounded-xl border border-neutral-200 bg-white p-3">
      <p class="text-[10px] uppercase tracking-wider text-neutral-500">Total Campaigns</p>
      <p class="mt-1 text-xl font-bold tabular-nums text-neutral-900">{fmtNumber(totalCount)}</p>
      <p class="text-[11px] text-neutral-400">{liveCount} running on this page</p>
    </article>
    <article class="rounded-xl border border-neutral-200 bg-white p-3">
      <p class="text-[10px] uppercase tracking-wider text-neutral-500">Recipients (page)</p>
      <p class="mt-1 text-xl font-bold tabular-nums text-neutral-900">{fmtNumber(totalRecipients)}</p>
      <p class="text-[11px] text-neutral-400">Across {campaigns.length} loaded</p>
    </article>
    <article class="rounded-xl border border-neutral-200 bg-white p-3">
      <p class="text-[10px] uppercase tracking-wider text-neutral-500">Sent (page)</p>
      <p class="mt-1 text-xl font-bold tabular-nums text-neutral-900">{fmtNumber(totalSent)}</p>
      <p class="text-[11px] text-neutral-400">Cumulative across rows</p>
    </article>
    <article class="rounded-xl border border-neutral-200 bg-white p-3">
      <p class="text-[10px] uppercase tracking-wider text-neutral-500">Opened (page)</p>
      <p class="mt-1 text-xl font-bold tabular-nums text-neutral-900">{fmtNumber(totalOpened)}</p>
      <p class="text-[11px] text-neutral-400">Cumulative across rows</p>
    </article>
  </section>

  <!-- ── Filters ────────────────────────────────────────────────────── -->
  <section class="flex flex-wrap items-center gap-2">
    <label class="flex-1 min-w-[200px]">
      <span class="sr-only">Search campaigns</span>
      <input
        type="search"
        bind:value={search}
        oninput={onFilterChange}
        placeholder="Search campaigns…"
        class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none"
      />
    </label>
    <select
      bind:value={statusFilter}
      onchange={onFilterChange}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
    >
      <option value="">All statuses</option>
      {#each Object.entries(STATUS_LABELS) as [value, label]}
        <option {value}>{label}</option>
      {/each}
    </select>
    <select
      bind:value={typeFilter}
      onchange={onFilterChange}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
    >
      <option value="">All types</option>
      {#each Object.entries(TYPE_LABELS) as [value, label]}
        <option {value}>{label}</option>
      {/each}
    </select>
    <select
      bind:value={channelFilter}
      onchange={onFilterChange}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
    >
      <option value="">All channels</option>
      {#each Object.entries(CHANNEL_LABELS) as [value, label]}
        <option {value}>{label}</option>
      {/each}
    </select>
  </section>

  <!-- ── Table ──────────────────────────────────────────────────────── -->
  <section class="rounded-xl border border-neutral-200 bg-white">
    <div class="flex items-center justify-between border-b border-neutral-100 px-4 py-2.5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Campaign Stream</h2>
      <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-600">
        {totalCount === 0 ? "0 rows" : `${fmtNumber(pageStart)}–${fmtNumber(pageEnd)} of ${fmtNumber(totalCount)}`}
      </span>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16">
        <div class="h-6 w-6 animate-spin rounded-full border-[2px] border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if campaigns.length === 0}
      <div class="px-6 py-16 text-center text-sm text-neutral-500">
        No campaigns match this filter.
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full text-xs">
          <thead class="bg-neutral-50 text-neutral-500">
            <tr>
              <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Campaign</th>
              <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Type</th>
              <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Channel</th>
              <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Status</th>
              <th class="px-3 py-2 text-right font-semibold uppercase tracking-wider">Recipients</th>
              <th class="px-3 py-2 text-right font-semibold uppercase tracking-wider">Sent</th>
              <th class="px-3 py-2 text-right font-semibold uppercase tracking-wider">Open Rate</th>
              <th class="px-3 py-2 text-right font-semibold uppercase tracking-wider">CTR</th>
              <th class="px-3 py-2 text-right font-semibold uppercase tracking-wider">Spend</th>
              <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody>
            {#each campaigns as item (item.id)}
              <tr
                class="cursor-pointer border-t border-neutral-100 text-neutral-700 hover:bg-neutral-50"
                onclick={() => openCampaign(item.id)}
              >
                <td class="px-3 py-2.5">
                  <p class="max-w-[260px] truncate font-semibold text-neutral-900">{item.name}</p>
                  {#if item.description}
                    <p class="max-w-[260px] truncate text-[10px] text-neutral-500">{item.description}</p>
                  {/if}
                </td>
                <td class="px-3 py-2.5">{TYPE_LABELS[item.campaign_type] ?? item.campaign_type_display}</td>
                <td class="px-3 py-2.5">{CHANNEL_LABELS[item.channel] ?? item.channel_display}</td>
                <td class="px-3 py-2.5">
                  <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_BADGE[item.status] ?? STATUS_BADGE.draft}">
                    {STATUS_LABELS[item.status] ?? item.status_display}
                  </span>
                </td>
                <td class="px-3 py-2.5 text-right tabular-nums">{fmtNumber(item.total_recipients)}</td>
                <td class="px-3 py-2.5 text-right tabular-nums">{fmtNumber(item.sent_count)}</td>
                <td class="px-3 py-2.5 text-right tabular-nums">{openRate(item)}</td>
                <td class="px-3 py-2.5 text-right tabular-nums">{clickRate(item)}</td>
                <td class="px-3 py-2.5 text-right tabular-nums">{fmtCurrency(item.spend_amount)}</td>
                <td class="px-3 py-2.5 text-left text-neutral-500">{fmtDateTime(item.created_at)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      {#if totalPages > 1}
        <div class="flex flex-wrap items-center justify-between gap-2 border-t border-neutral-100 px-4 py-2.5 text-[11px] text-neutral-600">
          <span>Page <span class="font-semibold text-neutral-900 tabular-nums">{currentPage}</span> of <span class="tabular-nums">{totalPages}</span></span>
          <div class="flex items-center gap-1">
            <button
              type="button"
              onclick={() => gotoPage(1)}
              disabled={currentPage === 1}
              class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
            >First</button>
            <button
              type="button"
              onclick={() => gotoPage(currentPage - 1)}
              disabled={currentPage === 1}
              class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
            >Prev</button>
            {#each pageNumbers as p}
              <button
                type="button"
                onclick={() => gotoPage(p)}
                class="rounded-lg border px-2 py-1 font-semibold tabular-nums {p === currentPage ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300'}"
              >{p}</button>
            {/each}
            <button
              type="button"
              onclick={() => gotoPage(currentPage + 1)}
              disabled={currentPage === totalPages}
              class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
            >Next</button>
            <button
              type="button"
              onclick={() => gotoPage(totalPages)}
              disabled={currentPage === totalPages}
              class="rounded-lg border border-neutral-200 bg-white px-2 py-1 font-semibold text-neutral-700 hover:border-neutral-300 disabled:cursor-not-allowed disabled:opacity-40"
            >Last</button>
          </div>
        </div>
      {/if}
    {/if}
  </section>
</div>

<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse, RFQListItem, RFQQuote } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let loading = $state(true);
  let loadingComparison = $state(false);
  let selectingQuoteId = $state<number | null>(null);

  let rfqs = $state<RFQListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");

  let selectedRfq = $state<RFQListItem | null>(null);
  let selectionNotes = $state("");
  let rankedQuotes = $state<(RFQQuote & { rank: number })[]>([]);

  const PAGE_SIZE = 20;
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / PAGE_SIZE)));

  function pageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | "...")[] = [1];
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  function formatCurrency(value: string | number | null): string {
    if (value === null || value === undefined) return "—";
    const n = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(n)) return "—";
    return currency.format(n);
  }

  function formatDate(value: string | null): string {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function rankBadge(rank: number): string {
    if (rank === 1) return "bg-emerald-50 text-emerald-700";
    if (rank === 2) return "bg-blue-50 text-blue-700";
    if (rank === 3) return "bg-amber-50 text-amber-700";
    return "bg-neutral-100 text-neutral-600";
  }

  async function loadComparison(rfq: RFQListItem) {
    selectedRfq = rfq;
    loadingComparison = true;
    try {
      const res = await api.get<{ quotes: (RFQQuote & { rank: number })[] }>(
        `/procurement/rfqs/${rfq.id}/comparison/`
      );
      rankedQuotes = res.quotes;
    } catch {
      rankedQuotes = [];
      toast.error("Load failed", "Could not load tender comparison.");
    } finally {
      loadingComparison = false;
    }
  }

  async function loadRFQs() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(PAGE_SIZE),
        ordering: "-created_at",
      };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;

      const res = await api.get<PaginatedResponse<RFQListItem>>("/procurement/rfqs/", params);
      rfqs = res.results;
      totalCount = res.count;

      if (rfqs.length === 0) {
        selectedRfq = null;
        rankedQuotes = [];
        selectionNotes = "";
        return;
      }

      if (!selectedRfq) {
        selectionNotes = "";
        await loadComparison(rfqs[0]);
        return;
      }

      const inPage = rfqs.find((row) => row.id === selectedRfq?.id);
      if (inPage) {
        selectedRfq = inPage;
        return;
      }

      selectionNotes = "";
      await loadComparison(rfqs[0]);
    } catch {
      rfqs = [];
      totalCount = 0;
      selectedRfq = null;
      rankedQuotes = [];
      selectionNotes = "";
      toast.error("Load failed", "Could not load RFQs.");
    } finally {
      loading = false;
    }
  }

  async function selectWinner(quoteId: number) {
    if (!selectedRfq) return;
    selectingQuoteId = quoteId;
    try {
      await api.post(`/procurement/rfqs/${selectedRfq.id}/select-vendor/`, {
        quote_id: quoteId,
        selection_notes: selectionNotes,
      });
      toast.success("Vendor selected", "Vendor has been marked as winner.");
      const currentId = selectedRfq.id;
      await loadRFQs();
      const refreshed = rfqs.find((row) => row.id === currentId);
      if (refreshed) {
        selectedRfq = refreshed;
        await loadComparison(refreshed);
      }
    } catch {
      toast.error("Selection failed", "Could not set winning vendor.");
    } finally {
      selectingQuoteId = null;
    }
  }

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(event: Event) {
    clearTimeout(searchTimeout);
    const value = (event.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
      currentPage = 1;
    }, 300);
  }

  function openSelectedRfq() {
    if (!selectedRfq) return;
    goto(`/procurement/rfqs/${selectedRfq.id}`);
  }

  $effect(() => {
    void currentPage;
    void statusFilter;
    void searchQuery;
    loadRFQs();
  });
</script>

<div class="space-y-6">
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Vendor Selection</h1>
    <p class="mt-1 text-sm text-neutral-500">Evaluate quotes and assign winning vendors for RFQs.</p>
  </div>

  <div class="flex flex-wrap items-center gap-3">
    <div class="relative w-full max-w-sm">
      <svg
        class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        stroke-width="1.5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
        />
      </svg>
      <input
        type="text"
        placeholder="Search RFQs..."
        oninput={onSearchInput}
        class="w-full rounded-lg border border-neutral-200 bg-white py-2.5 pl-10 pr-4 text-sm
               placeholder:text-neutral-400 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
      />
    </div>

    <select
      bind:value={statusFilter}
      onchange={() => (currentPage = 1)}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700
             focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All statuses</option>
      <option value="draft">Draft</option>
      <option value="issued">Issued</option>
      <option value="evaluation">Evaluation</option>
      <option value="submitted">Submitted</option>
      <option value="approved">Approved</option>
      <option value="closed">Closed</option>
      <option value="cancelled">Cancelled</option>
    </select>
  </div>

  <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white xl:col-span-1">
      <div class="border-b border-neutral-100 px-4 py-3">
        <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">RFQs</h2>
      </div>
      {#if loading}
        <div class="p-8 text-center">
          <div class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
        </div>
      {:else if rfqs.length === 0}
        <div class="p-6 text-sm text-neutral-500">No RFQs found.</div>
      {:else}
        <div class="max-h-[640px] divide-y divide-neutral-100 overflow-auto">
          {#each rfqs as rfq}
            <button
              class={`w-full px-4 py-3 text-left transition-colors hover:bg-neutral-50 ${selectedRfq?.id === rfq.id ? "bg-neutral-50" : ""}`}
              onclick={() => {
                selectionNotes = "";
                loadComparison(rfq);
              }}
            >
              <p class="text-sm font-medium text-neutral-900">{rfq.rfq_number}</p>
              <p class="truncate text-xs text-neutral-500">{rfq.title}</p>
              <div class="mt-1 flex items-center justify-between text-xs text-neutral-500">
                <span>{rfq.quote_count} quote{rfq.quote_count === 1 ? "" : "s"}</span>
                <span>{formatCurrency(rfq.lowest_quote)}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white xl:col-span-2">
      <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
        <div>
          <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Quote Evaluation</h2>
          {#if selectedRfq}
            <p class="mt-1 text-sm font-medium text-neutral-900">{selectedRfq.rfq_number}</p>
            <p class="text-xs text-neutral-500">{selectedRfq.title}</p>
          {/if}
        </div>
        {#if selectedRfq}
          <button class="text-xs font-medium text-neutral-700 hover:text-neutral-900" onclick={openSelectedRfq}>
            Open RFQ
          </button>
        {/if}
      </div>

      {#if !selectedRfq}
        <div class="p-8 text-sm text-neutral-500">Select an RFQ to evaluate vendors.</div>
      {:else}
        <div class="grid grid-cols-1 gap-4 border-b border-neutral-100 bg-neutral-50/60 px-5 py-4 md:grid-cols-3">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Submission Deadline</p>
            <p class="mt-1 text-sm text-neutral-900">{formatDate(selectedRfq.submission_deadline)}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Current Winner</p>
            <p class="mt-1 text-sm text-neutral-900">{selectedRfq.selected_vendor_name || "Not selected"}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Lowest Quote</p>
            <p class="mt-1 text-sm text-neutral-900">{formatCurrency(selectedRfq.lowest_quote)}</p>
          </div>
        </div>

        <div class="border-b border-neutral-100 px-5 py-4">
          <label for="selection-notes" class="mb-1 block text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Selection Notes
          </label>
          <textarea
            id="selection-notes"
            rows={2}
            bind:value={selectionNotes}
            placeholder="Why this vendor is selected..."
            class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm
                   focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
          ></textarea>
        </div>

        {#if loadingComparison}
          <div class="p-10 text-center">
            <div class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
          </div>
        {:else if rankedQuotes.length === 0}
          <div class="p-8 text-sm text-neutral-500">No quotes submitted for this RFQ.</div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Rank</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
                <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Amount</th>
                <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Score</th>
                <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each rankedQuotes as quote}
                <tr>
                  <td class="px-5 py-3">
                    <span class={`inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold ${rankBadge(quote.rank)}`}>
                      #{quote.rank}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-neutral-900">{quote.vendor_name}</td>
                  <td class="px-5 py-3 text-right tabular-nums">{formatCurrency(quote.quoted_amount)}</td>
                  <td class="px-5 py-3 text-right tabular-nums">{Number(quote.total_score).toFixed(2)}</td>
                  <td class="px-5 py-3 text-right">
                    <button
                      class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:border-neutral-300 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={selectingQuoteId !== null}
                      onclick={() => selectWinner(quote.id)}
                    >
                      {selectingQuoteId === quote.id ? "Selecting..." : "Set Winner"}
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      {/if}
    </div>
  </div>

  {#if totalPages > 1}
    <div class="flex items-center justify-end gap-1">
      <button
        onclick={() => (currentPage = Math.max(1, currentPage - 1))}
        disabled={currentPage <= 1}
        class="h-9 w-9 rounded-lg border border-neutral-200 text-neutral-500 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
        aria-label="Previous page"
      >
        ‹
      </button>
      {#each pageNumbers(currentPage, totalPages) as pg}
        {#if pg === "..."}
          <span class="h-9 w-9 text-center leading-9 text-neutral-300">…</span>
        {:else}
          <button
            onclick={() => (currentPage = pg)}
            class={`h-9 w-9 rounded-lg text-sm font-medium transition-colors ${currentPage === pg ? "bg-neutral-900 text-white" : "text-neutral-600 hover:bg-neutral-100"}`}
          >
            {pg}
          </button>
        {/if}
      {/each}
      <button
        onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
        disabled={currentPage >= totalPages}
        class="h-9 w-9 rounded-lg border border-neutral-200 text-neutral-500 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
        aria-label="Next page"
      >
        ›
      </button>
    </div>
  {/if}
</div>

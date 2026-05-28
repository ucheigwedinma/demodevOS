<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { RFQListItem, RFQ, RFQQuote, PaginatedResponse } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let loading = $state(true);
  let loadingComparison = $state(false);
  let rfqs = $state<RFQListItem[]>([]);
  let selectedRfq = $state<RFQListItem | null>(null);
  let rankedQuotes = $state<(RFQQuote & { rank: number })[]>([]);

  function formatCurrency(value: string | number | null): string {
    if (value === null || value === undefined) return "—";
    const n = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(n)) return "—";
    return currency.format(n);
  }

  async function loadRFQs() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<RFQListItem>>("/procurement/rfqs/", {
        page_size: "200",
        ordering: "-created_at",
      });
      rfqs = res.results;
      if (rfqs.length > 0) {
        await loadComparison(rfqs[0]);
      }
    } catch {
      toast.error("Load failed", "Could not load RFQs.");
      rfqs = [];
    } finally {
      loading = false;
    }
  }

  async function loadComparison(rfq: RFQListItem) {
    selectedRfq = rfq;
    loadingComparison = true;
    try {
      const res = await api.get<{ quotes: (RFQQuote & { rank: number })[] }>(`/procurement/rfqs/${rfq.id}/comparison/`);
      rankedQuotes = res.quotes;
    } catch {
      rankedQuotes = [];
      toast.error("Load failed", "Could not load tender comparison.");
    } finally {
      loadingComparison = false;
    }
  }

  function rankBadge(rank: number): string {
    if (rank === 1) return "bg-emerald-50 text-emerald-700";
    if (rank === 2) return "bg-blue-50 text-blue-700";
    if (rank === 3) return "bg-amber-50 text-amber-700";
    return "bg-neutral-100 text-neutral-600";
  }

  $effect(() => {
    loadRFQs();
  });

  // ── RFQ Detail Drawer (view-only) ──
  let showRfqDetail = $state(false);
  let rfqDetail = $state<RFQ | null>(null);
  let rfqDetailLoading = $state(false);

  function formatDate(value: string | null): string {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function openRfqDetail(id: number) {
    showRfqDetail = true;
    rfqDetailLoading = true;
    try {
      rfqDetail = await api.get<RFQ>(`/procurement/rfqs/${id}/`);
    } catch {
      toast.error("Load failed", "Could not load RFQ details.");
      showRfqDetail = false;
    }
    rfqDetailLoading = false;
  }

  function closeRfqDetail() {
    showRfqDetail = false;
    rfqDetail = null;
  }
</script>

<div class="space-y-6">
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Tender Comparisons</h1>
    <p class="text-sm text-neutral-400 mt-1">Compare vendor bids, scores, and rankings for each RFQ.</p>
  </div>

  <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-4 py-3 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">RFQs</h2>
      </div>

      {#if loading}
        <div class="p-8 text-center">
          <div class="inline-block w-5 h-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if rfqs.length === 0}
        <div class="p-6 text-sm text-neutral-500">No RFQs available.</div>
      {:else}
        <div class="max-h-[620px] overflow-auto divide-y divide-neutral-100">
          {#each rfqs as rfq}
            <button
              class={`w-full text-left px-4 py-3 hover:bg-neutral-50 transition-colors ${selectedRfq?.id === rfq.id ? "bg-neutral-50" : ""}`}
              onclick={() => loadComparison(rfq)}
            >
              <p class="font-medium text-neutral-900 text-sm">{rfq.rfq_number}</p>
              <p class="text-xs text-neutral-500 truncate">{rfq.title}</p>
              <div class="mt-1 flex items-center justify-between text-xs text-neutral-500">
                <span>{rfq.quote_count} quote{rfq.quote_count !== 1 ? "s" : ""}</span>
                <span>{formatCurrency(rfq.lowest_quote)}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <div class="xl:col-span-2 bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <div>
          <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Comparison</h2>
          {#if selectedRfq}
            <p class="text-xs text-neutral-500 mt-1">{selectedRfq.rfq_number} - {selectedRfq.title}</p>
          {/if}
        </div>
        {#if selectedRfq}
          <button onclick={() => openRfqDetail(selectedRfq!.id)}
            class="px-3 py-1.5 border border-neutral-200 rounded-lg text-xs font-medium text-neutral-700 hover:bg-neutral-50 flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /></svg>
            View RFQ
          </button>
        {/if}
      </div>

      {#if loadingComparison}
        <div class="p-12 text-center">
          <div class="inline-block w-5 h-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
        </div>
      {:else if !selectedRfq}
        <div class="p-8 text-sm text-neutral-500">Select an RFQ to view comparison.</div>
      {:else if rankedQuotes.length === 0}
        <div class="p-8 text-sm text-neutral-500">No quotes submitted for this RFQ.</div>
      {:else}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-50">
              <th class="px-5 py-3 text-left text-xs uppercase tracking-wider text-neutral-500 font-semibold">Rank</th>
              <th class="px-5 py-3 text-left text-xs uppercase tracking-wider text-neutral-500 font-semibold">Vendor</th>
              <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Amount</th>
              <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Tech</th>
              <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Comm</th>
              <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Compliance</th>
              <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Total</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rankedQuotes as quote}
              <tr>
                <td class="px-5 py-3">
                  <span class={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${rankBadge(quote.rank)}`}>#{quote.rank}</span>
                </td>
                <td class="px-5 py-3 text-neutral-900">{quote.vendor_name}</td>
                <td class="px-5 py-3 text-right tabular-nums">{formatCurrency(quote.quoted_amount)}</td>
                <td class="px-5 py-3 text-right tabular-nums">{Number(quote.technical_score).toFixed(2)}</td>
                <td class="px-5 py-3 text-right tabular-nums">{Number(quote.commercial_score).toFixed(2)}</td>
                <td class="px-5 py-3 text-right tabular-nums">{Number(quote.compliance_score).toFixed(2)}</td>
                <td class="px-5 py-3 text-right tabular-nums font-medium text-neutral-900">{Number(quote.total_score).toFixed(2)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
</div>

<!-- Read-only RFQ Detail Drawer -->
<DrawerShell open={showRfqDetail} onclose={closeRfqDetail} title={rfqDetail?.rfq_number ?? "RFQ"} subtitle={rfqDetail?.title ?? ""} width="max-w-xl">
  {#snippet badges()}
    {#if rfqDetail}
      <StatusBadge status={rfqDetail.status} />
      {#if rfqDetail.selected_vendor_name}
        <span class="inline-flex items-center rounded-full bg-emerald-900/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">Awarded</span>
      {/if}
    {/if}
  {/snippet}

  {#if rfqDetailLoading}
    <div class="flex items-center justify-center py-24">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if rfqDetail}
    <!-- Summary strip -->
    <div class="px-6 py-4 border-b border-neutral-100 bg-neutral-50/50">
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div>
          <p class="text-neutral-400 text-xs">Issue Date</p>
          <p class="font-semibold text-neutral-900">{formatDate(rfqDetail.issue_date)}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Deadline</p>
          <p class="font-semibold text-neutral-900">{formatDate(rfqDetail.submission_deadline)}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Quotes</p>
          <p class="font-semibold text-neutral-900">{rfqDetail.quotes?.length ?? rfqDetail.quote_count}</p>
        </div>
      </div>
    </div>

    <!-- Details -->
    <div class="p-6 space-y-4">
      <div class="grid grid-cols-2 gap-x-6 gap-y-4">
        <div class="col-span-2">
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Title</p>
          <p class="text-sm text-neutral-900">{rfqDetail.title || "—"}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Requisition</p>
          <p class="text-sm text-neutral-900">{rfqDetail.requisition_number || "—"}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Project</p>
          <p class="text-sm text-neutral-900">{rfqDetail.project_name || "—"}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Property</p>
          <p class="text-sm text-neutral-900">{rfqDetail.property_name || "—"}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Budget Code</p>
          <p class="text-sm text-neutral-900">{rfqDetail.budget_code || "—"}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Cost Code</p>
          <p class="text-sm text-neutral-900">{rfqDetail.cost_code || "—"}</p>
        </div>
        <div>
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Estimated Value</p>
          <p class="text-sm text-neutral-900 tabular-nums">{formatCurrency(rfqDetail.estimated_value)}</p>
        </div>
        {#if rfqDetail.selected_vendor_name}
          <div class="col-span-2">
            <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Selected Vendor</p>
            <p class="text-sm text-emerald-700 font-semibold">{rfqDetail.selected_vendor_name}</p>
          </div>
        {/if}
      </div>

      {#if rfqDetail.selection_notes}
        <div class="border-t border-neutral-100 pt-4">
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Selection Notes</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{rfqDetail.selection_notes}</p>
        </div>
      {/if}

      {#if rfqDetail.notes}
        <div class="border-t border-neutral-100 pt-4">
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Notes</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{rfqDetail.notes}</p>
        </div>
      {/if}

      <!-- Quotes summary -->
      {#if rfqDetail.quotes && rfqDetail.quotes.length > 0}
        <div class="border-t border-neutral-100 pt-4">
          <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-3">Vendor Quotes</p>
          <div class="rounded-xl border border-neutral-200 overflow-hidden">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200 bg-neutral-50">
                  <th class="px-4 py-2 text-left text-xs font-medium text-neutral-400 uppercase">Vendor</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-neutral-400 uppercase">Amount</th>
                  <th class="px-4 py-2 text-right text-xs font-medium text-neutral-400 uppercase">Score</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-neutral-400 uppercase">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each rfqDetail.quotes as quote}
                  <tr class="{quote.status === 'winner' ? 'bg-emerald-50/50' : ''}">
                    <td class="px-4 py-2.5 text-neutral-900">{quote.vendor_name}</td>
                    <td class="px-4 py-2.5 text-right tabular-nums">{formatCurrency(quote.quoted_amount)}</td>
                    <td class="px-4 py-2.5 text-right tabular-nums">{Number(quote.total_score).toFixed(1)}</td>
                    <td class="px-4 py-2.5 text-center"><StatusBadge status={quote.status} /></td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</DrawerShell>

<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { GoodsReceiptListItem, PaginatedResponse } from "$lib/types";

  let data = $state<GoodsReceiptListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let loading = $state(true);

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

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

  function formatDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  async function fetchGoodsReceipts() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;

      const res = await api.get<PaginatedResponse<GoodsReceiptListItem>>("/procurement/goods-receipts/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => {
    void searchQuery;
    void statusFilter;
    void currentPage;
    fetchGoodsReceipts();
  });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
      currentPage = 1;
    }, 300);
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Goods Receipts</h1>
      <p class="text-sm text-neutral-400 mt-1">Delivery tracking</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input
        type="text"
        placeholder="Search goods receipts..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={statusFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Statuses</option>
      <option value="pending">Pending</option>
      <option value="inspected">Inspected</option>
      <option value="accepted">Accepted</option>
      <option value="partially_accepted">Partial</option>
      <option value="rejected">Rejected</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading goods receipts...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-900">No goods receipts found</p>
        <p class="mt-1 text-sm text-neutral-400">Goods receipts are created from purchase order details.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">GRN #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">PO #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Received Date</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Received By</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as grn}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => goto(`/procurement/goods-receipts/${grn.id}`)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-900">{grn.grn_number}</span>
              </td>
              <td class="px-5 py-4 text-neutral-500">{grn.po_number}</td>
              <td class="px-5 py-4 text-neutral-500">{grn.vendor_name}</td>
              <td class="px-5 py-4">
                <StatusBadge status={grn.status} label={grn.status === "partially_accepted" ? "Partial" : undefined} />
              </td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(grn.received_date)}</td>
              <td class="px-5 py-4 text-neutral-500">{grn.received_by || "\u2014"}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <!-- Pagination -->
  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">
        Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "receipt" : "receipts"}
      </p>

      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button
            onclick={() => currentPage--}
            disabled={currentPage <= 1}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>

          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300">...</span>
            {:else}
              <button
                onclick={() => (currentPage = pg)}
                class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors
                       {currentPage === pg
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100'}"
              >
                {pg}
              </button>
            {/if}
          {/each}

          <button
            onclick={() => currentPage++}
            disabled={currentPage >= totalPages}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

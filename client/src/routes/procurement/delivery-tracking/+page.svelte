<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaginatedResponse,
    ProcurementOverview,
    PurchaseOrderListItem,
    VendorListItem,
  } from "$lib/types";

  let loading = $state(true);
  let orders = $state<PurchaseOrderListItem[]>([]);
  let overview = $state<ProcurementOverview | null>(null);
  let vendors = $state<VendorListItem[]>([]);

  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let vendorFilter = $state("");

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / PAGE_SIZE)));
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

  function formatCurrency(value: string | number | null): string {
    if (value === null || value === undefined || value === "") return "—";
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

  function daysUntil(dateValue: string): number {
    const target = new Date(`${dateValue}T00:00:00`);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const diffMs = target.getTime() - today.getTime();
    return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  }

  function deliveryHealth(po: PurchaseOrderListItem): { label: string; tone: string } {
    if (po.status === "received") {
      return { label: "Delivered", tone: "bg-emerald-50 text-emerald-700" };
    }
    if (!po.expected_delivery_date) {
      return { label: "No ETA", tone: "bg-neutral-100 text-neutral-600" };
    }
    const days = daysUntil(po.expected_delivery_date);
    if (days < 0) {
      return { label: `Overdue ${Math.abs(days)}d`, tone: "bg-red-50 text-red-700" };
    }
    if (days <= 7) {
      return { label: `Due in ${days}d`, tone: "bg-amber-50 text-amber-700" };
    }
    return { label: `On track (${days}d)`, tone: "bg-blue-50 text-blue-700" };
  }


  const overdueCount = $derived(
    orders.filter((po) => {
      const health = deliveryHealth(po);
      return health.label.startsWith("Overdue");
    }).length
  );

  async function fetchOverview() {
    try {
      overview = await api.get<ProcurementOverview>("/procurement/overview/");
    } catch {
      overview = null;
    }
  }

  async function fetchVendors() {
    try {
      const res = await api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", {
        page_size: "200",
        ordering: "name",
      });
      vendors = res.results;
    } catch {
      vendors = [];
    }
  }

  async function fetchOrders() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(PAGE_SIZE),
        ordering: "-expected_delivery_date",
      };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const res = await api.get<PaginatedResponse<PurchaseOrderListItem>>(
        "/procurement/purchase-orders/",
        params
      );
      orders = res.results;
      totalCount = res.count;
    } catch {
      orders = [];
      totalCount = 0;
    } finally {
      loading = false;
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

  $effect(() => {
    fetchVendors();
    fetchOverview();
  });

  $effect(() => {
    void currentPage;
    void searchQuery;
    void statusFilter;
    void vendorFilter;
    fetchOrders();
  });
</script>

<div class="space-y-6">
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Delivery Tracking</h1>
    <p class="mt-1 text-sm text-neutral-500">Track purchase order fulfillment and inbound delivery risks.</p>
  </div>

  <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Pending Deliveries</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{overview?.pending_delivery_count ?? 0}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Active POs</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{overview?.active_po_count ?? 0}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Overdue (Page)</p>
      <p class="mt-1 text-xl font-bold text-red-600 tabular-nums">{overdueCount}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Active PO Value</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{formatCurrency(overview?.active_po_value ?? null)}</p>
    </div>
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
        placeholder="Search PO #, vendor, notes..."
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
      <option value="">All PO statuses</option>
      <option value="draft">Draft</option>
      <option value="approved">Approved</option>
      <option value="issued">Issued</option>
      <option value="partially_received">Partially Received</option>
      <option value="received">Received</option>
      <option value="cancelled">Cancelled</option>
    </select>

    <select
      bind:value={vendorFilter}
      onchange={() => (currentPage = 1)}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700
             focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All vendors</option>
      {#each vendors as vendor}
        <option value={String(vendor.id)}>{vendor.name}</option>
      {/each}
    </select>
  </div>

  <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
        <p class="mt-3 text-sm text-neutral-500">Loading delivery data...</p>
      </div>
    {:else if orders.length === 0}
      <div class="p-16 text-center">
        <p class="text-sm font-medium text-neutral-900">No purchase orders found</p>
        <p class="mt-1 text-sm text-neutral-500">Adjust filters or create purchase orders to start tracking deliveries.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">PO</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project / Property</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Issue Date</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Expected Delivery</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Delivery Health</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">PO Status</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Value</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each orders as po}
            {@const health = deliveryHealth(po)}
            <tr
              class="cursor-pointer transition-colors hover:bg-neutral-50"
              onclick={() => goto(`/procurement/purchase-orders/${po.id}`)}
            >
              <td class="px-5 py-4">
                <p class="font-medium text-neutral-900">{po.po_number}</p>
                <p class="text-xs text-neutral-500">{po.item_count} line item{po.item_count === 1 ? "" : "s"}</p>
              </td>
              <td class="px-5 py-4 text-neutral-700">{po.vendor_name}</td>
              <td class="px-5 py-4 text-neutral-600">{po.project_name || po.property_name || "—"}</td>
              <td class="px-5 py-4 text-neutral-600">{formatDate(po.issue_date)}</td>
              <td class="px-5 py-4 text-neutral-600">{formatDate(po.expected_delivery_date)}</td>
              <td class="px-5 py-4">
                <span class={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${health.tone}`}>
                  {health.label}
                </span>
              </td>
              <td class="px-5 py-4">
                <StatusBadge status={po.status} />
              </td>
              <td class="px-5 py-4 text-right font-medium tabular-nums text-neutral-900">{formatCurrency(po.total_amount)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">
        Showing <span class="font-medium text-neutral-700">{startItem}–{endItem}</span> of
        <span class="font-medium text-neutral-700">{totalCount}</span>
      </p>

      {#if totalPages > 1}
        <div class="flex items-center gap-1">
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
  {/if}
</div>

<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import type { ProcurementOverview, PRStatus, PRPriority, POStatus } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";

  let data = $state<ProcurementOverview | null>(null);
  let loading = $state(true);

  async function fetchOverview() {
    loading = true;
    try {
      data = await api.get<ProcurementOverview>("/procurement/overview/");
    } catch {
      data = null;
    }
    loading = false;
  }

  $effect(() => {
    fetchOverview();
  });

  const live = useLiveKpis(
    ["PurchaseRequisition", "PurchaseOrder", "RFQ", "GoodsReceipt", "Vendor", "Contract"],
    fetchOverview,
    { debounceMs: 3000 },
  );

  function fmtCurrency(value: string | number): string {
    const n = typeof value === "string" ? Number(value) : value;
    return currency.format(n);
  }

  function fmtDate(dateStr: string): string {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  const prStatusColors: Record<PRStatus, string> = {
    draft: "bg-neutral-100 text-neutral-600",
    submitted: "bg-blue-50 text-blue-700",
    approved: "bg-emerald-50 text-emerald-700",
    rejected: "bg-red-50 text-red-700",
    cancelled: "bg-neutral-100 text-neutral-400",
    ordered: "bg-violet-50 text-violet-700",
  };

  const prStatusLabels: Record<PRStatus, string> = {
    draft: "Draft",
    submitted: "Submitted",
    approved: "Approved",
    rejected: "Rejected",
    cancelled: "Cancelled",
    ordered: "Ordered",
  };

  const prPriorityColors: Record<PRPriority, string> = {
    low: "bg-neutral-100 text-neutral-600",
    medium: "bg-blue-50 text-blue-700",
    high: "bg-amber-50 text-amber-700",
    urgent: "bg-red-50 text-red-700",
  };

  const prPriorityLabels: Record<PRPriority, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  const poStatusColors: Record<POStatus, string> = {
    draft: "bg-neutral-100 text-neutral-600",
    approved: "bg-blue-50 text-blue-700",
    issued: "bg-violet-50 text-violet-700",
    partially_received: "bg-amber-50 text-amber-700",
    received: "bg-emerald-50 text-emerald-700",
    cancelled: "bg-neutral-100 text-neutral-400",
  };

  const poStatusLabels: Record<POStatus, string> = {
    draft: "Draft",
    approved: "Approved",
    issued: "Issued",
    partially_received: "Partial",
    received: "Received",
    cancelled: "Cancelled",
  };
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if data}
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <div class="flex items-center gap-2">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
        <LiveBadge refreshing={live.refreshing} />
      </div>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Dashboard</h1>
      <p class="text-sm text-neutral-400 mt-1">Purchase requests, RFQs, vendor selection, orders, and delivery control</p>
    </div>

    <!-- KPI Strip -->
    <div class="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-3">
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Open PRs</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{data.open_requisitions_count}</p>
        <p class="text-[10px] text-neutral-400">{fmtCurrency(data.open_requisitions_value)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Pending Approval</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{data.pending_approval_count}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Active POs</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{data.active_po_count}</p>
        <p class="text-[10px] text-neutral-400">{fmtCurrency(data.active_po_value)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Awaiting Delivery</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{data.pending_delivery_count}</p>
      </div>
      <div class="rounded-xl border {(data.delayed_delivery_count ?? 0) > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} px-4 py-3.5">
        <p class="text-[9px] font-semibold {(data.delayed_delivery_count ?? 0) > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Delayed</p>
        <p class="mt-1 text-xl font-bold {(data.delayed_delivery_count ?? 0) > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{data.delayed_delivery_count ?? 0}</p>
        <p class="text-[10px] {(data.delayed_delivery_count ?? 0) > 0 ? 'text-red-400' : 'text-neutral-400'}">overdue deliveries</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Open RFQs</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{data.rfq_open_count ?? 0}</p>
      </div>
      <div class="rounded-xl border {(data.vendor_alerts ?? []).length > 0 ? 'border-amber-200 bg-amber-50' : 'border-neutral-200 bg-white'} px-4 py-3.5">
        <p class="text-[9px] font-semibold {(data.vendor_alerts ?? []).length > 0 ? 'text-amber-400' : 'text-neutral-400'} uppercase tracking-wider">Vendor Alerts</p>
        <p class="mt-1 text-xl font-bold {(data.vendor_alerts ?? []).length > 0 ? 'text-amber-700' : 'text-neutral-900'} tabular-nums">{(data.vendor_alerts ?? []).length}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">RFQs Submitted</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{data.rfq_submitted_count ?? 0}</p>
      </div>
    </div>

    <!-- Status Distributions -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- PR Status -->
      <div class="bg-white rounded-xl border border-neutral-200 px-5 py-4">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">Requisitions by Status</h3>
        <div class="flex flex-wrap gap-2">
          {#each data.prs_by_status as sc}
            {#if sc.count > 0}
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium {prStatusColors[sc.status as PRStatus] ?? 'bg-neutral-100 text-neutral-600'}">
                {sc.count} {prStatusLabels[sc.status as PRStatus] ?? sc.status}
              </span>
            {/if}
          {/each}
          {#if data.prs_by_status.every(sc => sc.count === 0)}
            <span class="text-xs text-neutral-400">No requisitions yet</span>
          {/if}
        </div>
      </div>

      <!-- PO Status -->
      <div class="bg-white rounded-xl border border-neutral-200 px-5 py-4">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">Purchase Orders by Status</h3>
        <div class="flex flex-wrap gap-2">
          {#each data.pos_by_status as sc}
            {#if sc.count > 0}
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium {poStatusColors[sc.status as POStatus] ?? 'bg-neutral-100 text-neutral-600'}">
                {sc.count} {poStatusLabels[sc.status as POStatus] ?? sc.status}
              </span>
            {/if}
          {/each}
          {#if data.pos_by_status.every(sc => sc.count === 0)}
            <span class="text-xs text-neutral-400">No purchase orders yet</span>
          {/if}
        </div>
      </div>
    </div>

    <!-- Delayed Deliveries -->
    {#if (data.delayed_deliveries ?? []).length > 0}
      <section class="rounded-xl border border-red-200 bg-white overflow-hidden">
        <div class="border-b border-red-100 bg-red-50 px-5 py-3 flex items-center justify-between">
          <h3 class="text-[10px] font-semibold text-red-500 uppercase tracking-widest">Delayed Deliveries ({data.delayed_delivery_count})</h3>
          <a href="/procurement/delivery-tracking" class="text-[10px] font-medium text-red-600 hover:text-red-800 no-underline">View All</a>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-4 py-2 text-left text-[10px] font-semibold text-neutral-500 uppercase">PO #</th>
                <th class="px-4 py-2 text-left text-[10px] font-semibold text-neutral-500 uppercase">Vendor</th>
                <th class="px-4 py-2 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
                <th class="px-4 py-2 text-center text-[10px] font-semibold text-neutral-500 uppercase">Expected</th>
                <th class="px-4 py-2 text-center text-[10px] font-semibold text-red-400 uppercase">Overdue</th>
                <th class="px-4 py-2 text-right text-[10px] font-semibold text-neutral-500 uppercase">Amount</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.delayed_deliveries as d}
                <tr class="hover:bg-red-50/50">
                  <td class="px-4 py-2.5 font-medium text-neutral-900">{d.po_number}</td>
                  <td class="px-4 py-2.5 text-neutral-700">{d.vendor_name}</td>
                  <td class="px-4 py-2.5 text-neutral-600">{d.project_name}</td>
                  <td class="px-4 py-2.5 text-center text-neutral-500 tabular-nums">{d.expected_date}</td>
                  <td class="px-4 py-2.5 text-center">
                    <span class="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-[10px] font-bold tabular-nums">{d.days_overdue}d late</span>
                  </td>
                  <td class="px-4 py-2.5 text-right font-semibold text-neutral-900 tabular-nums">{fmtCurrency(d.total_amount)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    <!-- Vendor Performance Alerts + Budget Consumption -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Vendor Alerts -->
      <section class="rounded-xl border {(data.vendor_alerts ?? []).length > 0 ? 'border-amber-200' : 'border-neutral-200'} bg-white overflow-hidden">
        <div class="border-b {(data.vendor_alerts ?? []).length > 0 ? 'border-amber-100 bg-amber-50' : 'border-neutral-100 bg-neutral-50'} px-5 py-3">
          <h3 class="text-[10px] font-semibold {(data.vendor_alerts ?? []).length > 0 ? 'text-amber-500' : 'text-neutral-400'} uppercase tracking-widest">Vendor Performance Alerts</h3>
        </div>
        {#if (data.vendor_alerts ?? []).length === 0}
          <div class="p-6 text-center">
            <p class="text-sm text-emerald-600 font-medium">All vendors performing well</p>
            <p class="text-[10px] text-neutral-400 mt-1">No low-rated or blacklisted vendors</p>
          </div>
        {:else}
          <div class="divide-y divide-neutral-50">
            {#each data.vendor_alerts as alert}
              <div class="flex items-start gap-3 px-5 py-3">
                <span class="mt-1 inline-block h-2 w-2 rounded-full shrink-0 {alert.severity === 'critical' ? 'bg-red-500' : 'bg-amber-500'}"></span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-900">{alert.vendor_name}</p>
                  <p class="text-[10px] text-neutral-500 mt-0.5">{alert.message}</p>
                </div>
                <span class="rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase {alert.type === 'blacklisted' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}">{alert.type === 'blacklisted' ? 'Blacklisted' : 'Low Rating'}</span>
              </div>
            {/each}
          </div>
        {/if}
      </section>

      <!-- Budget Consumption by Project -->
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Budget Consumption by Project</h3>
        </div>
        {#if (data.budget_consumption ?? []).length === 0}
          <div class="p-6 text-center">
            <p class="text-sm text-neutral-500">No project spend data yet</p>
          </div>
        {:else}
          <div class="divide-y divide-neutral-50 px-5 py-2">
            {#each data.budget_consumption as bc}
              <div class="py-3">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-sm font-medium text-neutral-900 truncate">{bc.project_name}</span>
                  <span class="text-[10px] font-semibold tabular-nums {bc.status === 'critical' ? 'text-red-700' : bc.status === 'warning' ? 'text-amber-700' : 'text-emerald-700'}">{bc.consumption_pct}%</span>
                </div>
                <div class="h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                  <div class="h-full rounded-full transition-all {bc.status === 'critical' ? 'bg-red-500' : bc.status === 'warning' ? 'bg-amber-500' : 'bg-emerald-500'}" style="width: {Math.min(100, bc.consumption_pct)}%"></div>
                </div>
                <div class="flex items-center justify-between mt-1">
                  <span class="text-[10px] text-neutral-400">{fmtCurrency(bc.committed)} of {fmtCurrency(bc.budget)}</span>
                  <span class="text-[10px] text-neutral-400">{bc.po_count} POs</span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    </div>

    <!-- Quick Actions -->
    <div>
      <div class="flex items-center gap-3 mb-4">
        <div class="h-px flex-1 bg-neutral-200"></div>
        <h2 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Quick Actions</h2>
        <div class="h-px flex-1 bg-neutral-200"></div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7 gap-4">
        <!-- Requisitions Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">Purchase Requests</h3>
            <p class="mt-1 text-sm text-neutral-400">Create and track request intake against budget lines and cost codes</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/requisitions" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              View all &rarr;
            </a>
            <a href="/procurement/requisitions/new" class="px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-xs font-medium hover:bg-neutral-800 transition-colors">
              + New PR
            </a>
          </div>
        </div>

        <!-- Purchase Orders Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-violet-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-violet-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">Purchase Orders</h3>
            <p class="mt-1 text-sm text-neutral-400">Manage purchase orders issued to vendors</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/purchase-orders" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              View all &rarr;
            </a>
            <a href="/procurement/purchase-orders/new" class="px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-xs font-medium hover:bg-neutral-800 transition-colors">
              + New PO
            </a>
          </div>
        </div>

        <!-- Goods Receipts Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.25 18.75a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 0 1-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m3 0h1.125c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H18.75m-7.5-3v6.75m0 0H9m2.25 0h1.5m0-6.75H6.375c-.621 0-1.125.504-1.125 1.125v3.5" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">Goods Received Notes</h3>
            <p class="mt-1 text-sm text-neutral-400">Inspect deliveries and register accepted or rejected quantities</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/goods-receipts" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              View all &rarr;
            </a>
          </div>
        </div>

        <!-- RFQs Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-cyan-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 4.5h16.5v15H3.75v-15Zm3 3h5.25m-5.25 3.75h10.5m-10.5 3.75h7.5" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">RFQs</h3>
            <p class="mt-1 text-sm text-neutral-400">Issue requests for quotation and manage vendor bids</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/rfqs" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              View all &rarr;
            </a>
          </div>
        </div>

        <!-- Tender Comparisons Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 18V6m5.25 12V9m5.25 9v-6m5.25 6V4.5" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">Tender Comparisons</h3>
            <p class="mt-1 text-sm text-neutral-400">Rank and compare vendor quotes with scoring analytics</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/tender-comparisons" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              Open &rarr;
            </a>
          </div>
        </div>

        <!-- Vendor Selection Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-teal-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-teal-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5m-16.5 4.5h10.5m-10.5 4.5h7.5m8.25-7.5 2.25 2.25 3.75-4.5" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">Vendor Selection</h3>
            <p class="mt-1 text-sm text-neutral-400">Evaluate scored bids and assign winning vendors by RFQ</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/vendor-selection" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              Open &rarr;
            </a>
          </div>
        </div>

        <!-- Delivery Tracking Card -->
        <div class="group bg-white rounded-xl border border-neutral-200 overflow-hidden hover:shadow-lg hover:border-neutral-300 transition-all">
          <div class="p-6">
            <div class="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center">
              <svg class="w-5 h-5 text-rose-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 3v18h18M6.75 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5Z" />
              </svg>
            </div>
            <h3 class="mt-4 text-lg font-semibold text-neutral-900">Delivery Tracking</h3>
            <p class="mt-1 text-sm text-neutral-400">Monitor ETA, overdue orders, and fulfillment progress</p>
          </div>
          <div class="px-6 py-3 bg-neutral-50 border-t border-neutral-100 flex items-center justify-between">
            <a href="/procurement/delivery-tracking" class="text-sm font-medium text-neutral-900 hover:text-neutral-700 transition-colors">
              Open &rarr;
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Recent Purchase Requests -->
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Recent Purchase Requests</h3>
          <a href="/procurement/requisitions" class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">View all &rarr;</a>
        </div>
        {#if data.recent_requisitions.length > 0}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">PR #</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Title</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-2.5 text-right text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Est. Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.recent_requisitions as pr}
                <tr
                  class="hover:bg-neutral-50 cursor-pointer transition-colors"
                  onclick={() => goto(`/procurement/requisitions/${pr.id}`)}
                >
                  <td class="px-5 py-3 text-xs font-medium text-neutral-900">{pr.pr_number}</td>
                  <td class="px-5 py-3 text-xs text-neutral-500 truncate max-w-[200px]">{pr.title}</td>
                  <td class="px-5 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium {prStatusColors[pr.status] ?? 'bg-neutral-100 text-neutral-600'}">
                      {prStatusLabels[pr.status] ?? pr.status}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-right text-xs text-neutral-500 tabular-nums">{fmtCurrency(pr.estimated_total)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <div class="px-5 py-8 text-center">
            <p class="text-sm text-neutral-400">No recent requisitions</p>
          </div>
        {/if}
      </div>

      <!-- Recent Purchase Orders -->
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Recent Purchase Orders</h3>
          <a href="/procurement/purchase-orders" class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">View all &rarr;</a>
        </div>
        {#if data.recent_purchase_orders.length > 0}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">PO #</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Vendor</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-2.5 text-right text-[10px] font-medium text-neutral-400 uppercase tracking-wider">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each data.recent_purchase_orders as po}
                <tr
                  class="hover:bg-neutral-50 cursor-pointer transition-colors"
                  onclick={() => goto(`/procurement/purchase-orders/${po.id}`)}
                >
                  <td class="px-5 py-3 text-xs font-medium text-neutral-900">{po.po_number}</td>
                  <td class="px-5 py-3 text-xs text-neutral-500">{po.vendor_name}</td>
                  <td class="px-5 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium {poStatusColors[po.status] ?? 'bg-neutral-100 text-neutral-600'}">
                      {poStatusLabels[po.status] ?? po.status}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-right text-xs text-neutral-500 tabular-nums">{fmtCurrency(po.total_amount)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <div class="px-5 py-8 text-center">
            <p class="text-sm text-neutral-400">No recent purchase orders</p>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

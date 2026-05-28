<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import type { InventoryOverview } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";

  let overview = $state<InventoryOverview | null>(null);
  let loading = $state(true);

  async function fetchOverview() {
    loading = true;
    try {
      overview = await api.get<InventoryOverview>("/inventory/overview/");
    } catch {
      overview = null;
    } finally {
      loading = false;
    }
  }

  function fmtCurrency(value: string): string {
    const n = Number(value || 0);
    return currency.format(n);
  }

  function fmtQty(value: string): string {
    const n = Number(value || 0);
    return n.toLocaleString("en-US", { maximumFractionDigits: 3 });
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  const typeBadge: Record<string, string> = {
    receipt: "bg-emerald-50 text-emerald-700 border-emerald-100",
    issue: "bg-amber-50 text-amber-700 border-amber-100",
    adjustment_in: "bg-blue-50 text-blue-700 border-blue-100",
    adjustment_out: "bg-orange-50 text-orange-700 border-orange-100",
    transfer_in: "bg-indigo-50 text-indigo-700 border-indigo-100",
    transfer_out: "bg-violet-50 text-violet-700 border-violet-100",
  };

  $effect(() => {
    fetchOverview();
  });

  const live = useLiveKpis(
    ["InventoryItem", "InventoryStock", "MaterialRequisition", "MaterialTransfer"],
    fetchOverview,
    { debounceMs: 3000 },
  );
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if overview}
  <div class="space-y-8">
    <div>
      <div class="flex items-center gap-2">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Supply Chain</p>
        <LiveBadge refreshing={live.refreshing} />
      </div>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Inventory</h1>
      <p class="text-sm text-neutral-400 mt-1">
        Procurement-linked stock control with project consumption and budget visibility.
      </p>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-6 gap-4">
      <div class="bg-white rounded-xl border border-cyan-200 px-4 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-700">Stock Value</p>
        <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtCurrency(overview.stock_value_total)}</p>
      </div>
      <div class="bg-white rounded-xl border border-rose-200 px-4 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Low Stock</p>
        <p class="mt-1 text-lg font-semibold text-neutral-900">{overview.low_stock_count}</p>
      </div>
      <div class="bg-white rounded-xl border border-emerald-200 px-4 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Receipts 30d</p>
        <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtCurrency(overview.receipts_30d_value)}</p>
      </div>
      <div class="bg-white rounded-xl border border-amber-200 px-4 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Issues 30d</p>
        <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtCurrency(overview.issues_30d_value)}</p>
      </div>
      <div class="bg-white rounded-xl border border-blue-200 px-4 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Budget-Covered</p>
        <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtCurrency(overview.budget_covered_issue_value)}</p>
      </div>
      <div class="bg-white rounded-xl border border-orange-200 px-4 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-700">Unbudgeted</p>
        <p class="mt-1 text-lg font-semibold text-neutral-900">{fmtCurrency(overview.unbudgeted_issue_value)}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Low Stock Alerts</h2>
          <a href="/inventory/stock" class="text-xs text-neutral-400 hover:text-neutral-700">View stock</a>
        </div>
        {#if overview.low_stock_items.length > 0}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2 text-left text-[10px] uppercase tracking-wider text-neutral-400">Item</th>
                <th class="px-5 py-2 text-left text-[10px] uppercase tracking-wider text-neutral-400">Warehouse</th>
                <th class="px-5 py-2 text-right text-[10px] uppercase tracking-wider text-neutral-400">On Hand</th>
                <th class="px-5 py-2 text-right text-[10px] uppercase tracking-wider text-neutral-400">Reorder</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each overview.low_stock_items as row}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => goto("/inventory/stock") }>
                  <td class="px-5 py-3">
                    <p class="text-xs font-medium text-neutral-900">{row.item_name}</p>
                    <p class="text-[11px] text-neutral-400">{row.item_sku}</p>
                  </td>
                  <td class="px-5 py-3 text-xs text-neutral-500">{row.warehouse_name}</td>
                  <td class="px-5 py-3 text-xs text-right text-rose-700 font-medium">{fmtQty(row.quantity_on_hand)}</td>
                  <td class="px-5 py-3 text-xs text-right text-neutral-500">{fmtQty(row.reorder_level)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <div class="px-5 py-10 text-sm text-neutral-400 text-center">No low stock alerts</div>
        {/if}
      </section>

      <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Recent Movements</h2>
          <a href="/inventory/movements" class="text-xs text-neutral-400 hover:text-neutral-700">View all</a>
        </div>
        {#if overview.recent_transactions.length > 0}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2 text-left text-[10px] uppercase tracking-wider text-neutral-400">Date</th>
                <th class="px-5 py-2 text-left text-[10px] uppercase tracking-wider text-neutral-400">Type</th>
                <th class="px-5 py-2 text-left text-[10px] uppercase tracking-wider text-neutral-400">Item</th>
                <th class="px-5 py-2 text-right text-[10px] uppercase tracking-wider text-neutral-400">Cost</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each overview.recent_transactions as tx}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => goto("/inventory/movements") }>
                  <td class="px-5 py-3 text-xs text-neutral-500">{fmtDate(tx.transaction_date)}</td>
                  <td class="px-5 py-3">
                    <span class={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] font-medium ${typeBadge[tx.transaction_type] ?? "bg-neutral-50 text-neutral-700 border-neutral-100"}`}>
                      {tx.transaction_type_display}
                    </span>
                  </td>
                  <td class="px-5 py-3">
                    <p class="text-xs text-neutral-900">{tx.item_name}</p>
                    <p class="text-[11px] text-neutral-400">{tx.warehouse_name}</p>
                  </td>
                  <td class="px-5 py-3 text-xs text-right text-neutral-700">{fmtCurrency(tx.total_cost)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {:else}
          <div class="px-5 py-10 text-sm text-neutral-400 text-center">No movements logged</div>
        {/if}
      </section>
    </div>

    <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Project Consumption (Last 30 Days)</h2>
        <a href="/projects/budget-cost" class="text-xs text-neutral-400 hover:text-neutral-700">Budget & Cost</a>
      </div>
      {#if overview.project_consumption_30d.length > 0}
        <div class="divide-y divide-neutral-100">
          {#each overview.project_consumption_30d as row}
            <div class="px-5 py-3 flex items-center justify-between gap-4">
              <div class="min-w-0">
                <p class="text-sm font-medium text-neutral-900 truncate">{row.project_name}</p>
                <p class="text-xs text-neutral-400">{row.movement_count} material movement{row.movement_count === 1 ? "" : "s"}</p>
              </div>
              <p class="text-sm font-semibold text-neutral-700 tabular-nums">{fmtCurrency(row.total_cost)}</p>
            </div>
          {/each}
        </div>
      {:else}
        <div class="px-5 py-10 text-sm text-neutral-400 text-center">No project-linked issues in last 30 days</div>
      {/if}
    </section>
  </div>
{:else}
  <div class="bg-white rounded-xl border border-neutral-200 px-6 py-10 text-center">
    <h2 class="text-lg font-semibold text-neutral-900">Unable to load inventory overview</h2>
    <p class="text-sm text-neutral-400 mt-1">Please retry. If this persists, confirm migrations are applied.</p>
    <button
      onclick={fetchOverview}
      class="mt-4 px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800"
    >
      Retry
    </button>
  </div>
{/if}

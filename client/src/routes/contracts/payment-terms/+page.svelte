<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import type { PurchaseOrder, PurchaseOrderListItem } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  type PaymentTermRow = {
    id: number;
    po_number: string;
    vendor_name: string;
    project_name: string | null;
    status: string;
    total_amount: string;
    payment_terms: string;
  };

  let loading = $state(true);
  let rows = $state<PaymentTermRow[]>([]);

  function fmtCurrency(value: string): string {
    return currency.format(toAmount(value));
  }

  async function load() {
    loading = true;
    try {
      const poList = await fetchAllPages<PurchaseOrderListItem>("/procurement/purchase-orders/", {
        ordering: "-created_at",
        page_size: "100",
      }, 3);
      const sample = poList.slice(0, 40);

      const details = await Promise.allSettled(
        sample.map((row) => api.get<PurchaseOrder>(`/procurement/purchase-orders/${row.id}/`))
      );

      rows = details
        .map((result, index): PaymentTermRow | null => {
          if (result.status !== "fulfilled") return null;
          const detail = result.value;
          return {
            id: detail.id,
            po_number: detail.po_number,
            vendor_name: detail.vendor_name,
            project_name: detail.project_name,
            status: detail.status,
            total_amount: detail.total_amount,
            payment_terms: detail.payment_terms || "Not specified",
          };
        })
        .filter((row): row is PaymentTermRow => row !== null);
    } catch {
      toast.error("Load failed", "Could not load payment terms.");
      rows = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    load();
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Payment Terms</h1>
    <p class="mt-1 text-sm text-neutral-500">Commercial payment terms currently tracked on purchase order contracts.</p>
  </div>

  <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="py-20 text-center">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
      </div>
    {:else if rows.length === 0}
      <div class="px-6 py-12 text-sm text-neutral-500">No payment term records available.</div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">PO</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Payment Terms</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Value</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each rows as row}
            <tr class="cursor-pointer hover:bg-neutral-50" onclick={() => goto(`/procurement/purchase-orders/${row.id}`)}>
              <td class="px-5 py-3 font-medium text-neutral-900">{row.po_number}</td>
              <td class="px-5 py-3 text-neutral-600">{row.vendor_name}</td>
              <td class="px-5 py-3 text-neutral-600">{row.project_name || "—"}</td>
              <td class="px-5 py-3 text-neutral-700">{row.status}</td>
              <td class="px-5 py-3 text-neutral-700">{row.payment_terms}</td>
              <td class="px-5 py-3 text-right font-medium tabular-nums text-neutral-900">{fmtCurrency(row.total_amount)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

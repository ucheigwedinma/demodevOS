<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import type { ProjectVariationOrder, ProjectVariationSummary } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let loading = $state(true);
  let rows = $state<ProjectVariationOrder[]>([]);
  let summary = $state<ProjectVariationSummary | null>(null);

  function fmtCurrency(value: number): string {
    return currency.format(value);
  }

  async function load() {
    loading = true;
    try {
      const [variationRows, summaryPayload] = await Promise.all([
        fetchAllPages<ProjectVariationOrder>("/projects/variations/", {
          ordering: "-created_at",
          page_size: "200",
        }),
        api.get<ProjectVariationSummary>("/projects/variations/summary/"),
      ]);
      rows = variationRows;
      summary = summaryPayload;
    } catch {
      toast.error("Load failed", "Could not load variation orders.");
      rows = [];
      summary = null;
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
    <h1 class="text-2xl font-bold text-neutral-900">Variation Orders</h1>
    <p class="mt-1 text-sm text-neutral-500">Change order register for contract scope/value adjustments.</p>
  </div>

  <div class="grid grid-cols-2 gap-4 lg:grid-cols-5">
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary?.total ?? 0}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Pending</p>
      <p class="mt-1 text-xl font-bold text-amber-700 tabular-nums">{summary?.pending ?? 0}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">High Value Pending</p>
      <p class="mt-1 text-xl font-bold text-red-700 tabular-nums">{summary?.high_value_pending ?? 0}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Approved Value</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(summary?.approved_value ?? 0)}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Pending Value</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(summary?.pending_value ?? 0)}</p>
    </div>
  </div>

  <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="py-20 text-center">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
      </div>
    {:else if rows.length === 0}
      <div class="px-6 py-12 text-sm text-neutral-500">No variation orders found.</div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Variation</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Contract Value</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each rows as row}
            <tr class="cursor-pointer hover:bg-neutral-50" onclick={() => goto("/projects/variations")}>
              <td class="px-5 py-3">
                <p class="font-medium text-neutral-900">{row.variation_number}</p>
                <p class="max-w-[320px] truncate text-xs text-neutral-500">{row.title}</p>
              </td>
              <td class="px-5 py-3 text-neutral-600">{row.project_name}</td>
              <td class="px-5 py-3 text-neutral-700">{row.status}</td>
              <td class="px-5 py-3 text-right font-medium tabular-nums text-neutral-900">{fmtCurrency(toAmount(row.contract_value))}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

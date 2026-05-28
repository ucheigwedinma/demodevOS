<script lang="ts">
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages, isMainContractDocument, toAmount } from "$lib/contracts";
  import type { DocumentRecord, ProjectVariationOrder } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let loading = $state(true);
  let contracts = $state<DocumentRecord[]>([]);
  let variations = $state<ProjectVariationOrder[]>([]);

  function fmtCurrency(value: number): string {
    return currency.format(value);
  }

  async function load() {
    loading = true;
    try {
      const [contractRows, variationRows] = await Promise.all([
        fetchAllPages<DocumentRecord>("/documents/records/", {
          category: "CON",
          ordering: "-created_at",
          page_size: "200",
        }),
        fetchAllPages<ProjectVariationOrder>("/projects/variations/", {
          ordering: "-created_at",
          page_size: "200",
        }),
      ]);
      contracts = contractRows.filter(isMainContractDocument);
      variations = variationRows;
    } catch {
      toast.error("Load failed", "Could not load value vs executed analytics.");
      contracts = [];
      variations = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    load();
  });

  const baselineValue = $derived.by(() =>
    contracts.reduce((sum, row) => sum + toAmount(row.contract_value), 0)
  );
  const approvedVariationValue = $derived.by(() =>
    variations
      .filter((row) => row.status === "approved")
      .reduce((sum, row) => sum + toAmount(row.contract_value), 0)
  );
  const pendingVariationValue = $derived.by(() =>
    variations
      .filter((row) => row.status === "submitted" || row.status === "under_review")
      .reduce((sum, row) => sum + toAmount(row.contract_value), 0)
  );
  const executionRatio = $derived.by(() =>
    baselineValue > 0 ? (approvedVariationValue / baselineValue) * 100 : 0
  );

  type ProjectRow = {
    project_name: string;
    baseline: number;
    approved: number;
    pending: number;
  };

  const projectRows = $derived.by(() => {
    const map = new Map<string, ProjectRow>();

    for (const row of contracts) {
      const key = row.project_name || "Unassigned";
      const found = map.get(key) || { project_name: key, baseline: 0, approved: 0, pending: 0 };
      found.baseline += toAmount(row.contract_value);
      map.set(key, found);
    }

    for (const row of variations) {
      const key = row.project_name || "Unassigned";
      const found = map.get(key) || { project_name: key, baseline: 0, approved: 0, pending: 0 };
      if (row.status === "approved") found.approved += toAmount(row.contract_value);
      if (row.status === "submitted" || row.status === "under_review") {
        found.pending += toAmount(row.contract_value);
      }
      map.set(key, found);
    }

    return [...map.values()].sort((a, b) => b.baseline - a.baseline);
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Contract Value vs Executed</h1>
    <p class="mt-1 text-sm text-neutral-500">Baseline contract commitments against approved/pending variation execution values.</p>
  </div>

  {#if loading}
    <div class="py-20 text-center">
      <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
    </div>
  {:else}
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Baseline Contract Value</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(baselineValue)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Approved Executed Value</p>
        <p class="mt-1 text-xl font-bold text-emerald-700 tabular-nums">{fmtCurrency(approvedVariationValue)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Pending Execution Value</p>
        <p class="mt-1 text-xl font-bold text-amber-700 tabular-nums">{fmtCurrency(pendingVariationValue)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Execution Ratio</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{executionRatio.toFixed(1)}%</p>
      </div>
    </div>

    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Baseline</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Approved</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Pending</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each projectRows as row}
            <tr>
              <td class="px-5 py-3 font-medium text-neutral-900">{row.project_name}</td>
              <td class="px-5 py-3 text-right tabular-nums text-neutral-700">{fmtCurrency(row.baseline)}</td>
              <td class="px-5 py-3 text-right tabular-nums text-emerald-700">{fmtCurrency(row.approved)}</td>
              <td class="px-5 py-3 text-right tabular-nums text-amber-700">{fmtCurrency(row.pending)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

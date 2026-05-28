<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ProcurementCycleDrilldown } from "$lib/types";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import DrilldownPanel from "./DrilldownPanel.svelte";

  let {
    startDate = "",
    endDate = "",
    onclose,
  }: {
    startDate?: string;
    endDate?: string;
    onclose: () => void;
  } = $props();

  let data = $state<ProcurementCycleDrilldown | null>(null);
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      data = await api.get<ProcurementCycleDrilldown>("/analytics/drilldowns/procurement-cycle/", params);
    } catch {
      toast.error("Load failed", "Could not load procurement cycle drilldown.");
    }
    loading = false;
  }

  $effect(() => { load(); });

  function fmtN(n: number): string {
    return n.toLocaleString("en-US", { maximumFractionDigits: 1 });
  }
</script>

<DrilldownPanel title="Procurement Cycle Time — Detail" {loading} {onclose}>
  {#if data}
    <div class="space-y-6">
      <!-- Summary stats -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        {#each [
          { label: "Median", value: `${fmtN(data.summary.median_days)} days` },
          { label: "P90", value: `${fmtN(data.summary.p90_days)} days` },
          { label: "Min", value: `${data.summary.min_days} days` },
          { label: "Max", value: `${data.summary.max_days} days` },
        ] as stat}
          <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
            <p class="text-[10px] text-neutral-400 uppercase tracking-wider">{stat.label}</p>
            <p class="text-sm font-semibold text-neutral-900 tabular-nums">{stat.value}</p>
          </div>
        {/each}
      </div>

      <!-- Histogram -->
      <div>
        <h4 class="text-xs font-semibold text-neutral-700 mb-2">Duration Distribution (days)</h4>
        <BarChart
          data={data.histogram.map(b => ({ label: b.bucket, value: b.count, count: b.count }))}
          colors={["#a3a3a3"]}
          height={220}
        />
      </div>

      <!-- Slowest POs -->
      {#if data.slowest_pos.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Slowest Purchase Orders</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100 text-left text-neutral-400">
                  <th class="pb-2 pr-4 font-medium">PO #</th>
                  <th class="pb-2 pr-4 font-medium">Vendor</th>
                  <th class="pb-2 pr-4 font-medium text-right">Days</th>
                  <th class="pb-2 font-medium">Issue Date</th>
                </tr>
              </thead>
              <tbody>
                {#each data.slowest_pos as po}
                  <tr class="border-b border-neutral-50">
                    <td class="py-2 pr-4 text-neutral-700 font-medium">{po.po_number || "—"}</td>
                    <td class="py-2 pr-4 text-neutral-600">{po.vendor || "—"}</td>
                    <td class="py-2 pr-4 text-right tabular-nums text-neutral-900 font-semibold">{po.duration_days}</td>
                    <td class="py-2 text-neutral-500">{po.issue_date}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>
  {/if}
</DrilldownPanel>

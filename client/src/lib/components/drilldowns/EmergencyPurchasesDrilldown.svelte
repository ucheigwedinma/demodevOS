<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { EmergencyPurchasesDrilldown } from "$lib/types";
  import AreaChart from "$lib/components/charts/AreaChart.svelte";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
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

  let data = $state<EmergencyPurchasesDrilldown | null>(null);
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      data = await api.get<EmergencyPurchasesDrilldown>("/analytics/drilldowns/emergency-purchases/", params);
    } catch {
      toast.error("Load failed", "Could not load emergency purchases drilldown.");
    }
    loading = false;
  }

  $effect(() => { load(); });

  const trendChartData = $derived(
    (data?.trend ?? []).map(t => ({
      x: new Date(t.month + "-01"),
      y: t.pct,
    }))
  );
</script>

<DrilldownPanel title="Emergency Purchases — Detail" {loading} {onclose}>
  {#if data}
    <div class="space-y-6">
      <!-- Monthly trend -->
      {#if trendChartData.length > 1}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Emergency Purchase Rate (% over time)</h4>
          <AreaChart
            data={trendChartData}
            formatX={(d) => {
              const dt = d as Date;
              return dt.toLocaleDateString("en-US", { month: "short" });
            }}
            formatY={(d) => `${d}%`}
            color="#f59e0b"
            height={220}
          />
        </div>
      {/if}

      <!-- By category donut -->
      {#if data.by_category.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">By Project</h4>
          <DonutChart
            data={data.by_category.map(c => ({ label: c.category, value: c.emergency }))}
            size={200}
            centerLabel="emergencies"
            centerValue={String(data.by_category.reduce((s, c) => s + c.emergency, 0))}
          />
        </div>
      {/if}

      <!-- Recent emergencies table -->
      {#if data.recent_emergencies.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Recent Emergency Requisitions</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100 text-left text-neutral-400">
                  <th class="pb-2 pr-4 font-medium">PR #</th>
                  <th class="pb-2 pr-4 font-medium">Title</th>
                  <th class="pb-2 pr-4 font-medium">Requester</th>
                  <th class="pb-2 font-medium">Project</th>
                </tr>
              </thead>
              <tbody>
                {#each data.recent_emergencies as pr}
                  <tr class="border-b border-neutral-50">
                    <td class="py-2 pr-4 text-neutral-700 font-medium">{pr.pr_number || "—"}</td>
                    <td class="py-2 pr-4 text-neutral-600 truncate max-w-[200px]">{pr.title}</td>
                    <td class="py-2 pr-4 text-neutral-500">{pr.requester || "—"}</td>
                    <td class="py-2 text-neutral-500">{pr.project || "—"}</td>
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

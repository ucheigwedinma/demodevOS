<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { VendorReliabilityDrilldown } from "$lib/types";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import DrilldownPanel from "./DrilldownPanel.svelte";

  // Vendor reliability score is computed from each Vendor's current
  // performance_rating, delivery_timeliness_score, and compliance_status —
  // current-state fields, not a date-stamped event stream. The board-metrics
  // date filter is accepted for prop-signature parity but cannot narrow this
  // view; surface that when a filter is active.
  let {
    startDate = "",
    endDate = "",
    onclose,
  }: {
    startDate?: string;
    endDate?: string;
    onclose: () => void;
  } = $props();

  let data = $state<VendorReliabilityDrilldown | null>(null);
  let loading = $state(true);

  const dateFilterActive = $derived(Boolean(startDate || endDate));

  async function load() {
    loading = true;
    try {
      data = await api.get<VendorReliabilityDrilldown>("/analytics/drilldowns/vendor-reliability/");
    } catch {
      toast.error("Load failed", "Could not load vendor reliability drilldown.");
    }
    loading = false;
  }

  $effect(() => { load(); });
</script>

<DrilldownPanel title="Vendor Reliability Score — Detail" {loading} {onclose}>
  {#if data}
    <div class="space-y-6">
      {#if dateFilterActive}
        <div class="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2 text-[11px] text-amber-800">
          Reliability scores reflect each vendor's current performance, timeliness, and compliance status — the date filter on Board Metrics does not apply here.
        </div>
      {/if}
      <!-- Summary -->
      <div class="grid grid-cols-2 gap-3">
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Median Score</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums">{data.summary.median_score}/100</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
          <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Active Vendors</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums">{data.summary.vendor_count}</p>
        </div>
      </div>

      <!-- Score distribution -->
      <div>
        <h4 class="text-xs font-semibold text-neutral-700 mb-2">Score Distribution</h4>
        <BarChart
          data={data.score_distribution.map(b => ({ label: b.bucket, value: b.count, count: b.count }))}
          colors={["#a3a3a3"]}
          height={200}
        />
      </div>

      <!-- Top/Bottom vendors side by side -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <h4 class="text-xs font-semibold text-emerald-700 mb-2">Top Vendors</h4>
          <div class="space-y-1">
            {#each data.top_vendors as v}
              <div class="flex items-center justify-between rounded-lg border border-neutral-50 bg-neutral-50/40 px-3 py-1.5">
                <span class="text-xs text-neutral-700 truncate mr-2">{v.name}</span>
                <span class="text-xs font-semibold text-emerald-700 tabular-nums shrink-0">{v.score}</span>
              </div>
            {/each}
          </div>
        </div>
        <div>
          <h4 class="text-xs font-semibold text-red-700 mb-2">Bottom Vendors</h4>
          <div class="space-y-1">
            {#each data.bottom_vendors as v}
              <div class="flex items-center justify-between rounded-lg border border-neutral-50 bg-neutral-50/40 px-3 py-1.5">
                <span class="text-xs text-neutral-700 truncate mr-2">{v.name}</span>
                <span class="text-xs font-semibold text-red-700 tabular-nums shrink-0">{v.score}</span>
              </div>
            {/each}
          </div>
        </div>
      </div>
    </div>
  {/if}
</DrilldownPanel>

<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ApprovalTimeDrilldown } from "$lib/types";
  import HorizontalBarChart from "$lib/components/charts/HorizontalBarChart.svelte";
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

  let data = $state<ApprovalTimeDrilldown | null>(null);
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (startDate) params.start_date = startDate;
      if (endDate) params.end_date = endDate;
      data = await api.get<ApprovalTimeDrilldown>("/analytics/drilldowns/approval-time/", params);
    } catch {
      toast.error("Load failed", "Could not load approval time drilldown.");
    }
    loading = false;
  }

  $effect(() => { load(); });

  function fmtH(n: number): string {
    return n.toLocaleString("en-US", { maximumFractionDigits: 1 });
  }
</script>

<DrilldownPanel title="Average Approval Time — Detail" {loading} {onclose}>
  {#if data}
    <div class="space-y-6">
      <!-- Summary stats -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        {#each [
          { label: "Median", value: `${fmtH(data.summary.median_hours)} hrs` },
          { label: "P90", value: `${fmtH(data.summary.p90_hours)} hrs` },
          { label: "Fastest", value: `${fmtH(data.summary.fastest_hours)} hrs` },
          { label: "Slowest", value: `${fmtH(data.summary.slowest_hours)} hrs` },
        ] as stat}
          <div class="rounded-lg border border-neutral-100 bg-neutral-50/60 px-3 py-2">
            <p class="text-[10px] text-neutral-400 uppercase tracking-wider">{stat.label}</p>
            <p class="text-sm font-semibold text-neutral-900 tabular-nums">{stat.value}</p>
          </div>
        {/each}
      </div>

      <!-- By workflow type -->
      {#if data.by_workflow_type.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Avg. Hours by Workflow Type</h4>
          <HorizontalBarChart
            data={data.by_workflow_type.map(t => ({ label: t.template_name.slice(0, 24), value: t.avg_hours }))}
            formatValue={(d: number) => `${d.toFixed(1)}h`}
            colors={["#6366f1"]}
            height={Math.max(180, data.by_workflow_type.length * 36)}
          />
        </div>
      {/if}

      <!-- Slowest approvals table -->
      {#if data.slowest_approvals.length > 0}
        <div>
          <h4 class="text-xs font-semibold text-neutral-700 mb-2">Slowest Approvals</h4>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100 text-left text-neutral-400">
                  <th class="pb-2 pr-4 font-medium">Workflow</th>
                  <th class="pb-2 pr-4 font-medium text-right">Hours</th>
                  <th class="pb-2 pr-4 font-medium">State</th>
                  <th class="pb-2 font-medium">Submitted</th>
                </tr>
              </thead>
              <tbody>
                {#each data.slowest_approvals as wf}
                  <tr class="border-b border-neutral-50">
                    <td class="py-2 pr-4 text-neutral-700 font-medium">{wf.template_name}</td>
                    <td class="py-2 pr-4 text-right tabular-nums text-neutral-900 font-semibold">{fmtH(wf.hours)}</td>
                    <td class="py-2 pr-4">
                      <span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-medium {wf.state === 'approved' ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}">
                        {wf.state}
                      </span>
                    </td>
                    <td class="py-2 text-neutral-500">{new Date(wf.submitted_at).toLocaleDateString()}</td>
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

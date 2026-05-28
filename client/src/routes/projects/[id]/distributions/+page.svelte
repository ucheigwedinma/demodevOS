<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { WaterfallDistributionListItem, PaginatedResponse, Project } from "$lib/types";

  const projectId = $derived($page.params.id);

  let project = $state<Project | null>(null);
  let distributions = $state<WaterfallDistributionListItem[]>([]);
  let loading = $state(true);

  async function loadData() {
    loading = true;
    try {
      const [projData, distData] = await Promise.all([
        api.get<Project>(`/projects/${projectId}/`),
        api.get<PaginatedResponse<WaterfallDistributionListItem>>(`/finance/distributions/?project=${projectId}&page_size=100`),
      ]);
      project = projData;
      distributions = distData.results;
    } catch {
      toast.error("Error", "Could not load distributions.");
    } finally {
      loading = false;
    }
  }

  async function deleteDistribution(id: number) {
    if (!confirm("Delete this distribution? This cannot be undone.")) return;

    try {
      await api.delete(`/finance/distributions/${id}/`);
      toast.success("Deleted", "Distribution deleted.");
      loadData();
    } catch {
      toast.error("Error", "Could not delete distribution.");
    }
  }

  $effect(() => {
    void projectId;
    loadData();
  });

  const statusColors: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600",
    calculated: "bg-blue-50 text-blue-700",
    approved: "bg-emerald-50 text-emerald-700",
    distributed: "bg-violet-50 text-violet-700",
    cancelled: "bg-red-50 text-red-600",
  };

  const statusLabels: Record<string, string> = {
    draft: "Draft",
    calculated: "Calculated",
    approved: "Approved",
    distributed: "Distributed",
    cancelled: "Cancelled",
  };
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !project}
  <div class="text-center py-24">
    <p class="text-neutral-400">Project not found.</p>
  </div>
{:else}
  <div class="space-y-6">
    <!-- Back Link -->
    <a
      href={`/projects/${projectId}`}
      class="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-900 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
      </svg>
      Back to project
    </a>

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-neutral-900">Distributions</h1>
        <p class="text-sm text-neutral-500 mt-1">{project.name}</p>
      </div>
      <a
        href={`/projects/${projectId}/distributions/new`}
        class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
      >
        New Distribution
      </a>
    </div>

    <!-- Summary Cards -->
    {#if distributions.length > 0}
      {@const totalDistributed = distributions
        .filter(d => d.status === "approved" || d.status === "distributed")
        .reduce((sum, d) => sum + parseFloat(d.total_amount), 0)}
      {@const totalCapitalReturned = distributions
        .filter(d => d.status === "approved" || d.status === "distributed")
        .reduce((sum, d) => sum + parseFloat(d.tier1_capital_returned), 0)}
      {@const totalProfitSplit = distributions
        .filter(d => d.status === "approved" || d.status === "distributed")
        .reduce((sum, d) => sum + parseFloat(d.tier2_profit_split), 0)}

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-white border border-neutral-200 rounded-xl p-4">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Distributed</div>
          <div class="text-2xl font-bold text-neutral-900">{currency.formatCompact(totalDistributed)}</div>
        </div>
        <div class="bg-white border border-neutral-200 rounded-xl p-4">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Capital Returned</div>
          <div class="text-2xl font-bold text-blue-600">{currency.formatCompact(totalCapitalReturned)}</div>
        </div>
        <div class="bg-white border border-neutral-200 rounded-xl p-4">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Profit Split</div>
          <div class="text-2xl font-bold text-emerald-600">{currency.formatCompact(totalProfitSplit)}</div>
        </div>
      </div>
    {/if}

    <!-- Distribution List -->
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      {#if distributions.length === 0}
        <div class="text-center py-16">
          <svg class="w-12 h-12 mx-auto mb-3 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
          </svg>
          <p class="text-neutral-400 text-sm">No distributions yet</p>
          <a
            href={`/projects/${projectId}/distributions/new`}
            class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline"
          >
            Create your first distribution
          </a>
        </div>
      {:else}
        <table class="w-full">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Distribution #</th>
              <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Date</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Total Amount</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Tier 1 (Capital)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Tier 2 (Profit)</th>
              <th class="px-4 py-3 text-center text-xs font-medium text-neutral-500 uppercase tracking-wider">Status</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each distributions as dist (dist.id)}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-4 py-3">
                  <a href={`/projects/${projectId}/distributions/${dist.id}`} class="text-sm font-medium text-neutral-900 hover:text-neutral-600">
                    {dist.distribution_number}
                  </a>
                </td>
                <td class="px-4 py-3 text-sm text-neutral-900">
                  {new Date(dist.distribution_date).toLocaleDateString()}
                </td>
                <td class="px-4 py-3 text-right text-sm font-medium text-neutral-900">
                  {currency.format(dist.total_amount)}
                </td>
                <td class="px-4 py-3 text-right text-sm text-blue-600">
                  {currency.format(dist.tier1_capital_returned)}
                </td>
                <td class="px-4 py-3 text-right text-sm text-emerald-600">
                  {currency.format(dist.tier2_profit_split)}
                </td>
                <td class="px-4 py-3 text-center">
                  <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {statusColors[dist.status]}">
                    {statusLabels[dist.status]}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="flex items-center justify-end gap-3">
                    <a
                      href={`/projects/${projectId}/distributions/${dist.id}`}
                      class="text-xs font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
                    >
                      View
                    </a>
                    {#if dist.status === "draft" || dist.status === "calculated"}
                      <button
                        onclick={() => deleteDistribution(dist.id)}
                        class="text-xs font-medium text-red-500 hover:text-red-700 transition-colors"
                      >
                        Delete
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>
{/if}

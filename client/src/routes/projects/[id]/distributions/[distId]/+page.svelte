<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { WaterfallDistribution } from "$lib/types";

  const projectId = $derived($page.params.id ?? "");
  const distId = $derived($page.params.distId ?? "");

  let distribution = $state<WaterfallDistribution | null>(null);
  let loading = $state(true);
  let actionLoading = $state(false);

  const percentages = $derived(distribution ? {
    tier1Pct: (parseFloat(distribution.tier1_capital_returned) / parseFloat(distribution.total_amount)) * 100,
    tier2Pct: (parseFloat(distribution.tier2_profit_split) / parseFloat(distribution.total_amount)) * 100,
    sponsorPct: (parseFloat(distribution.sponsor_amount) / parseFloat(distribution.total_amount)) * 100,
  } : { tier1Pct: 0, tier2Pct: 0, sponsorPct: 0 });

  async function loadDistribution() {
    loading = true;
    try {
      distribution = await api.get<WaterfallDistribution>(`/finance/distributions/${distId}/`);
    } catch {
      toast.error("Error", "Could not load distribution.");
    } finally {
      loading = false;
    }
  }

  async function approveDistribution() {
    if (!distribution) return;
    if (!confirm("Approve this distribution? This will update investor balances and cannot be undone.")) return;

    actionLoading = true;
    try {
      distribution = await api.post<WaterfallDistribution>(
        `/finance/distributions/${distId}/approve/`,
        {}
      );
      toast.success("Approved", "Distribution approved successfully.");
    } catch {
      toast.error("Error", "Could not approve distribution.");
    } finally {
      actionLoading = false;
    }
  }

  async function recalculateDistribution() {
    if (!distribution) return;

    actionLoading = true;
    try {
      distribution = await api.post<WaterfallDistribution>(
        `/finance/distributions/${distId}/recalculate/`,
        {}
      );
      toast.success("Recalculated", "Distribution recalculated successfully.");
    } catch {
      toast.error("Error", "Could not recalculate distribution.");
    } finally {
      actionLoading = false;
    }
  }

  async function deleteDistribution() {
    if (!distribution) return;
    if (!confirm("Delete this distribution? This cannot be undone.")) return;

    try {
      await api.delete(`/finance/distributions/${distId}/`);
      toast.success("Deleted", "Distribution deleted.");
      goto(`/projects/${projectId}/distributions`);
    } catch {
      toast.error("Error", "Could not delete distribution.");
    }
  }

  async function cancelDistribution() {
    if (!distribution) return;
    if (!confirm("Cancel this distribution? This action cannot be undone.")) return;

    actionLoading = true;
    try {
      distribution = await api.patch<WaterfallDistribution>(
        `/finance/distributions/${distId}/`,
        { status: "cancelled" }
      );
      toast.success("Cancelled", "Distribution cancelled.");
    } catch {
      toast.error("Error", "Could not cancel distribution.");
    } finally {
      actionLoading = false;
    }
  }

  $effect(() => {
    void distId;
    loadDistribution();
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
{:else if !distribution}
  <div class="text-center py-24">
    <p class="text-neutral-400">Distribution not found.</p>
  </div>
{:else}
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-xl font-bold text-neutral-900">{distribution.distribution_number}</h1>
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {statusColors[distribution.status]}">
            {statusLabels[distribution.status]}
          </span>
        </div>
        <p class="text-sm text-neutral-500 mt-1">
          {distribution.project_name} • {new Date(distribution.distribution_date).toLocaleDateString()}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <a
          href={`/projects/${projectId}/distributions`}
          class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
        >
          Back to List
        </a>

        {#if distribution.status === "draft" || distribution.status === "calculated"}
          <button
            onclick={recalculateDistribution}
            disabled={actionLoading}
            class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors disabled:opacity-50"
          >
            Recalculate
          </button>
        {/if}

        {#if distribution.status === "calculated"}
          <button
            onclick={approveDistribution}
            disabled={actionLoading}
            class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50"
          >
            {actionLoading ? "Approving..." : "Approve"}
          </button>
        {/if}

        {#if distribution.status === "draft" || distribution.status === "calculated"}
          <button
            onclick={deleteDistribution}
            class="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            Delete
          </button>
        {/if}

        {#if distribution.status === "approved"}
          <button
            onclick={cancelDistribution}
            disabled={actionLoading}
            class="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        {/if}
      </div>
    </div>

    <!-- Distribution Info -->
    <div class="bg-white border border-neutral-200 rounded-xl p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div>
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Amount</div>
          <div class="text-xl font-bold text-neutral-900">{currency.format(distribution.total_amount)}</div>
        </div>
        <div>
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Distribution Date</div>
          <div class="text-xl font-semibold text-neutral-900">{new Date(distribution.distribution_date).toLocaleDateString()}</div>
        </div>
        <div>
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Created By</div>
          <div class="text-sm text-neutral-900">{distribution.created_by_name || "—"}</div>
          <div class="text-xs text-neutral-500">{new Date(distribution.created_at).toLocaleDateString()}</div>
        </div>
        {#if distribution.approved_by_name}
          <div>
            <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Approved By</div>
            <div class="text-sm text-neutral-900">{distribution.approved_by_name}</div>
            {#if distribution.approved_at}
              <div class="text-xs text-neutral-500">{new Date(distribution.approved_at).toLocaleDateString()}</div>
            {/if}
          </div>
        {/if}
      </div>

      {#if distribution.notes}
        <div class="mt-4 pt-4 border-t border-neutral-200">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Notes</div>
          <p class="text-sm text-neutral-700">{distribution.notes}</p>
        </div>
      {/if}
    </div>

    <!-- Waterfall Breakdown -->
    <div class="bg-white border border-neutral-200 rounded-xl p-6">
      <h2 class="text-lg font-semibold text-neutral-900 mb-4">Waterfall Breakdown</h2>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div class="bg-neutral-50 rounded-lg p-4">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Tier 1: Capital Return</div>
          <div class="text-2xl font-bold text-blue-600">{currency.format(distribution.tier1_capital_returned)}</div>
          <div class="text-xs text-neutral-500 mt-1">
            {((parseFloat(distribution.tier1_capital_returned) / parseFloat(distribution.total_amount)) * 100).toFixed(1)}% of total
          </div>
        </div>
        <div class="bg-neutral-50 rounded-lg p-4">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Tier 2: Profit Split</div>
          <div class="text-2xl font-bold text-emerald-600">{currency.format(distribution.tier2_profit_split)}</div>
          <div class="text-xs text-neutral-500 mt-1">
            {((parseFloat(distribution.tier2_profit_split) / parseFloat(distribution.total_amount)) * 100).toFixed(1)}% of total
          </div>
        </div>
        <div class="bg-neutral-50 rounded-lg p-4">
          <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Sponsor/GP Amount</div>
          <div class="text-2xl font-bold text-violet-600">{currency.format(distribution.sponsor_amount)}</div>
          <div class="text-xs text-neutral-500 mt-1">
            {((parseFloat(distribution.sponsor_amount) / parseFloat(distribution.total_amount)) * 100).toFixed(1)}% of total
          </div>
        </div>
      </div>

      <!-- Visual Bar Chart -->
      <div class="space-y-2">
        <div class="flex items-center gap-2 text-xs text-neutral-500">
          <span class="font-medium">Distribution Allocation:</span>
          <span>{currency.format(distribution.total_amount)}</span>
        </div>
        <div class="h-8 flex rounded-lg overflow-hidden">
          {#if percentages.tier1Pct > 0}
            <div class="bg-blue-500 flex items-center justify-center text-white text-xs font-medium" style="width: {percentages.tier1Pct}%">
              {percentages.tier1Pct > 10 ? `${percentages.tier1Pct.toFixed(0)}%` : ''}
            </div>
          {/if}
          {#if percentages.tier2Pct > 0}
            <div class="bg-emerald-500 flex items-center justify-center text-white text-xs font-medium" style="width: {percentages.tier2Pct}%">
              {percentages.tier2Pct > 10 ? `${percentages.tier2Pct.toFixed(0)}%` : ''}
            </div>
          {/if}
          {#if percentages.sponsorPct > 0}
            <div class="bg-violet-500 flex items-center justify-center text-white text-xs font-medium" style="width: {percentages.sponsorPct}%">
              {percentages.sponsorPct > 10 ? `${percentages.sponsorPct.toFixed(0)}%` : ''}
            </div>
          {/if}
        </div>
        <div class="flex items-center gap-6 text-xs">
          <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 bg-blue-500 rounded"></div>
            <span class="text-neutral-600">Tier 1 (Capital Return)</span>
          </div>
          <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 bg-emerald-500 rounded"></div>
            <span class="text-neutral-600">Tier 2 (Profit to Investors)</span>
          </div>
          <div class="flex items-center gap-1.5">
            <div class="w-3 h-3 bg-violet-500 rounded"></div>
            <span class="text-neutral-600">Sponsor/GP Share</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Investor Allocations -->
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <div class="px-6 py-4 border-b border-neutral-200">
        <h3 class="text-base font-semibold text-neutral-900">Investor Allocations</h3>
      </div>

      {#if distribution.line_items && distribution.line_items.length > 0}
        <table class="w-full">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Investor</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Ownership %</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Tier 1 (Capital)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Tier 2 (Profit)</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Total Amount</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Cumulative Capital</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Cumulative Profit</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each distribution.line_items as item}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-4 py-3 text-sm font-medium text-neutral-900">{item.investor_name}</td>
                <td class="px-4 py-3 text-right text-sm text-neutral-600">{item.ownership_pct}%</td>
                <td class="px-4 py-3 text-right text-sm text-blue-600">{currency.format(item.tier1_capital_amount)}</td>
                <td class="px-4 py-3 text-right text-sm text-emerald-600">{currency.format(item.tier2_profit_amount)}</td>
                <td class="px-4 py-3 text-right text-sm font-medium text-neutral-900">{currency.format(item.total_amount)}</td>
                <td class="px-4 py-3 text-right text-sm text-neutral-500">{currency.format(item.capital_returned_to_date)}</td>
                <td class="px-4 py-3 text-right text-sm text-neutral-500">{currency.format(item.profit_distributed_to_date)}</td>
              </tr>
            {/each}
          </tbody>
          <tfoot class="bg-neutral-50 border-t-2 border-neutral-200">
            <tr>
              <td colspan="2" class="px-4 py-3 text-sm font-semibold text-neutral-900">Total to Investors</td>
              <td class="px-4 py-3 text-right text-sm font-semibold text-blue-600">
                {currency.format(distribution.line_items.reduce((sum, item) => sum + parseFloat(item.tier1_capital_amount), 0))}
              </td>
              <td class="px-4 py-3 text-right text-sm font-semibold text-emerald-600">
                {currency.format(distribution.line_items.reduce((sum, item) => sum + parseFloat(item.tier2_profit_amount), 0))}
              </td>
              <td class="px-4 py-3 text-right text-sm font-semibold text-neutral-900">
                {currency.format(distribution.line_items.reduce((sum, item) => sum + parseFloat(item.total_amount), 0))}
              </td>
              <td colspan="2"></td>
            </tr>
          </tfoot>
        </table>
      {:else}
        <div class="text-center py-8 text-neutral-400 text-sm">
          No investor allocations
        </div>
      {/if}
    </div>
  </div>
{/if}

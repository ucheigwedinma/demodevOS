<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { Project, WaterfallDistribution } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const projectId = $derived($page.params.id ?? "");

  let project = $state<Project | null>(null);
  let loading = $state(true);
  let creating = $state(false);
  let step = $state(1); // 1: Details, 2: Preview, 3: Confirm

  let formData = $state({
    distribution_date: new Date().toISOString().split("T")[0],
    total_amount: 0,
    notes: "",
  });

  let preview = $state<WaterfallDistribution | null>(null);
  let previewLoading = $state(false);

  const percentages = $derived(preview ? {
    tier1Pct: (parseFloat(preview.tier1_capital_returned) / parseFloat(preview.total_amount)) * 100,
    tier2Pct: (parseFloat(preview.tier2_profit_split) / parseFloat(preview.total_amount)) * 100,
    sponsorPct: (parseFloat(preview.sponsor_amount) / parseFloat(preview.total_amount)) * 100,
  } : { tier1Pct: 0, tier2Pct: 0, sponsorPct: 0 });

  async function loadProject() {
    loading = true;
    try {
      project = await api.get<Project>(`/projects/${projectId}/`);
    } catch {
      toast.error("Error", "Could not load project.");
    } finally {
      loading = false;
    }
  }

  async function generatePreview() {
    if (!validateForm()) return;
    const parsedProjectId = Number.parseInt(projectId, 10);
    if (Number.isNaN(parsedProjectId)) {
      toast.error("Error", "Invalid project identifier.");
      return;
    }

    previewLoading = true;
    try {
      // Create distribution in DRAFT status
      preview = await api.post<WaterfallDistribution>(`/finance/distributions/`, {
        project: parsedProjectId,
        ...formData,
        status: "draft",
      });

      // Get preview calculation
      const previewData = await api.get<any>(`/finance/distributions/${preview.id}/preview/`);

      // Merge preview data into distribution object
      preview = {
        ...preview,
        ...previewData,
      };

      step = 2;
    } catch {
      toast.error("Error", "Could not generate preview.");
    } finally {
      previewLoading = false;
    }
  }

  async function createDistribution() {
    if (!preview) return;

    creating = true;
    try {
      // Update distribution to CALCULATED status
      const updated = await api.patch<WaterfallDistribution>(
        `/finance/distributions/${preview.id}/`,
        { status: "calculated" }
      );

      toast.success("Created", "Distribution created successfully.");
      goto(`/projects/${projectId}/distributions/${updated.id}`);
    } catch {
      toast.error("Error", "Could not create distribution.");
      creating = false;
    }
  }

  async function cancelPreview() {
    if (preview) {
      try {
        await api.delete(`/finance/distributions/${preview.id}/`);
      } catch {
        // Ignore delete errors
      }
    }
    preview = null;
    step = 1;
  }

  function validateForm(): boolean {
    const amount = Number(formData.total_amount);
    if (!amount || amount <= 0) {
      toast.error("Validation Error", "Distribution amount must be greater than zero.");
      return false;
    }
    if (!formData.distribution_date) {
      toast.error("Validation Error", "Distribution date is required.");
      return false;
    }
    return true;
  }

  onMount(() => {
    loadProject();
  });
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
  <div class="max-w-5xl mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-neutral-900">New Distribution</h1>
        <p class="text-sm text-neutral-500 mt-1">{project.name}</p>
      </div>
      <a
        href={`/projects/${projectId}/distributions`}
        class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
      >
        Cancel
      </a>
    </div>

    <!-- Progress Steps -->
    <div class="bg-white border border-neutral-200 rounded-xl p-6">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="flex items-center justify-center w-8 h-8 rounded-full {step >= 1 ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-500'} text-sm font-medium">
            1
          </div>
          <span class="text-sm font-medium {step >= 1 ? 'text-neutral-900' : 'text-neutral-500'}">Details</span>
        </div>
        <div class="flex-1 h-px bg-neutral-200 mx-4"></div>
        <div class="flex items-center gap-2">
          <div class="flex items-center justify-center w-8 h-8 rounded-full {step >= 2 ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-500'} text-sm font-medium">
            2
          </div>
          <span class="text-sm font-medium {step >= 2 ? 'text-neutral-900' : 'text-neutral-500'}">Preview</span>
        </div>
      </div>
    </div>

    {#if step === 1}
      <!-- Step 1: Distribution Details -->
      <div class="bg-white border border-neutral-200 rounded-xl p-6">
        <h2 class="text-lg font-semibold text-neutral-900 mb-6">Distribution Details</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">Distribution Date</label>
            <DateInput bind:value={formData.distribution_date} />
          </div>

          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">Total Distribution Amount</label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 text-sm">{currency.config.symbol}</span>
              <input
                type="number"
                step="0.01"
                bind:value={formData.total_amount}
                placeholder="0.00"
                class="w-full border border-neutral-200 rounded-lg pl-8 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">Notes (Optional)</label>
            <textarea
              bind:value={formData.notes}
              rows="3"
              placeholder="Add any notes about this distribution..."
              class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
            ></textarea>
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <a
            href={`/projects/${projectId}/distributions`}
            class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            Cancel
          </a>
          <button
            onclick={generatePreview}
            disabled={previewLoading}
            class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {previewLoading ? "Calculating..." : "Preview Waterfall"}
          </button>
        </div>
      </div>
    {:else if step === 2 && preview}
      <!-- Step 2: Preview Waterfall Calculation -->
      <div class="space-y-6">
        <!-- Tier Summary -->
        <div class="bg-white border border-neutral-200 rounded-xl p-6">
          <h2 class="text-lg font-semibold text-neutral-900 mb-4">Waterfall Breakdown</h2>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="bg-neutral-50 rounded-lg p-4">
              <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Tier 1: Capital Return</div>
              <div class="text-2xl font-bold text-blue-600">{currency.format(preview.tier1_capital_returned)}</div>
            </div>
            <div class="bg-neutral-50 rounded-lg p-4">
              <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Tier 2: Profit Split</div>
              <div class="text-2xl font-bold text-emerald-600">{currency.format(preview.tier2_profit_split)}</div>
            </div>
            <div class="bg-neutral-50 rounded-lg p-4">
              <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Sponsor Amount</div>
              <div class="text-2xl font-bold text-violet-600">{currency.format(preview.sponsor_amount)}</div>
            </div>
          </div>

          <!-- Visual Bar Chart -->
          <div class="space-y-2">
            <div class="flex items-center gap-2 text-xs text-neutral-500">
              <span class="font-medium">Distribution Allocation:</span>
              <span>{currency.format(preview.total_amount)}</span>
            </div>
            <div class="h-8 flex rounded-lg overflow-hidden">
              {#if percentages.tier1Pct > 0}
                <div class="bg-blue-500 flex items-center justify-center text-white text-xs font-medium" style="width: {percentages.tier1Pct}%">
                  {percentages.tier1Pct.toFixed(0)}%
                </div>
              {/if}
              {#if percentages.tier2Pct > 0}
                <div class="bg-emerald-500 flex items-center justify-center text-white text-xs font-medium" style="width: {percentages.tier2Pct}%">
                  {percentages.tier2Pct.toFixed(0)}%
                </div>
              {/if}
              {#if percentages.sponsorPct > 0}
                <div class="bg-violet-500 flex items-center justify-center text-white text-xs font-medium" style="width: {percentages.sponsorPct}%">
                  {percentages.sponsorPct.toFixed(0)}%
                </div>
              {/if}
            </div>
            <div class="flex items-center gap-6 text-xs">
              <div class="flex items-center gap-1.5">
                <div class="w-3 h-3 bg-blue-500 rounded"></div>
                <span class="text-neutral-600">Tier 1 (Capital)</span>
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

          {#if preview.line_items && preview.line_items.length > 0}
            <table class="w-full">
              <thead class="bg-neutral-50 border-b border-neutral-200">
                <tr>
                  <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Investor</th>
                  <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Ownership %</th>
                  <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Tier 1 (Capital)</th>
                  <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Tier 2 (Profit)</th>
                  <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Total</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each preview.line_items as item}
                  <tr>
                    <td class="px-4 py-3 text-sm font-medium text-neutral-900">{item.investor_name}</td>
                    <td class="px-4 py-3 text-right text-sm text-neutral-600">{item.ownership_pct}%</td>
                    <td class="px-4 py-3 text-right text-sm text-blue-600">{currency.format(item.tier1_capital_amount)}</td>
                    <td class="px-4 py-3 text-right text-sm text-emerald-600">{currency.format(item.tier2_profit_amount)}</td>
                    <td class="px-4 py-3 text-right text-sm font-medium text-neutral-900">{currency.format(item.total_amount)}</td>
                  </tr>
                {/each}
              </tbody>
              <tfoot class="bg-neutral-50 border-t border-neutral-200">
                <tr>
                  <td colspan="2" class="px-4 py-3 text-sm font-semibold text-neutral-900">Total to Investors</td>
                  <td class="px-4 py-3 text-right text-sm font-semibold text-blue-600">
                    {currency.format(preview.line_items.reduce((sum, item) => sum + parseFloat(item.tier1_capital_amount), 0))}
                  </td>
                  <td class="px-4 py-3 text-right text-sm font-semibold text-emerald-600">
                    {currency.format(preview.line_items.reduce((sum, item) => sum + parseFloat(item.tier2_profit_amount), 0))}
                  </td>
                  <td class="px-4 py-3 text-right text-sm font-semibold text-neutral-900">
                    {currency.format(preview.line_items.reduce((sum, item) => sum + parseFloat(item.total_amount), 0))}
                  </td>
                </tr>
              </tfoot>
            </table>
          {:else}
            <div class="text-center py-8 text-neutral-400 text-sm">
              No investors in cap table
            </div>
          {/if}
        </div>

        <!-- Actions -->
        <div class="flex justify-between items-center">
          <button
            onclick={cancelPreview}
            class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            Back to Edit
          </button>
          <div class="flex gap-3">
            <a
              href={`/projects/${projectId}/distributions`}
              class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              Cancel
            </a>
            <button
              onclick={createDistribution}
              disabled={creating}
              class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {creating ? "Creating..." : "Create Distribution"}
            </button>
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}

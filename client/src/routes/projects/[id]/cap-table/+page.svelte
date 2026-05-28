<script lang="ts">
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { ProjectInvestor, InvestorListItem, PaginatedResponse, Project } from "$lib/types";

  const projectId = $derived($page.params.id);

  let project = $state<Project | null>(null);
  let capTable = $state<ProjectInvestor[]>([]);
  let availableInvestors = $state<InvestorListItem[]>([]);
  let loading = $state(true);
  let showAddModal = $state(false);
  let editingId = $state<number | null>(null);

  const totals = $derived({
    totalOwnership: capTable.reduce((s, i) => s + parseFloat(i.ownership_percentage), 0),
    totalContributed: capTable.reduce((s, i) => s + parseFloat(i.capital_contributed), 0),
    totalUnreturned: capTable.reduce((s, i) => s + parseFloat(i.unreturned_capital), 0),
  });

  let newInvestor = $state({
    investor: 0,
    ownership_percentage: "0.00",
    capital_committed: "0.00",
    capital_contributed: "0.00",
    custom_profit_split_pct: null as string | null,
    notes: "",
  });

  function parseApiErrorMessage(error: ApiError): string {
    const detail = error.data?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    const nonField = error.fieldErrors.non_field_errors?.[0];
    if (nonField) return nonField;
    for (const values of Object.values(error.fieldErrors)) {
      if (values.length > 0) return values[0];
    }
    return "Please review your entries and try again.";
  }

  async function loadData() {
    loading = true;
    try {
      const [projData, capData, invData] = await Promise.all([
        api.get<Project>(`/projects/${projectId}/`),
        api.get<PaginatedResponse<ProjectInvestor>>(`/finance/project-investors/?project=${projectId}&page_size=100`),
        api.get<PaginatedResponse<InvestorListItem>>(`/finance/investors/?is_active=true&page_size=100`),
      ]);
      project = projData;
      capTable = capData.results;
      availableInvestors = invData.results;
    } catch {
      toast.error("Error", "Could not load cap table.");
    } finally {
      loading = false;
    }
  }

  async function addInvestor() {
    if (!newInvestor.investor) {
      toast.error("Error", "Please select an investor.");
      return;
    }

    try {
      await api.post(`/finance/project-investors/`, {
        project: parseInt(projectId!),
        ...newInvestor,
      });
      toast.success("Added", "Investor added to cap table.");
      showAddModal = false;
      resetForm();
      loadData();
    } catch (error) {
      if (error instanceof ApiError) {
        toast.error("Could not add investor", parseApiErrorMessage(error));
      } else {
        toast.error("Error", "Could not add investor.");
      }
    }
  }

  async function updateInvestor(id: number, data: Partial<ProjectInvestor>) {
    try {
      await api.patch(`/finance/project-investors/${id}/`, data);
      toast.success("Updated", "Investor updated.");
      editingId = null;
      loadData();
    } catch {
      toast.error("Error", "Could not update investor.");
    }
  }

  async function removeInvestor(id: number) {
    if (!confirm("Remove this investor from the cap table? This cannot be undone.")) return;

    try {
      await api.delete(`/finance/project-investors/${id}/`);
      toast.success("Removed", "Investor removed from cap table.");
      loadData();
    } catch {
      toast.error("Error", "Could not remove investor.");
    }
  }

  function resetForm() {
    newInvestor = {
      investor: 0,
      ownership_percentage: "0.00",
      capital_committed: "0.00",
      capital_contributed: "0.00",
      custom_profit_split_pct: null,
      notes: "",
    };
  }

  $effect(() => {
    void projectId;
    loadData();
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
        <h1 class="text-xl font-bold text-neutral-900">Cap Table</h1>
        <p class="text-sm text-neutral-500 mt-1">{project.name}</p>
      </div>
      <button
        onclick={() => showAddModal = true}
        class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
      >
        Add Investor
      </button>
    </div>

    <!-- Summary Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-white border border-neutral-200 rounded-xl p-4">
        <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Ownership</div>
        <div class="text-2xl font-bold {totals.totalOwnership >= 99.99 && totals.totalOwnership <= 100.01 ? 'text-emerald-600' : 'text-amber-600'}">
          {totals.totalOwnership.toFixed(2)}%
        </div>
        {#if totals.totalOwnership < 99.99 || totals.totalOwnership > 100.01}
          <p class="text-xs text-amber-600 mt-1">Must sum to 100%</p>
        {/if}
      </div>
      <div class="bg-white border border-neutral-200 rounded-xl p-4">
        <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Capital</div>
        <div class="text-2xl font-bold text-neutral-900">{currency.formatCompact(totals.totalContributed)}</div>
      </div>
      <div class="bg-white border border-neutral-200 rounded-xl p-4">
        <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Unreturned Capital</div>
        <div class="text-2xl font-bold text-neutral-900">{currency.formatCompact(totals.totalUnreturned)}</div>
      </div>
    </div>

    <!-- Cap Table -->
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      {#if capTable.length === 0}
        <div class="text-center py-16">
          <svg class="w-12 h-12 mx-auto mb-3 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
          </svg>
          <p class="text-neutral-400 text-sm">No investors in cap table</p>
          <button
            onclick={() => showAddModal = true}
            class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline"
          >
            Add your first investor
          </button>
        </div>
      {:else}
        <table class="w-full">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Investor</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Ownership %</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Capital Contributed</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Capital Returned</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Profit Dist.</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Unreturned</th>
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each capTable as inv (inv.id)}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-4 py-3">
                  <a href={`/finance/investors/${inv.investor}`} class="text-sm font-medium text-neutral-900 hover:text-neutral-600">
                    {inv.investor_name}
                  </a>
                </td>
                <td class="px-4 py-3 text-right text-sm font-medium text-neutral-900">{inv.ownership_percentage}%</td>
                <td class="px-4 py-3 text-right text-sm text-neutral-900">{currency.format(inv.capital_contributed)}</td>
                <td class="px-4 py-3 text-right text-sm text-neutral-600">{currency.format(inv.total_capital_returned)}</td>
                <td class="px-4 py-3 text-right text-sm text-emerald-600">{currency.format(inv.total_profit_distributed)}</td>
                <td class="px-4 py-3 text-right text-sm font-medium text-neutral-900">{currency.format(inv.unreturned_capital)}</td>
                <td class="px-4 py-3 text-right">
                  <button
                    onclick={() => removeInvestor(inv.id)}
                    class="text-xs font-medium text-red-500 hover:text-red-700 transition-colors"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  </div>

  <!-- Add Investor Modal -->
  {#if showAddModal}
          <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onclick={() => showAddModal = false} onkeydown={(e) => { if (e.key === 'Escape') showAddModal = false; }} role="button" tabindex="0" aria-label="Close modal">
      <div class="bg-white rounded-xl p-6 w-full max-w-lg" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabindex="-1">
        <h2 id="modal-title" class="text-lg font-semibold text-neutral-900 mb-4">Add Investor to Cap Table</h2>
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">
              Investor
              <select
                bind:value={newInvestor.investor}
                class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-neutral-900"
              >
              <option value={0}>Select investor...</option>
              {#each availableInvestors as inv}
                <option value={inv.id}>{inv.name}</option>
              {/each}
              </select>
            </label>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-medium text-neutral-500 mb-1.5">
                Ownership %
                <input
                  type="number"
                  step="0.01"
                  bind:value={newInvestor.ownership_percentage}
                  class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-neutral-900"
                />
              </label>
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-500 mb-1.5">
                Capital Committed
                <input
                  type="number"
                  step="0.01"
                  bind:value={newInvestor.capital_committed}
                  class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-neutral-900"
                />
              </label>
            </div>
          </div>
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">
              Capital Contributed
              <input
                type="number"
                step="0.01"
                bind:value={newInvestor.capital_contributed}
                class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
            </label>
          </div>
        </div>
        <div class="flex justify-end gap-3 mt-6">
          <button
            onclick={() => { showAddModal = false; resetForm(); }}
            class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={addInvestor}
            class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
          >
            Add to Cap Table
          </button>
        </div>
      </div>
    </div>
  {/if}
{/if}

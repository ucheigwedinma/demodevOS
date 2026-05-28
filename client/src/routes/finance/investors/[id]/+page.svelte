<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { Investor, ProjectInvestor, PaginatedResponse } from "$lib/types";

  const investorId = $derived($page.params.id);

  let investor = $state<Investor | null>(null);
  let investments = $state<ProjectInvestor[]>([]);
  let loading = $state(true);
  let editing = $state(false);
  let saving = $state(false);
  let activeTab = $state<"overview" | "investments">("overview");

  let formData = $state({
    name: "",
    investor_type: "individual",
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    tax_id: "",
    entity_name: "",
    registration_number: "",
    notes: "",
    is_active: true,
  });

  async function loadInvestor() {
    loading = true;
    try {
      const [invData, invInvestments] = await Promise.all([
        api.get<Investor>(`/finance/investors/${investorId}/`),
        api.get<PaginatedResponse<ProjectInvestor>>(`/finance/project-investors/?investor=${investorId}&page_size=100`),
      ]);
      investor = invData;
      investments = invInvestments.results;

      // Populate form
      formData = {
        name: investor.name,
        investor_type: investor.investor_type,
        contact_person: investor.contact_person,
        email: investor.email,
        phone: investor.phone,
        address: investor.address,
        tax_id: investor.tax_id,
        entity_name: investor.entity_name,
        registration_number: investor.registration_number,
        notes: investor.notes,
        is_active: investor.is_active,
      };
    } catch {
      toast.error("Error", "Could not load investor.");
    } finally {
      loading = false;
    }
  }

  async function saveInvestor() {
    if (!investor) return;
    saving = true;
    try {
      const updated = await api.patch<Investor>(`/finance/investors/${investorId}/`, formData);
      investor = updated;
      editing = false;
      toast.success("Saved", "Investor updated successfully.");
    } catch {
      toast.error("Error", "Could not save investor.");
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    void investorId;
    loadInvestor();
  });

  const investorTypeLabels: Record<string, string> = {
    individual: "Individual",
    institutional: "Institutional",
    family_office: "Family Office",
    fund: "Fund",
    corporate: "Corporate",
  };

  const totalInvestedDisplay = $derived.by(() => {
    if (!investor) return "0";
    if (investor.total_invested) return investor.total_invested;
    const fallback = investments.reduce((sum, row) => {
      const parsed = Number(row.capital_contributed);
      return Number.isFinite(parsed) ? sum + parsed : sum;
    }, 0);
    return String(fallback);
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
  </div>
{:else if !investor}
  <div class="text-center py-24">
    <p class="text-neutral-400">Investor not found.</p>
    <a href="/finance/investors" class="mt-4 inline-block text-sm font-medium text-neutral-800 hover:underline">
      Back to investors
    </a>
  </div>
{:else}
  <div class="space-y-6">
    <!-- Breadcrumb -->
    <Breadcrumb items={[{ label: "Finance", href: "/finance" }, { label: "Investors", href: "/finance/investors" }, { label: investor.name }]} />

    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-bold text-neutral-800">{investor.name}</h1>
        <div class="flex items-center gap-3 mt-2">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">
            {investorTypeLabels[investor.investor_type]}
          </span>
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {investor.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
            {investor.is_active ? "Active" : "Inactive"}
          </span>
        </div>
      </div>
      <div class="flex gap-2">
        {#if editing}
          <button
            onclick={() => { editing = false; loadInvestor(); }}
            class="px-4 py-2 border border-neutral-200 text-neutral-700 text-sm font-medium rounded-lg hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={saveInvestor}
            disabled={saving}
            class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-40 transition-colors"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        {:else}
          <button
            onclick={() => editing = true}
            class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
          >
            Edit
          </button>
        {/if}
      </div>
    </div>

    <!-- Tabs -->
    <div class="border-b border-neutral-200">
      <nav class="flex gap-6">
        <button
          onclick={() => activeTab = "overview"}
          class="pb-3 text-sm font-medium border-b-2 transition-colors -mb-px {activeTab === 'overview' ? 'border-neutral-800 text-neutral-800' : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
        >
          Overview
        </button>
        <button
          onclick={() => activeTab = "investments"}
          class="pb-3 text-sm font-medium border-b-2 transition-colors -mb-px {activeTab === 'investments' ? 'border-neutral-800 text-neutral-800' : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
        >
          Investments ({investments.length})
        </button>
      </nav>
    </div>

    {#if activeTab === "overview"}
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Main Info -->
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-4">Investor Information</h3>
            {#if editing}
              <div class="space-y-4">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1.5">Name</span>
                  <input type="text" bind:value={formData.name} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1.5">Type</span>
                  <select bind:value={formData.investor_type} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
                    <option value="individual">Individual</option>
                    <option value="institutional">Institutional</option>
                    <option value="family_office">Family Office</option>
                    <option value="fund">Fund</option>
                    <option value="corporate">Corporate</option>
                  </select>
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1.5">Entity Name (if different)</span>
                  <input type="text" bind:value={formData.entity_name} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                </label>
                <div class="grid grid-cols-2 gap-4">
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1.5">Tax ID</span>
                    <input type="text" bind:value={formData.tax_id} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                  </label>
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1.5">Registration Number</span>
                    <input type="text" bind:value={formData.registration_number} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                  </label>
                </div>
                <label class="flex items-center gap-2">
                  <input type="checkbox" bind:checked={formData.is_active} class="rounded border-neutral-300" />
                  <span class="text-sm text-neutral-700">Active</span>
                </label>
              </div>
            {:else}
              <div class="grid md:grid-cols-2 gap-x-10 gap-y-3 text-sm">
                <div class="flex justify-between"><span class="text-neutral-400">Type</span><span class="text-neutral-800">{investorTypeLabels[investor.investor_type]}</span></div>
                <div class="flex justify-between"><span class="text-neutral-400">Status</span><span class="text-neutral-800">{investor.is_active ? "Active" : "Inactive"}</span></div>
                {#if investor.entity_name}
                  <div class="flex justify-between col-span-2"><span class="text-neutral-400">Legal Entity</span><span class="text-neutral-800">{investor.entity_name}</span></div>
                {/if}
                {#if investor.tax_id}
                  <div class="flex justify-between"><span class="text-neutral-400">Tax ID</span><span class="text-neutral-800">{investor.tax_id}</span></div>
                {/if}
                {#if investor.registration_number}
                  <div class="flex justify-between"><span class="text-neutral-400">Registration #</span><span class="text-neutral-800">{investor.registration_number}</span></div>
                {/if}
              </div>
            {/if}
          </div>

          <div class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-4">Contact Information</h3>
            {#if editing}
              <div class="space-y-4">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1.5">Contact Person</span>
                  <input type="text" bind:value={formData.contact_person} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                </label>
                <div class="grid grid-cols-2 gap-4">
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1.5">Email</span>
                    <input type="email" bind:value={formData.email} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                  </label>
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1.5">Phone</span>
                    <input type="tel" bind:value={formData.phone} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
                  </label>
                </div>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1.5">Address</span>
                  <textarea bind:value={formData.address} rows="3" class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"></textarea>
                </label>
              </div>
            {:else}
              <div class="space-y-2 text-sm">
                {#if investor.contact_person}
                  <div class="flex justify-between"><span class="text-neutral-400">Contact Person</span><span class="text-neutral-800">{investor.contact_person}</span></div>
                {/if}
                {#if investor.email}
                  <div class="flex justify-between"><span class="text-neutral-400">Email</span><a href={`mailto:${investor.email}`} class="text-neutral-800 hover:underline">{investor.email}</a></div>
                {/if}
                {#if investor.phone}
                  <div class="flex justify-between"><span class="text-neutral-400">Phone</span><a href={`tel:${investor.phone}`} class="text-neutral-800 hover:underline">{investor.phone}</a></div>
                {/if}
                {#if investor.address}
                  <div><span class="text-neutral-400 block mb-1">Address</span><span class="text-neutral-800 whitespace-pre-line">{investor.address}</span></div>
                {/if}
                {#if !investor.contact_person && !investor.email && !investor.phone && !investor.address}
                  <p class="text-neutral-400 text-sm">No contact information</p>
                {/if}
              </div>
            {/if}
          </div>

          {#if editing || investor.notes}
            <div class="bg-white rounded-xl border border-neutral-200 p-6">
              <h3 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-4">Notes</h3>
              {#if editing}
                <textarea bind:value={formData.notes} rows="4" placeholder="Internal notes..." class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"></textarea>
              {:else}
                <p class="text-sm text-neutral-700 whitespace-pre-line">{investor.notes}</p>
              {/if}
            </div>
          {/if}
        </div>

        <!-- Summary Sidebar -->
        <div class="space-y-4">
          <div class="bg-white border border-neutral-200 rounded-xl p-4">
            <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Investments</div>
            <div class="text-2xl font-bold text-neutral-800">{investor.investment_count}</div>
          </div>
          <div class="bg-white border border-neutral-200 rounded-xl p-4">
            <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Capital Invested</div>
            <div class="text-2xl font-bold text-neutral-800">{currency.formatCompact(totalInvestedDisplay)}</div>
          </div>
        </div>
      </div>
    {:else if activeTab === "investments"}
      <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
        {#if investments.length === 0}
          <div class="text-center py-16">
            <p class="text-neutral-400 text-sm">No investments yet</p>
          </div>
        {:else}
          <table class="w-full">
            <thead class="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Project</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Ownership</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Contributed</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Returned</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Profit Dist.</th>
                <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Unreturned</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each investments as inv (inv.id)}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-4 py-3 text-sm text-neutral-800 font-medium">{inv.project_name || (inv.project ? `Project #${inv.project}` : "Project")}</td>
                  <td class="px-4 py-3 text-right text-sm text-neutral-800">{inv.ownership_percentage}%</td>
                  <td class="px-4 py-3 text-right text-sm text-neutral-800">{currency.format(inv.capital_contributed)}</td>
                  <td class="px-4 py-3 text-right text-sm text-neutral-600">{currency.format(inv.total_capital_returned)}</td>
                  <td class="px-4 py-3 text-right text-sm text-emerald-600">{currency.format(inv.total_profit_distributed)}</td>
                  <td class="px-4 py-3 text-right text-sm font-medium text-neutral-800">{currency.format(inv.unreturned_capital)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    {/if}
  </div>
{/if}

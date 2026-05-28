<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type { Investor, InvestorListItem, InvestorType, PaginatedResponse } from "$lib/types";

  let investors = $state<InvestorListItem[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let filterType = $state<string>("");
  let filterActive = $state<string>("");

  // Create drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      name: "",
      investor_type: "individual" as InvestorType,
      contact_person: "",
      email: "",
      phone: "",
      address: "",
      tax_id: "",
      entity_name: "",
      registration_number: "",
      notes: "",
      is_active: true,
    };
  }

  function devFillInvestor() {
    form = {
      name: "Meridian Capital Partners",
      investor_type: "institutional",
      contact_person: "Chief Emeka Okafor",
      email: "emeka@meridiancapital.ng",
      phone: "+234 803 555 1234",
      address: "14 Kofo Abayomi Street, Victoria Island, Lagos",
      tax_id: "TIN-98765432",
      entity_name: "Meridian Capital Partners Ltd",
      registration_number: "RC-2019-04872",
      notes: "Primary focus on mixed-use developments in Lagos and Abuja. Typical ticket size: ₦500M-₦2B. Board seat required for investments above ₦1B.",
      is_active: true,
    };
  }

  function toAmount(value: string | number | null | undefined): number {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    if (typeof value === "string") {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
  }

  async function loadInvestors() {
    loading = true;
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append("search", searchQuery);
      if (filterType) params.append("investor_type", filterType);
      if (filterActive) params.append("is_active", filterActive);
      params.append("page_size", "100");

      const data = await api.get<PaginatedResponse<InvestorListItem>>(
        `/finance/investors/?${params}`
      );
      investors = Array.isArray(data.results) ? data.results : [];
    } catch {
      toast.error("Error", "Could not load investors.");
    } finally {
      loading = false;
    }
  }

  async function saveInvestor(event: Event) {
    event.preventDefault();
    if (!form.name.trim()) {
      toast.error("Validation error", "Investor name is required.");
      return;
    }
    saving = true;
    try {
      await api.post<Investor>("/finance/investors/", {
        ...form,
        name: form.name.trim(),
        contact_person: form.contact_person.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        address: form.address.trim(),
        tax_id: form.tax_id.trim(),
        entity_name: form.entity_name.trim(),
        registration_number: form.registration_number.trim(),
        notes: form.notes.trim(),
      });
      toast.success("Investor created", `"${form.name}" has been added.`);
      createOpen = false;
      form = defaultForm();
      await loadInvestors();
    } catch (error) {
      if (error instanceof ApiError) {
        const firstField = Object.values(error.fieldErrors)[0]?.[0];
        toast.error("Could not create investor", firstField ?? "Please check the form.");
      } else {
        toast.error("Could not create investor", "An unexpected error occurred.");
      }
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    loadInvestors();
  });

  const investorTypeLabels: Record<string, string> = {
    individual: "Individual",
    institutional: "Institutional",
    family_office: "Family Office",
    fund: "Fund",
    corporate: "Corporate",
  };
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-800">Investors</h1>
      <p class="text-sm text-neutral-500 mt-1">Manage external investors and capital sources</p>
    </div>
    <button
      onclick={() => { form = defaultForm(); createOpen = true; }}
      class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      Add Investor
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white border border-neutral-200 rounded-xl p-4">
    <div class="flex items-center gap-4 flex-wrap">
      <div class="flex-1 min-w-[240px]">
        <input
          type="text"
          bind:value={searchQuery}
          onkeydown={(e) => e.key === "Enter" && loadInvestors()}
          placeholder="Search investors..."
          class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
      </div>
      <select
        bind:value={filterType}
        onchange={loadInvestors}
        class="border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
      >
        <option value="">All Types</option>
        <option value="individual">Individual</option>
        <option value="institutional">Institutional</option>
        <option value="family_office">Family Office</option>
        <option value="fund">Fund</option>
        <option value="corporate">Corporate</option>
      </select>
      <select
        bind:value={filterActive}
        onchange={loadInvestors}
        class="border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
      >
        <option value="">All Status</option>
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>
      <button
        onclick={loadInvestors}
        class="px-4 py-2 bg-neutral-100 text-neutral-700 text-sm font-medium rounded-lg hover:bg-neutral-200 transition-colors"
      >
        Search
      </button>
    </div>
  </div>

  <!-- Summary Cards -->
  {#if !loading}
    {@const totalInvested = investors.reduce((sum, inv) => sum + toAmount(inv.total_invested), 0)}
    {@const activeCount = investors.filter((inv) => inv.is_active).length}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-white border border-neutral-200 rounded-xl p-4">
        <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Investors</div>
        <div class="text-2xl font-bold text-neutral-800">{investors.length}</div>
      </div>
      <div class="bg-white border border-neutral-200 rounded-xl p-4">
        <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Active</div>
        <div class="text-2xl font-bold text-neutral-800">{activeCount}</div>
      </div>
      <div class="bg-white border border-neutral-200 rounded-xl p-4">
        <div class="text-xs font-medium text-neutral-500 uppercase tracking-wider mb-1">Total Invested</div>
        <div class="text-2xl font-bold text-neutral-800">{currency.format(totalInvested)}</div>
      </div>
    </div>
  {/if}

  <!-- Table -->
  <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-16">
        <div class="w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if investors.length === 0}
      <div class="text-center py-16">
        <svg class="w-12 h-12 mx-auto mb-3 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
        </svg>
        <p class="text-neutral-400 text-sm">No investors found</p>
        <button onclick={() => { form = defaultForm(); createOpen = true; }} class="mt-4 inline-block text-sm font-medium text-neutral-800 hover:underline">
          Add your first investor
        </button>
      </div>
    {:else}
      <table class="w-full">
        <thead class="bg-neutral-50 border-b border-neutral-200">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Investor</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Type</th>
            <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Contact</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Investments</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Total Invested</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-neutral-500 uppercase tracking-wider">Status</th>
            <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each investors as investor (investor.id)}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-4 py-3">
                <a href={`/finance/investors/${investor.id}`} class="font-medium text-neutral-800 hover:text-neutral-600 transition-colors">
                  {investor.name}
                </a>
              </td>
              <td class="px-4 py-3 text-sm text-neutral-500">
                {investorTypeLabels[investor.investor_type] || investor.investor_type}
              </td>
              <td class="px-4 py-3 text-sm text-neutral-500">
                <div>{investor.contact_person || "—"}</div>
                {#if investor.email}
                  <div class="text-xs text-neutral-400">{investor.email}</div>
                {/if}
              </td>
              <td class="px-4 py-3 text-right text-sm text-neutral-800">
                {investor.investment_count}
              </td>
              <td class="px-4 py-3 text-right text-sm font-medium text-neutral-800">
                {currency.format(toAmount(investor.total_invested))}
              </td>
              <td class="px-4 py-3 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {investor.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-500'}">
                  {investor.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <a
                  href={`/finance/investors/${investor.id}`}
                  class="text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors"
                >
                  View
                </a>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

<!-- ═══════════ CREATE INVESTOR DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Add Investor" subtitle="Create an external investor profile" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={saveInvestor} class="p-6 space-y-4">
    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Investor Name *</span>
      <input bind:value={form.name} placeholder="Full name or entity" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span>
        <select bind:value={form.investor_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
          <option value="individual">Individual</option>
          <option value="institutional">Institutional</option>
          <option value="family_office">Family Office</option>
          <option value="fund">Fund</option>
          <option value="corporate">Corporate</option>
        </select>
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Entity Name</span>
        <input bind:value={form.entity_name} placeholder="Legal entity" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
      </label>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Contact Person</span>
        <input bind:value={form.contact_person} placeholder="Full name" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Email</span>
        <input type="email" bind:value={form.email} placeholder="name@company.com" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Phone</span>
      <input bind:value={form.phone} placeholder="+234 800 000 0000" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Tax ID</span>
        <input bind:value={form.tax_id} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Registration #</span>
        <input bind:value={form.registration_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Address</span>
      <textarea bind:value={form.address} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"></textarea>
    </label>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
      <textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"></textarea>
    </label>

    <label class="flex items-center gap-2">
      <input type="checkbox" bind:checked={form.is_active} class="rounded border-neutral-300" />
      <span class="text-xs font-medium text-neutral-600">Active investor</span>
    </label>

    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}
        <button type="button" onclick={devFillInvestor} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
      {/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
        {saving ? "Saving..." : "Create Investor"}
      </button>
    </div>
  </form>
</DrawerShell>

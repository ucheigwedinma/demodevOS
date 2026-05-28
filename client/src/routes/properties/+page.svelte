<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import type { PropertyListItem, PaginatedResponse } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";

  let data = $state<PropertyListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let typeFilter = $state("");
  let classificationFilter = $state("");
  let activeFilter = $state("");
  let loading = $state(true);

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  function pageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | "...")[] = [1];
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  const typeLabels: Record<string, string> = {
    land: "Land",
    building: "Building",
    mixed: "Mixed-Use",
    estate: "Estate",
    warehouse: "Warehouse",
    industrial: "Industrial",
  };

  const classificationLabels: Record<string, string> = {
    owned: "Owned",
    lease: "Lease",
    concession: "Concession",
    under_development: "Under Development",
  };

  async function fetchProperties() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (typeFilter) params.property_type = typeFilter;
      if (classificationFilter) params.classification = classificationFilter;
      if (activeFilter) params.is_active = activeFilter;

      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => {
    void searchQuery;
    void typeFilter;
    void classificationFilter;
    void activeFilter;
    void currentPage;
    fetchProperties();
  });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
      currentPage = 1;
    }, 300);
  }

  function formatCurrency(value: string | null): string {
    if (!value) return "\u2014";
    return currency.formatCompact(value);
  }

  function formatArea(value: string | null): string {
    if (!value) return "\u2014";
    return Number(value).toLocaleString() + " sqft";
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Properties</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage your property portfolio</p>
    </div>
    <a
      href="/properties/new"
      class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + Add Property
    </a>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input
        type="text"
        placeholder="Search properties..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={typeFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Types</option>
      <option value="land">Land</option>
      <option value="building">Building</option>
      <option value="mixed">Mixed-Use</option>
      <option value="estate">Estate</option>
      <option value="warehouse">Warehouse</option>
      <option value="industrial">Industrial</option>
    </select>
    <select
      bind:value={classificationFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Classifications</option>
      <option value="owned">Owned</option>
      <option value="lease">Lease</option>
      <option value="concession">Concession</option>
      <option value="under_development">Under Development</option>
    </select>
    <select
      bind:value={activeFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Status</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading properties...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3H21m-3.75 3H21" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-900">No properties found</p>
        <p class="mt-1 text-sm text-neutral-400">Get started by adding your first property.</p>
        <a
          href="/properties/new"
          class="inline-block mt-4 px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + Add Property
        </a>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Classification</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Address</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Value</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Area</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Units</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as property}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => goto(`/properties/${property.id}`)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-900">{property.name}</span>
              </td>
              <td class="px-5 py-4">
                <StatusBadge status={property.property_type} label={typeLabels[property.property_type] ?? property.property_type} />
              </td>
              <td class="px-5 py-4">
                <StatusBadge status={property.classification} label={classificationLabels[property.classification] ?? property.classification} />
              </td>
              <td class="px-5 py-4 text-neutral-500 max-w-xs truncate">{property.address}</td>
              <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(property.current_value)}</td>
              <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{formatArea(property.total_area_sqft)}</td>
              <td class="px-5 py-4 text-center text-neutral-500">{property.unit_count}</td>
              <td class="px-5 py-4 text-center">
                {#if property.is_active}
                  <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-900">
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-900"></span>
                    Active
                  </span>
                {:else}
                  <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400">
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-300"></span>
                    Inactive
                  </span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <!-- Pagination -->
  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">
        Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "property" : "properties"}
      </p>

      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button
            onclick={() => currentPage--}
            disabled={currentPage <= 1}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>

          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300">...</span>
            {:else}
              <button
                onclick={() => (currentPage = pg)}
                class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors
                       {currentPage === pg
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100'}"
              >
                {pg}
              </button>
            {/if}
          {/each}

          <button
            onclick={() => currentPage++}
            disabled={currentPage >= totalPages}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

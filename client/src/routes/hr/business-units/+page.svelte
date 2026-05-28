<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { DivisionListItem, PaginatedResponse } from "$lib/types";

  let divisions = $state<DivisionListItem[]>([]);
  let loading = $state(true);
  let searchQuery = $state("");
  let expandedDivisionId = $state<number | null>(null);
  let savingDivisionId = $state<number | null>(null);
  let metadataDrafts = $state<Record<number, { unit_category: "profit_center" | "cost_center"; location_region: string }>>({});

  function formatAmount(value: string): string {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return value || "0";
    return numeric.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function seedDrafts(items: DivisionListItem[]) {
    const next: Record<number, { unit_category: "profit_center" | "cost_center"; location_region: string }> = {};
    for (const division of items) {
      next[division.id] = {
        unit_category: division.unit_category ?? "cost_center",
        location_region: division.location_region ?? "",
      };
    }
    metadataDrafts = next;
  }

  async function fetchDivisions() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (searchQuery) params.search = searchQuery;
      const res = await api.get<PaginatedResponse<DivisionListItem>>("/settings/divisions/", params);
      divisions = res.results;
      seedDrafts(res.results);
    } catch {
      divisions = [];
      metadataDrafts = {};
    } finally {
      loading = false;
    }
  }

  async function saveOperationalMetadata(division: DivisionListItem) {
    const draft = metadataDrafts[division.id];
    if (!draft || savingDivisionId) return;
    savingDivisionId = division.id;
    try {
      await api.patch(`/settings/divisions/${division.id}/`, {
        unit_category: draft.unit_category,
        location_region: draft.location_region.trim(),
      });
      toast.success("Business unit metadata updated");
      await fetchDivisions();
    } catch {
      toast.error("Unable to update business unit metadata");
    } finally {
      savingDivisionId = null;
    }
  }

  function toggleExpanded(divisionId: number) {
    expandedDivisionId = expandedDivisionId === divisionId ? null : divisionId;
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchDivisions, 300);
  }

  $effect(() => {
    fetchDivisions();
  });
</script>

<div class="max-w-7xl mx-auto">
  <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Business Units</h1>
      <p class="mt-1 text-sm text-neutral-500">Top-level organizational divisions with operational metadata</p>
    </div>
  </div>

  <section class="mb-6 rounded-xl border border-neutral-200 bg-white p-4">
    <h2 class="text-sm font-semibold text-neutral-900">Operational Metadata</h2>
    <p class="mt-1 text-xs text-neutral-500">
      Unit category and location are editable. Headcount and annual operating budget are read-only and synced from HR and Finance.
    </p>
  </section>

  <div class="mb-6">
    <div class="relative max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input
        type="text"
        placeholder="Search business units..."
        value={searchQuery}
        oninput={(e) => handleSearch(e.currentTarget.value)}
        class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if divisions.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">No business units found</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Name</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Code</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Head</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Category</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="text-right px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Details</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each divisions as division}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-3.5">
                <span class="font-medium text-neutral-900">{division.name}</span>
              </td>
              <td class="px-5 py-3.5">
                <span class="font-mono text-xs text-neutral-500">{division.code}</span>
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{division.head_name ?? "\u2014"}</td>
              <td class="px-5 py-3.5">
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {division.unit_category === 'profit_center' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">
                  {division.unit_category_display}
                </span>
              </td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {division.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
                  {division.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td class="px-5 py-3.5 text-right">
                <button
                  type="button"
                  onclick={() => toggleExpanded(division.id)}
                  class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100 transition-colors"
                >
                  {expandedDivisionId === division.id ? "Hide metadata" : "Operational metadata"}
                </button>
              </td>
            </tr>
            {#if expandedDivisionId === division.id}
              <tr class="bg-neutral-50/40">
                <td colspan="6" class="px-5 py-4">
                  <div class="rounded-lg border border-neutral-200 bg-white p-4">
                    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                      <div>
                        <label for="unit-category-{division.id}" class="block text-xs font-medium uppercase tracking-wider text-neutral-500 mb-1.5">Unit Category</label>
                        <select
                          id="unit-category-{division.id}"
                          value={metadataDrafts[division.id]?.unit_category ?? "cost_center"}
                          onchange={(event) => {
                            const next = { ...metadataDrafts };
                            const draft = next[division.id] ?? { unit_category: "cost_center", location_region: "" };
                            draft.unit_category = event.currentTarget.value as "profit_center" | "cost_center";
                            next[division.id] = draft;
                            metadataDrafts = next;
                          }}
                          class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900"
                        >
                          <option value="cost_center">Cost Center</option>
                          <option value="profit_center">Profit Center</option>
                        </select>
                      </div>
                      <div>
                        <label for="location-region-{division.id}" class="block text-xs font-medium uppercase tracking-wider text-neutral-500 mb-1.5">Location / Region</label>
                        <input
                          id="location-region-{division.id}"
                          type="text"
                          value={metadataDrafts[division.id]?.location_region ?? ""}
                          oninput={(event) => {
                            const next = { ...metadataDrafts };
                            const draft = next[division.id] ?? { unit_category: "cost_center", location_region: "" };
                            draft.location_region = event.currentTarget.value;
                            next[division.id] = draft;
                            metadataDrafts = next;
                          }}
                          placeholder="e.g. Lagos HQ / West Region"
                          class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900"
                        />
                      </div>
                      <div>
                        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500 mb-1.5">Total Headcount</p>
                        <p class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold text-neutral-900">
                          {division.total_headcount}
                        </p>
                      </div>
                      <div>
                        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500 mb-1.5">Operating Budget (Annual)</p>
                        <p class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm font-semibold text-neutral-900">
                          {formatAmount(division.operating_budget)}
                        </p>
                      </div>
                    </div>
                    <div class="mt-4 flex flex-wrap items-center justify-end gap-2">
                      <button
                        type="button"
                        onclick={() => saveOperationalMetadata(division)}
                        disabled={savingDivisionId === division.id}
                        class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
                      >
                        {savingDivisionId === division.id ? "Saving..." : "Save metadata"}
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

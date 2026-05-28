<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PortfolioAnalytics, TypeDistributionItem, ClassificationBreakdownItem, UnitOccupancyItem, PropertyGainItem } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let loading = $state(true);
  let data = $state<PortfolioAnalytics | null>(null);

  $effect(() => {
    api.get<PortfolioAnalytics>("/analytics/portfolio/")
      .then((res) => { data = res; })
      .catch(() => { toast.error("Error", "Could not load portfolio data"); })
      .finally(() => { loading = false; });
  });

  function fmt(value: string | null): string {
    if (!value || value === "0" || value === "0.00") return currency.formatCompact(0);
    const n = Number(value);
    return currency.formatAbbreviated(n);
  }

  function fmtArea(value: string | null): string {
    if (!value || value === "0" || value === "0.00") return "0";
    return Number(value).toLocaleString();
  }

  function pct(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }

  function maxValue(items: { total_value: string }[]): number {
    return Math.max(...items.map((i) => Number(i.total_value)), 1);
  }

  const typeLabels: Record<string, string> = {
    land: "Land", building: "Building", mixed: "Mixed-Use",
    estate: "Estate", warehouse: "Warehouse", industrial: "Industrial",
  };

  const classLabels: Record<string, string> = {
    owned: "Owned", lease: "Lease", concession: "Concession",
    under_development: "Under Development",
  };

  const unitStatusLabels: Record<string, string> = {
    available: "Available", reserved: "Reserved", sold: "Sold", leased: "Leased",
  };

  const typeColors: Record<string, string> = {
    land: "bg-amber-500", building: "bg-neutral-700", mixed: "bg-violet-500",
    estate: "bg-emerald-500", warehouse: "bg-orange-400", industrial: "bg-slate-400",
  };

  const classColors: Record<string, string> = {
    owned: "bg-neutral-800", lease: "bg-neutral-500", concession: "bg-neutral-400",
    under_development: "bg-neutral-300",
  };

  const unitStatusColors: Record<string, string> = {
    available: "bg-emerald-500", reserved: "bg-amber-400", sold: "bg-neutral-700", leased: "bg-blue-500",
  };
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if data}
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Portfolio Segmentation</h1>
      <p class="text-sm text-neutral-400 mt-1">Property portfolio breakdown by type, classification, and performance</p>
    </div>

    <!-- KPI Strip -->
    <div class="grid grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Properties</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1 tabular-nums">{data.kpis.property_count}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Value</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1 tabular-nums">{fmt(data.kpis.total_value)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Area</p>
        <p class="text-2xl font-bold text-neutral-900 mt-1 tabular-nums">{fmtArea(data.kpis.total_area_sqft)} <span class="text-sm font-normal text-neutral-400">sqft</span></p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Unrealized Gain</p>
        <p class="text-2xl font-bold tabular-nums mt-1 {Number(data.kpis.unrealized_gain) >= 0 ? 'text-neutral-900' : 'text-red-600'}">{fmt(data.kpis.unrealized_gain)}</p>
      </div>
    </div>

    <!-- Two-column segmentation -->
    <div class="grid grid-cols-2 gap-6">

      <!-- By Property Type -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">By Property Type</h2>
        {#if data.type_distribution.length === 0}
          <p class="text-sm text-neutral-400 py-8 text-center">No properties yet</p>
        {:else}
          <!-- Stacked bar -->
          <div class="flex rounded-full h-3 overflow-hidden mb-6">
            {#each data.type_distribution as seg}
              {@const width = pct(seg.count, data.kpis.property_count)}
              {#if width > 0}
                <div class="{typeColors[seg.type] ?? 'bg-neutral-300'}" style="width: {width}%"></div>
              {/if}
            {/each}
          </div>
          <!-- Breakdown rows -->
          <div class="space-y-4">
            {#each data.type_distribution as seg}
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span class="w-2.5 h-2.5 rounded-full shrink-0 {typeColors[seg.type] ?? 'bg-neutral-300'}"></span>
                  <span class="text-sm font-medium text-neutral-900">{typeLabels[seg.type] ?? seg.type}</span>
                </div>
                <div class="flex items-center gap-6">
                  <span class="text-xs text-neutral-400 tabular-nums w-20 text-right">{fmtArea(seg.total_area)} sqft</span>
                  <span class="text-sm font-medium text-neutral-900 tabular-nums w-20 text-right">{fmt(seg.total_value)}</span>
                  <span class="text-xs font-semibold text-neutral-500 tabular-nums w-12 text-right">{seg.count} <span class="font-normal text-neutral-400">{seg.count === 1 ? 'prop' : 'props'}</span></span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- By Classification -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">By Classification</h2>
        {#if data.classification_breakdown.length === 0}
          <p class="text-sm text-neutral-400 py-8 text-center">No properties yet</p>
        {:else}
          <!-- Stacked bar -->
          <div class="flex rounded-full h-3 overflow-hidden mb-6">
            {#each data.classification_breakdown as seg}
              {@const width = pct(seg.count, data.kpis.property_count)}
              {#if width > 0}
                <div class="{classColors[seg.classification] ?? 'bg-neutral-300'}" style="width: {width}%"></div>
              {/if}
            {/each}
          </div>
          <!-- Breakdown rows -->
          <div class="space-y-4">
            {#each data.classification_breakdown as seg}
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span class="w-2.5 h-2.5 rounded-full shrink-0 {classColors[seg.classification] ?? 'bg-neutral-300'}"></span>
                  <span class="text-sm font-medium text-neutral-900">{classLabels[seg.classification] ?? seg.classification}</span>
                </div>
                <div class="flex items-center gap-6">
                  <span class="text-sm font-medium text-neutral-900 tabular-nums w-20 text-right">{fmt(seg.total_value)}</span>
                  <span class="text-xs font-semibold text-neutral-500 tabular-nums w-12 text-right">{seg.count} <span class="font-normal text-neutral-400">{seg.count === 1 ? 'prop' : 'props'}</span></span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Unit Occupancy -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">Unit Occupancy</h2>
        {#if data.unit_occupancy.length === 0}
          <p class="text-sm text-neutral-400 py-8 text-center">No units yet</p>
        {:else}
          {@const totalUnits = data.unit_occupancy.reduce((s, u) => s + u.count, 0)}
          <!-- Stacked bar -->
          <div class="flex rounded-full h-3 overflow-hidden mb-6">
            {#each data.unit_occupancy as seg}
              {@const width = pct(seg.count, totalUnits)}
              {#if width > 0}
                <div class="{unitStatusColors[seg.status] ?? 'bg-neutral-300'}" style="width: {width}%"></div>
              {/if}
            {/each}
          </div>
          <!-- Breakdown rows -->
          <div class="space-y-4">
            {#each data.unit_occupancy as seg}
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span class="w-2.5 h-2.5 rounded-full shrink-0 {unitStatusColors[seg.status] ?? 'bg-neutral-300'}"></span>
                  <span class="text-sm font-medium text-neutral-900">{unitStatusLabels[seg.status] ?? seg.status}</span>
                </div>
                <div class="flex items-center gap-6">
                  <span class="text-xs text-neutral-400 tabular-nums w-20 text-right">{fmtArea(seg.total_area)} sqft</span>
                  <span class="text-sm font-medium text-neutral-900 tabular-nums w-20 text-right">{fmt(seg.total_asking_price)}</span>
                  <span class="text-xs font-semibold text-neutral-500 tabular-nums w-12 text-right">{seg.count} <span class="font-normal text-neutral-400">{seg.count === 1 ? 'unit' : 'units'}</span></span>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Encumbrances -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">Encumbrances</h2>
        {#if data.encumbrance_summary.total_count === 0}
          <div class="py-8 text-center">
            <div class="w-10 h-10 mx-auto rounded-full bg-neutral-100 flex items-center justify-center mb-3">
              <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
              </svg>
            </div>
            <p class="text-sm text-neutral-400">No active encumbrances</p>
          </div>
        {:else}
          <div class="flex items-center justify-between mb-5 pb-4 border-b border-neutral-100">
            <span class="text-sm text-neutral-500">{data.encumbrance_summary.total_count} active</span>
            <span class="text-sm font-semibold text-neutral-900 tabular-nums">{fmt(data.encumbrance_summary.total_amount)}</span>
          </div>
          <div class="space-y-3">
            {#each data.encumbrance_summary.by_type as enc}
              {@const barWidth = pct(Number(enc.total_amount), Number(data.encumbrance_summary.total_amount))}
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-sm text-neutral-700 capitalize">{enc.type.replace(/_/g, " ")}</span>
                  <div class="flex items-center gap-3">
                    <span class="text-sm font-medium text-neutral-900 tabular-nums">{fmt(enc.total_amount)}</span>
                    <span class="text-xs text-neutral-400 tabular-nums w-8 text-right">{enc.count}</span>
                  </div>
                </div>
                <div class="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                  <div class="h-full bg-neutral-400 rounded-full" style="width: {barWidth}%"></div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Top Performers -->
    <div class="grid grid-cols-2 gap-6">
      <!-- Top Appreciating -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">Top Appreciating</h2>
        {#if data.top_appreciating.length === 0}
          <p class="text-sm text-neutral-400 py-6 text-center">No data available</p>
        {:else}
          <div class="space-y-3">
            {#each data.top_appreciating as prop, i}
              <a href="/properties/{prop.id}" class="flex items-center gap-4 p-3 -mx-1 rounded-lg hover:bg-neutral-50 transition-colors group">
                <div class="w-7 h-7 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-semibold text-neutral-500 shrink-0 group-hover:bg-neutral-900 group-hover:text-white transition-colors">
                  {i + 1}
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-900 truncate">{prop.name}</p>
                  <p class="text-xs text-neutral-400 capitalize">{prop.property_type}</p>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmt(prop.gain)}</p>
                  <p class="text-xs font-medium text-neutral-500 tabular-nums">+{Number(prop.gain_pct).toFixed(1)}%</p>
                </div>
              </a>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Top Depreciating -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">Top Depreciating</h2>
        {#if data.top_depreciating.length === 0}
          <p class="text-sm text-neutral-400 py-6 text-center">No depreciating properties</p>
        {:else}
          <div class="space-y-3">
            {#each data.top_depreciating as prop, i}
              <a href="/properties/{prop.id}" class="flex items-center gap-4 p-3 -mx-1 rounded-lg hover:bg-neutral-50 transition-colors group">
                <div class="w-7 h-7 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-semibold text-neutral-500 shrink-0 group-hover:bg-neutral-900 group-hover:text-white transition-colors">
                  {i + 1}
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-900 truncate">{prop.name}</p>
                  <p class="text-xs text-neutral-400 capitalize">{prop.property_type}</p>
                </div>
                <div class="text-right shrink-0">
                  <p class="text-sm font-semibold text-red-600 tabular-nums">{fmt(prop.gain)}</p>
                  <p class="text-xs font-medium text-red-500 tabular-nums">{Number(prop.gain_pct).toFixed(1)}%</p>
                </div>
              </a>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Valuation History -->
    {#if data.valuation_history.length > 0}
      {@const maxVal = Math.max(...data.valuation_history.map((v) => Number(v.total_value)), 1)}
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-5">Valuation Trend</h2>
        <div class="flex items-end gap-1.5 h-40">
          {#each data.valuation_history as point}
            {@const height = (Number(point.total_value) / maxVal) * 100}
            <div class="flex-1 flex flex-col items-center gap-1.5 group relative">
              <div class="absolute bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div class="bg-neutral-900 text-white text-xs rounded-md px-2 py-1 whitespace-nowrap tabular-nums">
                  {fmt(point.total_value)}
                </div>
              </div>
              <div
                class="w-full bg-neutral-200 group-hover:bg-neutral-900 rounded-t transition-colors"
                style="height: {Math.max(height, 2)}%"
              ></div>
              <span class="text-[10px] text-neutral-400 tabular-nums">{point.month.slice(5)}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}

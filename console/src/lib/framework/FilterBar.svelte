<script lang="ts">
  import type { FilterDef } from "./types";

  let {
    filters = [],
    values = {},
    onFilterChange,
  }: {
    filters: FilterDef[];
    values: Record<string, string>;
    onFilterChange: (key: string, value: string) => void;
  } = $props();
</script>

{#if filters.length > 0}
  <div class="flex items-center gap-3 flex-wrap">
    {#each filters as filter}
      {#if filter.type === "search"}
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="text"
            value={values[filter.key] ?? ""}
            oninput={(e) => onFilterChange(filter.key, e.currentTarget.value)}
            placeholder={filter.placeholder ?? "Search..."}
            class="pl-9 pr-3 py-2 text-sm border border-neutral-200 rounded-lg w-64
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
        </div>
      {:else if filter.type === "select" && filter.options}
        <select
          value={values[filter.key] ?? ""}
          onchange={(e) => onFilterChange(filter.key, e.currentTarget.value)}
          class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">{filter.label}: All</option>
          {#each filter.options as opt}
            <option value={opt.value}>{opt.label}</option>
          {/each}
        </select>
      {/if}
    {/each}
  </div>
{/if}

<script lang="ts">
  import type { WidgetType } from "$lib/types";
  import { WIDGET_CATALOG, type WidgetGroup } from "$lib/dashboard/widget-catalog";

  let { onadd }: { onadd: (widgetType: WidgetType, kpiKey?: string) => void } = $props();

  const groups: { key: WidgetGroup; label: string }[] = [
    { key: "board_kpi", label: "Board KPIs" },
    { key: "portfolio", label: "Portfolio" },
    { key: "finance", label: "Finance" },
    { key: "operations", label: "Operations" },
  ];

  function widgetsFor(group: WidgetGroup) {
    return WIDGET_CATALOG.filter((entry) => entry.group === group);
  }
</script>

<div class="space-y-5">
  {#each groups as group}
    {@const items = widgetsFor(group.key)}
    {#if items.length > 0}
      <div>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-2">{group.label}</h3>
        <div class="space-y-1">
          {#each items as widget}
            <button
              onclick={() => onadd(widget.type, widget.kpiKey)}
              class="w-full flex items-center gap-2 rounded-lg border border-neutral-100 bg-white px-3 py-2 text-left text-xs text-neutral-700 hover:bg-neutral-50 hover:border-neutral-200 transition-colors"
            >
              <svg class="w-3.5 h-3.5 text-neutral-400 shrink-0" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              {widget.label}
            </button>
          {/each}
        </div>
      </div>
    {/if}
  {/each}
</div>

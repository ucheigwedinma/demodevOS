<script lang="ts">
  import { pie, arc } from "d3-shape";

  let {
    data,
    labelKey = "label",
    valueKey = "value",
    colors = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316", "#ec4899"],
    centerLabel = "",
    centerValue = "",
    size = 240,
    showLegend = true,
    formatValue = (value: number) => String(value),
  }: {
    data: Record<string, any>[];
    labelKey?: string;
    valueKey?: string;
    colors?: string[];
    centerLabel?: string;
    centerValue?: string;
    size?: number;
    showLegend?: boolean;
    formatValue?: (value: number) => string;
  } = $props();

  const radius = $derived(size / 2);
  const innerRadius = $derived(radius * 0.6);

  const pieGen = pie<Record<string, any>>()
    .value((d) => Number(d[valueKey]))
    .sort(null);

  const arcGen = $derived(
    arc<any>()
      .innerRadius(innerRadius)
      .outerRadius(radius - 4)
      .cornerRadius(3)
      .padAngle(0.02)
  );

  const arcs = $derived(data.length > 0 ? pieGen(data) : []);
</script>

<div class="flex items-center gap-6">
  <div style="width: {size}px; height: {size}px;" class="shrink-0 relative">
    {#if arcs.length > 0}
      <svg width={size} height={size} class="font-sans">
        <g transform="translate({radius}, {radius})">
          {#each arcs as a, i}
            <path
              d={arcGen(a) ?? ""}
              fill={colors[i % colors.length]}
            >
              <title>{a.data[labelKey]}: {formatValue(Number(a.data[valueKey]))}</title>
            </path>
          {/each}
        </g>
      </svg>
      {#if centerLabel || centerValue}
        <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          {#if centerValue}<span class="text-lg font-bold text-neutral-900">{centerValue}</span>{/if}
          {#if centerLabel}<span class="text-[10px] text-neutral-400 uppercase tracking-wider">{centerLabel}</span>{/if}
        </div>
      {/if}
    {:else}
      <div class="h-full flex items-center justify-center">
        <p class="text-sm text-neutral-400">No data</p>
      </div>
    {/if}
  </div>

  <!-- Legend -->
  {#if showLegend && data.length > 0}
    <div class="flex flex-col gap-2">
      {#each data as d, i}
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-sm shrink-0" style="background: {colors[i % colors.length]};"></div>
          <span class="text-xs text-neutral-600">{d[labelKey]}</span>
          <span class="text-xs text-neutral-400 tabular-nums ml-auto">{formatValue(Number(d[valueKey]))}</span>
        </div>
      {/each}
    </div>
  {/if}
</div>

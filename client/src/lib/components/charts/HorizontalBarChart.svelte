<script lang="ts">
  import { scaleBand, scaleLinear } from "d3-scale";

  let {
    data,
    labelKey = "label",
    valueKey = "value",
    formatValue = (d: number) => String(d),
    colors = ["#6366f1", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4", "#f97316", "#ec4899"],
    height = 280,
  }: {
    data: Record<string, any>[];
    labelKey?: string;
    valueKey?: string;
    formatValue?: (d: number) => string;
    colors?: string[];
    height?: number;
  } = $props();

  const padding = { top: 8, right: 60, bottom: 8, left: 120 };

  const innerWidth = $derived(400 - padding.left - padding.right);
  const innerHeight = $derived(Math.max(height - padding.top - padding.bottom, 0));

  const yScale = $derived(
    scaleBand<string>()
      .domain(data.map((d) => d[labelKey]))
      .range([0, innerHeight])
      .padding(0.3)
  );

  const xScale = $derived(
    scaleLinear()
      .domain([0, Math.max(...data.map((d) => Number(d[valueKey])), 1)])
      .nice()
      .range([0, innerWidth])
  );
</script>

<div style="height: {height}px;" class="overflow-hidden">
  {#if data.length > 0}
    <svg width="100%" height="{height}" viewBox="0 0 400 {height}" preserveAspectRatio="xMidYMid meet" class="font-sans">
      <g transform="translate({padding.left}, {padding.top})">
        {#each data as d, i}
          {@const y = yScale(d[labelKey]) ?? 0}
          {@const barWidth = xScale(Number(d[valueKey]))}
          {@const barHeight = yScale.bandwidth()}
          <rect
            x={0}
            {y}
            width={Math.max(barWidth, 0)}
            height={barHeight}
            rx={3}
            fill={colors[i % colors.length]}
          />
          <text
            x={-8}
            y={y + barHeight / 2}
            dy="0.35em"
            text-anchor="end"
            class="text-[11px] fill-neutral-600"
            font-family="inherit"
          >{d[labelKey]}</text>
          <text
            x={Math.max(barWidth, 0) + 6}
            y={y + barHeight / 2}
            dy="0.35em"
            text-anchor="start"
            class="text-[10px] fill-neutral-500 font-medium"
            font-family="inherit"
          >{formatValue(Number(d[valueKey]))}</text>
        {/each}
      </g>
    </svg>
  {:else}
    <div class="h-full flex items-center justify-center">
      <p class="text-sm text-neutral-400">No data available</p>
    </div>
  {/if}
</div>

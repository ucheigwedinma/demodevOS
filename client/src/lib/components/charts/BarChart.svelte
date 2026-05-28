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

  const padding = { top: 16, right: 16, bottom: 44, left: 56 };
  const svgWidth = 400;

  const innerWidth = $derived(svgWidth - padding.left - padding.right);
  const innerHeight = $derived(height - padding.top - padding.bottom);

  const xScale = $derived(
    scaleBand<string>()
      .domain(data.map((d) => d[labelKey]))
      .range([0, innerWidth])
      .padding(0.3)
  );

  const yScale = $derived(
    scaleLinear()
      .domain([0, Math.max(...data.map((d) => Number(d[valueKey])), 1)])
      .nice()
      .range([innerHeight, 0])
  );
</script>

<div style="height: {height}px;" class="overflow-hidden">
  {#if data.length > 0}
    <svg width="100%" height="{height}" viewBox="0 0 {svgWidth} {height}" preserveAspectRatio="xMidYMid meet" class="font-sans">
      <g transform="translate({padding.left}, {padding.top})">
        <!-- Grid -->
        {#each yScale.ticks(5) as tick}
          <line x1={0} y1={yScale(tick)} x2={innerWidth} y2={yScale(tick)} stroke="#f5f5f5" stroke-width="1" />
          <text x={-8} y={yScale(tick)} dy="0.32em" text-anchor="end" class="text-[10px] fill-neutral-400" font-family="inherit">{formatValue(tick)}</text>
        {/each}

        <!-- Bars -->
        {#each data as d, i}
          {@const x = xScale(d[labelKey]) ?? 0}
          {@const val = Number(d[valueKey])}
          <rect
            {x}
            y={yScale(val)}
            width={xScale.bandwidth()}
            height={innerHeight - yScale(val)}
            rx={3}
            fill={colors[i % colors.length]}
          />
          <!-- Count label on top -->
          {#if d.count !== undefined}
            <text
              x={x + xScale.bandwidth() / 2}
              y={yScale(val) - 6}
              text-anchor="middle"
              class="text-[10px] fill-neutral-500 font-medium"
              font-family="inherit"
            >{d.count}</text>
          {/if}
          <!-- X label -->
          <text
            x={x + xScale.bandwidth() / 2}
            y={innerHeight + 16}
            text-anchor="middle"
            class="text-[10px] fill-neutral-500"
            font-family="inherit"
          >{d[labelKey]}</text>
        {/each}

        <!-- Baseline -->
        <line x1={0} y1={innerHeight} x2={innerWidth} y2={innerHeight} stroke="#e5e5e5" stroke-width="1" />
      </g>
    </svg>
  {:else}
    <div class="h-full flex items-center justify-center">
      <p class="text-sm text-neutral-400">No data available</p>
    </div>
  {/if}
</div>

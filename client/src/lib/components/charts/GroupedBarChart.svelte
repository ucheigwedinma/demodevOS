<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { scaleBand, scaleLinear } from "d3-scale";

  let {
    data,
    labelKey = "label",
    value1Key = "value1",
    value2Key = "value2",
    label1 = "Planned",
    label2 = "Actual",
    color1 = "#c7d2fe",
    color2 = "#6366f1",
    formatValue = (d: number) => String(d),
    formatAxisValue = (d: number) => currency.formatAbbreviated(d),
    height = 280,
  }: {
    data: Record<string, any>[];
    labelKey?: string;
    value1Key?: string;
    value2Key?: string;
    label1?: string;
    label2?: string;
    color1?: string;
    color2?: string;
    formatValue?: (d: number) => string;
    formatAxisValue?: (d: number) => string;
    height?: number;
  } = $props();

  const padding = { top: 16, right: 16, bottom: 72, left: 84 };
  const svgWidth = 720;

  const innerWidth = $derived(svgWidth - padding.left - padding.right);
  const innerHeight = $derived(height - padding.top - padding.bottom);

  const xScale = $derived(
    scaleBand<string>()
      .domain(data.map((d) => d[labelKey]))
      .range([0, innerWidth])
      .padding(0.3)
  );

  const maxVal = $derived(
    Math.max(...data.flatMap((d) => [Number(d[value1Key]), Number(d[value2Key])]), 1)
  );

  const yScale = $derived(
    scaleLinear()
      .domain([0, maxVal])
      .nice()
      .range([innerHeight, 0])
  );

  const barWidth = $derived(Math.min(xScale.bandwidth() / 2, 24));
  const yTicks = $derived.by(() => {
    const ticks = yScale.ticks(5);
    return ticks.includes(0) ? ticks : [0, ...ticks].sort((a, b) => a - b);
  });

</script>

<div class="w-full overflow-hidden" style="height: {height}px;">
  {#if data.length > 0}
    <div class="h-full flex flex-col">
      <div class="mb-2 flex items-center justify-end gap-4 pr-1">
        <span class="inline-flex items-center gap-1.5 text-[11px] text-neutral-600">
          <span class="inline-block h-2.5 w-2.5 rounded-sm" style="background-color: {color1};"></span>
          {label1}
        </span>
        <span class="inline-flex items-center gap-1.5 text-[11px] text-neutral-600">
          <span class="inline-block h-2.5 w-2.5 rounded-sm" style="background-color: {color2};"></span>
          {label2}
        </span>
      </div>

      <div class="min-h-0 grow">
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 {svgWidth} {height}"
          preserveAspectRatio="xMidYMid meet"
          class="font-sans"
        >
          <g transform="translate({padding.left}, {padding.top})">
            <!-- Grid lines -->
            {#each yTicks as tick}
              <line
                x1={0} y1={yScale(tick)}
                x2={innerWidth} y2={yScale(tick)}
                stroke="#f5f5f5" stroke-width="1"
              />
              <text
                x={-8} y={yScale(tick)}
                dy="0.32em" text-anchor="end"
                class="text-[10px] fill-neutral-400" font-family="inherit"
              >{formatAxisValue(tick)}</text>
            {/each}

            <!-- Bars -->
            {#each data as d}
              {@const x = xScale(d[labelKey]) ?? 0}
              {@const v1 = Number(d[value1Key])}
              {@const v2 = Number(d[value2Key])}
              <rect
                x={x}
                y={yScale(v1)}
                width={barWidth}
                height={innerHeight - yScale(v1)}
                rx={2}
                fill={color1}
              />
              <rect
                x={x + barWidth}
                y={yScale(v2)}
                width={barWidth}
                height={innerHeight - yScale(v2)}
                rx={2}
                fill={color2}
              />
              <!-- Label -->
              <text
                x={x + barWidth}
                y={innerHeight + 20}
                text-anchor="middle"
                class="text-[10px] fill-neutral-500"
                font-family="inherit"
                transform="rotate(-25, {x + barWidth}, {innerHeight + 20})"
              >{d[labelKey].length > 14 ? d[labelKey].slice(0, 14) + "..." : d[labelKey]}</text>
            {/each}

            <!-- Baseline -->
            <line x1={0} y1={innerHeight} x2={innerWidth} y2={innerHeight} stroke="#e5e5e5" stroke-width="1" />
          </g>
        </svg>
      </div>
    </div>
  {:else}
    <div class="h-full flex items-center justify-center">
      <p class="text-sm text-neutral-400">No data available</p>
    </div>
  {/if}
</div>

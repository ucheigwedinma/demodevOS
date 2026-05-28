<script lang="ts">
  import { LayerCake, Svg, Html } from "layercake";
  import { scaleTime } from "d3-scale";
  import AxisX from "./AxisX.svelte";
  import AxisY from "./AxisY.svelte";
  import Tooltip from "./Tooltip.svelte";
  import AreaPath from "./AreaPath.svelte";

  let {
    data,
    xKey = "x",
    yKey = "y",
    formatX = (d: unknown) => String(d),
    formatY = (d: unknown) => String(d),
    color = "#6366f1",
    height = 280,
  }: {
    data: Record<string, any>[];
    xKey?: string;
    yKey?: string;
    formatX?: (d: unknown) => string;
    formatY?: (d: unknown) => string;
    color?: string;
    height?: number;
  } = $props();
</script>

<div style="height: {height}px;">
  {#if data.length > 0}
    <LayerCake
      {data}
      x={xKey}
      y={yKey}
      xScale={scaleTime()}
      yNice={true}
      padding={{ top: 16, right: 16, bottom: 28, left: 56 }}
    >
      <Svg>
        <AxisX formatTick={formatX} />
        <AxisY formatTick={formatY} />
        <AreaPath {color} />
      </Svg>
      <Html>
        <Tooltip {xKey} {yKey} formatTitle={formatX} formatValue={formatY} />
      </Html>
    </LayerCake>
  {:else}
    <div class="h-full flex items-center justify-center">
      <p class="text-sm text-neutral-400">No data available</p>
    </div>
  {/if}
</div>

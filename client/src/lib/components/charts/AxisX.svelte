<script lang="ts">
  import { getContext } from "svelte";

  let { formatTick = (d: unknown) => String(d), tickCount = 6 } = $props();

  const { width, height, xScale, padding } = getContext("LayerCake") as Record<string, any>;
</script>

{#each $xScale.ticks ? $xScale.ticks(tickCount) : $xScale.domain() as tick}
  {@const x = $xScale(tick)}
  <g transform="translate({x}, {$height})">
    <line y1={0} y2={5} stroke="#d4d4d4" stroke-width="1" />
    <text
      y={18}
      text-anchor="middle"
      class="text-[10px] fill-neutral-400"
      font-family="inherit"
    >{formatTick(tick)}</text>
  </g>
{/each}
<line
  x1={0} y1={$height}
  x2={$width} y2={$height}
  stroke="#e5e5e5" stroke-width="1"
/>

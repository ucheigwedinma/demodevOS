<script lang="ts">
  import { getContext } from "svelte";

  let { formatTick = (d: unknown) => String(d), tickCount = 5 } = $props();

  const { height, yScale, width } = getContext("LayerCake") as Record<string, any>;
</script>

{#each $yScale.ticks ? $yScale.ticks(tickCount) : $yScale.domain() as tick}
  {@const y = $yScale(tick)}
  <g transform="translate(0, {y})">
    <line x1={0} x2={$width} stroke="#f5f5f5" stroke-width="1" />
    <text
      x={-8}
      dy="0.32em"
      text-anchor="end"
      class="text-[10px] fill-neutral-400"
      font-family="inherit"
    >{formatTick(tick)}</text>
  </g>
{/each}

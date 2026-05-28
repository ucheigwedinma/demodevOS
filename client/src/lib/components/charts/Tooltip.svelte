<script lang="ts">
  import { getContext } from "svelte";

  let {
    formatTitle = (d: unknown) => String(d),
    formatValue = (d: unknown) => String(d),
    xKey = "x",
    yKey = "y",
  } = $props();

  const { data, xGet, yGet, width, height } = getContext("LayerCake") as Record<string, any>;

  let mouseX = $state(0);
  let mouseY = $state(0);
  let visible = $state(false);
  let closest = $state<Record<string, any> | null>(null);

  function handleMouseMove(e: MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    mouseX = e.clientX - rect.left;
    mouseY = e.clientY - rect.top;
    visible = true;

    // Find closest data point by x position
    let minDist = Infinity;
    for (const d of $data) {
      const dx = Math.abs($xGet(d) - mouseX);
      if (dx < minDist) {
        minDist = dx;
        closest = d;
      }
    }
  }

  function handleMouseLeave() {
    visible = false;
    closest = null;
  }

  const tooltipLeft = $derived(
    closest ? Math.min($xGet(closest), $width - 140) : 0
  );
  const tooltipTop = $derived(
    closest ? Math.max($yGet(closest) - 48, 0) : 0
  );
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="absolute inset-0"
  onmousemove={handleMouseMove}
  onmouseleave={handleMouseLeave}
>
  {#if visible && closest}
    <!-- Vertical guide line -->
    <div
      class="absolute top-0 w-px bg-neutral-300 pointer-events-none"
      style="left: {$xGet(closest)}px; height: {$height}px;"
    ></div>

    <!-- Tooltip box -->
    <div
      class="absolute bg-neutral-900 text-white text-xs rounded-lg px-3 py-2 pointer-events-none shadow-lg whitespace-nowrap"
      style="left: {tooltipLeft + 8}px; top: {tooltipTop}px;"
    >
      <p class="text-neutral-400">{formatTitle(closest[xKey])}</p>
      <p class="font-semibold">{formatValue(closest[yKey])}</p>
    </div>

    <!-- Dot on data point -->
    <div
      class="absolute w-3 h-3 rounded-full bg-indigo-500 border-2 border-white shadow pointer-events-none"
      style="left: {$xGet(closest) - 6}px; top: {$yGet(closest) - 6}px;"
    ></div>
  {/if}
</div>

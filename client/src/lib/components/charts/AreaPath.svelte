<script lang="ts">
  import { getContext } from "svelte";
  import { area, line, curveMonotoneX } from "d3-shape";

  let { color = "#6366f1" } = $props();

  const { data, xGet, yGet, height } = getContext("LayerCake") as Record<string, any>;

  const areaPath = $derived.by(() => {
    const gen = area<Record<string, any>>()
      .x((d) => $xGet(d))
      .y0($height)
      .y1((d) => $yGet(d))
      .curve(curveMonotoneX);
    return gen($data) ?? "";
  });

  const linePath = $derived.by(() => {
    const gen = line<Record<string, any>>()
      .x((d) => $xGet(d))
      .y((d) => $yGet(d))
      .curve(curveMonotoneX);
    return gen($data) ?? "";
  });
</script>

<path d={areaPath} fill={color} fill-opacity="0.12" />
<path d={linePath} fill="none" stroke={color} stroke-width="2" />

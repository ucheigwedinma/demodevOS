<script lang="ts">
  import { onMount } from "svelte";
  import maplibregl from "maplibre-gl";
  import "maplibre-gl/dist/maplibre-gl.css";

  let { latitude, longitude }: { latitude: number; longitude: number } = $props();

  let container: HTMLDivElement;
  let map: maplibregl.Map | null = null;

  const key = import.meta.env.VITE_MAPTILER_KEY;

  onMount(() => {
    map = new maplibregl.Map({
      container,
      style: `https://api.maptiler.com/maps/streets-v2/style.json?key=${key}`,
      center: [longitude, latitude],
      zoom: 15,
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");

    new maplibregl.Marker({ color: "#171717" })
      .setLngLat([longitude, latitude])
      .addTo(map);

    return () => {
      map?.remove();
      map = null;
    };
  });
</script>

<div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
  <div bind:this={container} class="h-[300px] w-full"></div>
  <div class="px-4 py-2.5 border-t border-neutral-100 flex items-center justify-between">
    <span class="text-xs text-neutral-400">GPS Coordinates</span>
    <span class="text-xs text-neutral-500 tabular-nums">{latitude}, {longitude}</span>
  </div>
</div>

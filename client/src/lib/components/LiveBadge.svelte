<script lang="ts">
  import { ws } from "$lib/stores/websocket.svelte";

  let {
    refreshing = false,
  }: {
    refreshing?: boolean;
  } = $props();
</script>

{#if ws.connected}
  <span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5">
    <span class="h-1.5 w-1.5 rounded-full {refreshing ? 'bg-amber-500 animate-pulse' : 'bg-emerald-500 animate-pulse'}"></span>
    <span class="text-[9px] font-semibold {refreshing ? 'text-amber-700' : 'text-emerald-700'}">
      {refreshing ? "Updating" : "Live"}
    </span>
  </span>
{/if}

<script lang="ts">
  import { fly } from "svelte/transition";

  let {
    title,
    loading = false,
    onclose,
    children,
  }: {
    title: string;
    loading?: boolean;
    onclose: () => void;
    children: import("svelte").Snippet;
  } = $props();
</script>

<div
  class="mt-4 rounded-2xl border border-neutral-200 bg-white shadow-sm overflow-hidden"
  transition:fly={{ y: 12, duration: 200 }}
>
  <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-3">
    <h3 class="text-sm font-semibold text-neutral-900">{title}</h3>
    <button
      onclick={onclose}
      class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
      aria-label="Close drilldown"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>

  <div class="px-5 py-4">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else}
      {@render children()}
    {/if}
  </div>
</div>

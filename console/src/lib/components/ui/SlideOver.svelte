<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    open = false,
    onclose,
    title,
    maxWidth = "max-w-lg",
    children,
  }: {
    open: boolean;
    onclose: () => void;
    title: string;
    maxWidth?: string;
    children: Snippet;
  } = $props();

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm cursor-default"
      onclick={onclose}
      tabindex="-1"
      aria-label="Close"
    ></button>

    <div
      class="relative bg-white {maxWidth} w-full h-full flex flex-col shadow-2xl slide-in"
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
        <h2 class="text-lg font-semibold text-neutral-900">{title}</h2>
        <button
          onclick={onclose}
          class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-6 py-5">
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  .slide-in {
    animation: slideIn 0.25s ease-out;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
</style>

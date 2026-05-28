<script lang="ts">
  import type { Snippet } from "svelte";
  import EditingAwareness from "$lib/components/EditingAwareness.svelte";

  let {
    open = false,
    title = "",
    subtitle = "",
    width = "max-w-md" as string,
    model = "",
    recordId = null as number | string | null,
    onclose,
    actions,
    badges,
    children,
  }: {
    open: boolean;
    title: string;
    subtitle?: string;
    width?: string;
    model?: string;
    recordId?: number | string | null;
    onclose: () => void;
    actions?: Snippet;
    badges?: Snippet;
    children: Snippet;
  } = $props();
</script>

{#if open}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={onclose} aria-label="Close drawer"></button>
    <div class="relative w-full {width} bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <!-- Dark header -->
      <div class="flex items-center justify-between px-6 py-5 bg-linear-to-br from-neutral-900 to-neutral-800">
        <div class="min-w-0 flex-1">
          <h2 class="text-base font-semibold text-white truncate">{title}</h2>
          {#if subtitle}
            <p class="text-xs text-neutral-400 mt-0.5 truncate">{subtitle}</p>
          {/if}
          {#if badges}
            <div class="flex items-center gap-1.5 mt-2">
              {@render badges()}
            </div>
          {/if}
        </div>
        <div class="flex items-center gap-2 ml-4 shrink-0">
          {#if actions}
            {@render actions()}
          {/if}
          <button
            onclick={onclose}
            class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-white transition-colors"
            aria-label="Close"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Editing awareness banner -->
      {#if model && recordId != null}
        <div class="px-4 pt-3">
          <EditingAwareness {model} {recordId} />
        </div>
      {/if}

      <!-- Body -->
      <div class="flex-1 overflow-y-auto">
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
</style>

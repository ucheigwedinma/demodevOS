<script lang="ts">
  import type { Snippet } from "svelte";
  import { fly, fade, scale } from "svelte/transition";

  interface FloatingActionOption {
    label: string;
    onclick: () => void;
    icon?: Snippet;
  }

  let {
    options,
    class: className = "",
  }: {
    options: FloatingActionOption[];
    class?: string;
  } = $props();

  let isOpen = $state(false);

  function toggle() {
    isOpen = !isOpen;
  }

  function select(option: FloatingActionOption) {
    isOpen = false;
    option.onclick();
  }
</script>

<div class="fixed bottom-8 right-8 {className}">
  {#if isOpen}
    <!-- Backdrop -->
    <button
      class="fixed inset-0 z-40 cursor-default"
      onclick={() => (isOpen = false)}
      tabindex="-1"
      aria-label="Close menu"
      transition:fade={{ duration: 150 }}
    ></button>
  {/if}

  <!-- Options -->
  {#if isOpen}
    <div class="absolute bottom-14 right-0 mb-1 z-50 flex flex-col items-end gap-2">
      {#each options as option, i}
        <button
          class="flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-neutral-900/60 hover:bg-neutral-900/85 shadow-[0_0_20px_rgba(0,0,0,0.2)] rounded-xl backdrop-blur-sm transition-colors whitespace-nowrap"
          onclick={() => select(option)}
          in:fly={{ x: 20, duration: 250, delay: i * 50 }}
          out:fly={{ x: 20, duration: 150 }}
        >
          {#if option.icon}
            {@render option.icon()}
          {/if}
          <span>{option.label}</span>
        </button>
      {/each}
    </div>
  {/if}

  <!-- FAB trigger -->
  <button
    class="relative z-50 w-10 h-10 rounded-full bg-neutral-900/60 hover:bg-neutral-900/85 shadow-[0_0_20px_rgba(0,0,0,0.2)] text-white flex items-center justify-center transition-all"
    onclick={toggle}
    aria-label={isOpen ? "Close menu" : "Open menu"}
  >
    <svg
      class="w-5 h-5 transition-transform duration-200 {isOpen ? 'rotate-45' : ''}"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      stroke-width="2"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  </button>
</div>
